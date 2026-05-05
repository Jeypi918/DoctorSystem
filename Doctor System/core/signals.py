from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, EmdDoctor

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance, defaults={'role': 'doctor'})

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()

# Optional: Auto-create EmdDoctor for new doctors (if needed)
@receiver(post_save, sender=User)
def create_doctor_profile(sender, instance, created, **kwargs):
    # Disabled to avoid cycle with userprofile access before create_user_profile
    pass

