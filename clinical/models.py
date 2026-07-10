from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core.models import OptimisticLockModel, TimeStampedModel


class Patient(TimeStampedModel, OptimisticLockModel):
  """Dossier patient — isolation stricte des données."""
  user = models.OneToOneField(
      settings.AUTH_USER_MODEL,
      on_delete=models.SET_NULL,
      null=True,
      blank=True,
      related_name='patient_profile',
  )
  numero_dossier = models.CharField(max_length=20, unique=True, db_index=True)
  nom = models.CharField(max_length=100)
  prenom = models.CharField(max_length=100)
  date_naissance = models.DateField()
  sexe = models.CharField(max_length=1, choices=[('M', 'Masculin'), ('F', 'Féminin'), ('A', 'Autre')])
  telephone = models.CharField(max_length=20, blank=True)
  email = models.EmailField(blank=True)
  adresse = models.TextField(blank=True)
  groupe_sanguin = models.CharField(max_length=5, blank=True)
  consentement_traitement = models.BooleanField(default=False)
  consentement_date = models.DateTimeField(null=True, blank=True)
  archived = models.BooleanField(default=False)

  class Meta:
      ordering = ['nom', 'prenom']
      verbose_name = 'Patient'
      verbose_name_plural = 'Patients'

  def __str__(self):
      return f'{self.nom} {self.prenom} ({self.numero_dossier})'

  @property
  def nom_complet(self):
      return f'{self.prenom} {self.nom}'


class Building(TimeStampedModel):
  nom = models.CharField(max_length=100)
  adresse = models.TextField(blank=True)

  def __str__(self):
      return self.nom


class HospitalService(TimeStampedModel):
  building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='services')
  nom = models.CharField(max_length=100)
  code = models.CharField(max_length=10, unique=True)

  class Meta:
      verbose_name = 'Service hospitalier'
      verbose_name_plural = 'Services hospitaliers'

  def __str__(self):
      return f'{self.code} — {self.nom}'


class Room(TimeStampedModel):
  service = models.ForeignKey(HospitalService, on_delete=models.CASCADE, related_name='chambres')
  numero = models.CharField(max_length=20)
  capacite = models.PositiveSmallIntegerField(default=1)

  class Meta:
      unique_together = ['service', 'numero']
      verbose_name = 'Chambre'

  def __str__(self):
      return f'Chambre {self.numero} — {self.service}'


class Bed(TimeStampedModel):
  """Règle métier : 1 lit = 1 patient maximum."""
  chambre = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='lits')
  numero_lit = models.CharField(max_length=10)
  est_disponible = models.BooleanField(default=True)

  class Meta:
      unique_together = ['chambre', 'numero_lit']
      verbose_name = 'Lit'

  def __str__(self):
      return f'Lit {self.numero_lit} — {self.chambre}'


class Hospitalization(TimeStampedModel, OptimisticLockModel):
  class Statut(models.TextChoices):
      ACTIVE = 'ACTIVE', 'En cours'
      SORTIE = 'SORTIE', 'Sorti(e)'
      TRANSFERT = 'TRANSFERT', 'Transfert en cours'

  patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='hospitalisations')
  lit = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='hospitalisations')
  medecin_referent = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.PROTECT,
      related_name='hospitalisations_referent',
      limit_choices_to={'role': 'MEDECIN'},
  )
  date_entree = models.DateTimeField()
  date_sortie_prevue = models.DateField()
  date_sortie_effective = models.DateTimeField(null=True, blank=True)
  statut = models.CharField(max_length=15, choices=Statut.choices, default=Statut.ACTIVE)
  motif_admission = models.TextField()
  notes = models.TextField(blank=True)

  class Meta:
      ordering = ['-date_entree']
      verbose_name = 'Hospitalisation'

  def clean(self):
      if not self.lit.est_disponible and self.statut == self.Statut.ACTIVE:
          active = Hospitalization.objects.filter(
              lit=self.lit, statut=self.Statut.ACTIVE,
          ).exclude(pk=self.pk)
          if active.exists():
              raise ValidationError('Ce lit est déjà occupé.')

  def save(self, *args, **kwargs):
      self.full_clean()
      super().save(*args, **kwargs)
      if self.statut == self.Statut.ACTIVE:
          self.lit.est_disponible = False
          self.lit.save(update_fields=['est_disponible', 'updated_at'])
      elif self.statut == self.Statut.SORTIE:
          self.lit.est_disponible = True
          self.lit.save(update_fields=['est_disponible', 'updated_at'])


class Consultation(TimeStampedModel, OptimisticLockModel):
  hospitalisation = models.ForeignKey(
      Hospitalization,
      on_delete=models.CASCADE,
      related_name='consultations',
      null=True,
      blank=True,
  )
  patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='consultations')
  medecin = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.PROTECT,
      related_name='consultations',
      limit_choices_to={'role': 'MEDECIN'},
  )
  date_consultation = models.DateTimeField(auto_now_add=True)
  diagnostic_cim10 = models.CharField(max_length=10, help_text='Code CIM-10')
  diagnostic_libelle = models.CharField(max_length=255)
  notes_cliniques = models.TextField(blank=True)
  validee = models.BooleanField(default=False)
  date_validation = models.DateTimeField(null=True, blank=True)

  class Meta:
      ordering = ['-date_consultation']


