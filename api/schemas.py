from datetime import date, datetime, time
from decimal import Decimal
import re
from typing import Optional

from ninja import Schema
from pydantic import EmailStr, Field, field_validator

from api.validators import (
    only_digits,
    only_text,
    require_alnum,
    require_letters,
    require_phone,
)


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginIn(Schema):
    username: str
    password: str


class LoginResultOut(Schema):
    """Réponse login — tokens ou demande MFA par email."""
    requires_mfa: bool = False
    pending_token: str = ''
    mfa_sent_to: str = ''
    mfa_channel: str = ''
    mfa_hint: str = ''
    mfa_expires_in: int = 0
    mfa_expires_at: str = ''
    access_token: str = ''
    refresh_token: str = ''
    token_type: str = 'bearer'
    expires_in: int = 0
    role: str = ''
    user_id: int = 0
    username: str = ''
    email: str = ''
    first_name: str = ''
    last_name: str = ''
    mfa_dev_code: str = ''  # code affiché à l'écran si MFA_SHOW_CODE_ON_SCREEN=True
    mfa_email_error: str = ''  # erreur Brevo/SMTP si l'envoi a échoué


class LoginMfaVerifyIn(Schema):
    pending_token: str
    code: str

    @field_validator('pending_token', mode='before')
    @classmethod
    def strip_token(cls, v):
        return str(v or '').strip()

    @field_validator('code', mode='before')
    @classmethod
    def normalize_code(cls, v):
        if v is None:
            return ''
        if isinstance(v, (int, float)):
            v = str(int(v))
        digits = re.sub(r'\D', '', str(v).strip())
        if not digits or len(digits) > 6:
            return digits[:6] if len(digits) > 6 else ''
        return digits.zfill(6)


class MfaSetupOut(Schema):
    mfa_enabled: bool
    hospital_email: str = ''
    hospital_email_masked: str = ''
    message: str = ''


class EmailDiagnosticOut(Schema):
    configured: bool
    provider: str = 'none'
    brevo_key_set: bool = False
    brevo_key_valid: bool = False
    smtp_host: str
    smtp_port: int
    smtp_user: str
    from_email: str
    hospital_email: str
    password_set: bool
    render_smtp_blocked: bool = False
    message: str


class EmailTestOut(Schema):
    success: bool
    detail: str
    sent_to: str = ''


class TokenOut(Schema):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    role: str
    user_id: int
    username: str
    email: str
    first_name: str
    last_name: str


class RefreshIn(Schema):
    refresh_token: str


class LogoutIn(Schema):
    refresh_token: str


class UserOut(Schema):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    specialty: str = ''
    phone: str = ''
    photo_url: Optional[str] = None
    disponible_rdv: bool = True
    mfa_enabled: bool = False


class PatientRegisterIn(Schema):
    username: str
    password: str = Field(min_length=10)
    email: EmailStr
    nom: str
    prenom: str
    date_naissance: date
    sexe: str
    telephone: str = Field(min_length=8, max_length=25)
    adresse: str = ''
    consentement_traitement: bool = True

    @field_validator('username', mode='before')
    @classmethod
    def validate_username(cls, v):
        return require_alnum(v, 'Identifiant')

    @field_validator('nom', 'prenom', mode='before')
    @classmethod
    def validate_names(cls, v, info):
        label = 'Nom' if info.field_name == 'nom' else 'Prénom'
        return require_letters(v, label)

    @field_validator('telephone', mode='before')
    @classmethod
    def validate_telephone(cls, v: str) -> str:
        return require_phone(v, 'Téléphone')

    @field_validator('adresse', mode='before')
    @classmethod
    def validate_adresse(cls, v):
        return only_text(v).strip()


