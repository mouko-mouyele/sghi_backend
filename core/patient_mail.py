"""Notifications email patient — RDV, labo, facturation, pharmacie, messages, hospitalisation."""

import logging

from django.conf import settings
from django.utils import timezone as dj_tz

from accounts.models import User

logger = logging.getLogger(__name__)

SIGNATURE = '\n\n— SGHL / CHU Brazzaville'


def patient_email(patient) -> str:
    if patient.email:
        return patient.email.strip()
    if patient.user and patient.user.email:
        return patient.user.email.strip()
    return ''


def format_datetime(dt) -> str:
    if not dt:
        return '—'
    return dj_tz.localtime(dt).strftime('%d/%m/%Y à %H:%M')


def format_amount(amount) -> str:
    try:
        return f'{int(amount):,} FCFA'.replace(',', ' ')
    except (TypeError, ValueError):
        return f'{amount} FCFA'


def send_patient_email(subject: str, body: str, patient, *, extra_recipients: list[str] | None = None) -> bool:
    """Envoie un email au patient (console si SMTP non configuré)."""
    recipients = []
    pe = patient_email(patient)
    if pe and '@' in pe:
        recipients.append(pe)
    if extra_recipients:
        recipients.extend(e for e in extra_recipients if e and '@' in e)
    recipients = list(dict.fromkeys(recipients))
    if not recipients:
        logger.warning('Aucun email patient pour : %s — %s', patient, subject)
        return False

    full_body = body.rstrip() + SIGNATURE

    from core.sghi_mail import email_is_configured, send_sghi_email

    if not email_is_configured():
        preview = (
            f'\n{"=" * 60}\n'
            f'[SGHL — Email patient simulé — configurez BREVO_API_KEY sur Render]\n'
            f'À : {", ".join(recipients)}\n'
            f'Objet : {subject}\n'
            f'{"-" * 60}\n'
            f'{full_body}\n'
            f'{"=" * 60}\n'
        )
        print(preview)
        logger.info(preview)
        return True

    ok, err = send_sghi_email(subject, full_body, recipients)
    if not ok:
        logger.error('Échec envoi email patient à %s : %s', recipients, err)
    return ok


def _greeting(patient) -> str:
    return f'Bonjour {patient.prenom},'


# ── Laboratoire ───────────────────────────────────────────────────────────────

def notify_lab_result_published(result) -> bool:
    patient = result.commande.patient
    examen = result.commande.examen.libelle
    body = (
        f'{_greeting(patient)}\n\n'
        f'Vos résultats d\'examen sont disponibles sur votre portail patient SGHL.\n\n'
        f'Examen : {examen}\n'
        f'Résultat : {result.valeur} {result.unite or ""}'.strip() + '\n'
    )
    if result.valeur_reference:
        body += f'Valeur de référence : {result.valeur_reference}\n'
    if result.date_validation:
        body += f'Validé le : {format_datetime(result.date_validation)}\n'
    body += '\nConnectez-vous à l\'application pour consulter le rapport PDF.'
    return send_patient_email(
        f'[SGHL] Résultat labo disponible — {examen}',
        body,
        patient,
    )


# ── Facturation ───────────────────────────────────────────────────────────────

def notify_invoice_issued(invoice) -> bool:
    patient = invoice.patient
    body = (
        f'{_greeting(patient)}\n\n'
        f'Une nouvelle facture a été émise à votre nom.\n\n'
        f'Numéro : {invoice.numero}\n'
        f'Montant total : {format_amount(invoice.montant_total)}\n'
        f'À votre charge : {format_amount(invoice.montant_patient)}\n'
        f'Date d\'émission : {format_datetime(invoice.emise_le)}\n\n'
        f'Consultez et payez depuis le portail patient (Facturation / Mobile Money).'
    )
    return send_patient_email(
        f'[SGHL] Nouvelle facture {invoice.numero}',
        body,
        patient,
    )


def notify_payment_received(invoice, payment) -> bool:
    from billing.mobile_money import montant_restant

    patient = invoice.patient
    reste = montant_restant(invoice)
    mode_labels = {
        'ESPECES': 'Espèces',
        'CARTE': 'Carte bancaire',
        'VIREMENT': 'Virement',
        'MTN_MOMO': 'MTN Mobile Money',
        'AIRTEL_MONEY': 'Airtel Money',
        'CHEQUE': 'Chèque',
    }
    mode = mode_labels.get(payment.mode, payment.mode)
    body = (
        f'{_greeting(patient)}\n\n'
        f'Nous confirmons la réception d\'un paiement pour votre facture {invoice.numero}.\n\n'
        f'Montant reçu : {format_amount(payment.montant)}\n'
        f'Mode : {mode}\n'
    )
    if payment.reference:
        body += f'Référence : {payment.reference}\n'
    body += (
        f'Total payé : {format_amount(invoice.montant_paye)}\n'
        f'Reste à payer : {format_amount(reste)}\n'
    )
    if invoice.statut == invoice.Statut.PAYEE:
        body += '\nVotre facture est entièrement soldée. Merci.'
    return send_patient_email(
        f'[SGHL] Paiement reçu — facture {invoice.numero}',
        body,
        patient,
    )


