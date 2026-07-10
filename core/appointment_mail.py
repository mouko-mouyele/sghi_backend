"""Notifications email rendez-vous — patient et accueil."""

import logging

from django.core.mail import send_mail
from django.conf import settings

from core.patient_mail import (
    format_datetime,
    secretary_emails,
    send_patient_email,
    SIGNATURE,
)

logger = logging.getLogger(__name__)


def _rdv_details(patient, medecin, rdv) -> str:
    return (
        f'Patient : {patient.prenom} {patient.nom}\n'
        f'Médecin : Dr {medecin.first_name} {medecin.last_name}'
        f'{(" — " + medecin.specialty) if medecin.specialty else ""}\n'
        f'Date : {format_datetime(rdv.date_heure)}\n'
        f'Durée : {rdv.duree_minutes} minutes\n'
        f'Motif : {rdv.motif}\n'
    )


def send_appointment_email(subject: str, body: str, recipients: list[str]) -> bool:
    recipients = [e for e in recipients if e and '@' in e]
    if not recipients:
        logger.warning('Aucun email destinataire pour : %s', subject)
        return False

    full_body = body.rstrip() + SIGNATURE

    if not settings.EMAIL_HOST_USER:
        preview = (
            f'\n{"=" * 60}\n'
            f'[SGHL — Email simulé — configurez EMAIL_HOST_USER dans .env pour Gmail]\n'
            f'À : {", ".join(recipients)}\n'
            f'Objet : {subject}\n'
            f'{"-" * 60}\n'
            f'{full_body}\n'
            f'{"=" * 60}\n'
        )
        print(preview)
        logger.info(preview)
        return True

    try:
        send_mail(
            subject=subject,
            message=full_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception('Échec envoi email RDV à %s', recipients)
        return False


def notify_appointment_pending(rdv) -> bool:
    patient, medecin = rdv.patient, rdv.medecin
    details = _rdv_details(patient, medecin, rdv)

    patient_ok = send_patient_email(
        f'[SGHL] Demande de RDV en attente — {format_datetime(rdv.date_heure)}',
        (
            f'Bonjour {patient.prenom},\n\n'
            f'Votre demande de rendez-vous a bien été reçue.\n'
            f'Statut : EN ATTENTE de confirmation par l\'accueil.\n\n'
            f'{details}\n'
            f'Vous recevrez un email dès que la secrétaire aura confirmé ou annulé.'
        ),
        patient,
    )

    sec_ok = send_appointment_email(
        f'[SGHL] ⚠ RDV à confirmer — {patient.prenom} {patient.nom}',
        (
            f'Bonjour,\n\n'
            f'Un patient vient de demander un rendez-vous.\n'
            f'Action requise : CONFIRMER ou ANNULER dans SGHL → Rendez-vous.\n\n'
            f'{details}\n'
            f'Réf. RDV #{rdv.id}'
        ),
        secretary_emails(),
    )
    return patient_ok or sec_ok


def notify_appointment_confirmed(rdv) -> bool:
    patient, medecin = rdv.patient, rdv.medecin
    details = _rdv_details(patient, medecin, rdv)
    extra = [medecin.email] if medecin.email else []

    ok = send_patient_email(
        f'[SGHL] ✓ RDV confirmé — {format_datetime(rdv.date_heure)}',
        (
            f'Bonjour,\n\n'
            f'Votre rendez-vous est CONFIRMÉ par l\'accueil du CHU de Brazzaville.\n\n'
            f'{details}\n'
            f'Présentez-vous 15 minutes avant l\'heure prévue.'
        ),
        patient,
        extra_recipients=extra,
    )
    if ok:
        rdv.confirmation_envoyee = True
        rdv.save(update_fields=['confirmation_envoyee', 'updated_at'])
    return ok


def notify_appointment_created(rdv) -> bool:
    return notify_appointment_confirmed(rdv)


def notify_appointment_updated(rdv, old_values: dict, reason: str = '') -> bool:
    from clinical.models import Appointment

    old_statut = old_values.get('statut')
    if old_statut and old_statut != rdv.statut:
        if rdv.statut == Appointment.Statut.CONFIRME:
            return notify_appointment_confirmed(rdv)
        if rdv.statut == Appointment.Statut.ANNULE:
            return notify_appointment_cancelled(rdv, reason=reason or 'Annulation par l\'accueil')

    patient, medecin = rdv.patient, rdv.medecin
    changes = []
    if old_values.get('date_heure') and str(old_values['date_heure']) != str(rdv.date_heure):
        changes.append(
            f'  • Date/heure : {format_datetime(old_values.get("date_heure"))} → {format_datetime(rdv.date_heure)}'
        )
    if old_values.get('medecin_id') and old_values['medecin_id'] != rdv.medecin_id:
        changes.append('  • Médecin remplacé (indisponibilité ou réorganisation)')

    subject = '[SGHL] Modification de votre rendez-vous'
    if old_values.get('medecin_id') and old_values['medecin_id'] != rdv.medecin_id:
        subject = '[SGHL] RDV modifié — médecin indisponible'

    body = (
        f'Bonjour,\n\n'
        f'Votre rendez-vous au CHU de Brazzaville a été modifié par l\'accueil.\n\n'
        f'{_rdv_details(patient, medecin, rdv)}'
        f'Statut : {rdv.statut}\n'
    )
    if changes:
        body += '\nModifications :\n' + '\n'.join(changes) + '\n'
    if reason:
        body += f'\nRaison : {reason}\n'

    extra = [medecin.email] if medecin.email else []
    return send_patient_email(subject, body, patient, extra_recipients=extra)


def notify_appointment_cancelled(rdv, reason: str = '') -> bool:
    patient, medecin = rdv.patient, rdv.medecin
    body = (
        f'Bonjour,\n\n'
        f'Le rendez-vous suivant a été ANNULÉ :\n\n'
        f'{_rdv_details(patient, medecin, rdv)}'
    )
    if reason:
        body += f'\nRaison : {reason}\n'
    body += '\nContactez l\'accueil pour reprogrammer.'

    extra = []
    if medecin.email:
        extra.append(medecin.email)
    extra.extend(secretary_emails())
    extra = list(dict.fromkeys(extra))
    return send_patient_email(
        f'[SGHL] ✗ RDV annulé — {format_datetime(rdv.date_heure)}',
        body,
        patient,
        extra_recipients=extra,
    )
