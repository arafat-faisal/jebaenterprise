import logging
import google.generativeai as genai
from django.conf import settings
import PIL.Image
import json

logger = logging.getLogger(__name__)

# Uses the same API Key from settings, but handles logic locally
def configure_genai():
    if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not found in settings.")
        return False
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return True

def clean_json_text(text):
    """Removes markdown wrappers from JSON string."""
    text = text.strip()
    if text.startswith("```json"): text = text[7:]
    elif text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    return text.strip()

def generate_landing_content(product_name, description, category, image_path=None):
    """
    Specialized AI for Landing Pages: Generates Hero, Story, Features, and FAQ.
    """
    if not configure_genai():
        return None

    # The "Conversion Copywriter" Prompt
    prompt = f"""
    Act as a Direct-Response Copywriter.
    
    PRODUCT: {product_name}
    CATEGORY: {category}
    DETAILS: {description}

    TASK: Write content for a high-converting landing page structure.
    
    1. HERO SECTION:
       - Headline: Punchy, benefit-driven (Max 12 words).
       - Subhead: Explains the "Why" (Max 25 words).
    
    2. STORY SECTION ("Why You Need This"):
       - Heading: Emotional hook.
       - Content: 2 paragraphs addressing the user's pain point and how this solves it. (HTML <p> tags allowed).

    3. FEATURES GRID (4 Items):
       - Extract 4 distinct selling points.
       - Icon: Suggest a free FontAwesome 6 class (e.g., 'fas fa-shipping-fast').
       - Title: Short benefit name.
       - Desc: 1-sentence explanation.

    4. FAQ (4 Items):
       - Write 4 common objections/questions and persuasive answers.

    OUTPUT JSON ONLY:
    {{
        "hero_headline": "...",
        "hero_subhead": "...",
        "story_heading": "...",
        "story_content": "<p>...</p>",
        "features": [
            {{"icon": "fas fa-...", "title": "...", "desc": "..."}},
            {{"icon": "fas fa-...", "title": "...", "desc": "..."}},
            {{"icon": "fas fa-...", "title": "...", "desc": "..."}},
            {{"icon": "fas fa-...", "title": "...", "desc": "..."}}
        ],
        "faqs": [
            {{"question": "...", "answer": "..."}},
            {{"question": "...", "answer": "..."}}
        ]
    }}
    """

    inputs = [prompt]
    if image_path:
        try:
            img = PIL.Image.open(image_path)
            inputs.append(img)
        except Exception as e:
            logger.warning(f"Image load failed: {e}")

    # Try reliable models
    models_to_try = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-pro']
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                inputs, 
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(clean_json_text(response.text))
        except Exception as e:
            logger.warning(f"Landing AI ({model_name}) failed: {e}")
            continue

    return None