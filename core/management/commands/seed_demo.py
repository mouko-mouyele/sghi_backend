from datetime import date, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from billing.models import Insurance
from clinical.models import Bed, Building, HospitalService, Patient, Room
from core.constants import HOSPITAL_EMERGENCY_PHONE
from core.models import HospitalInfo
from hr.models import ShiftSchedule
from laboratory.models import LabTestCatalog
from pharmacy.models import Medication, StockLot


class Command(BaseCommand):
    help = 'Initialise des données de démonstration SGHL'

    def handle(self, *args, **options):
        self.stdout.write('Création des utilisateurs...')
        users = {}
        for role, username, pwd in [
            ('ADMIN', 'admin', 'Admin@2026!'),
            ('MEDECIN', 'dr.martin', 'Medecin@2026!'),
            ('INFIRMIER', 'inf.dupont', 'Infirmier@2026!'),
            ('BIOLOGISTE', 'bio.leroy', 'Bio@2026!'),
            ('PHARMACIEN', 'pharma.vega', 'Pharma@2026!'),
            ('COMPTABLE', 'compta.roy', 'Compta@2026!'),
            ('RECEPTIONNISTE', 'accueil', 'Accueil@2026!'),
        ]:
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@sghl.local',
                    'role': role,
                    'first_name': username.split('.')[0].title(),
                    'last_name': 'Demo',
                    'is_staff': role == 'ADMIN',
                    'is_superuser': role == 'ADMIN',
                },
            )
            u.role = role
            u.set_password(pwd)
            u.is_active = True
            u.save()
            users[role] = u

        self.stdout.write('Infrastructure hospitalière...')
        bat, _ = Building.objects.get_or_create(
            nom='CHU de Brazzaville — Pôle central',
            defaults={'adresse': 'Avenue Amilcar Cabral, Brazzaville, Congo'},
        )
        urg, _ = HospitalService.objects.get_or_create(
            code='URG', defaults={'building': bat, 'nom': 'Urgences'},
        )
        ch, _ = Room.objects.get_or_create(service=urg, numero='101', defaults={'capacite': 2})
        for i in range(1, 4):
            Bed.objects.get_or_create(chambre=ch, numero_lit=str(i), defaults={'est_disponible': True})

        self.stdout.write('Patients...')
        for n in range(1, 6):
            Patient.objects.get_or_create(
                numero_dossier=f'PAT-2026-{n:04d}',
                defaults={
                    'nom': f'Patient{n}',
                    'prenom': 'Jean',
                    'date_naissance': date(1980 + n, 1, 15),
                    'sexe': 'M' if n % 2 else 'F',
                    'telephone': f'+237600000{n:03d}',
                    'consentement_traitement': True,
                    'consentement_date': timezone.now(),
                },
            )

        self.stdout.write('Catalogue laboratoire...')
        catalog = {}
        for code, lib, prix in [
            ('NFS', 'Numération formule sanguine', '15000'),
            ('GLY', 'Glycémie à jeun', '5000'),
            ('CREAT', 'Créatininémie', '8000'),
            ('HIV', 'Test VIH', '10000'),
        ]:
            exam, _ = LabTestCatalog.objects.get_or_create(
                code=code,
                defaults={'libelle': lib, 'prix': Decimal(prix)},
            )
            catalog[code] = exam

        self.stdout.write('Commandes laboratoire demo...')
        from laboratory.models import LabOrder, LabResult

        demo_patient = Patient.objects.filter(numero_dossier='PAT-2026-DEMO').first()
        pat1 = Patient.objects.filter(numero_dossier='PAT-2026-0001').first()
        medecin = users.get('MEDECIN')
        biologiste = users.get('BIOLOGISTE')

        if demo_patient and medecin and biologiste:
            o1, _ = LabOrder.objects.get_or_create(
                patient=demo_patient,
                examen=catalog['NFS'],
                statut=LabOrder.Statut.COMMANDE,
                defaults={'medecin_prescripteur': medecin, 'notes': 'Contrôle annuel'},
            )
            o2, created2 = LabOrder.objects.get_or_create(
                patient=demo_patient,
                examen=catalog['GLY'],
                statut=LabOrder.Statut.PRELEVEMENT,
                defaults={
                    'medecin_prescripteur': medecin,
                    'date_prelevement': timezone.now(),
                    'technicien': biologiste,
                },
            )
            if pat1:
                o3, created3 = LabOrder.objects.get_or_create(
                    patient=pat1,
                    examen=catalog['CREAT'],
                    statut=LabOrder.Statut.VALIDATION,
                    defaults={
                        'medecin_prescripteur': medecin,
                        'date_prelevement': timezone.now(),
                        'technicien': biologiste,
                    },
                )
                if created3:
                    LabResult.objects.create(
                        commande=o3,
                        valeur='12.5',
                        unite='mg/L',
                        valeur_reference='7 - 13',
                        commentaire='Dans les normes',
                        saisi_par=biologiste,
                    )

        self.stdout.write('Pharmacie...')

        PHARMA_CATALOG = [
            ('PARA500', 'Paracétamol 500 mg', 'Comprimé', 'ANTALGIQUES', 500, 800, 'Antalgique, antipyrétique'),
            ('PARA1G', 'Paracétamol 1 g', 'Comprimé', 'ANTALGIQUES', 750, 600, 'Douleurs modérées à intenses'),
            ('IBU400', 'Ibuprofène 400 mg', 'Comprimé', 'ANTALGIQUES', 800, 450, 'Anti-inflammatoire non stéroïdien'),
            ('ASPI100', 'Aspirine 100 mg', 'Comprimé', 'ANTALGIQUES', 600, 300, 'Antiagrégant plaquettaire'),
            ('TRAM50', 'Tramadol 50 mg', 'Gélule', 'ANTALGIQUES', 1500, 120, 'Antalgique opioïde faible'),
            ('AMOX500', 'Amoxicilline 500 mg', 'Gélule', 'ANTIBIOTIQUES', 1200, 400, 'Antibiotique à large spectre'),
            ('AMOXCLAV', 'Amoxicilline + Acide clavulanique', 'Comprimé', 'ANTIBIOTIQUES', 2500, 200, 'Infections résistantes'),
            ('CIPRO500', 'Ciprofloxacine 500 mg', 'Comprimé', 'ANTIBIOTIQUES', 1800, 180, 'Fluoroquinolone'),
            ('AZIT500', 'Azithromycine 500 mg', 'Comprimé', 'ANTIBIOTIQUES', 2200, 150, 'Macrolide — pneumopathies'),
            ('METRO400', 'Métronidazole 400 mg', 'Comprimé', 'ANTIBIOTIQUES', 900, 250, 'Anaérobies, parasitoses'),
            ('DOXY100', 'Doxycycline 100 mg', 'Comprimé', 'ANTIBIOTIQUES', 1100, 220, 'Tétracycline'),
            ('CEFTR1G', 'Ceftriaxone 1 g', 'Poudre injectable', 'ANTIBIOTIQUES', 4500, 80, 'Céphalosporine 3e génération'),
            ('GENT80', 'Gentamicine 80 mg/2 ml', 'Ampoule', 'ANTIBIOTIQUES', 3500, 60, 'Aminoside injectable'),
            ('AML5', 'Amlodipine 5 mg', 'Comprimé', 'CARDIO', 1500, 350, 'Antihypertenseur — inhibiteur calcique'),
            ('AML10', 'Amlodipine 10 mg', 'Comprimé', 'CARDIO', 1800, 280, 'Hypertension artérielle'),
            ('LOS50', 'Losartan 50 mg', 'Comprimé', 'CARDIO', 2000, 200, 'Antagoniste des récepteurs AT1'),
            ('ENAL10', 'Énalapril 10 mg', 'Comprimé', 'CARDIO', 1600, 180, 'IEC — insuffisance cardiaque'),
            ('FURO40', 'Furosémide 40 mg', 'Comprimé', 'CARDIO', 700, 400, 'Diurétique de l\'anse'),
            ('ATEN50', 'Atenolol 50 mg', 'Comprimé', 'CARDIO', 900, 250, 'Bêta-bloquant'),
            ('CLOP75', 'Clopidogrel 75 mg', 'Comprimé', 'CARDIO', 3500, 150, 'Antiagrégant plaquettaire'),
            ('METF850', 'Metformine 850 mg', 'Comprimé', 'DIABETE', 1200, 500, 'Antidiabétique oral — biguanide'),
            ('GLIB5', 'Glibenclamide 5 mg', 'Comprimé', 'DIABETE', 800, 300, 'Sulfamide hypoglycémiant'),
            ('INSULN', 'Insuline NPH 100 UI/ml', 'Flacon', 'DIABETE', 8500, 40, 'Insuline à action intermédiaire'),
            ('GLIB2', 'Gliclazide 80 mg', 'Comprimé', 'DIABETE', 1500, 200, 'Sulfamide hypoglycémiant'),
            ('SALB100', 'Salbutamol 100 µg/dose', 'Aérosol', 'RESPIRATOIRE', 3500, 90, 'Bronchodilatateur — crise asthme'),
            ('AMBR30', 'Ambroxol 30 mg/5 ml', 'Sirop', 'RESPIRATOIRE', 2500, 120, 'Mucolytique'),
            ('LORA10', 'Loratadine 10 mg', 'Comprimé', 'RESPIRATOIRE', 900, 350, 'Antihistaminique H1'),
            ('PRED20', 'Prednisolone 20 mg', 'Comprimé', 'RESPIRATOIRE', 600, 280, 'Corticoïde oral'),
            ('OMEP20', 'Oméprazole 20 mg', 'Gélule', 'GASTRO', 1100, 450, 'Inhibiteur de la pompe à protons'),
            ('LOPE2', 'Lopéramide 2 mg', 'Gélule', 'GASTRO', 700, 300, 'Antidiarrhéique'),
            ('SMECT3', 'Smectite 3 g', 'Sachet', 'GASTRO', 500, 600, 'Protecteur muqueux gastrique'),
            ('METOC10', 'Métoclopramide 10 mg', 'Comprimé', 'GASTRO', 600, 220, 'Antémétique, prokinétique'),
            ('COTRI960', 'Sulfaméthoxazole + Triméthoprime', 'Comprimé', 'GASTRO', 900, 180, 'Antibiotique — infections digestives'),
            ('CLOB1', 'Clotrimazole 1 % crème', 'Tube 30 g', 'DERMATO', 1800, 150, 'Antifongique cutané'),
            ('BETA1', 'Bétaméthasone 0,1 % crème', 'Tube 30 g', 'DERMATO', 2200, 120, 'Corticoïde cutané'),
            ('HYDR15', 'Acide hyaluronique 0,15 %', 'Collyre', 'OPHTALMO', 4500, 80, 'Lubrifiant oculaire'),
            ('TOB034', 'Tobramycine 0,3 % collyre', 'Flacon 5 ml', 'OPHTALMO', 3800, 70, 'Antibiotique ophtalmique'),
            ('VITC1000', 'Vitamine C 1000 mg', 'Comprimé effervescent', 'VITAMINES', 800, 400, 'Supplément vitaminien'),
            ('VITD1000', 'Vitamine D3 1000 UI', 'Gélule', 'VITAMINES', 1200, 350, 'Carence en vitamine D'),
            ('FER80', 'Sulfate ferreux 80 mg', 'Comprimé', 'VITAMINES', 900, 280, 'Anémie ferriprive'),
            ('ACFOL5', 'Acide folique 5 mg', 'Comprimé', 'VITAMINES', 500, 500, 'Supplémentation grossesse'),
            ('BETAD125', 'Povidone iodée 10 %', 'Flacon 125 ml', 'ANTISEPTIQUES', 2500, 200, 'Antiseptique cutané'),
            ('CHX025', 'Chlorhexidine 0,25 %', 'Flacon 500 ml', 'ANTISEPTIQUES', 3500, 150, 'Antiseptique hospitalier'),
            ('ALCO70', 'Alcool modifié 70°', 'Flacon 250 ml', 'ANTISEPTIQUES', 1500, 300, 'Désinfection des mains'),
            ('SERUM500', 'Sérum physiologique 0,9 %', 'Poche 500 ml', 'MATERIEL', 1200, 400, 'Perfusion — réhydratation'),
            ('GANTM', 'Gants latex stériles M', 'Boîte 100', 'MATERIEL', 4500, 80, 'Protection individuelle'),
            ('SERING5', 'Seringue 5 ml stérile', 'Unité', 'MATERIEL', 150, 1000, 'Injection IM/IV'),
            ('COMPRES', 'Compresses stériles 10×10', 'Pochette 10', 'MATERIEL', 800, 350, 'Pansements'),
            ('BAND5', 'Bande élastique 5 m', 'Rouleau', 'MATERIEL', 600, 200, 'Immobilisation'),
            ('GLUC50', 'Glucose 50 % ampoule', 'Ampoule 50 ml', 'AUTRE', 1800, 100, 'Hypoglycémie sévère'),
            ('ADRE1', 'Adrénaline 1 mg/ml', 'Ampoule', 'AUTRE', 5500, 50, 'Urgences — anaphylaxie'),
        ]

        for i, (code, nom, forme, cat, prix, qty, desc) in enumerate(PHARMA_CATALOG, start=1):
            med, _ = Medication.objects.update_or_create(
                code=code,
                defaults={
                    'nom': nom,
                    'forme': forme,
                    'categorie': cat,
                    'description': desc,
                    'prix_unitaire': Decimal(str(prix)),
                    'seuil_alerte': 15,
                },
            )
            StockLot.objects.get_or_create(
                medicament=med,
                numero_lot=f'LOT-2026-{i:03d}',
                defaults={
                    'quantite': qty,
                    'date_peremption': date.today() + timedelta(days=365 + (i % 12) * 30),
                    'emplacement': f'RAY-{cat[:3]}-{i % 5 + 1}',
                },
            )

        Insurance.objects.get_or_create(
            code='CNPS',
            defaults={'nom': 'CNPS Cameroun', 'taux_prise_en_charge': Decimal('80')},
        )

        from core.models import HospitalInfo
        HospitalInfo.get_instance()
        info = HospitalInfo.objects.first()
        if info:
            info.nom_etablissement = 'CHU de Brazzaville — Centre Hospitalier Universitaire'
            info.adresse = 'Avenue Amilcar Cabral, BP 32, Brazzaville, République du Congo'
            info.telephone = '+242 06 808 38 38'
            info.urgences_telephone = HOSPITAL_EMERGENCY_PHONE
            info.email = 'accueil@chu-brazzaville.cg'
            info.horaires = (
                'Accueil : Lun-Ven 7h30-18h | Sam 8h-13h\n'
                'Urgences : 24h/24 — 7j/7\n'
                'Consultations spécialisées sur rendez-vous'
            )
            info.description = (
                'Centre Hospitalier Universitaire de Brazzaville — '
                'consultations, urgences, maternité, laboratoire et imagerie médicale.'
            )
            info.site_web = 'https://www.sante.gouv.cg'
            info.latitude = -4.2594
            info.longitude = 15.2847
            info.google_maps_query = 'Centre Hospitalier Universitaire de Brazzaville, Congo'
            info.save()

        # Compte patient de démonstration — email réel pour recevoir le code MFA
        demo_patient_email = (
            getattr(settings, 'MFA_HOSPITAL_EMAIL', '') or settings.EMAIL_HOST_USER or 'patient.demo@example.com'
        ).strip()
        pu, created = User.objects.get_or_create(
            username='patient.demo',
            defaults={
                'email': demo_patient_email,
                'role': 'PATIENT',
                'first_name': 'Marie',
                'last_name': 'Nkounkou',
            },
        )
        pu.role = User.Role.PATIENT
        pu.email = demo_patient_email
        pu.set_password('Patient@2026!')
        pu.is_active = True
        pu.save()
        Patient.objects.get_or_create(
            numero_dossier='PAT-2026-DEMO',
            defaults={
                'user': pu,
                'nom': 'Nkounkou',
                'prenom': 'Marie',
                'date_naissance': date(1995, 6, 12),
                'sexe': 'F',
                'telephone': '+242 06 123 45 67',
                'email': demo_patient_email,
                'adresse': '12 Avenue de la Paix, Bacongo, Brazzaville, Congo',
                'groupe_sanguin': 'O+',
                'consentement_traitement': True,
                'consentement_date': timezone.now(),
            },
        )
        demo_patient = Patient.objects.filter(numero_dossier='PAT-2026-DEMO').first()
        if demo_patient:
            demo_patient.adresse = '12 Avenue de la Paix, Bacongo, Brazzaville, Congo'
            demo_patient.groupe_sanguin = 'O+'
            demo_patient.email = demo_patient_email
            demo_patient.save(update_fields=['adresse', 'groupe_sanguin', 'email', 'updated_at'])

        self.stdout.write('Données cliniques demo patient...')
        from clinical.models import Consultation, Hospitalization, Prescription

        medecin = users.get('MEDECIN')
        demo_patient = Patient.objects.filter(numero_dossier='PAT-2026-DEMO').first()
        lit = Bed.objects.filter(chambre__service__code='URG', numero_lit='1').first()
        if demo_patient and medecin and lit:
            hosp, _ = Hospitalization.objects.get_or_create(
                patient=demo_patient,
                statut=Hospitalization.Statut.ACTIVE,
                defaults={
                    'lit': lit,
                    'medecin_referent': medecin,
                    'date_entree': timezone.now() - timedelta(days=2),
                    'date_sortie_prevue': date.today() + timedelta(days=5),
                    'motif_admission': 'Surveillance post-opératoire — appendicectomie',
                    'notes': 'Patient stable, alimentation reprise',
                },
            )
            cons, _ = Consultation.objects.get_or_create(
                patient=demo_patient,
                diagnostic_cim10='K35.8',
                defaults={
                    'medecin': medecin,
                    'hospitalisation': hosp,
                    'diagnostic_libelle': 'Appendicite aiguë — post-opératoire',
                    'notes_cliniques': 'Évolution favorable',
                    'validee': True,
                    'date_validation': timezone.now(),
                },
            )
            Prescription.objects.get_or_create(
                consultation=cons,
                medicament_nom='Amoxicilline 500 mg',
                defaults={
                    'posologie': '1 gélule × 3/jour',
                    'duree_jours': 7,
                    'instructions': 'Pendant les repas',
                    'validee': True,
                    'verrouillee': True,
                },
            )
            Prescription.objects.get_or_create(
                consultation=cons,
                medicament_nom='Paracétamol 500 mg',
                defaults={
                    'posologie': '1 comprimé si douleur',
                    'duree_jours': 5,
                    'validee': True,
                    'verrouillee': True,
                },
            )

            infirmier = users.get('INFIRMIER')
            para_rx = Prescription.objects.filter(
                consultation=cons, medicament_nom='Paracétamol 500 mg',
            ).first()
            if infirmier:
                from clinical.models import MedicationReminder, NursingCare, VitalSign

                soins_demo = [
                    ('Prise des constantes vitales (TA, FC, SpO2)', timezone.now() - timedelta(hours=6), True),
                    ('Administration Paracétamol 500 mg — douleur légère', timezone.now() - timedelta(hours=2), True),
                    ('Pansement post-opératoire — contrôle cicatrisation', timezone.now() + timedelta(hours=4), False),
                    ('Administration Amoxicilline 500 mg', timezone.now() + timedelta(hours=8), False),
                    ('Surveillance température — 18h', timezone.now() + timedelta(hours=10), False),
                ]
                for desc, planifie, fait in soins_demo:
                    NursingCare.objects.get_or_create(
                        hospitalisation=hosp,
                        description=desc,
                        planifie_a=planifie,
                        defaults={
                            'infirmier': infirmier,
                            'prescription': para_rx if 'Paracétamol' in desc or 'Amoxicilline' in desc else None,
                            'realise_a': planifie if fait else None,
                            'dose_omise': False,
                        },
                    )

                for i, (temp, ta_sys, ta_dia, fc, spo2) in enumerate([
                    (37.2, 120, 78, 72, 98),
                    (36.8, 118, 76, 70, 99),
                    (37.0, 122, 80, 74, 97),
                ]):
                    VitalSign.objects.get_or_create(
                        hospitalisation=hosp,
                        date_prise=timezone.now() - timedelta(hours=8 - i * 4),
                        defaults={
                            'infirmier': infirmier,
                            'temperature': temp,
                            'tension_systolique': ta_sys,
                            'tension_diastolique': ta_dia,
                            'frequence_cardiaque': fc,
                            'saturation_o2': spo2,
                            'notes': 'Surveillance post-opératoire',
                        },
                    )

                MedicationReminder.objects.get_or_create(
                    patient=demo_patient,
                    medicament='Amoxicilline 500 mg',
                    heure_prise=time(8, 0),
                    defaults={'actif': True, 'prescription': Prescription.objects.filter(
                        consultation=cons, medicament_nom='Amoxicilline 500 mg',
                    ).first()},
                )
                MedicationReminder.objects.get_or_create(
                    patient=demo_patient,
                    medicament='Paracétamol 500 mg',
                    heure_prise=time(14, 0),
                    defaults={'actif': True},
                )

        self.stdout.write('Factures demo...')
        from billing.models import Invoice, InvoiceLine

        demo_patient = Patient.objects.filter(numero_dossier='PAT-2026-DEMO').first()
        if demo_patient:
            fac1, created_f1 = Invoice.objects.get_or_create(
                numero='FAC-2026-DEMO01',
                defaults={
                    'patient': demo_patient,
                    'statut': Invoice.Statut.EMISE,
                    'montant_total': Decimal('45000'),
                    'montant_assurance': Decimal('0'),
                    'montant_patient': Decimal('45000'),
                    'montant_paye': Decimal('0'),
                    'emise_le': timezone.now(),
                },
            )
            if created_f1:
                InvoiceLine.objects.create(
                    facture=fac1, type_ligne='ACTE', libelle='Consultation spécialisée',
                    quantite=1, prix_unitaire=Decimal('15000'), montant=Decimal('15000'),
                )
                InvoiceLine.objects.create(
                    facture=fac1, type_ligne='EXAMEN', libelle='Glycémie à jeun',
                    quantite=1, prix_unitaire=Decimal('5000'), montant=Decimal('5000'),
                )
                InvoiceLine.objects.create(
                    facture=fac1, type_ligne='EXAMEN', libelle='Numération formule sanguine',
                    quantite=1, prix_unitaire=Decimal('15000'), montant=Decimal('15000'),
                )
                InvoiceLine.objects.create(
                    facture=fac1, type_ligne='MEDICAMENT', libelle='Ordonnance pharmacie',
                    quantite=1, prix_unitaire=Decimal('10000'), montant=Decimal('10000'),
                )

            fac2, created_f2 = Invoice.objects.get_or_create(
                numero='FAC-2026-DEMO02',
                defaults={
                    'patient': demo_patient,
                    'statut': Invoice.Statut.PAYEE,
                    'montant_total': Decimal('25000'),
                    'montant_assurance': Decimal('0'),
                    'montant_patient': Decimal('25000'),
                    'montant_paye': Decimal('25000'),
                    'emise_le': timezone.now() - timedelta(days=15),
                },
            )
            if created_f2:
                InvoiceLine.objects.create(
                    facture=fac2, type_ligne='NUITEE', libelle='Nuitée hospitalisation',
                    quantite=1, prix_unitaire=Decimal('25000'), montant=Decimal('25000'),
                )

        self.stdout.write('Planning de gardes...')
        now = timezone.now()
        medecin = users['MEDECIN']
        infirmier = users['INFIRMIER']
        for offset, person, garde_type in [
            (0, medecin, 'JOUR'),
            (1, infirmier, 'NUIT'),
            (2, medecin, 'ASTREINTE'),
        ]:
            debut = (now + timedelta(days=offset)).replace(hour=8, minute=0, second=0, microsecond=0)
            fin = debut + timedelta(hours=12)
            ShiftSchedule.objects.get_or_create(
                personnel=person,
                service=urg,
                date_debut=debut,
                defaults={
                    'date_fin': fin,
                    'type_garde': garde_type,
                    'notes': 'Garde de démonstration',
                },
            )

        self.stdout.write(self.style.SUCCESS('Donnees de demo creees avec succes !'))
        self.stdout.write('Comptes : admin / Admin@2026!  |  dr.martin / Medecin@2026!  |  bio.leroy / Bio@2026!')
        self.stdout.write('Patient : patient.demo / Patient@2026!')
        self.stdout.write(
            'MFA par email : personnel → MFA_HOSPITAL_EMAIL (ou Infos pratiques) | patient → email personnel',
        )
