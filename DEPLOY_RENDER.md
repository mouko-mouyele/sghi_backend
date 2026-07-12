# 🚀 Guide de Déploiement sur Render

## Prérequis

- Compte GitHub avec ton projet
- Compte Render (https://render.com) - inscription gratuite
- Secret key unique pour production

## Étapes de Déploiement

### 1️⃣ Préparer la branche

```bash
# Commit les derniers changements
git add .
git commit -m "Préparer pour déploiement Render"
git push origin main
```

### 2️⃣ Créer une Secret Key Unique

```bash
# Génère une clé sécurisée
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copie le résultat.

### 3️⃣ Connecter à Render

1. Va sur https://render.com
2. Clique **"New +"** → **"Blueprint"**
3. Sélectionne **"Public Git repository"**
4. Colle l'URL de ton repo GitHub:
   ```
   https://github.com/ton-username/sghi_backend
   ```
5. Clique **"Connect"**

### 4️⃣ Configurer le Blueprint

Render détectera automatiquement `render.yaml` :

- ✅ Service Web (Django) 
- ✅ Base de données PostgreSQL
- ✅ Variables d'environnement

> **Important :** si une erreur mentionne `pythonVersion` ou `DB_HOST`, Render utilise un ancien commit.
> Allez dans le Blueprint → **Manual sync** pour récupérer le dernier commit `main` sur GitHub.

### 5️⃣ Définir les Variables d'Environnement

Render va te demander d'ajouter les variables manquantes :

**Variables à ajouter :**

| Variable | Valeur |
|----------|--------|
| `SECRET_KEY` | Colle la clé générée à l'étape 2 |
| `DEBUG` | `false` |
| `ALLOWED_HOSTS` | `sghi-backend.onrender.com` |
| `EMAIL_HOST_USER` | ton-email@gmail.com (optionnel) |
| `EMAIL_HOST_PASSWORD` | App password Gmail (optionnel) |

**Pour Gmail App Password :**
1. Va sur https://myaccount.google.com/apppasswords
2. Sélectionne "Mail" et "Windows Computer"
3. Copie le mot de passe généré

### 6️⃣ Déployer

1. Clique **"Deploy"**
2. Attends 5-10 minutes (premier build plus long)
3. Checks les logs si erreur

### ✅ Vérification

Ton site est live sur : `https://sghi-backend.onrender.com`

**Test :**
```bash
# API
curl https://sghi-backend.onrender.com/api/v1/...

# Frontend
https://sghi-backend.onrender.com
```

### Application mobile Flutter (Web)

- **URL** : `https://sghi-mobile.onrender.com`
- Site statique (pas de veille comme l'API)
- Build via `mobile/build_web.sh` (Flutter Web)

Après sync du Blueprint, Render crée automatiquement le service **sghi-mobile**.

## 📝 Monitoring

- Render Dashboard : logs en temps réel
- Email alerts sur erreurs
- Redémarrage auto si crash

## 💰 Coût Gratuit

- ✅ Service Web : 750 heures/mois (gratuit)
- ✅ PostgreSQL : gratuit (0,5 GB)
- ✅ Certificat SSL : gratuit
- ❌ Après 15 jours inactivité → spin down (puis spin up à la demande)

## 🔄 Mises à Jour

Chaque push sur `main` redéploie automatiquement :

```bash
git add .
git commit -m "Nouvelle feature"
git push origin main  # Render redéploie automatiquement
```

## 🐛 Troubleshooting

### Service redémarre en boucle
```bash
# Vérifier les migrations
python manage.py migrate --check
# Vérifier la variable SECRET_KEY est définie
```

### Erreur "Permission denied"
- Ajoute `gunicorn` à requirements.txt (déjà fait ✓)
- Vérifier fichiers permissions dans render.yaml

### Frontend pas visible
- Vérifier `npm build` réussit localement
- Vérifier `frontend/dist/index.html` existe

### Problèmes de statiques
- Récréer les static files : `python manage.py collectstatic --noinput`
- Vérifier `STATIC_ROOT` dans render.yaml

## 📚 Ressources

- [Render Docs](https://render.com/docs)
- [Django on Render](https://render.com/docs/deploy-django)
- [Blueprint Guide](https://render.com/docs/infrastructure-as-code)
