from django.contrib import admin
from .models import AIPage, PageConversation, PageVersion

class PageVersionInline(admin.TabularInline):
    model = PageVersion
    extra = 0
    readonly_fields = ('created_at',)

class ConversationInline(admin.TabularInline):
    model = PageConversation
    extra = 0
    readonly_fields = ('created_at',)

@admin.register(AIPage)
class AIPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_published', 'updated_at')
    search_fields = ('title', 'slug')
    inlines = [ConversationInline, PageVersionInline]