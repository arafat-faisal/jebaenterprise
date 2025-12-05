import os
import google.generativeai as genai
import json
import requests
from io import BytesIO
from PIL import Image
from django.db.models import Q, Case, When, Value, IntegerField, F
from django.conf import settings
from .models import Message, Conversation, AISuggestion
from jeba_inventory.models import Product 

# Configure Gemini
GENAI_API_KEY = os.getenv('GEMINI_API_KEY')
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)

def analyze_image_content(image_url):
    try:
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = """
        You are a product search engine. Analyze this image and extract 5-8 distinct search keywords.
        Focus on:
        1. The Item Name (e.g. Rack, Blender, Saree)
        2. Key Attributes (e.g. 5 Layer, Foldable, Digital, 1.5 Ton)
        3. Material/Color (e.g. Metal, Black, Cotton)
        
        Return ONLY the keywords separated by spaces.
        """
        result = model.generate_content([prompt, img])
        return result.text.strip()
    except Exception as e:
        print(f"👁️ Vision Error: {e}")
        return ""

def get_inventory_context(search_query):
    if not search_query: return "", []
    
    stop_words = {'the', 'is', 'are', 'do', 'you', 'have', 'what', 'price', 'of', 'in', 'for', 'to', 'a', 'an', 'available', 'can', 'show', 'me', 'sent', 'image', 'this', 'looking', 'product'}
    raw_words = search_query.split()
    keywords = [w for w in raw_words if w.lower() not in stop_words and (len(w) >= 2 or w.isdigit())]
    
    found_products_text = []
    found_products_data = []
    
    if keywords:
        score_expression = Value(0, output_field=IntegerField())
        or_query = Q()
        for k in keywords:
            or_query |= (Q(name__icontains=k) | Q(tags__name__icontains=k) | Q(ai_suggested_tags__icontains=k) | Q(short_description__icontains=k))
            score_expression = score_expression + Case(
                When(name__icontains=k, then=Value(5)),
                When(tags__name__icontains=k, then=Value(3)),
                When(ai_suggested_tags__icontains=k, then=Value(3)),
                When(short_description__icontains=k, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )

        products = Product.objects.filter(or_query).annotate(
            relevance_score=score_expression
        ).filter(relevance_score__gt=0).order_by('-relevance_score', '-id').distinct()[:8] 
        
        for p in products:
            status = "In Stock" if p.stock_quantity > 0 else "Out of Stock"
            found_products_text.append(f"- {p.name}: {p.selling_price} Tk | Stock: {p.stock_quantity}")
            img_url = "/static/placeholder.png"
            if hasattr(p, 'thumbnail') and p.thumbnail:
                img_url = p.thumbnail.url
            elif p.images.exists():
                img_url = p.images.first().image.url
            
            found_products_data.append({
                'id': p.id, 'name': p.name, 'price': float(p.selling_price), 
                'stock': p.stock_quantity, 'image': img_url, 'score': p.relevance_score
            })
            
    text_context = "\nINVENTORY MATCHES:\n" + "\n".join(found_products_text) if found_products_text else "\nNO DIRECT MATCHES.\n"
    return text_context, found_products_data

def generate_ai_suggestions(message_id=None, conversation_id=None, custom_prompt="", use_global_context=False, language="bn", search_db=True):
    try:
        if message_id:
            current_msg = Message.objects.get(id=message_id)
            conversation = current_msg.conversation
        elif conversation_id:
            conversation = Conversation.objects.get(id=conversation_id)
            current_msg = conversation.messages.last()
        else: return {'suggestions': [], 'candidates': []}

        # 1. Vision Analysis & Search Logic
        image_context = ""
        inventory_text = ""
        product_candidates = []

        # Only perform expensive search operations if the toggle is ON (search_db=True)
        if search_db:
            search_query_parts = []
            if custom_prompt: # Custom prompt takes priority for search
                search_query_parts.append(custom_prompt)
            elif current_msg and current_msg.text: # Otherwise use last message
                search_query_parts.append(current_msg.text)
            
            if current_msg and current_msg.image_url:
                description = analyze_image_content(current_msg.image_url)
                image_context = f"\n[USER SENT IMAGE]: The image search keywords are: {description}\n"
                search_query_parts.append(description)

            full_search_query = " ".join(search_query_parts)
            inventory_text, product_candidates = get_inventory_context(full_search_query)
        else:
            inventory_text = "\n[INVENTORY SEARCH DISABLED]: Respond conversationally. Do not hallucinate product prices.\n"

        # 2. History (Increased to 50 for full context)
        history_msgs = conversation.messages.order_by('-timestamp')[:50]
        history_msgs = reversed(history_msgs) 
        chat_context = "--- CHAT HISTORY ---\n"
        for msg in history_msgs:
            role = "Customer" if msg.sender == 'user' else "Agent"
            content = msg.text or "[Image]"
            if msg.image_url: content += " (Image)"
            chat_context += f"{role}: {content}\n"

        # 3. CRM Context
        crm_context = f"\n[CUSTOMER INFO]: Phone: {conversation.saved_phone or 'Unknown'}, Addr: {conversation.saved_address or 'Unknown'}, Mood: {conversation.sentiment}\n"

        # 4. Global Context
        global_context = ""
        if use_global_context:
            other_chats = Message.objects.exclude(conversation=conversation).order_by('-timestamp')[:10]
            if other_chats.exists():
                global_context = "\n--- OTHER CUSTOMER CHATS (Style Reference) ---\n"
                for msg in reversed(other_chats):
                     role = "Customer" if msg.sender == 'user' else "Agent"
                     global_context += f"({role}): {msg.text}\n"

        # 5. Master Prompt
        lang_instruction = "Bengali (Bangla)" if language == 'bn' else "English"
        
        system_instruction = f"""
        You are 'Jeba AI', the expert sales assistant.
        
        {global_context}
        {crm_context}
        {image_context}
        {inventory_text}
        {chat_context}
        
        INSTRUCTION: {custom_prompt if custom_prompt else "Identify product if matches found, update customer info, and reply."}
        
        TASK:
        1. Analyze SENTIMENT.
        2. Extract Customer Info (Phone/Address) if mentioned in HISTORY (even if old).
        3. Recommend best product match IF provided in INVENTORY MATCHES. If disabled, just chat.
        4. Generate 3 distinct responses (Professional, Friendly, Persuasive).
        
        LANGUAGE: {lang_instruction}
        
        OUTPUT FORMAT (Strict JSON):
        [
            {{
                "tone": "Professional", 
                "text": "...", 
                "sentiment": "hot", 
                "detected_product": "Name of best match (or None)",
                "order_data": {{"name": "", "phone": "", "address": ""}} 
            }}
        ]
        """

        model = genai.GenerativeModel('gemini-2.0-flash') 
        response = model.generate_content(system_instruction)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        suggestions_data = json.loads(clean_json)
        
        # Auto-Save CRM
        if suggestions_data and len(suggestions_data) > 0:
            first_sug = suggestions_data[0]
            if 'sentiment' in first_sug:
                conversation.sentiment = first_sug['sentiment'].lower()
            info = first_sug.get('order_data', {})
            if info.get('phone') and info['phone'] != "Unknown":
                conversation.saved_phone = info['phone']
            if info.get('address') and info['address'] != "Unknown":
                conversation.saved_address = info['address']
            conversation.save()
        
        return {
            'suggestions': suggestions_data,
            'candidates': product_candidates 
        }

    except Exception as e:
        print(f"❌ AI Error: {e}")
        return {'suggestions': [], 'candidates': []}