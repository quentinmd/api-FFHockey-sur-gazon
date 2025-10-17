# 🚀 Guide de Déploiement - API Hockey sur Gazon France

## Options de déploiement gratuit recommandées

### 1️⃣ **Railway** ⭐ RECOMMANDÉ

Railway est la meilleure option pour une FastAPI :
- ✅ Gratuit ($5/mois de crédits, renouvelés mensuellement)
- ✅ Très facile à utiliser
- ✅ Pas de "cold start" (serveur ne s'endort pas)
- ✅ Support Python natif
- ✅ Interface intuitive

#### Étapes de déploiement sur Railway :

1. **Créer un compte**
   - Aller sur https://railway.app
   - Cliquer "Start Project"
   - Se connecter avec GitHub

2. **Déployer le projet**
   - Cliquer "New Project" → "Deploy from GitHub repo"
   - Autoriser Railway à accéder à votre GitHub
   - Sélectionner votre repo `CHC - Code/V1 - API`
   - Railway détecte automatiquement Python
   - Cliquer "Deploy" → Attendre 2-3 minutes

3. **Obtenir votre URL publique**
   - Dans Railway, aller à "Deployments"
   - Voir votre URL : `https://votre-app-random.railway.app`
   - Tester : `https://votre-app-random.railway.app/docs`

4. **Utiliser votre API**
   ```bash
   # Exemple
   curl https://votre-app-random.railway.app/api/v1/elite-hommes/classement
   ```

---

### 2️⃣ **Render** (Alternative)

Render.com est une bonne alternative, mais avec une limitation :

- ⚠️ Le serveur se met en veille après 15 minutes d'inactivité
- ✅ Redémarrage automatique quand vous appelez l'API
- ✅ Gratuit

#### Étapes :
1. Créer un compte sur https://render.com
2. Créer un nouveau "Web Service"
3. Connecter votre GitHub
4. Configuration :
   - Build command : `pip install -r requirements.txt`
   - Start command : `uvicorn main:app --host 0.0.0.0`
5. Deploy et obtenir votre URL

---

### 3️⃣ **Fly.io**

- ✅ Gratuit (crédits généreux)
- ✅ Bonne performance
- ⚠️ Un peu plus complexe à configurer

---

## 📋 Avant de déployer - Checklist

- [x] `requirements.txt` à jour ✅
- [x] `Procfile` créé ✅
- [x] `Dockerfile` créé ✅
- [x] `.gitignore` créé ✅
- [x] Code testé localement ✅

---

## 🔧 Configuration post-déploiement

Une fois déployé sur Railway/Render, vous pouvez accéder à :

- **API** : `https://votre-url.railway.app`
- **Swagger UI** : `https://votre-url.railway.app/docs`
- **ReDoc** : `https://votre-url.railway.app/redoc`

### Variables d'environnement (optionnel)

Si vous avez besoin de variables d'env :

1. Dans Railway : "Settings" → "Environment"
2. Ajouter vos variables

Pour votre projet actuel, aucune variable d'env n'est nécessaire.

---

## ✅ Vérifier que ça marche

Après déploiement, testez :

```bash
# Classement élite hommes
curl https://votre-url.railway.app/api/v1/elite-hommes/classement

# Matchs Carquefou 1SH
curl https://votre-url.railway.app/api/v1/carquefou/1sh/matchs

# Health check
curl https://votre-url.railway.app/health
```

---

## 📊 Comparaison des plateformes

| Plateforme | Gratuit | Cold Start | Facilité | Support Python |
|-----------|--------|-----------|---------|----------------|
| **Railway** ⭐ | $5/mois | Non | ★★★★★ | Excellent |
| Render | Oui | 15 min | ★★★★☆ | Bon |
| Fly.io | Oui | Non | ★★★☆☆ | Bon |
| PythonAnywhere | Oui | Non | ★★★☆☆ | Excellent |

---

## 🎯 Prochaines étapes

1. Créer un compte Railway
2. Déployer en 1 clic
3. Partager votre URL avec d'autres projets
4. Ajouter d'autres équipes/données facilement

---

**Questions ?** Consultez la documentation officielle :
- Railway : https://docs.railway.app
- Render : https://render.com/docs
- Fly.io : https://fly.io/docs
