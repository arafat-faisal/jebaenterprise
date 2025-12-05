from django.db import models
from django.utils.translation import gettext_lazy as _


# --- NEW MODEL: SETTINGS ---
class MessengerSettings(models.Model):
    """
    Singleton model to store global messenger configurations.
    """
    enable_auto_ai = models.BooleanField(
        default=False, 
        verbose_name=_("Enable Auto AI Research"),
        help_text=_("If checked, AI will automatically generate suggestions for every new message. Uncheck to save API costs.")
    )

    def save(self, *args, **kwargs):
        self.pk = 1 # Force singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    class Meta:
        verbose_name = "Messenger Settings"
        verbose_name_plural = "Messenger Settings"
# ---------------------------

class Conversation(models.Model):
    """
    Represents a chat session with a specific Facebook user.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('blocked', 'Blocked'),
    ]
    
    # --- NEW CRM FIELDS (Memory) ---
    SENTIMENT_CHOICES = [
        ('hot', '🔥 Hot Lead'),
        ('warm', '😊 Interested'),
        ('cold', '❄️ Just Browsing'),
        ('angry', '😡 Complaint'),
        ('neutral', '😐 Neutral'),
    ]
    
    # Facebook User ID
    psid = models.CharField(max_length=255, unique=True, help_text="Facebook Page Scoped ID")
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    profile_pic = models.TextField(blank=True, null=True)
    
    # Permanent Customer Data (Auto-filled by AI)
    saved_phone = models.CharField(max_length=20, blank=True, null=True)
    saved_address = models.TextField(blank=True, null=True)
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, default='neutral')
    notes = models.TextField(blank=True, null=True, help_text="Admin private notes")
    # -------------------------------

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    last_interaction = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.psid})"

    class Meta:
        ordering = ['-last_interaction']


class Message(models.Model):
    """
    Individual messages sent or received.
    """
    SENDER_CHOICES = [
        ('user', 'Customer'),
        ('page', 'Jeba Admin'),
    ]

    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    text = models.TextField(blank=True, null=True)
    
    # CHANGED: Use TextField to handle long Facebook image URLs
    image_url = models.TextField(blank=True, null=True, help_text="URL of image sent by user")
    
    # Store Facebook's message ID to prevent duplicates
    fb_message_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender}: {self.text[:50]}..."
    
    class Meta:
        ordering = ['timestamp']


class AISuggestion(models.Model):
    """
    Stores AI-generated response suggestions for a specific incoming message.
    """
    trigger_message = models.ForeignKey(Message, related_name='suggestions', on_delete=models.CASCADE)
    suggested_text = models.TextField()
    tone = models.CharField(max_length=50, help_text="e.g., Professional, Friendly, Persuasive")
    language = models.CharField(max_length=10, default='bn', help_text="bn or en")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.tone}] {self.suggested_text[:50]}..."