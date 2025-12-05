import json
import logging
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from .models import Conversation, Message, AISuggestion, MessengerSettings
from .ai_agent import generate_ai_suggestions
from .utils import send_facebook_message

logger = logging.getLogger(__name__)

@csrf_exempt
def fb_webhook(request):
    if request.method == 'GET':
        verify_token = os.getenv('FB_VERIFY_TOKEN')
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        if mode and token:
            if mode == 'subscribe' and token == verify_token:
                return HttpResponse(challenge)
            else:
                return HttpResponse('Verification token mismatch', status=403)
        return HttpResponse('Jeba Messenger Webhook Active', status=200)

    elif request.method == 'POST':
        try:
            body = json.loads(request.body)
            if body.get('object') == 'page':
                for entry in body.get('entry', []):
                    messaging_events = entry.get('messaging', [])
                    for event in messaging_events:
                        sender_id = event.get('sender', {}).get('id')
                        message_data = event.get('message', {})
                        if sender_id and message_data:
                            handle_incoming_message(sender_id, message_data)
                return HttpResponse('EVENT_RECEIVED', status=200)
            else:
                return HttpResponse('Not a page event', status=404)
        except Exception as e:
            logger.error(f"Webhook Error: {e}")
            return HttpResponse('Internal Server Error', status=500)
    return HttpResponse('Method not allowed', status=405)

def handle_incoming_message(psid, message_data):
    text = message_data.get('text')
    attachments = message_data.get('attachments')
    mid = message_data.get('mid')
    
    if text or attachments:
        conversation, created = Conversation.objects.get_or_create(psid=psid)
        if not Message.objects.filter(fb_message_id=mid).exists():
            image_url = None
            if attachments and attachments[0]['type'] == 'image':
                image_url = attachments[0]['payload']['url']

            message = Message.objects.create(
                conversation=conversation,
                sender='user',
                text=text if text else "[Image Sent]",
                image_url=image_url,
                fb_message_id=mid
            )
            conversation.save()
            
            settings = MessengerSettings.load()
            if settings.enable_auto_ai:
                try:
                    # Auto mode always searches for now, unless we want to make it smart too
                    # For now, default auto behavior is fine
                    generate_ai_suggestions(message.id, search_db=True)
                except Exception as e:
                    print(f"AI Auto-Gen Error: {e}")

@staff_member_required
def chat_dashboard(request):
    conversations = Conversation.objects.all().order_by('-last_interaction')
    for conv in conversations:
        last_msg = conv.messages.last()
        conv.needs_reply = True if last_msg and last_msg.sender == 'user' else False

    active_conversation = None
    chat_messages = []
    suggestions = []
    
    settings = MessengerSettings.load()

    chat_id = request.GET.get('chat_id')
    if chat_id:
        active_conversation = get_object_or_404(Conversation, id=chat_id)
        chat_messages = active_conversation.messages.all().order_by('timestamp')
        last_msg = chat_messages.last()
        if last_msg and last_msg.sender == 'user':
            suggestions = last_msg.suggestions.all()

    context = {
        'conversations': conversations,
        'active_conversation': active_conversation,
        'chat_messages': chat_messages, 
        'suggestions': suggestions,
        'auto_ai_enabled': settings.enable_auto_ai
    }
    return render(request, 'jeba_messenger/dashboard.html', context)

@staff_member_required
def manual_ai_generate(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        conversation_id = data.get('conversation_id')
        custom_prompt = data.get('custom_prompt', '')
        use_global = data.get('use_global', False)
        language = data.get('language', 'bn')
        # READ THE TOGGLE STATE
        search_db = data.get('search_db', True)

        result_data = generate_ai_suggestions(
            conversation_id=conversation_id,
            custom_prompt=custom_prompt,
            use_global_context=use_global,
            language=language,
            search_db=search_db  # Pass to AI
        )
        return JsonResponse({'status': 'success', 'suggestions': result_data})
    return JsonResponse({'status': 'error'}, status=400)

@staff_member_required
def toggle_auto_ai(request):
    if request.method == 'POST':
        settings = MessengerSettings.load()
        data = json.loads(request.body)
        settings.enable_auto_ai = data.get('enabled', False)
        settings.save()
        return JsonResponse({'status': 'success', 'enabled': settings.enable_auto_ai})
    return JsonResponse({'status': 'error'}, status=400)

@staff_member_required
def send_reply(request):
    if request.method == 'POST':
        conversation_id = request.POST.get('conversation_id')
        text = request.POST.get('message_text')
        conversation = get_object_or_404(Conversation, id=conversation_id)
        success = send_facebook_message(conversation.psid, text)
        if success:
            Message.objects.create(
                conversation=conversation, sender='page', text=text,
                fb_message_id=f"sent_{request.user.id}_{os.urandom(4).hex()}"
            )
            conversation.save()
            return redirect(f'/messenger/dashboard/?chat_id={conversation.id}')
        else:
            return HttpResponse("Failed to send message to Facebook.", status=500)
    return redirect('/messenger/dashboard/')