class StaffRegisterIn(Schema):
    username: str
    password: str = Field(min_length=10, description='Min. 10 caractères, majuscule, minuscule et chiffre')
    email: str
    first_name: str
    last_name: str
    role: str
    specialty: str = ''
    phone: str = ''

    @field_validator('username', mode='before')
    @classmethod
    def validate_username(cls, v):
        return require_alnum(v, 'Identifiant')

    @field_validator('first_name', 'last_name', mode='before')
    @classmethod
    def validate_staff_names(cls, v, info):
        label = 'Prénom' if info.field_name == 'first_name' else 'Nom'
        return require_letters(v, label)

    @field_validator('phone', mode='before')
    @classmethod
    def validate_phone(cls, v):
        if not str(v or '').strip():
            return ''
        return require_phone(v, 'Téléphone', required=False)

    @field_validator('specialty', mode='before')
    @classmethod
    def validate_specialty(cls, v):
        return only_text(v).strip()

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        if '@' not in v or len(v) < 5 or '.' not in v.split('@')[-1]:
            raise ValueError('Adresse email invalide')
        return v


class RegisterIn(Schema):
    """Legacy — conservé pour compatibilité."""
    username: str
    password: str = Field(min_length=10)
    email: EmailStr
    first_name: str = ''
    last_name: str = ''
    role: str = 'PATIENT'


# ── Patients ──────────────────────────────────────────────────────────────────

class PatientIn(Schema):
    numero_dossier: str
    nom: str
    prenom: str
    date_naissance: date
    sexe: str
    telephone: str = ''
    email: str = ''
    adresse: str = ''
    groupe_sanguin: str = ''

    @field_validator('numero_dossier', mode='before')
    @classmethod
    def validate_numero(cls, v):
        return require_alnum(v, 'N° dossier')

    @field_validator('nom', 'prenom', mode='before')
    @classmethod
    def validate_patient_names(cls, v, info):
        label = 'Nom' if info.field_name == 'nom' else 'Prénom'
        return require_letters(v, label)

    @field_validator('telephone', mode='before')
    @classmethod
    def validate_patient_phone(cls, v):
        if not str(v or '').strip():
            return ''
        return require_phone(v, 'Téléphone', required=False)

    @field_validator('adresse', mode='before')
    @classmethod
    def validate_patient_adresse(cls, v):
        return only_text(v).strip()


class PatientOut(Schema):
    id: int
    numero_dossier: str
    nom: str
    prenom: str
    date_naissance: date
    sexe: str
    telephone: str
    email: str
    adresse: str = ''
    groupe_sanguin: str
    consentement_traitement: bool


# ── Hospitalisation ───────────────────────────────────────────────────────────

class BedOut(Schema):
    id: int
    numero_lit: str
    est_disponible: bool
    chambre_numero: str
    service_nom: str
    service_id: int = 0


class HospitalizationIn(Schema):
    patient_id: int
    lit_id: int
    medecin_referent_id: int
    date_entree: datetime
    date_sortie_prevue: date
    motif_admission: str


class HospitalizationOut(Schema):
    id: int
    patient_id: int
    lit_id: int
    statut: str
    date_entree: datetime
    date_sortie_prevue: date
    motif_admission: str
    medecin_referent_id: int = 0


class HospitalizationDetailOut(Schema):
    id: int
    patient_id: int
    patient_nom: str
    patient_dossier: str
    lit_id: int
    lit_label: str
    service_nom: str
    medecin_referent_id: int
    medecin_nom: str
    date_entree: datetime
    date_sortie_prevue: date
    date_sortie_effective: Optional[datetime] = None
    statut: str
    motif_admission: str
    notes: str = ''


class HospitalizationUpdateIn(Schema):
    date_sortie_prevue: Optional[date] = None
    statut: Optional[str] = None
    notes: Optional[str] = None
    motif_admission: Optional[str] = None


class TransferIn(Schema):
    nouveau_lit_id: int
    nouveau_service_id: Optional[int] = None
    notes: str = ''


class DischargeIn(Schema):
    date_sortie_effective: Optional[datetime] = None
    notes: str = ''


# ── Consultation & Prescriptions ──────────────────────────────────────────────

