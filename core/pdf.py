"""Génération PDF — comptes-rendus labo et factures."""

import io
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def generate_lab_report_pdf(*, patient_nom: str, examen: str, valeur: str,
                            unite: str, reference: str, biologiste: str) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    c.setFont('Helvetica-Bold', 16)
    c.drawString(2 * cm, h - 2 * cm, 'SGHL — Compte-rendu de laboratoire')
    c.setFont('Helvetica', 11)
    y = h - 3.5 * cm
    for line in [
        f'Patient : {patient_nom}',
        f'Examen : {examen}',
        f'Résultat : {valeur} {unite}',
        f'Valeurs de référence : {reference}',
        f'Validé par : {biologiste}',
        '',
        'Document signé électroniquement — SGHL',
    ]:
        c.drawString(2 * cm, y, line)
        y -= 0.7 * cm
    c.showPage()
    c.save()
    return buffer.getvalue()


def generate_invoice_pdf(*, numero: str, patient_nom: str, lignes: list,
                         montant_total: Decimal, montant_paye: Decimal) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    c.setFont('Helvetica-Bold', 16)
    c.drawString(2 * cm, h - 2 * cm, f'Facture {numero}')
    c.setFont('Helvetica', 11)
    c.drawString(2 * cm, h - 3 * cm, f'Patient : {patient_nom}')
    y = h - 4.5 * cm
    for lg in lignes:
        c.drawString(2 * cm, y, f"{lg['libelle']} x{lg['quantite']} — {lg['montant']} FCFA")
        y -= 0.6 * cm
    y -= 0.5 * cm
    c.setFont('Helvetica-Bold', 12)
    c.drawString(2 * cm, y, f'Total : {montant_total} FCFA | Payé : {montant_paye} FCFA')
    c.showPage()
    c.save()
    return buffer.getvalue()


def generate_admin_stats_pdf(*, stats: dict, generated_at: str, admin_name: str) -> bytes:
    """Rapport PDF des statistiques administrateur."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    c.setFont('Helvetica-Bold', 18)
    c.drawString(2 * cm, h - 2 * cm, 'SGHL — Rapport statistiques')
    c.setFont('Helvetica', 10)
    c.drawString(2 * cm, h - 2.7 * cm, f'Généré le {generated_at} par {admin_name}')

    c.setFont('Helvetica-Bold', 13)
    c.drawString(2 * cm, h - 4 * cm, 'Indicateurs clés')

    rows = [
        ('Patients enregistrés', str(stats.get('patients_total', 0))),
        ('Médecins actifs', str(stats.get('medecins_total', 0))),
        ('Personnel total', str(stats.get('personnel_total', 0))),
        ('RDV aujourd\'hui', str(stats.get('rdv_aujourdhui', 0))),
        ('RDV à venir', str(stats.get('rdv_en_attente', 0))),
        ('Hospitalisations actives', str(stats.get('hospitalisations_actives', 0))),
        ('Taux occupation lits', f"{stats.get('taux_occupation', 0)} %"),
        ('Examens labo en attente', str(stats.get('examens_en_attente', 0))),
        ('Urgences actives', str(stats.get('urgences_actives', 0))),
        ('Recettes du mois (FCFA)', f"{float(stats.get('recettes_mois', 0)):,.0f}".replace(',', ' ')),
    ]

    c.setFont('Helvetica', 11)
    y = h - 5 * cm
    for label, value in rows:
        c.drawString(2 * cm, y, label)
        c.drawRightString(w - 2 * cm, y, value)
        y -= 0.65 * cm

    y -= 1 * cm
    c.setFont('Helvetica-Oblique', 9)
    c.drawString(2 * cm, y, 'Document généré automatiquement — SGHL ERP Médical')
    c.showPage()
    c.save()
    return buffer.getvalue()


def generate_patient_card_pdf(
    *,
    prenom: str,
    nom: str,
    email: str,
    adresse: str,
    numero_dossier: str,
    qr_url: str,
    etablissement: str = 'CHU de Brazzaville',
) -> bytes:
    """Carte patient : identité visible + QR code pour données médicales complètes."""
    from django.utils import timezone as dj_tz
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode import qr
    from reportlab.graphics.shapes import Drawing

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    c.setFillColorRGB(0.05, 0.45, 0.42)
    c.rect(0, h - 3.2 * cm, w, 3.2 * cm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont('Helvetica-Bold', 18)
    c.drawString(2 * cm, h - 1.8 * cm, (etablissement or 'CHU de Brazzaville')[:55])
    c.setFont('Helvetica', 10)
    c.drawString(2 * cm, h - 2.5 * cm, 'Carte patient — Informations publiques')

    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(2 * cm, h - 5 * cm, 'Identite du patient')
    c.setFont('Helvetica', 12)
    y = h - 6 * cm
    visible_lines = [
        ('Prenom', prenom),
        ('Nom', nom),
        ('E-mail', email or '-'),
        ('Adresse', adresse or '-'),
    ]
    for label, value in visible_lines:
        c.setFont('Helvetica-Bold', 11)
        c.drawString(2 * cm, y, f'{label} :')
        c.setFont('Helvetica', 11)
        safe_val = str(value).encode('latin-1', errors='replace').decode('latin-1')[:80]
        c.drawString(5.5 * cm, y, safe_val)
        y -= 0.9 * cm

    y -= 0.5 * cm
    c.setFont('Helvetica-Oblique', 9)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(2 * cm, y, 'Informations medicales accessibles via le QR code ci-contre.')
    y -= 0.45 * cm
    c.drawString(2 * cm, y, '(hospitalisation, ordonnances, medecin, factures...)')

    qr_size = 6.5 * cm
    qr_x = w - qr_size - 2 * cm
    qr_y = h - 6 * cm - qr_size
    widget = qr.QrCodeWidget(qr_url)
    bounds = widget.getBounds()
    bw = bounds[2] - bounds[0]
    bh = bounds[3] - bounds[1]
    drawing = Drawing(
        qr_size, qr_size,
        transform=[qr_size / bw, 0, 0, qr_size / bh, 0, 0],
    )
    drawing.add(widget)
    renderPDF.draw(drawing, c, qr_x, qr_y)

    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica-Bold', 10)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 0.6 * cm, 'Scanner pour dossier complet')
    c.setFont('Helvetica', 8)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 1.2 * cm, f'Dossier {numero_dossier}')

    c.setFont('Helvetica', 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(2 * cm, 2 * cm, f'Document genere le {dj_tz.now().strftime("%d/%m/%Y %H:%M")} — SGHL ERP')

    c.showPage()
    c.save()
    return buffer.getvalue()
