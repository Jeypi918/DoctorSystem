from django.db import models

class EmdDoctorManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().only('pk_emddoctors', 'doctors_name', 'smsplusmobileno', 'tin', 'active', 'prctype', 'specialization')

    def all_doctors(self):
        return list(self.get_queryset())