class Prescription(TimeStampedModel, OptimisticLockModel):
  consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='prescriptions')
  medicament_nom = models.CharField(max_length=200)
  posologie = models.CharField(max_length=255)
  duree_jours = models.PositiveSmallIntegerField()
  instructions = models.TextField(blank=True)
  validee = models.BooleanField(default=False)
  verrouillee = models.BooleanField(default=False)

  def save(self, *args, **kwargs):
      if self.pk:
          old = Prescription.objects.filter(pk=self.pk).values('verrouillee').first()
          if old and old['verrouillee']:
              raise ValidationError('Prescription verrouillée — modification impossible.')
      if self.validee:
          self.verrouillee = True
      super().save(*args, **kwargs)


class VitalSign(TimeStampedModel):
  hospitalisation = models.ForeignKey(Hospitalization, on_delete=models.CASCADE, related_name='constantes')
  infirmier = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.PROTECT,
      limit_choices_to={'role': 'INFIRMIER'},
  )
  temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
  tension_systolique = models.PositiveSmallIntegerField(null=True, blank=True)
  tension_diastolique = models.PositiveSmallIntegerField(null=True, blank=True)
  frequence_cardiaque = models.PositiveSmallIntegerField(null=True, blank=True)
  saturation_o2 = models.PositiveSmallIntegerField(null=True, blank=True)
  notes = models.TextField(blank=True)
  date_prise = models.DateTimeField(auto_now_add=True)

  class Meta:
      ordering = ['date_prise']


class NursingCare(TimeStampedModel):
  hospitalisation = models.ForeignKey(Hospitalization, on_delete=models.CASCADE, related_name='soins')
  infirmier = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.PROTECT,
      limit_choices_to={'role': 'INFIRMIER'},
  )
  prescription = models.ForeignKey(
      Prescription, on_delete=models.SET_NULL, null=True, blank=True, related_name='soins',
  )
  description = models.TextField()
  planifie_a = models.DateTimeField()
  realise_a = models.DateTimeField(null=True, blank=True)
  dose_omise = models.BooleanField(default=False)

  class Meta:
      ordering = ['planifie_a']
      verbose_name = 'Soin infirmier'


class MedicalDocument(TimeStampedModel):
  """Archivage documentaire sécurisé."""
  patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='documents')
  titre = models.CharField(max_length=200)
  fichier = models.FileField(upload_to='documents/%Y/%m/')
  mime_type = models.CharField(max_length=100)
  taille_octets = models.PositiveIntegerField()
  signe_electroniquement = models.BooleanField(default=False)
  uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

  class Meta:
      verbose_name = 'Document médical'


class Appointment(TimeStampedModel):
  """Prise de rendez-vous synchronisée aux disponibilités médecins."""
  class Statut(models.TextChoices):
      PLANIFIE = 'PLANIFIE', 'Planifié'
      CONFIRME = 'CONFIRME', 'Confirmé'
      ANNULE = 'ANNULE', 'Annulé'
      TERMINE = 'TERMINE', 'Terminé'

  patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='rendez_vous')
  medecin = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.PROTECT,
      related_name='rendez_vous_medecin',
      limit_choices_to={'role': 'MEDECIN'},
  )
  date_heure = models.DateTimeField()
  duree_minutes = models.PositiveSmallIntegerField(default=30)
  motif = models.TextField()
  statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.PLANIFIE)
  confirmation_envoyee = models.BooleanField(default=False)

  class Meta:
      ordering = ['date_heure']
      verbose_name = 'Rendez-vous'


class Conversation(TimeStampedModel):
  patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='conversations')
  medecin = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.PROTECT,
      related_name='conversations_medecin',
      limit_choices_to={'role': 'MEDECIN'},
  )
  sujet = models.CharField(max_length=200, blank=True)

  class Meta:
      verbose_name = 'Conversation'


class ChatMessage(TimeStampedModel):
  conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
  auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
  contenu = models.TextField()
  lu = models.BooleanField(default=False)

  class Meta:
      ordering = ['created_at']


class MedicationReminder(TimeStampedModel):
  """Rappels médicamenteux — observance thérapeutique."""
  patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='rappels_medicaments')
  prescription = models.ForeignKey(
      Prescription, on_delete=models.SET_NULL, null=True, blank=True, related_name='rappels',
  )
  medicament = models.CharField(max_length=200)
  heure_prise = models.TimeField()
  actif = models.BooleanField(default=True)
  derniere_notification = models.DateTimeField(null=True, blank=True)

  class Meta:
      verbose_name = 'Rappel médicament'


class PatientCardToken(TimeStampedModel):
    """Jeton QR pour accès public aux informations médicales complètes du patient."""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='cartes_qr')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    active = models.BooleanField(default=True)
    pdf_file = models.FileField(upload_to='cartes_patient/%Y/%m/', blank=True)

    class Meta:
        verbose_name = 'Carte patient QR'
        ordering = ['-created_at']
