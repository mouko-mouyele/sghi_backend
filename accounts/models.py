import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models import TimeStampedModel


class User(AbstractUser):
    """Utilisateur SGHL avec rôle RBAC."""

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrateur'
        MEDECIN = 'MEDECIN', 'Médecin'
        INFIRMIER = 'INFIRMIER', 'Infirmier(ère)'
        BIOLOGISTE = 'BIOLOGISTE', 'Biologiste'
        PHARMACIEN = 'PHARMACIEN', 'Pharmacien'
        COMPTABLE = 'COMPTABLE', 'Comptable'
        RECEPTIONNISTE = 'RECEPTIONNISTE', 'Réceptionniste'
        PATIENT = 'PATIENT', 'Patient'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RECEPTIONNISTE)
    phone = models.CharField(max_length=20, blank=True)
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=64, blank=True)
    specialty = models.CharField(max_length=120, blank=True, help_text='Spécialité médicale')
    is_active_staff = models.BooleanField(default=True)
    photo = models.ImageField(upload_to='staff_photos/%Y/%m/', blank=True)
    disponible_rdv = models.BooleanField(
        default=True,
        help_text='Médecin disponible pour consultations et RDV',
    )

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'


class RefreshToken(TimeStampedModel):
    """Refresh tokens JWT avec rotation."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refresh_tokens')
    token_hash = models.CharField(max_length=128, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    replaced_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replaces',
    )

    class Meta:
        ordering = ['-created_at']


class LoginJournal(models.Model):
    """Journal des connexions."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_journal')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    success = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Connexion'
        verbose_name_plural = 'Journal des connexions'


class LoginMfaChallenge(models.Model):
    """Code MFA connexion — stocké en base (fiable sans Redis)."""
    pending_token = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mfa_challenges')
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Défi MFA connexion'
