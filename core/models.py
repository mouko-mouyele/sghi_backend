from django.conf import settings
from django.db import models

from core.constants import HOSPITAL_EMERGENCY_PHONE


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OptimisticLockModel(models.Model):
    """Verrouillage optimiste pour dossiers critiques."""
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True


class AuditLog(models.Model):
    """Livre-journal immuable des actions sensibles."""

    class ActionType(models.TextChoices):
        CREATE = 'CREATE', 'Création'
        UPDATE = 'UPDATE', 'Modification'
        DELETE = 'DELETE', 'Suppression'
        LOGIN = 'LOGIN', 'Connexion'
        LOGOUT = 'LOGOUT', 'Déconnexion'
        VALIDATE = 'VALIDATE', 'Validation'
        PUBLISH = 'PUBLISH', 'Publication'
        ACCESS = 'ACCESS', 'Consultation'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=64, blank=True)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Journal d\'audit'
        verbose_name_plural = 'Journaux d\'audit'

    def __str__(self):
        return f'{self.action_type} — {self.model_name} #{self.object_id}'


class HospitalInfo(TimeStampedModel):
    """Informations pratiques de l'établissement (singleton)."""
    nom_etablissement = models.CharField(max_length=200, default='SGHL — Centre Hospitalier')
    adresse = models.TextField(blank=True)
    telephone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    horaires = models.TextField(blank=True, help_text='Horaires d\'ouverture')
    urgences_telephone = models.CharField(
        max_length=30,
        blank=True,
        default=HOSPITAL_EMERGENCY_PHONE,
    )
    description = models.TextField(blank=True)
    site_web = models.URLField(blank=True)
    latitude = models.FloatField(
        default=-4.2594,
        help_text='Latitude GPS (CHU Brazzaville par défaut)',
    )
    longitude = models.FloatField(
        default=15.2847,
        help_text='Longitude GPS (CHU Brazzaville par défaut)',
    )
    google_maps_query = models.CharField(
        max_length=300,
        blank=True,
        default='Centre Hospitalier Universitaire de Brazzaville, Congo',
        help_text='Requête Google Maps pour l\'embed et l\'itinéraire',
    )

    class Meta:
        verbose_name = 'Informations établissement'
        verbose_name_plural = 'Informations établissement'

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        if not obj.urgences_telephone or obj.urgences_telephone.strip() in (
            '',
            '+242 06 808 38 38',
            '+242 068083838',
        ):
            obj.urgences_telephone = HOSPITAL_EMERGENCY_PHONE
            obj.save(update_fields=['urgences_telephone', 'updated_at'])
        return obj
