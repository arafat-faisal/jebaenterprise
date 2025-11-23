from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("Phone Number"))
    address = models.TextField(blank=True, null=True, verbose_name=_("Address"))

    class Meta:
        db_table = 'products_userprofile'

    def __str__(self):
        return f"Profile for {self.user.username}"

@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, **kwargs):
    UserProfile.objects.get_or_create(user=instance)