class ConsultationIn(Schema):
    patient_id: int
    hospitalisation_id: Optional[int] = None
    diagnostic_cim10: str
    diagnostic_libelle: str
    notes_cliniques: str = ''


class ConsultationOut(Schema):
    id: int
    patient_id: int
    diagnostic_cim10: str
    diagnostic_libelle: str
    validee: bool
    date_consultation: datetime


class PrescriptionIn(Schema):
    consultation_id: int
    medicament_nom: str
    posologie: str
    duree_jours: int
    instructions: str = ''


class PrescriptionOut(Schema):
    id: int
    consultation_id: int
    medicament_nom: str
    posologie: str
    validee: bool
    verrouillee: bool


# ── Soins infirmiers ──────────────────────────────────────────────────────────

class VitalSignIn(Schema):
    hospitalisation_id: int
    temperature: Optional[float] = None
    tension_systolique: Optional[int] = None
    tension_diastolique: Optional[int] = None
    frequence_cardiaque: Optional[int] = None
    saturation_o2: Optional[int] = None
    notes: str = ''


class VitalSignOut(Schema):
    id: int
    hospitalisation_id: int
    temperature: Optional[float]
    tension_systolique: Optional[int]
    frequence_cardiaque: Optional[int]
    date_prise: datetime


class NursingCareIn(Schema):
    hospitalisation_id: int
    prescription_id: Optional[int] = None
    description: str
    planifie_a: datetime


class NursingCareOut(Schema):
    id: int
    description: str
    planifie_a: datetime
    realise_a: Optional[datetime]
    dose_omise: bool


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentOut(Schema):
    id: int
    titre: str
    mime_type: str
    taille_octets: int
    signe_electroniquement: bool
    created_at: datetime


# ── Laboratoire ───────────────────────────────────────────────────────────────

class LabOrderIn(Schema):
    patient_id: int
    examen_id: int
    hospitalisation_id: Optional[int] = None
    notes: str = ''


class LabOrderOut(Schema):
    id: int
    patient_id: int
    examen_code: str
    statut: str
    date_commande: datetime


class LabResultBriefOut(Schema):
    id: int
    valeur: str
    unite: str
    valeur_reference: str
    commentaire: str
    valide: bool
    date_validation: Optional[datetime] = None
    pdf_url: Optional[str] = None


class LabOrderDetailOut(Schema):
    id: int
    patient_id: int
    patient_nom: str
    patient_dossier: str
    examen_code: str
    examen_libelle: str
    statut: str
    date_commande: datetime
    date_prelevement: Optional[datetime] = None
    notes: str = ''
    resultat: Optional[LabResultBriefOut] = None


class LabDashboardOut(Schema):
    total_commandes: int
    commandes_jour: int
    en_attente_prelevement: int
    en_analyse: int
    a_valider: int
    publies_jour: int
    publies_total: int
    examens_catalogue: int


class LabResultIn(Schema):
    valeur: str
    unite: str = ''
    valeur_reference: str = ''
    commentaire: str = ''


class LabWorkflowStepIn(Schema):
    statut: str


# ── Pharmacie ─────────────────────────────────────────────────────────────────

class DispenseIn(Schema):
    prescription_id: int
    lot_id: int
    quantite: int


class StockAlertOut(Schema):
    medicament: str
    lot: str
    quantite: int
    seuil: int
    en_rupture: bool
    date_peremption: date


class MedicationOut(Schema):
    id: int
    code: str
    nom: str
    forme: str
    categorie: str
    categorie_label: str
    description: str
    prix_unitaire: Decimal
    stock_disponible: int
    disponible: bool
    seuil_alerte: int


class PharmacyRequestLineIn(Schema):
    medicament_id: int
    quantite: int = 1


class PharmacyRequestIn(Schema):
    lignes: list[PharmacyRequestLineIn]
    notes: str = ''


