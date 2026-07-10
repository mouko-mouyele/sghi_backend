# SGHL — Système de Gestion Hospitalière et de Laboratoire

ERP médical full-stack conforme au cahier des charges GI3 2025-2026.

## Stack

| Couche | Technologie |
|--------|-------------|
| Backend | Python 3.12 · Django 5 · Django Ninja |
| Frontend Web | Vue.js 3 · Tailwind CSS · Axios |
| Mobile | Flutter (dossier séparé recommandé) |
| BDD | PostgreSQL (SQLite en dev) |
| Auth | JWT stateless + rotation refresh tokens |
| Cache KPIs | Redis (optionnel) |

## Démarrage rapide

```bash
# Environnement virtuel
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Migrations & données de démo
python manage.py migrate
python manage.py seed_demo

# Lancer le serveur
python manage.py runserver
```

- **API Docs (Swagger)** : http://127.0.0.1:8000/api/docs
- **Admin Django** : http://127.0.0.1:8000/admin/
- **Santé** : http://127.0.0.1:8000/api/v1/sante

### Comptes de démonstration

| Utilisateur | Mot de passe | Rôle |
|-------------|--------------|------|
| `admin` | `Admin@2026!` | Administrateur |
| `dr.martin` | `Medecin@2026!` | Médecin |
| `bio.leroy` | `Bio@2026!` | Biologiste |

## Frontend Vue.js

```bash
cd frontend
npm install
npm run dev
```

Interface sur http://localhost:5173

## Docker (PostgreSQL + Redis)

```bash
docker-compose up -d
```

## Modules fonctionnels

- **Gestion clinique** : Patients, hospitalisation (Bâtiment → Service → Chambre → Lit), consultations CIM-10, prescriptions verrouillées, soins infirmiers, constantes vitales
- **LIS** : Workflow laboratoire complet avec validation biologiste et immuabilité des résultats
- **Pharmacie** : Stocks par lots, alertes rupture, décrémentation automatique
- **Facturation** : Factures, tiers-payant, paiements partiels, journal comptable
- **RH** : Planning de garde, RBAC strict
- **Audit** : Livre-journal immuable (user, IP, old/new values)

## Tests

```bash
pytest
```

## Structure du projet

```
sghi_backend/
├── accounts/      # Utilisateurs, RBAC, JWT refresh
├── clinical/      # Patients, hospitalisation, soins
├── laboratory/    # LIS
├── pharmacy/      # Stocks & dispensations
├── billing/       # Facturation
├── hr/            # Planning gardes
├── core/          # Audit trail, middleware
├── api/           # Routes Django Ninja /api/v1/
└── frontend/      # Vue.js 3 + Tailwind
```

## Livrables académiques

- [x] API REST versionnée `/api/v1/`
- [x] MCD implémenté (modèles Django)
- [x] Documentation OpenAPI auto-générée
- [x] Tests Pytest
- [x] CI/CD GitHub Actions
- [ ] Application Flutter patient (à développer)
- [ ] DAT & manuels utilisateurs