def notify_mobile_money_pending(tx) -> bool:
    patient = tx.patient
    invoice = tx.facture
    op = 'MTN MoMo' if tx.operateur == 'MTN' else 'Airtel Money'
    body = (
        f'{_greeting(patient)}\n\n'
        f'Une demande de paiement Mobile Money a été initiée.\n\n'
        f'Facture : {invoice.numero}\n'
        f'Montant : {format_amount(tx.montant)}\n'
        f'Opérateur : {op}\n'
        f'Numéro : {tx.numero_mobile}\n'
        f'Référence : {tx.reference}\n\n'
        f'Validez la transaction sur votre téléphone pour finaliser le règlement.'
    )
    return send_patient_email(
        f'[SGHL] Paiement Mobile Money en attente — {invoice.numero}',
        body,
        patient,
    )


# ── Pharmacie ─────────────────────────────────────────────────────────────────

def _pharmacy_lines(req) -> str:
    lines = []
    for line in req.lignes.select_related('medicament'):
        lines.append(f'  • {line.medicament.nom} × {line.quantite}')
    return '\n'.join(lines) if lines else '  —'


def notify_pharmacy_request_submitted(req) -> bool:
    patient = req.patient
    body = (
        f'{_greeting(patient)}\n\n'
        f'Votre demande de médicaments a bien été enregistrée.\n\n'
        f'Référence : {req.reference}\n'
        f'Statut : Soumise — en attente de traitement par la pharmacie\n\n'
        f'Produits demandés :\n{_pharmacy_lines(req)}\n\n'
        f'Vous serez notifié par email à chaque changement de statut.'
    )
    return send_patient_email(
        f'[SGHL] Demande pharmacie {req.reference}',
        body,
        patient,
    )


def notify_pharmacy_status_updated(req, old_statut: str = '') -> bool:
    from pharmacy.models import PatientPharmacyRequest

    labels = dict(PatientPharmacyRequest.Statut.choices)
    label = labels.get(req.statut, req.statut)
    patient = req.patient
    body = (
        f'{_greeting(patient)}\n\n'
        f'Le statut de votre demande pharmacie a été mis à jour.\n\n'
        f'Référence : {req.reference}\n'
    )
    if old_statut and old_statut != req.statut:
        body += f'Ancien statut : {labels.get(old_statut, old_statut)}\n'
    body += f'Nouveau statut : {label}\n\n'
    if req.statut == PatientPharmacyRequest.Statut.PRETE:
        body += 'Vos médicaments sont prêts — présentez-vous à la pharmacie du CHU avec cette référence.\n'
    elif req.statut == PatientPharmacyRequest.Statut.RETIREE:
        body += 'Retrait enregistré. Bon rétablissement.\n'
    elif req.statut == PatientPharmacyRequest.Statut.ANNULEE:
        body += 'Demande annulée. Contactez la pharmacie pour plus d\'informations.\n'
    body += f'\nProduits :\n{_pharmacy_lines(req)}'
    return send_patient_email(
        f'[SGHL] Pharmacie {req.reference} — {label}',
        body,
        patient,
    )


# ── Messagerie ────────────────────────────────────────────────────────────────

def notify_patient_new_message(message) -> bool:
    conv = message.conversation
    if message.auteur_id == conv.patient.user_id:
        return False
    patient = conv.patient
    medecin = conv.medecin
    body = (
        f'{_greeting(patient)}\n\n'
        f'Vous avez reçu un nouveau message de Dr {medecin.first_name} {medecin.last_name}'
        f'{(" (" + medecin.specialty + ")") if medecin.specialty else ""}.\n\n'
        f'Message :\n"{message.contenu[:500]}"'
        f'{"…" if len(message.contenu) > 500 else ""}\n\n'
        f'Répondez depuis le portail patient → Messages.'
    )
    return send_patient_email(
        f'[SGHL] Nouveau message — Dr {medecin.last_name}',
        body,
        patient,
    )


# ── Hospitalisation ───────────────────────────────────────────────────────────

def notify_hospitalization_admitted(hosp) -> bool:
    patient = hosp.patient
    service = hosp.lit.chambre.service.nom if hosp.lit_id else '—'
    medecin = hosp.medecin_referent
    body = (
        f'{_greeting(patient)}\n\n'
        f'Votre admission à l\'hospitalisation a été enregistrée.\n\n'
        f'Service : {service}\n'
        f'Médecin référent : Dr {medecin.first_name} {medecin.last_name}\n'
        f'Date d\'entrée : {format_datetime(hosp.date_entree)}\n'
    )
    if hosp.date_sortie_prevue:
        body += f'Sortie prévue : {format_datetime(hosp.date_sortie_prevue)}\n'
    if hosp.motif_admission:
        body += f'Motif : {hosp.motif_admission}\n'
    body += '\nSuivez votre plan de soins sur le portail patient.'
    return send_patient_email(
        f'[SGHL] Admission hospitalisation — {service}',
        body,
        patient,
    )


def notify_hospitalization_discharged(hosp) -> bool:
    patient = hosp.patient
    body = (
        f'{_greeting(patient)}\n\n'
        f'Votre sortie d\'hospitalisation a été enregistrée.\n\n'
        f'Date de sortie : {format_datetime(hosp.date_sortie_effective or dj_tz.now())}\n'
    )
    if hosp.motif_admission:
        body += f'Motif initial : {hosp.motif_admission}\n'
    body += '\nRespectez les consignes médicales et vos rendez-vous de suivi.'
    return send_patient_email(
        f'[SGHL] Sortie d\'hospitalisation',
        body,
        patient,
    )


def secretary_emails() -> list[str]:
    return list(
        User.objects.filter(
            role__in=[User.Role.RECEPTIONNISTE, User.Role.ADMIN],
            is_active=True,
        ).exclude(email='').values_list('email', flat=True).distinct()
    )
