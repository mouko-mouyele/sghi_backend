from django.conf import settings
from django.db import models

from clinical.models import Hospitalization, Patient
from core.models import TimeStampedModel


class Insurance(TimeStampedModel):
    nom = models.CharField(max_length=150)
    code = models.CharField(max_length=20, unique=True)
    taux_prise_en_charge = models.DecimalField(max_digits=5, decimal_places=2, default=80)
    contact = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.nom


class PatientInsurance(TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='assurances')
    assurance = models.ForeignKey(Insurance, on_delete=models.PROTECT)
    numero_police = models.CharField(max_length=50)
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)
    actif = models.BooleanField(default=True)


class Invoice(TimeStampedModel):
    class Statut(models.TextChoices):
        BROUILLON = 'BROUILLON', 'Brouillon'
        EMISE = 'EMISE', 'Émise'
        PARTIEL = 'PARTIEL', 'Paiement partiel'
        PAYEE = 'PAYEE', 'Payée'
        ANNULEE = 'ANNULEE', 'Annulée'

    numero = models.CharField(max_length=30, unique=True)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='factures')
    hospitalisation = models.ForeignKey(
        Hospitalization, on_delete=models.SET_NULL, null=True, blank=True,
    )
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.BROUILLON)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_assurance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_patient = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_paye = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pdf = models.FileField(upload_to='factures/%Y/%m/', blank=True)
    emise_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Facture'


class InvoiceLine(TimeStampedModel):
    class TypeLigne(models.TextChoices):
        ACTE = 'ACTE', 'Acte médical'
        NUITEE = 'NUITEE', 'Nuitée'
        EXAMEN = 'EXAMEN', 'Examen'
        MEDICAMENT = 'MEDICAMENT', 'Médicament'
        CONSOMMABLE = 'CONSOMMABLE', 'Consommable'

    facture = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lignes')
    type_ligne = models.CharField(max_length=15, choices=TypeLigne.choices)
    libelle = models.CharField(max_length=255)
    quantite = models.PositiveIntegerField(default=1)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    montant = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.montant = self.quantite * self.prix_unitaire
        super().save(*args, **kwargs)


class Payment(TimeStampedModel):
    class Statut(models.TextChoices):
        VALIDE = 'VALIDE', 'Validé'
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        REFUSE = 'REFUSE', 'Refusé'

    facture = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='paiements')
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    mode = models.CharField(max_length=30, choices=[
        ('ESPECES', 'Espèces'), ('CARTE', 'Carte'), ('VIREMENT', 'Virement'), ('CHEQUE', 'Chèque'),
        ('MTN_MOMO', 'MTN Mobile Money'), ('AIRTEL_MONEY', 'Airtel Money'),
    ])
    reference = models.CharField(max_length=100, blank=True)
    numero_mobile = models.CharField(max_length=20, blank=True)
    operateur = models.CharField(max_length=10, blank=True)
    statut = models.CharField(max_length=15, choices=Statut.choices, default=Statut.VALIDE)
    encaisse_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        limit_choices_to={'role__in': ['COMPTABLE', 'ADMIN', 'RECEPTIONNISTE']},
    )

    class Meta:
        verbose_name = 'Paiement'


class MobileMoneyTransaction(TimeStampedModel):
    """Flux USSD / confirmation téléphone — MTN MoMo & Airtel Money."""

    class Statut(models.TextChoices):
        INITIE = 'INITIE', 'Initié'
        EN_ATTENTE_CONFIRMATION = 'EN_ATTENTE_CONFIRMATION', 'En attente confirmation téléphone'
        CONFIRME = 'CONFIRME', 'Confirmé'
        REFUSE = 'REFUSE', 'Refusé'
        EXPIRE = 'EXPIRE', 'Expiré'

    facture = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='transactions_mobile')
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='paiements_mobile')
    numero_mobile = models.CharField(max_length=20)
    operateur = models.CharField(max_length=10)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=40, unique=True)
    statut = models.CharField(max_length=30, choices=Statut.choices, default=Statut.INITIE)
    message_operateur = models.TextField(blank=True)
    expire_le = models.DateTimeField()
    code_push = models.CharField(max_length=6, blank=True, help_text='Code SMS / notification opérateur')
    approuve_telephone_le = models.DateTimeField(null=True, blank=True)
    confirme_le = models.DateTimeField(null=True, blank=True)
    paiement = models.OneToOneField(
        Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='transaction_mobile',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Transaction Mobile Money'


class AccountingJournal(TimeStampedModel):
    """Journal comptable immuable."""
    reference = models.CharField(max_length=50, unique=True)
    type_operation = models.CharField(max_length=30)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    libelle = models.TextField()
    facture = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True)
    immutable = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Écriture comptable'
