import logging
import google.generativeai as genai
from django.conf import settings
import PIL.Image
import json

logger = logging.getLogger(__name__)

# UPDATED: Matches the models found in your API Key
PREFERRED_MODELS = [
    'gemini-2.5-flash',          # Best Choice (Newest)
    'gemini-flash-latest',       # Safe Alias
    'gemini-2.0-flash',          # Reliable Fallback
    'gemini-2.0-flash-lite',     # Ultra-fast Fallback
    'models/gemini-2.5-flash',   # Explicit Path (Just in case)
]

def configure_genai():
    """Configures the AI with the key from settings."""
    if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not found in settings.")
        return False
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return True

def generate_product_seo(product_name, product_description, category_name):
    """
    Uses Google Gemini to generate SEO title and description.
    """
    if not configure_genai():
        return None, None

    prompt = f"""
    Act as an expert SEO Specialist.
    I have a product with these details:
    - Name: {product_name}
    - Category: {category_name}
    - Description: {product_description}

    Task:
    1. Write a Click-Worthy Meta Title (max 60 chars). It must include the product name.
    2. Write a Compelling Meta Description (max 160 chars). It should sell the benefits.

    Format your response exactly like this:
    Title: [Your Title Here]
    Description: [Your Description Here]
    """

    # Loop through the models you actually have access to
    for model_name in PREFERRED_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            # Parse the response
            title = ""
            description = ""
            
            lines = text.split('\n')
            for line in lines:
                # Robust parsing to handle bolding or slight format variations
                clean_line = line.replace('*', '').strip()
                if clean_line.startswith("Title:"):
                    title = clean_line.split(":", 1)[1].strip()
                elif clean_line.startswith("Description:"):
                    description = clean_line.split(":", 1)[1].strip()
            
            # If we successfully extracted data, return it
            if title or description:
                return title, description
                
        except Exception as e:
            # Log the specific model failure and continue to the next one
            logger.warning(f"Model {model_name} failed: {e}. Trying next...")
            continue

    logger.error("All AI models failed.")
    return None, None

# --- Standard Utility Functions (No changes needed below) ---

def clean_and_truncate(text, max_length):
    if not text: return ""
    text = str(text).strip().replace('<div>', '').replace('</div>', '').replace('<br>', ' ')
    if len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0] + '...'
    return text

def clean_json_text(text):
    """Removes markdown wrappers from JSON string."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def get_seo_data(request, obj=None, page_type=None):
    from .models import GlobalSEOSettings, StaticPageSEO
    
    defaults = GlobalSEOSettings.objects.first()
    data = {'seo_title': "Jeba Enterprise", 'seo_description': "Welcome", 'seo_image': ""}

    if defaults:
        if defaults.default_meta_title: data['seo_title'] = defaults.default_meta_title
        elif defaults.site_name: data['seo_title'] = defaults.site_name
        if defaults.default_meta_description: data['seo_description'] = defaults.default_meta_description
        if defaults.default_social_image: data['seo_image'] = defaults.default_social_image.url

    if page_type:
        try:
            static_seo = StaticPageSEO.objects.get(page_name=page_type)
            if static_seo.meta_title: data['seo_title'] = static_seo.meta_title
            if static_seo.meta_description: data['seo_description'] = static_seo.meta_description
        except StaticPageSEO.DoesNotExist: pass

    elif obj:
        manual_title = getattr(obj, 'meta_title', None)
        manual_desc = getattr(obj, 'meta_description', None)

        ai_title = getattr(obj, 'meta_title_ai', None)
        ai_desc = getattr(obj, 'meta_description_ai', None)

        final_title = manual_title if manual_title else (ai_title if ai_title else getattr(obj, 'name', ''))
        
        content_desc = getattr(obj, 'short_description', None) or getattr(obj, 'description', None)
        final_desc = manual_desc if manual_desc else (ai_desc if ai_desc else content_desc)

        if final_title: data['seo_title'] = clean_and_truncate(final_title, 60)
        if final_desc: data['seo_description'] = clean_and_truncate(final_desc, 160)
        
        image = getattr(obj, 'image', None) or getattr(obj, 'main_image', None)
        if image: data['seo_image'] = image.url

    return data


# def generate_product_content(product_name, current_desc, category_name, image_path=None):
#     """
#     Generates SEO-optimized Name and Description for the Bangladeshi Market.
#     Uses Image + Text if image_path is provided.
#     """
#     if not configure_genai():
#         return None, None, None, None

