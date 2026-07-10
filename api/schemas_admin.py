from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema
from pydantic import Field, field_validator

from api.validators import only_text, require_alnum, require_letters, require_phone


class AdminStatsOut(Schema):
    patients_total: int
    medecins_total: int
    personnel_total: int
    rdv_aujourdhui: int
    rdv_en_attente: int
    hospitalisations_actives: int
    taux_occupation: float
    examens_en_attente: int
    recettes_mois: Decimal
    urgences_actives: int


class AdminAppointmentOut(Schema):
    id: int
    patient_id: int
    patient_nom: str
    medecin_id: int
    medecin_nom: str
    date_heure: datetime
    motif: str
    statut: str
    duree_minutes: int


class AdminAppointmentIn(Schema):
    patient_id: int
    medecin_id: int
    date_heure: datetime
    motif: str
    duree_minutes: int = 30
    statut: str = 'CONFIRME'


class AdminAppointmentUpdate(Schema):
    statut: str


class AdminAppointmentEdit(Schema):
    patient_id: Optional[int] = None
    medecin_id: Optional[int] = None
    date_heure: Optional[datetime] = None
    motif: Optional[str] = None
    statut: Optional[str] = None
    duree_minutes: Optional[int] = None
    raison_modification: Optional[str] = None


class AdminMedecinOut(Schema):
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
    specialty: str
    rdv_count: int
    phone: str = ''
    photo_url: Optional[str] = None
    disponible_rdv: bool = True


class AdminTeamMemberOut(Schema):
    id: int
    username: str
    first_name: str
    last_name: str
    role: str
    email: str
    specialty: str = ''
    phone: str = ''
    photo_url: Optional[str] = None


class AdminServiceOut(Schema):
    id: int
    code: str
    nom: str
    building: str
    chambres: int
    lits_total: int
    lits_disponibles: int
    hospitalisations_actives: int


class AdminServiceIn(Schema):
    code: str
    nom: str
    building_id: int


class AdminUrgenceOut(Schema):
    hospitalisation_id: int
    patient_nom: str
    numero_dossier: str
    lit: str
    medecin: str
    date_entree: datetime
    motif: str


class HospitalInfoOut(Schema):
    nom_etablissement: str
    adresse: str
    telephone: str
    email: str
    horaires: str
    urgences_telephone: str
    description: str
    site_web: str
    latitude: float = -4.2594
    longitude: float = 15.2847
    google_maps_query: str = ''


class HospitalInfoIn(Schema):
    nom_etablissement: str
    adresse: str = ''
    telephone: str = ''
    email: str = ''
    horaires: str = ''
    urgences_telephone: str = ''
    description: str = ''
    site_web: str = ''
    latitude: float = -4.2594
    longitude: float = 15.2847
    google_maps_query: str = ''

    @field_validator(
        'nom_etablissement', 'adresse', 'horaires', 'description', 'google_maps_query',
        mode='before',
    )
    @classmethod
    def validate_text_fields(cls, v):
        return only_text(v).strip()

    @field_validator('telephone', 'urgences_telephone', mode='before')
    @classmethod
    def validate_phones(cls, v, info):
        label = 'Téléphone urgences' if info.field_name == 'urgences_telephone' else 'Téléphone'
        if not str(v or '').strip():
            return ''
        return require_phone(v, label, required=False)


class AdminPatientEdit(Schema):
    numero_dossier: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    date_naissance: Optional[date] = None
    sexe: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    adresse: Optional[str] = None
    groupe_sanguin: Optional[str] = None

    @field_validator('numero_dossier', mode='before')
    @classmethod
    def validate_numero(cls, v):
        if v is None or not str(v).strip():
            return v
        return require_alnum(v, 'N° dossier')

    @field_validator('nom', 'prenom', mode='before')
    @classmethod
    def validate_names(cls, v, info):
        if v is None or not str(v).strip():
            return v
        label = 'Nom' if info.field_name == 'nom' else 'Prénom'
        return require_letters(v, label)

    @field_validator('telephone', mode='before')
    @classmethod
    def validate_phone(cls, v):
        if v is None or not str(v).strip():
            return v
        return require_phone(v, 'Téléphone', required=False)

    @field_validator('adresse', mode='before')
    @classmethod
    def validate_adresse(cls, v):
        if v is None:
            return v
        return only_text(v).strip()


class AdminStaffEdit(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    specialty: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=10)

    @field_validator('first_name', 'last_name', mode='before')
    @classmethod
    def validate_staff_names(cls, v, info):
        if v is None or not str(v).strip():
            return v
        label = 'Prénom' if info.field_name == 'first_name' else 'Nom'
        return require_letters(v, label)

    @field_validator('phone', mode='before')
    @classmethod
    def validate_staff_phone(cls, v):
        if v is None or not str(v).strip():
            return v
        return require_phone(v, 'Téléphone', required=False)

    @field_validator('specialty', mode='before')
    @classmethod
    def validate_specialty(cls, v):
        if v is None:
            return v
        return only_text(v).strip()

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not str(v).strip():
            return v
        v = v.strip()
        if '@' not in v or len(v) < 5 or '.' not in v.split('@')[-1]:
            raise ValueError('Adresse email invalide')
        return v


class LoginJournalOut(Schema):
    user__username: Optional[str] = None
    ip_address: Optional[str] = None
    success: bool
    timestamp: datetime
    user_agent: Optional[str] = None


class PaginatedAdminMedecinOut(Schema):
    items: list[AdminMedecinOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedAdminTeamMemberOut(Schema):
    items: list[AdminTeamMemberOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedAdminAppointmentOut(Schema):
    items: list[AdminAppointmentOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedLoginJournalOut(Schema):
    items: list[LoginJournalOut]
    total: int
    page: int
    page_size: int
    total_pages: int
