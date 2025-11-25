# 📚 Index de la Documentation

## 📖 Fichiers Principaux

### 🎯 [README_CLEAN.md](./README_CLEAN.md)
**À lire en premier !** Vue d'ensemble de l'API, quick start et architecture.

### 🔌 [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
Documentation complète de tous les endpoints, avec exemples curl et réponses JSON.

### 📝 [CHANGES_QUICK_SUMMARY.md](./CHANGES_QUICK_SUMMARY.md)
Résumé des derniers changements et corrections (git log formaté).

---

## 💾 Archive de Documentation

Anciens fichiers archivés dans le dossier `_ARCHIVE_DOCS/`:

### Déploiement (Obsolète)
- `DEPLOYMENT.md` - Ancienne documentation Fly.io
- `DEPLOYMENT_SUMMARY.md` - Ancien résumé de déploiement
- `DEPLOYMENT_FLYIO.md` - Ancien guide Fly.io détaillé
- `CONFIGURE_FIREBASE_FLYIO.md` - Configuration Firebase ancienne
- `FIREBASE_FLY_SETUP.md` - Setup Firebase ancien
- `GITHUB_RENDER_GUIDE.md` - Guide Render (non-utilisé)
- `RENDER_SEPARATE_SERVICES_GUIDE.md` - Architecture Render (non-utilisé)
- `GITHUB_ET_EMAIL.md` - Intégration GitHub/Email (obsolète)

### Endpoints (Remplacé par API_DOCUMENTATION.md)
- `API_ENDPOINTS_COMPLETE.md` - Ancien format de documentation
- `FILES_OVERLAY.md` - Documentation HTML overlays
- `FIREBASE_LIVE_SCORE_READY.md` - Announcement ancien

### Email (Obsolète)
- `EMAIL_NOTIFICATIONS.md` - Notifications email anciennes
- `EMAIL_SETUP_README.md` - Setup email ancien
- `README_EMAIL_NOTIFICATIONS.md` - Email notifications docs
- `SETUP_EMAIL_RAPIDE.md` - Configuration email rapide

### Live Score & Overlays (Remplacé par API_DOCUMENTATION.md)
- `README_OVERLAY.md` - Documentation HTML overlays
- `OVERLAY_QUICKSTART.md` - Quick start overlays
- `SCORE_OVERLAY_GUIDE.md` - Guide overlays score
- `SCORE_SIMPLE_GUIDE.md` - Guide overlays simples
- `EXPLANATION_LIVE_SCORES.md` - Explication live scores
- `LIVE_SCORE_README.md` - Documentation live scores
- `LIVE_SCORE_SETUP.md` - Setup live scores
- `LIVE_SCORE_QUICK_START.md` - Quick start live scores

### Technique Interne (Référence)
- `FIREBASE_RULES_SETUP.md` - Règles Firebase
- `IMPLEMENTATION_SUMMARY.md` - Résumé implémentation
- `IMPORT_IMPROVEMENTS.md` - Améliorations imports
- `PERFORMANCE_IMPROVEMENTS.md` - Améliorations performance

---

## 🗂️ Structure des Fichiers

```
/ (racine)
├── 📄 README_CLEAN.md              ← Commence ici
├── 📄 API_DOCUMENTATION.md         ← Endpoints détaillés
├── 📄 CHANGES_QUICK_SUMMARY.md     ← Derniers changements
├── 📄 DOCUMENTATION_INDEX.md       ← Ce fichier
│
├── 📁 _ARCHIVE_DOCS/               ← Ancienne documentation
│   ├── API_ENDPOINTS_COMPLETE.md
│   ├── DEPLOYMENT_*.md
│   ├── EMAIL_*.md
│   ├── LIVE_SCORE_*.md
│   └── ... (25+ fichiers archivés)
│
├── 🐍 main.py                      ← API principale (~5246 lignes)
├── 🐍 scraper.py                   ← Scraper FFHockey (~712 lignes)
├── 📋 requirements.txt              ← Dépendances Python
├── 🐳 Dockerfile                   ← Config Docker Fly.io
└── ... (autres fichiers projet)
```

---

## 🎯 Comment utiliser cette documentation

### Pour les **développeurs**:
1. Lire [README_CLEAN.md](./README_CLEAN.md) pour comprendre l'architecture
2. Consulter [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) pour les endpoints
3. Vérifier [CHANGES_QUICK_SUMMARY.md](./CHANGES_QUICK_SUMMARY.md) avant de pusher

### Pour les **utilisateurs de l'API**:
1. Lire [README_CLEAN.md](./README_CLEAN.md) - quick start
2. Utiliser [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) pour les exemples curl
3. Essayer les endpoints directement sur https://api-ffhockey-sur-gazon.fly.dev

### Pour le **déploiement**:
- Documentation à jour: voir `fly.toml` et `Dockerfile`
- Commande: `flyctl deploy --app api-ffhockey-sur-gazon`

---

## 🔄 Workflow de Développement

```bash
# 1. Modifier le code
nano main.py

# 2. Tester localement
python main.py

# 3. Vérifier la syntaxe
python -m py_compile main.py

# 4. Commiter
git add -A && git commit -m "Décrire le changement"

# 5. Pusher
git push origin main

# 6. Déployer
flyctl deploy --app api-ffhockey-sur-gazon
```

---

## ✨ Championnats gérés

| Discipline | Championnat | Route | ManifId |
|---|---|---|---|
| 🌾 Gazon | Elite Hommes | `/gazon/elite-hommes/` | 4399 |
| 🌾 Gazon | Elite Femmes | `/gazon/elite-femmes/` | 4404 |
| 🏛️ Salle | Elite Femmes | `/salle/elite-femmes/` | 4403 |
| 🏛️ Salle | N2 Hommes Zone 3 | `/salle/nationale-2-hommes-zone-3/` | 4430 |
| 🎯 Autres | Carquefou 1SH | `/carquefou-1sh/` | - |
| 🎯 Autres | U14 Garçons | `/interligues-u14-garcons/` | 4400 |
| 🎯 Autres | U14 Filles | `/interligues-u14-filles/` | 4401 |

---

## 🚀 URLs Importantes

- **API Production**: https://api-ffhockey-sur-gazon.fly.dev
- **API Local**: http://localhost:8000
- **Swagger/OpenAPI**: `/docs`
- **Status**: `/api/v1/live/status`
- **Repository**: https://github.com/quentinmd/api-FFHockey-sur-gazon

---

**Mis à jour**: 25 novembre 2025  
**Version**: 1.0 Clean
