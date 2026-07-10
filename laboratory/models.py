from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from clinical.models import Hospitalization, Patient
from core.models import TimeStampedModel


class LabTestCatalog(TimeStampedModel):
    code = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=200)
    prix = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delai_heures = models.PositiveSmallIntegerField(default=24)

    def __str__(self):
        return f'{self.code} — {self.libelle}'


class LabOrder(TimeStampedModel):
    """
    Workflow LIS :
    Commande → Prélèvement → Affectation → Saisie → Validation → Publication
    """

    class Statut(models.TextChoices):
        COMMANDE = 'COMMANDE', 'Commandé'
        PRELEVEMENT = 'PRELEVEMENT', 'Prélèvement effectué'
        AFFECTATION = 'AFFECTATION', 'Affecté au labo'
        SAISIE = 'SAISIE', 'Résultats saisis'
        VALIDATION = 'VALIDATION', 'En attente validation'
        PUBLIE = 'PUBLIE', 'Publié'
        ANNULE = 'ANNULE', 'Annulé'

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='examens_lab')
    hospitalisation = models.ForeignKey(
        Hospitalization, on_delete=models.SET_NULL, null=True, blank=True, related_name='examens_lab',
    )
    medecin_prescripteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='prescriptions_lab',
        limit_choices_to={'role': 'MEDECIN'},
    )
    examen = models.ForeignKey(LabTestCatalog, on_delete=models.PROTECT)
    statut = models.CharField(max_length=15, choices=Statut.choices, default=Statut.COMMANDE)
    date_commande = models.DateTimeField(auto_now_add=True)
    date_prelevement = models.DateTimeField(null=True, blank=True)
    technicien = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prelevements_lab',
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_commande']
        verbose_name = 'Commande laboratoire'


class LabResult(TimeStampedModel):
    commande = models.OneToOneField(LabOrder, on_delete=models.CASCADE, related_name='resultat')
    valeur = models.TextField()
    unite = models.CharField(max_length=30, blank=True)
    valeur_reference = models.CharField(max_length=100, blank=True)
    commentaire = models.TextField(blank=True)
    saisi_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='saisies_lab',
    )
    valide = models.BooleanField(default=False)
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validations_lab',
        limit_choices_to={'role': 'BIOLOGISTE'},
    )
    date_validation = models.DateTimeField(null=True, blank=True)
    rapport_pdf = models.FileField(upload_to='rapports_lab/%Y/%m/', blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old = LabResult.objects.filter(pk=self.pk).values('valide').first()
            if old and old['valide']:
                raise ValidationError('Résultat validé = immuable.')
        super().save(*args, **kwargs)
        if self.valide and self.commande.statut != LabOrder.Statut.PUBLIE:
            self.commande.statut = LabOrder.Statut.PUBLIE
            self.commande.save(update_fields=['statut', 'updated_at'])


class LabResultAudit(TimeStampedModel):
    """Audit trail obligatoire avant validation."""
    resultat = models.ForeignKey(LabResult, on_delete=models.CASCADE, related_name='audits')
    modifie_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    ancienne_valeur = models.TextField()
    nouvelle_valeur = models.TextField()
    raison = models.TextField(blank=True)
