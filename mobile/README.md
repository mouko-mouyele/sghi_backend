# SGHL Mobile — Patient & Médecin

Application Flutter (Android, iOS, **Chrome/Web**) connectée au backend Django.

## Profils supportés

| Profil | Compte démo | Mot de passe |
|--------|-------------|--------------|
| **Patient** | `patient.demo` | `Patient@2026!` |
| **Médecin** | `dr.martin` | `Medecin@2026!` |

Les autres rôles (admin, infirmier, etc.) utilisent le **portail web** Vue.js.

## Prérequis

1. Backend Django lancé : `python manage.py runserver` (port **8000**)
2. Flutter SDK 3.2+

## Hébergement gratuit (Render Web)

L'app Flutter **Web** est déployée sur Render en site statique :

- **URL** : [https://sghi-mobile.onrender.com](https://sghi-mobile.onrender.com)
- **Backend API** : [https://sghi-backend.onrender.com/api/v1](https://sghi-backend.onrender.com/api/v1)

Build local (identique à Render) :

```bash
cd mobile
flutter pub get
flutter build web --release --dart-define=SGHL_API_URL=https://sghi-backend.onrender.com/api/v1
# Fichiers dans build/web/
```

Sur téléphone : ouvrez l'URL dans Chrome/Safari → **Ajouter à l'écran d'accueil** (PWA).

## Lancer dans Chrome (développement local)

```bash
cd mobile
flutter pub get
flutter run -d chrome
```

L'API pointe automatiquement vers `http://127.0.0.1:8000/api/v1` en mode web.

## Android émulateur

```bash
flutter run -d android
```

URL API : `http://10.0.2.2:8000/api/v1`

## Fonctionnalités

### Patient
- Tableau de bord (RDV, labo, factures, hospitalisation)
- Rendez-vous
- Plan de soins & ordonnances
- Résultats laboratoire
- **Pharmacie** : catalogue, panier, suivi des demandes
- **Factures & paiement** : payer directement dans l'app via **Mobile Money** (MTN MoMo / Airtel Money)
- **Carte patient PDF** : téléchargement, ouverture en ligne, lien QR dossier médical
- Inscription avec téléphone obligatoire

### Médecin
- Agenda rendez-vous
- Liste patients (recherche)
- **Pharmacie** : catalogue, stocks (lecture seule), demandes patients
- Profil médecin
