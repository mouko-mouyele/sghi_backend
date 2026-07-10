"""RBAC — contrôle d'accès par profil."""

from ninja.errors import HttpError

from accounts.models import User

# Matrice des permissions par module
ROLE_PERMISSIONS = {
    'ADMIN': {'*'},
    'MEDECIN': {
        'patients', 'consultations', 'prescriptions', 'hospitalisations',
        'lab_orders', 'documents', 'messages', 'dashboard',
    },
    'INFIRMIER': {
        'patients_read', 'constantes', 'soins', 'hospitalisations_read', 'dashboard',
    },
    'BIOLOGISTE': {'lab', 'dashboard'},
    'PHARMACIEN': {'pharmacie', 'prescriptions_read', 'dashboard'},
    'COMPTABLE': {'billing', 'dashboard'},
    'RECEPTIONNISTE': {
        'patients', 'admissions', 'rdv', 'documents', 'billing_read', 'dashboard',
        'medecins', 'hospitalisations',
    },
    'PATIENT': {'self', 'rdv', 'results', 'messages', 'reminders', 'pharmacie'},
}

STAFF_ROLES = {
    User.Role.ADMIN, User.Role.MEDECIN, User.Role.INFIRMIER,
    User.Role.BIOLOGISTE, User.Role.PHARMACIEN, User.Role.COMPTABLE,
    User.Role.RECEPTIONNISTE,
}


def has_role(user, *roles: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.role == User.Role.ADMIN:
        return True
    return user.role in roles


def require_role(user, *roles: str):
    if not has_role(user, *roles):
        raise HttpError(403, f'Accès refusé — rôle requis : {", ".join(roles)}')


def can_access_patient(user, patient) -> bool:
    if has_role(user, User.Role.ADMIN, User.Role.MEDECIN, User.Role.INFIRMIER,
                 User.Role.RECEPTIONNISTE, User.Role.BIOLOGISTE, User.Role.PHARMACIEN,
                 User.Role.COMPTABLE):
        return True
    if user.role == User.Role.PATIENT:
        profile = getattr(user, 'patient_profile', None)
        return profile and profile.id == patient.id
    return False
