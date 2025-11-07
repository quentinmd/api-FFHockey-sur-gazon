# Guide de Déploiement sur Fly.io

## 📋 Prérequis

- Compte Fly.io (gratuit : https://fly.io)
- Fly CLI installé : `brew install flyctl`
- GitHub avec le repo
- Variables d'environnement Firebase

## 🚀 Déploiement de l'API FastAPI

### 1. Configurer les variables d'environnement sur Fly.io

```bash
# Se connecter à Fly
fly auth login

# Aller dans le répertoire de l'API
cd "/Users/qm/Library/CloudStorage/OneDrive-EcolesGaliléoGlobalEducationFrance/CHC - Code/V1 - API"

# Ajouter les secrets Fly
fly secrets set \
  FIREBASE_DB_URL="https://api-ffhockey-default-rtdb.europe-west1.firebasedatabase.app" \
  ADMIN_PASSWORD="admin123"

# Ajouter la clé Firebase comme secret
fly secrets set --file firebase_key.json
```

### 2. Déployer l'API

```bash
# Build et déployer
fly deploy

# Vérifier le déploiement
fly status
fly logs
```

L'API sera accessible à : **https://api-ffhockey-sur-gazon.fly.dev**

## 🎨 Déploiement du Dashboard React

### 1. Build du Dashboard

```bash
cd Dashboard

# Créer le fichier .env.production
cat > .env.production << EOF
VITE_API_URL=https://api-ffhockey-sur-gazon.fly.dev
VITE_ADMIN_PASSWORD=admin123
EOF

# Build Vite
npm run build

# Cela crée un dossier 'dist' avec les fichiers statiques
```

### 2. Servir le Dashboard depuis Fly

**Option A : Depuis l'API FastAPI**

Placez les fichiers du Dashboard dans le dossier `public/` de l'API et configurez FastAPI pour les servir :

```python
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="public", html=True), name="static")
```

**Option B : Déployer séparément sur Netlify/Vercel (recommandé)**

```bash
# Sur Netlify
npm run build
# Uploadez le dossier 'dist'

# URL: https://votre-domaine.netlify.app
```

## 🔧 Configuration pour Production

### Variables d'environnement critiques

**API (.env)**
```
FIREBASE_DB_URL=https://api-ffhockey-default-rtdb.europe-west1.firebasedatabase.app
FIREBASE_KEY_PATH=/path/to/firebase_key.json
ADMIN_PASSWORD=admin123
```

**Dashboard (.env.production)**
```
VITE_API_URL=https://api-ffhockey-sur-gazon.fly.dev
VITE_ADMIN_PASSWORD=admin123
```

## ✨ Utiliser les VRAIS Matchs en Production

### Endpoints disponibles

1. **Import de démo** (4 matchs de test)
   ```
   POST /api/v1/live/import-demo?admin_token=admin123
   ```

2. **Import des vrais matchs**
   ```
   POST /api/v1/live/import-real-data/{championship}?admin_token=admin123
   
   Championnats: elite-hommes, elite-femmes, u14-garcons, u14-filles,
                 carquefou-1sh, carquefou-2sh, carquefou-sd, salle-elite-femmes
   ```

### Depuis le Dashboard
- Sélectionner le championnat dans le dropdown
- Cliquer sur "Importer matchs"
- Attendre que les vrais matchs se chargent depuis l'API FFHockey
- Les matchs apparaissent en temps réel dans Firebase

## 📊 Monitoring

```bash
# Voir les logs
fly logs

# Vérifier la santé
fly status

# Arrêter l'app
fly suspend

# Redémarrer
fly resume
```

## 🔐 Sécurité

- ✅ Authentification admin via token dans les queries
- ✅ Firebase Realtime Database (règles = read/write public en dev)
- ✅ CORS activé pour localhost et domaines approuvés
- ✅ HTTPS forcé sur Fly.io

**À faire pour production :**
- [ ] Configurer Firebase Rules pour l'authentification
- [ ] Ajouter rate limiting
- [ ] Chiffrer la clé Firebase en transit
- [ ] Logs centralisés

## 📞 Dépannage

| Problème | Solution |
|----------|----------|
| 404 Not Found | Endpoint inexistant ou endpoint déploié ne correspond pas au code local |
| Timeout | API FFH lente - augmenter timeout à 60+ secondes |
| Firebase vide | Vérifier que FIREBASE_DB_URL est correct |
| CORS error | Ajouter origin au CORS dans FastAPI |

## 🎯 Checklist Pré-Déploiement

- [ ] Code committé sur GitHub
- [ ] Variables d'environnement configurées
- [ ] Firebase clé uploadée sur Fly
- [ ] Tests locaux passants
- [ ] Dashboard build fonctionnel en local
- [ ] Endpoints API testés
- [ ] Import de vrais matchs fonctionnel

**Bon déploiement ! 🚀**
