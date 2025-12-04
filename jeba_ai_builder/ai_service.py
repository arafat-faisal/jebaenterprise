import google.generativeai as genai
from django.conf import settings
import json
import logging
import re
from PIL import Image

logger = logging.getLogger(__name__)

def configure_genai():
    """Configures the AI with the key from settings."""
    if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not found in settings.")
        return False
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return True

def clean_json_response(text):
    """
    Robustly extracts the JSON object from the AI response.
    Finds the first '{' and the last '}' to handle any conversational wrapper text.
    """
    try:
        # 1. Locate the outermost curly braces
        start_index = text.find('{')
        end_index = text.rfind('}')

        if start_index != -1 and end_index != -1:
            # Extract everything between the first { and last }
            possible_json = text[start_index : end_index + 1]
            return possible_json
        
        # Fallback: Return original if no braces found (will likely fail parsing, but clean)
        return text.strip()
        
    except Exception as e:
        logger.error(f"JSON Cleaning Error: {e}")
        return text

def generate_page_update(current_html, current_css, user_prompt, image_path=None, product_context=None):
    """
    Main function to Generate OR Update a page.
    """
    if not configure_genai():
        return None

    # 1. Define the Persona and Rules
    system_instruction = """
    You are an Expert Web Developer & UI Designer for 'Jeba Enterprise'.
    Your task is to write clean, responsive HTML/CSS using BOOTSTRAP 5.
    
    BRANDING GUIDELINES (Use these CSS Variables):
    - Primary Background: var(--bg-body) (Light Grey #F3F5F9)
    - Card Background: var(--bg-card) (White)
    - Primary Text: var(--text-main) (Dark #1A1C1E)
    - Accent Color: var(--accent-lime) (Lime #D4F759) -> USE FOR BUTTONS/HIGHLIGHTS
    - Font: 'Plus Jakarta Sans', sans-serif
    
    RULES:
    1. Output MUST be valid JSON with keys: "html", "css", "explanation".
    2. HTML must use Bootstrap 5 classes.
    3. IMPORTANT: For Buttons, use inline styles or custom classes using `var(--accent-lime)` and `var(--text-main)`.
    4. Do NOT include <html>, <head>, or <body> tags. Return only the INNER content.
    5. Ensure the design is modern, visually appealing, and responsive.
    6. If updating, PRESERVE existing content unless asked to change it.
    7. Escape all double quotes in HTML string (e.g. <div class=\\"row\\">).
    """

    # 2. Build the Input
    model_name = "gemini-2.5-flash" 
    
    inputs = [system_instruction]
    
    # --- NEW: Inject Product Data ---
    if product_context:
        inputs.append(f"""
        PRODUCT CONTEXT (Use this data for text, prices, and specs):
        {product_context}
        """)
    # --------------------------------
    
    if current_html:
        # CONTEXT: Modification Mode
        inputs.append(f"CURRENT HTML:\n{current_html}")
        inputs.append(f"CURRENT CSS:\n{current_css}")
        inputs.append(f"USER INSTRUCTION: Modify the code above to: {user_prompt}")
    else:
        # CONTEXT: Creation Mode
        inputs.append(f"USER INSTRUCTION: Create a new landing page: {user_prompt}")
    
    # 3. Handle Image Input (Vision)
    if image_path:
        try:
            img = Image.open(image_path)
            inputs.append("REFERENCE IMAGE: Use this image as a design reference for layout/colors.")
            inputs.append(img)
        except Exception as e:
            logger.error(f"Image load error: {e}")

    # 4. Prompt for specific JSON format
    inputs.append("""
    RETURN JSON ONLY:
    {
        "html": "",
        "css": "/* New/Updated CSS code here */",
        "explanation": "Briefly explain what you did."
    }
    """)

    # 5. Call AI (Same as before)
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            inputs,
            generation_config={"response_mime_type": "application/json"}
        )
        
        raw_text = clean_json_response(response.text)
        
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as json_err:
            logger.error(f"JSON Parse Failed. Raw Text: {raw_text[:200]}... Error: {json_err}")
            return {
                "html": current_html or "<div class='alert alert-warning'>AI Glitch: JSON Error. Try again.</div>",
                "css": current_css or "",
                "explanation": "I encountered a formatting error. Please try again."
            }

    except Exception as e:
        logger.error(f"AI Generation Critical Failure: {e}")
        return {
            "html": current_html or "<div class='alert alert-danger'>AI Service Unavailable</div>",
            "css": current_css or "",
            "explanation": f"System Error: {str(e)}"
        }