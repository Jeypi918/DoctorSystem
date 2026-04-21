from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, EmdDoctor

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()

# Optional: Auto-create EmdDoctor for new doctors (if needed)
@receiver(post_save, sender=User)
def create_doctor_profile(sender, instance, created, **kwargs):
    if created:
        try:
            profile = instance.userprofile
            if profile.role == 'doctor':
                EmdDoctor.objects.get_or_create(
                    user=instance,
                    defaults={
                        'doctors_name': f"{instance.last_name}, {instance.first_name}",
                        'specialization': 'General',
                        'active': True,
                        'tin': '',
                        'smsplusmobileno': '',
                    }
                )
        except UserProfile.DoesNotExist:
            pass