#     # 1. Prepare the Prompt for Bangladeshi Context
#     prompt_text = f"""
#     You are an expert E-Commerce Copywriter for the Bangladeshi market.
    
#     Product Context:
#     - Current Name: {product_name}
#     - Category: {category_name}
#     - Current Description: {current_desc}

#     Target Audience:
#     - Bangladeshi consumers.
#     - Tone: Professional, Trustworthy, yet Engaging.
#     - Language: English (but optimized for local understanding).

#     Task:
#     1. ANALYZE the product image (if provided) and details.
#     2. WRITE a 'Display Name': Catchy, clear, includes key features (Max 80 chars).
#     3. WRITE a 'Description': Persuasive, bullet points allowed, focuses on benefits (Max 500 chars).
#     4. WRITE a 'Meta Title': SEO optimized for Google Search (Max 60 chars).
#     5. WRITE a 'Meta Description': SEO optimized for clicks (Max 160 chars).

#     Format your response exactly like this:
#     DisplayName: [Your Name]
#     DisplayDescription: [Your Description]
#     MetaTitle: [Your Meta Title]
#     MetaDescription: [Your Meta Description]
#     """

#     # 2. Prepare Inputs (Multimodal)
#     inputs = [prompt_text]
#     if image_path:
#         try:
#             img = PIL.Image.open(image_path)
#             inputs.append(img)
#             logger.info(f"Attached image for analysis: {image_path}")
#         except Exception as e:
#             logger.warning(f"Could not load image at {image_path}: {e}")

#     # 3. Call AI
#     for model_name in PREFERRED_MODELS:
#         try:
#             model = genai.GenerativeModel(model_name)
#             response = model.generate_content(inputs)
#             text = response.text.strip()
            
#             # 4. Parse Response
#             d_name, d_desc, m_title, m_desc = "", "", "", ""
            
#             lines = text.split('\n')
#             for line in lines:
#                 clean = line.replace('*', '').strip()
#                 if clean.startswith("DisplayName:"):
#                     d_name = clean.split(":", 1)[1].strip()
#                 elif clean.startswith("DisplayDescription:"):
#                     d_desc = clean.split(":", 1)[1].strip()
#                 elif clean.startswith("MetaTitle:"):
#                     m_title = clean.split(":", 1)[1].strip()
#                 elif clean.startswith("MetaDescription:"):
#                     m_desc = clean.split(":", 1)[1].strip()
            
#             if d_name and d_desc:
#                 return d_name, d_desc, m_title, m_desc
                
#         except Exception as e:
#             logger.warning(f"Model {model_name} failed: {e}. Trying next...")
#             continue

#     return None, None, None, None

# def generate_product_content(product_name, current_desc, category_name, image_path=None):
#     """
#     Generates SEO content + HTML Description in JSON format.
#     """
#     if not configure_genai():
#         return None

#     # Prompt: Explicitly asks for JSON and HTML
#     prompt_text = f"""
#     Act as a Senior E-Commerce Copywriter & SEO Expert.
    
#     PRODUCT DETAILS:
#     - Name: {product_name}
#     - Category: {category_name}
#     - Raw Info: {current_desc}

