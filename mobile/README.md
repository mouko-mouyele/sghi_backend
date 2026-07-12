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

## Hébergement gratuit (GitHub Pages)

L'app Flutter **Web** est déployée automatiquement via **GitHub Actions** :

- **URL** : [https://mouko-mouyele.github.io/sghi_backend/](https://mouko-mouyele.github.io/sghi_backend/)
- **Backend API** : [https://sghi-backend.onrender.com/api/v1](https://sghi-backend.onrender.com/api/v1)

### Activer GitHub Pages (une seule fois)

1. GitHub → repo **sghi_backend** → **Settings** → **Pages**
2. Source : branche **`gh-pages`** / dossier **`/ (root)`**
3. Sauvegarder — après le prochain push sur `main`, l'app sera en ligne

Build manuel :

```bash
cd mobile
bash build_web.sh
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
