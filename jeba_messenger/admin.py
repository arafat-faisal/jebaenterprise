from django.contrib import admin
from .models import Conversation, Message, AISuggestion

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'psid', 'status', 'last_interaction')
    list_filter = ('status', 'last_interaction')
    search_fields = ('first_name', 'last_name', 'psid')
    readonly_fields = ('psid',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'text_preview', 'timestamp')
    list_filter = ('sender', 'timestamp')
    search_fields = ('text',)

    def text_preview(self, obj):
        return obj.text[:50] + "..." if obj.text else ""

@admin.register(AISuggestion)
class AISuggestionAdmin(admin.ModelAdmin):
    list_display = ('tone', 'suggested_text_preview', 'created_at')
    
    def suggested_text_preview(self, obj):
        return obj.suggested_text[:50] + "..."