#     TASK:
#     1. Verify the 'Raw Info'. Only use facts that are physically possible for this product. Ignore spammy/irrelevant text.
#     2. Write a 'display_name': Catchy, professional, max 80 chars.
#     3. Write a 'description': 
#        - MUST be valid HTML format (no <html> or <body> tags).
#        - Use <h3> for headings, <p> for intro, <ul>/<li> for key features.
#        - Highlight key benefits with <strong>.
#        - Max 600 chars.
#     4. Write 'meta_title' (60 chars) and 'meta_description' (160 chars) for Google.

#     OUTPUT FORMAT:
#     Return ONLY a valid JSON object like this:
#     {{
#         "display_name": "...",
#         "description": "<p>Intro...</p><ul><li>Feature 1</li>...</ul>",
#         "meta_title": "...",
#         "meta_description": "..."
#     }}
#     """

#     inputs = [prompt_text]
#     if image_path:
#         try:
#             img = PIL.Image.open(image_path)
#             inputs.append(img)
#         except Exception as e:
#             logger.warning(f"Image load failed: {e}")

#     for model_name in PREFERRED_MODELS:
#         try:
#             model = genai.GenerativeModel(model_name)
#             # Request JSON MIME type for stability
#             response = model.generate_content(
#                 inputs, 
#                 generation_config={"response_mime_type": "application/json"}
#             )
#             text = clean_json_text(response.text)
            
#             data = json.loads(text)
#             return data # Returns Dict {'display_name': '...', ...}

#         except Exception as e:
#             logger.warning(f"Model {model_name} failed: {e}")
#             continue

#     return None

# def generate_product_content(product_name, current_desc, category_name, image_path=None):
#     """
#     Generates Name, Short Desc, Long Desc (HTML), and SEO Meta.
#     """
#     if not configure_genai(): return None

#     prompt_text = f"""
#     Act as an E-Commerce Expert.
    
#     Product: {product_name}
#     Category: {category_name}
#     Raw Info: {current_desc}

#     TASK:
#     1. display_name: Catchy, standard e-commerce title (Max 80 chars).
#     2. short_description: 1-2 sentence summary, plain text or simple HTML (Max 250 chars).
#     3. description: Full sales copy in HTML (<p>, <ul>, <li>, <strong>). Max 600 chars.
#     4. meta_title: Google search title (Max 60 chars).
#     5. meta_description: Google search snippet (Max 160 chars).

#     OUTPUT JSON ONLY:
#     {{
#         "display_name": "...",
#         "short_description": "...",
#         "description": "<p>...</p>",
#         "meta_title": "...",
#         "meta_description": "..."
#     }}
#     """

#     inputs = [prompt_text]
#     if image_path:
#         try:
#             img = PIL.Image.open(image_path)
#             inputs.append(img)
#         except: pass

#     # Use the best available model
#     model_name = 'gemini-2.5-flash' 
    
#     try:
#         model = genai.GenerativeModel(model_name)
#         response = model.generate_content(inputs, generation_config={"response_mime_type": "application/json"})
#         return json.loads(clean_json_text(response.text))
#     except Exception as e:
#         return None


# def generate_product_content(product_name, current_desc, category_name, image_path=None):
#     """
#     Generates 'Amazon-Style' detailed content with SEO optimization.
#     """
#     if not configure_genai(): return None

#     prompt_text = f"""
#     Act as a Senior E-Commerce Copywriter & SEO Strategist.
    
#     PRODUCT CONTEXT:
#     - Name: {product_name}
#     - Category: {category_name}
#     - Raw Data: {current_desc}

