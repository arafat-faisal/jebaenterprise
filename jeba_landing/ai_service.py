import google.generativeai as genai
import os
import json
from django.conf import settings

def generate_landing_copy(product_name, product_description, price, currency="BDT"):
    """
    Generates tailored landing page content using Gemini Pro.
    Returns a dictionary suitable for populating Campaign variants.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', os.getenv('GEMINI_API_KEY'))
    
    if not api_key:
        return None, "Missing GEMINI_API_KEY in settings or environment."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        Act as a world-class conversion copywriter for the Bangladeshi market. 
        Product: {product_name}
        Description: {product_description}
        Price: {currency} {price}
        
        Generate a COMPLETE high-conversion landing page structure in valid JSON.
        Target Audience: value-conscious Bangladeshi buyers.
        Tone: Urgent, Trustworthy, Emotional.
        
        Required JSON Structure:
        {{
            "hero": {{
                "headline": "Short, punchy 5-7 word hook (English)",
                "subheadline": "Persuasive 15-20 word supporting text"
            }},
            "features": [
                {{ "title": "Feature 1", "text": "Benefit description", "icon": "Use a relevant emoji" }},
                {{ "title": "Feature 2", "text": "Benefit description", "icon": "emoji" }},
                {{ "title": "Feature 3", "text": "Benefit description", "icon": "emoji" }}
            ],
            "testimonials": [
                {{ "name": "Bangladeshi Name", "text": "Short glowing review.", "rating": 5 }}
            ],
            "faq": [
                {{ "question": "Common objection?", "answer": "Reassuring answer." }}
            ],
            "fomo": {{
                "text": "Only X units left at this price!"
            }}
        }}
        """
        
        response = model.generate_content(prompt)
        # Clean potential markdown fences
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text), None
        
    except Exception as e:
        return None, f"AI Error: {str(e)}"
