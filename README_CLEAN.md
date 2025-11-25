# 🏒 API FFHockey sur Gazon

API moderne et performante pour les championnats de hockey sur gazon et salle.

**Status**: ✅ **PRODUCTION READY**  
**Déploiement**: Fly.io  
**Base de données**: Firebase Realtime Database  

---

## 🚀 Quick Start

```bash
# Démarrer l'API localement
python main.py

# Ou via FastAPI
uvicorn main:app --reload
```

**L'API sera disponible à**: `http://localhost:8000`

---

## 📚 Documentation

### 📖 [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
Documentation complète des endpoints, championnats disponibles et exemples d'utilisation.

### 📝 [CHANGES_QUICK_SUMMARY.md](./CHANGES_QUICK_SUMMARY.md)
Résumé des derniers changements et mises à jour.

---

## 🌐 Championnats disponibles

### 🌾 Gazon
- **Elite Hommes** (`/api/v1/gazon/elite-hommes/`)
- **Elite Femmes** (`/api/v1/gazon/elite-femmes/`)

### 🏛️ Salle
- **Elite Femmes Salle** (`/api/v1/salle/elite-femmes/`)
- **N2 Hommes Salle Zone 3** (`/api/v1/salle/nationale-2-hommes-zone-3/`)

### 🎯 Autres
- Carquefou 1SH & 2SH
- U14 Garçons & Filles

---

## 🛠️ Architecture

### Fichiers principaux

| Fichier | Description |
|---|---|
| **main.py** | Application FastAPI principale (~5246 lignes) |
| **scraper.py** | Récupération des données FFHockey |
| **requirements.txt** | Dépendances Python |
| **Dockerfile** | Configuration Docker pour Fly.io |

### Structure API

```
/api/v1/
  ├── /gazon/
  │   ├── elite-hommes/
  │   │   ├── classement
  │   │   └── matchs
  │   └── elite-femmes/
  │       ├── classement
  │       └── matchs
  ├── /salle/
  │   ├── elite-femmes/
  │   │   ├── classement
  │   │   └── matchs
  │   └── nationale-2-hommes-zone-3/
  │       ├── classement
  │       └── matchs
  ├── /live/ (Firebase)
  │   ├── matches
  │   ├── match/{id}
  │   └── match/{id}/score
  └── /webhooks/
      ├── match-update
      └── list
```

---

## 🔑 Endpoints Clés

### Classements & Matchs
```bash
GET /api/v1/{discipline}/{championship}/classement
GET /api/v1/{discipline}/{championship}/matchs
```

### Live Score (Firebase)
```bash
GET /api/v1/live/matches
PUT /api/v1/live/match/{id}/score?admin_token=TOKEN
```

### Webhooks
```bash
POST /api/v1/webhooks/match-update?webhook_url=...
DELETE /api/v1/webhooks/match-update/{webhook_id}
```

**Voir [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) pour la documentation complète**

---

## 🔧 Configuration

### Variables d'environnement

```bash
# Firebase
FIREBASE_URL=https://votre-project.firebaseio.com
FIREBASE_KEY={"type":"service_account",...}

# Admin
ADMIN_PASSWORD=your_secret_token

# Notifications (optionnel)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password
```

### Déploiement sur Fly.io

```bash
# Login
flyctl auth login

# Déployer
flyctl deploy --app api-ffhockey-sur-gazon
```

---

## 📊 Performance

- **Classement/Matchs**: 50-150ms (avec cache 5min)
- **Live Score**: <100ms
- **Webhooks**: Asynchrone (non-bloquant)

---

## 🤝 Contribution

Les modifications doivent être:
1. Testées localement avec `python -m py_compile main.py`
2. Commitées avec message explicite
3. Pushées à GitHub
4. Déployées sur Fly.io via `flyctl deploy`

---

## 📦 Stack Technologique

- **Framework**: FastAPI 0.95+
- **Python**: 3.9+
- **Database**: Firebase Realtime Database
- **Hosting**: Fly.io (Docker)
- **Caching**: cachetools (TTL 5min)
- **External API**: FFHockey REST API

---

## 📞 Support

- **Repository**: [github.com/quentinmd/api-FFHockey-sur-gazon](https://github.com/quentinmd/api-FFHockey-sur-gazon)
- **Production**: https://api-ffhockey-sur-gazon.fly.dev
- **Status**: `/api/v1/live/status`

---

**Dernière mise à jour**: 25 novembre 2025