#     TASK:
#     1. **Display Name:** Write a high-converting, keyword-rich title (Max 100 chars).
#     2. **Short Description:** A punchy 2-3 sentence summary/hook (HTML allowed).
#     3. **Long Description:** Write a comprehensive, persuasive sales page (Min 300 words).
#        - **Structure:**
#          - <h2>Catchy Headline</h2>: Hook the reader.
#          - <p>Engaging Introduction</p>: Focus on the problem this product solves.
#          - <h3>Key Features</h3>: Use <ul> and <li>. Each bullet must explain the BENEFIT, not just the feature.
#          - <h3>Technical Specifications</h3>: If raw data (volts, watts, size) exists, format it into a neat HTML <table> or list. DO NOT omit technical details (like Lumens, Battery Life).
#          - <p><strong>Perfect For:</strong></p>: List use cases (e.g., Vlogging, Home Decor).
#        - **Tone:** Professional, enthusiastic, and authoritative.
#        - **SEO:** naturally weave in relevant keywords for this category.
#     4. **Meta Tags:** Google-optimized Title (60 chars) and Description (160 chars).

#     OUTPUT JSON ONLY:
#     {{
#         "display_name": "...",
#         "short_description": "...",
#         "description": "...", 
#         "meta_title": "...",
#         "meta_description": "..."
#     }}
#     """

#     inputs = [prompt_text]
#     if image_path:
#         try:
#             img = PIL.Image.open(image_path)
#             inputs.append(img)
#         except Exception: pass

#     # Use the best available model
#     model_name = 'gemini-2.5-flash' 
    
#     for model_name in PREFERRED_MODELS:
#         try:
#             model = genai.GenerativeModel(model_name)
#             response = model.generate_content(
#                 inputs, 
#                 generation_config={"response_mime_type": "application/json"}
#             )
#             return json.loads(clean_json_text(response.text))
#         except Exception as e:
#             logger.warning(f"Model {model_name} failed: {e}")
#             continue

#     return None

def generate_product_content(product_name, current_desc, category_name, image_path=None):
    """
    Generates Clean, Beautiful, Retail-Ready content (JSON).
    """
    if not configure_genai(): return None

    prompt_text = f"""
    Act as a Senior E-Commerce Copywriter & Designer.
    
    PRODUCT CONTEXT:
    - Name: {product_name}
    - Category: {category_name}
    - Raw Info: {current_desc}

    STRICT RULES (The "Filter"):
    1. REMOVE any mention of competitor names (specifically "Rabeya Enterprise" or others).
    2. REMOVE wholesale restrictions (e.g., "MOQ", "Minimum Order", "Bulk Only"). Write for individual retail customers.
    3. REMOVE internal codes (e.g., "Code: 1347") from the description.

    DESIGN RULES (The "Beautifier"):
    1. Use EMOJIS to make headings pop (e.g., "✨ Key Features", "📏 Specifications").
    2. If there are technical specs (volts, size, etc.), format them as an HTML Table.
       - IMPORTANT: The table MUST have borders. Use exactly this style:
         <table style="width:100%; border-collapse:collapse; border:1px solid #ddd; margin:10px 0;">
           <tr style="background:#f9f9f9;"><td style="padding:8px; border:1px solid #ddd;"><strong>Feature</strong></td><td style="padding:8px; border:1px solid #ddd;"><strong>Value</strong></td></tr>
           ...
         </table>
    
    TASK:
    1. **display_name**: Catchy, clean, max 100 chars.
    2. **short_description**: 2-3 lines with emojis, summarizing the best benefit.
    3. **description**: Full sales page (HTML).
       - Start with a Hook.
       - Use <ul><li> with emojis for bullet points.
       - Use the Styled Table for specs.
       - Max 1000 chars.
    4. **meta_title**: SEO optimized (60 chars).
    5. **meta_description**: SEO optimized (160 chars).

    OUTPUT JSON ONLY:
    {{
        "display_name": "...",
        "short_description": "...",
        "description": "...", 
        "meta_title": "...",
        "meta_description": "..."
    }}
    """

    inputs = [prompt_text]
    if image_path:
        try:
            img = PIL.Image.open(image_path)
            inputs.append(img)
        except Exception: pass

    # Use the best available model
    model_name = 'gemini-2.5-flash' 
    
    for model_name in PREFERRED_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                inputs, 
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(clean_json_text(response.text))
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}")
            continue

    return None

