from django.conf import settings
from django.db import models

from clinical.models import Prescription
from core.models import TimeStampedModel


class Medication(TimeStampedModel):
    class Categorie(models.TextChoices):
        ANTALGIQUES = 'ANTALGIQUES', 'Antalgiques & antipyrétiques'
        ANTIBIOTIQUES = 'ANTIBIOTIQUES', 'Antibiotiques'
        CARDIO = 'CARDIO', 'Cardiovasculaire'
        DIABETE = 'DIABETE', 'Diabète'
        RESPIRATOIRE = 'RESPIRATOIRE', 'Respiratoire'
        GASTRO = 'GASTRO', 'Gastro-entérologie'
        DERMATO = 'DERMATO', 'Dermatologie'
        VITAMINES = 'VITAMINES', 'Vitamines & suppléments'
        OPHTALMO = 'OPHTALMO', 'Ophtalmologie'
        ANTISEPTIQUES = 'ANTISEPTIQUES', 'Antiseptiques & désinfection'
        MATERIEL = 'MATERIEL', 'Matériel médical'
        AUTRE = 'AUTRE', 'Autres'

    code = models.CharField(max_length=30, unique=True)
    nom = models.CharField(max_length=200)
    forme = models.CharField(max_length=50, blank=True)
    categorie = models.CharField(max_length=20, choices=Categorie.choices, default=Categorie.AUTRE)
    description = models.CharField(max_length=500, blank=True)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    seuil_alerte = models.PositiveIntegerField(default=10)

    def __str__(self):
        return self.nom

    @property
    def stock_total(self) -> int:
        return self.lots.aggregate(total=models.Sum('quantite'))['total'] or 0


class StockLot(TimeStampedModel):
    medicament = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='lots')
    numero_lot = models.CharField(max_length=50)
    quantite = models.PositiveIntegerField()
    date_peremption = models.DateField()
    emplacement = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ['medicament', 'numero_lot']
        verbose_name = 'Lot de stock'

    @property
    def en_rupture(self):
        return self.quantite <= self.medicament.seuil_alerte


class StockMovement(TimeStampedModel):
    class TypeMouvement(models.TextChoices):
        ENTREE = 'ENTREE', 'Entrée'
        SORTIE = 'SORTIE', 'Sortie'
        AJUSTEMENT = 'AJUSTEMENT', 'Ajustement'

    lot = models.ForeignKey(StockLot, on_delete=models.PROTECT, related_name='mouvements')
    type_mouvement = models.CharField(max_length=12, choices=TypeMouvement.choices)
    quantite = models.PositiveIntegerField()
    motif = models.CharField(max_length=255, blank=True)
    effectue_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Mouvement de stock'


class Dispensation(TimeStampedModel):
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT, related_name='dispensations')
    lot = models.ForeignKey(StockLot, on_delete=models.PROTECT)
    quantite = models.PositiveIntegerField()
    pharmacien = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        limit_choices_to={'role': 'PHARMACIEN'},
    )
    validee = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.validee and self.lot.quantite >= self.quantite:
            self.lot.quantite -= self.quantite
            self.lot.save(update_fields=['quantite', 'updated_at'])
            StockMovement.objects.create(
                lot=self.lot,
                type_mouvement=StockMovement.TypeMouvement.SORTIE,
                quantite=self.quantite,
                motif=f'Dispensation prescription #{self.prescription_id}',
                effectue_par=self.pharmacien,
            )


class PatientPharmacyRequest(TimeStampedModel):
    class Statut(models.TextChoices):
        SOUMISE = 'SOUMISE', 'Soumise'
        EN_PREPARATION = 'EN_PREPARATION', 'En préparation'
        PRETE = 'PRETE', 'Prête au retrait'
        RETIREE = 'RETIREE', 'Retirée'
        ANNULEE = 'ANNULEE', 'Annulée'

    patient = models.ForeignKey(
        'clinical.Patient',
        on_delete=models.CASCADE,
        related_name='demandes_pharmacie',
    )
    reference = models.CharField(max_length=30, unique=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.SOUMISE)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Demande pharmacie patient'

    @property
    def montant_total(self):
        return sum(l.sous_total for l in self.lignes.all())


class PatientPharmacyRequestLine(TimeStampedModel):
    demande = models.ForeignKey(
        PatientPharmacyRequest,
        on_delete=models.CASCADE,
        related_name='lignes',
    )
    medicament = models.ForeignKey(Medication, on_delete=models.PROTECT)
    quantite = models.PositiveIntegerField(default=1)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Ligne demande pharmacie'

    @property
    def sous_total(self):
        return self.prix_unitaire * self.quantite
