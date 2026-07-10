from django.conf import settings
from django.db import models

from clinical.models import HospitalService
from core.models import TimeStampedModel


class ShiftSchedule(TimeStampedModel):
    """Planning de garde."""
    personnel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='gardes')
    service = models.ForeignKey(HospitalService, on_delete=models.CASCADE, related_name='plannings')
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    type_garde = models.CharField(max_length=30, choices=[
        ('JOUR', 'Jour'), ('NUIT', 'Nuit'), ('ASTREINTE', 'Astreinte'),
    ])
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['date_debut']
        verbose_name = 'Garde'
        verbose_name_plural = 'Plannings de garde'