class PharmacyRequestLineOut(Schema):
    id: int
    medicament_id: int
    medicament_nom: str
    medicament_code: str
    forme: str
    quantite: int
    prix_unitaire: Decimal
    sous_total: Decimal


class PharmacyRequestOut(Schema):
    id: int
    reference: str
    statut: str
    statut_label: str
    notes: str
    montant_total: Decimal
    created_at: datetime
    patient_id: Optional[int] = None
    patient_nom: Optional[str] = None
    patient_dossier: Optional[str] = None
    lignes: list[PharmacyRequestLineOut]


class PharmacyRequestStatusIn(Schema):
    statut: str


# ── Facturation ─────────────────────────────────────────────────────────────────

class InvoiceCreateIn(Schema):
    patient_id: int
    hospitalisation_id: Optional[int] = None


class InvoiceLineIn(Schema):
    type_ligne: str
    libelle: str
    quantite: int = 1
    prix_unitaire: Decimal
    reinitialiser_paiements: bool = False


class InvoiceLineUpdateIn(Schema):
    libelle: Optional[str] = None
    quantite: Optional[int] = None
    prix_unitaire: Optional[Decimal] = None
    reinitialiser_paiements: bool = False


class InvoiceMontantUpdateIn(Schema):
    montant_patient: Decimal
    motif: str = ''
    reinitialiser_paiements: bool = False


class PaymentIn(Schema):
    montant: Decimal
    mode: str
    reference: str = ''


class MobileMoneyInitIn(Schema):
    numero_mobile: str
    montant: Optional[Decimal] = None

    @field_validator('numero_mobile', mode='before')
    @classmethod
    def validate_mobile(cls, v):
        return require_phone(v, 'Numéro mobile')


class MobileMoneyConfirmIn(Schema):
    transaction_id: int
    code_pin: str = ''
    code_push: str = ''

    @field_validator('code_pin', 'code_push', mode='before')
    @classmethod
    def validate_codes(cls, v):
        return only_digits(v)


class MobileMoneyPhoneApproveIn(Schema):
    numero_mobile: str

    @field_validator('numero_mobile', mode='before')
    @classmethod
    def validate_mobile(cls, v):
        return require_phone(v, 'Numéro mobile')


class InvoiceLineOut(Schema):
    id: int
    type_ligne: str
    libelle: str
    quantite: int
    prix_unitaire: Decimal
    montant: Decimal


class PaymentOut(Schema):
    id: int
    montant: Decimal
    mode: str
    reference: str = ''
    numero_mobile: str = ''
    operateur: str = ''
    statut: str = 'VALIDE'
    created_at: datetime


class InvoiceOut(Schema):
    id: int
    numero: str
    patient_id: int
    patient_nom: str = ''
    patient_dossier: str = ''
    statut: str
    statut_libelle: str = ''
    est_payee: bool = False
    est_impayee: bool = True
    montant_total: Decimal
    montant_assurance: Decimal = Decimal('0')
    montant_patient: Decimal = Decimal('0')
    montant_paye: Decimal
    montant_restant: Decimal = Decimal('0')
    emise_le: Optional[datetime] = None
    created_at: Optional[datetime] = None
    pdf_url: str = ''
    lignes: list[InvoiceLineOut] = []
    paiements: list[PaymentOut] = []