def generate_category_and_tags(product_name, description, existing_categories_list):
    """
    Analyzes product to suggest the Best Category and relevant Tags.
    Allows AI to suggest NEW categories if existing ones don't fit.
    """
    if not configure_genai():
        return None, []

    categories_str = ", ".join(existing_categories_list)

    prompt = f"""
    Act as an E-Commerce Information Architect.
    
    Product: {product_name}
    Description: {description}
    
    Current Database Categories: [{categories_str}]
    
    Task:
    1. Analyze the product.
    2. Check if it fits PERFECTLY into one of the 'Current Database Categories'.
    3. IF it fits, use that name.
    4. IF it does NOT fit (e.g., it is a car part, pet food, or drill), INVENT a new, standard, professional category name (e.g., "Automotive", "Pet Supplies", "Tools & Hardware").
    5. Generate 5-8 relevant SEO Tags.
    
    Format exactly like this:
    Category: [Selected or New Category Name]
    Tags: [Tag1, Tag2, Tag3, Tag4, Tag5]
    """
    
    # Use Flash for speed
    model_name = 'gemini-2.5-flash' 
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        suggested_category = None
        suggested_tags = []
        
        lines = text.split('\n')
        for line in lines:
            clean = line.replace('*', '').strip()
            if clean.startswith("Category:"):
                suggested_category = clean.split(":", 1)[1].strip()
            elif clean.startswith("Tags:"):
                tags_str = clean.split(":", 1)[1].strip()
                suggested_tags = [t.strip() for t in tags_str.split(',') if t.strip()]
                
        return suggested_category, suggested_tags

    except Exception as e:
        logger.warning(f"Categorization failed: {e}")
        return None, []
    


def generate_bulk_analysis(products_data, existing_categories):
    """
    Processes a list of products in ONE API call.
    
    Args:
        products_data: List of dicts [{'id': 1, 'name': '...', 'description': '...'}]
        existing_categories: List of category names strings.
        
    Returns:
        Dict mapping Product ID -> {title, description, category, tags}
    """
    if not configure_genai():
        return {}

    # 1. Prepare Data for Prompt
    # We convert the list of products into a clean text block
    products_text = ""
    for p in products_data:
        products_text += f"ID: {p['id']} | Name: {p['name']} | Desc: {p['description'][:200]}...\n"

    categories_str = ", ".join(existing_categories)

    # 2. The Mega-Prompt
    prompt = f"""
    Act as an E-Commerce AI Architect.
    I will provide a list of products. For EACH product, you must generate:
    1. A SEO-friendly 'Meta Title' (Max 60 chars).
    2. A sales-focused 'Meta Description' (Max 160 chars).
    3. The Best 'Category' (Pick from the list below, or Invent a standard one if it doesn't fit).
    4. 5 relevant 'Tags' (Comma separated).

    Existing Categories: [{categories_str}]

    INPUT PRODUCTS:
    {products_text}

    OUTPUT FORMAT:
    You must return a valid JSON List of objects. Do not include markdown formatting (like ```json).
    Structure:
    [
        {{
            "id": 123,
            "title": "...",
            "description": "...",
            "category": "...",
            "tags": "tag1, tag2, tag3"
        }},
        ...
    ]
    """

    # 3. Call AI
    model_name = 'gemini-2.5-flash' # Flash is perfect for large context windows
    
    try:
        model = genai.GenerativeModel(model_name)
        # We ask for JSON response specifically
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        text = response.text.strip()
        
        # Clean potential markdown wrappers if the model ignores the config
        if text.startswith("```json"): text = text[7:]
        if text.endswith("```"): text = text[:-3]
        
        # 4. Parse JSON
        results_list = json.loads(text)
        
        # Convert to a Dict for easy lookup: {101: {...}, 102: {...}}
        processed_data = {item['id']: item for item in results_list}
        return processed_data

    except Exception as e:
        logger.error(f"Bulk Generation Failed: {e}")
        return {}