class PaginatedInvoicesOut(Schema):
    items: list[InvoiceOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class MobileMoneyTransactionOut(Schema):
    id: int
    reference: str
    operateur: str
    numero_mobile: str
    numero_mobile_affiche: str
    montant: Decimal
    statut: str
    message: str
    instruction_ussd: str
    expire_le: datetime
    facture_id: int
    facture_numero: str
    code_push: str = ''
    push_message: str = ''


class MobileMoneyStatusOut(Schema):
    id: int
    statut: str
    message: str
    facture_statut: str = ''
    montant_paye: Decimal = Decimal('0')
    montant_restant: Decimal = Decimal('0')


# ── RDV & Mobile patient ────────────────────────────────────────────────────────

class AppointmentIn(Schema):
    medecin_id: int
    date_heure: datetime
    motif: str
    duree_minutes: int = 30


class AppointmentOut(Schema):
    id: int
    medecin_id: int
    date_heure: datetime
    motif: str
    statut: str


class MedecinDispoOut(Schema):
    id: int
    username: str
    first_name: str
    last_name: str
    specialty: str
    phone: str = ''
    photo_url: Optional[str] = None
    disponible_rdv: bool = True


class MedecinDisponibiliteIn(Schema):
    disponible_rdv: bool


class ChatMessageIn(Schema):
    contenu: str


class ChatMessageOut(Schema):
    id: int
    auteur_id: int
    contenu: str
    lu: bool
    created_at: datetime


class ReminderIn(Schema):
    medicament: str
    heure_prise: time
    prescription_id: Optional[int] = None


# ── RH ────────────────────────────────────────────────────────────────────────

class ShiftIn(Schema):
    personnel_id: int
    service_id: int
    date_debut: datetime
    date_fin: datetime
    type_garde: str
    notes: str = ''


class ShiftOut(Schema):
    id: int
    personnel_id: int
    personnel_nom: str = ''
    service_id: int
    service_nom: str = ''
    service_code: str = ''
    date_debut: datetime
    date_fin: datetime
    type_garde: str
    notes: str = ''


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardKPIs(Schema):
    taux_occupation: float
    lits_disponibles: int
    lits_total: int
    examens_en_attente: int
    recettes_mois: Decimal
    hospitalisations_actives: int
    patients_total: int
    alertes_stock: int = 0
    doses_omises: int = 0


class RoleDashboardOut(Schema):
    role: str
    role_label: str = ''
    taux_occupation: float = 0
    lits_disponibles: int = 0
    lits_total: int = 0
    hospitalisations_actives: int = 0
    patients_total: int = 0
    examens_en_attente: int = 0
    recettes_mois: Decimal = Decimal('0')
    recettes_jour: Decimal = Decimal('0')
    doses_omises: int = 0
    alertes_stock: int = 0
    factures_impayees: int = 0
    factures_payees_mois: int = 0
    factures_brouillon: int = 0
    montant_impaye_total: Decimal = Decimal('0')
    paiements_jour: int = 0
    soins_en_attente: int = 0
    soins_en_retard: int = 0
    soins_realises_jour: int = 0
    rdv_aujourdhui: int = 0
    rdv_en_attente: int = 0
    demandes_pharmacie: int = 0
    labo_a_valider: int = 0
    labo_publies_jour: int = 0
    mes_rdv_jour: int = 0


class ComptableChartSeriesOut(Schema):
    labels: list[str]
    recettes: list[float]
    impayes: list[float]
    payees: list[float]
    brouillons: list[float]
    operations: list[int]
    periode_jours: int = 14


class NursingCareDetailOut(Schema):
    id: int
    hospitalisation_id: int
    patient_nom: str = ''
    patient_dossier: str = ''
    service: str = ''
    description: str
    planifie_a: datetime
    realise_a: Optional[datetime] = None
    dose_omise: bool = False
    statut: str = 'PLANIFIE'


class MessageOut(Schema):
    message: str
    detail: str = ''


class HealthOut(Schema):
    status: str
    version: str
    database: str
    email_provider: str = 'none'
    brevo_configured: bool = False
    brevo_key_valid: bool = False


# ── Portail patient ───────────────────────────────────────────────────────────

class PatientEstablishmentOut(Schema):
    nom_etablissement: str
    adresse: str
    telephone: str
    email: str
    horaires: str
    urgences_telephone: str
    description: str
    site_web: str
    latitude: float
    longitude: float
    google_maps_query: str
    google_maps_embed_url: str
    google_maps_directions_url: str


class PatientDashboardOut(Schema):
    prochain_rdv: Optional[dict] = None
    rdv_a_venir: int = 0
    resultats_disponibles: int = 0
    rappels_actifs: int = 0
    hospitalisation_active: bool = False
    factures_impayees: int = 0
    montant_du: Decimal = Decimal('0')


class PatientAppointmentDetailOut(Schema):
    id: int
    medecin_id: int
    medecin_nom: str
    medecin_specialty: str
    date_heure: datetime
    motif: str
    statut: str
    duree_minutes: int


class PatientConsultationSummaryOut(Schema):
    id: int
    date_consultation: datetime
    diagnostic_cim10: str
    diagnostic_libelle: str
    medecin_nom: str
    prescriptions: list[PrescriptionOut] = []


class PatientCareItemOut(Schema):
    id: int
    description: str
    planifie_a: datetime
    realise_a: Optional[datetime] = None
    dose_omise: bool
    infirmier_nom: str = ''
    statut: str = 'PLANIFIE'
    statut_label: str = 'Planifié'
    medicament_lie: str = ''


class PatientVitalSignPatientOut(Schema):
    id: int
    temperature: Optional[float] = None
    tension_systolique: Optional[int] = None
    tension_diastolique: Optional[int] = None
    frequence_cardiaque: Optional[int] = None
    saturation_o2: Optional[int] = None
    date_prise: datetime


class PatientOrdonnanceCareOut(Schema):
    id: int
    medicament: str
    posologie: str
    duree_jours: int
    instructions: str = ''
    medecin: str
    date_consultation: datetime


class PatientCareHospitalizationOut(Schema):
    id: int
    statut: str
    statut_label: str
    localisation: str
    service: str
    chambre: str
    lit: str
    batiment: str
    medecin_referent: str
    motif_admission: str
    date_entree: datetime
    date_sortie_prevue: Optional[date] = None
    notes: str = ''


class PatientReminderOut(Schema):
    id: int
    medicament: str
    heure_prise: time
    actif: bool


class PatientCarePlanOut(Schema):
    hospitalisation: Optional[PatientCareHospitalizationOut] = None
    soins: list[PatientCareItemOut]
    constantes: list[PatientVitalSignPatientOut]
    ordonnances: list[PatientOrdonnanceCareOut]
    rappels: list[PatientReminderOut]
    soins_total: int = 0
    soins_realises: int = 0
    soins_en_attente: int = 0
    soins_omis: int = 0


class ReminderUpdateIn(Schema):
    actif: Optional[bool] = None


class PatientConversationOut(Schema):
    id: int
    medecin_id: int
    medecin_nom: str
    medecin_specialty: str
    dernier_message: str = ''
    non_lus: int = 0


class PatientLabResultOut(Schema):
    id: int
    examen: str
    valeur: str
    unite: str
    date_validation: Optional[datetime] = None
    pdf_url: str = ''


class PatientCardMedecinOut(Schema):
    id: Optional[int] = None
    nom_complet: str = ''
    prenom: str = ''
    nom: str = ''
    email: str = ''
    specialite: str = ''
    telephone: str = ''


class PatientCardFullOut(Schema):
    genere_le: str
    etablissement: dict
    identite: dict
    hospitalisations: list
    consultations: list
    rendez_vous: list
    factures: list
    resultats_laboratoire: list
    demandes_pharmacie: list
    rappels_medicaments: list


class PatientCardPdfLinkOut(Schema):
    pdf_url: str
    media_url: str = ''
    filename: str
    qr_url: str
    chemin: str = ''


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginatedPatientsOut(Schema):
    items: list[PatientOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedUsersOut(Schema):
    items: list[UserOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedMedecinsOut(Schema):
    items: list[MedecinDispoOut]
    total: int
    page: int
    page_size: int
    total_pages: int
    disponibles_total: int = 0
    indisponibles_total: int = 0


class PaginatedHospitalizationsOut(Schema):
    items: list[HospitalizationDetailOut]
    total: int
    page: int
    page_size: int
    total_pages: int
