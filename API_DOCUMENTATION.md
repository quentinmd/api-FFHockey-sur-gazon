# 🏒 API Hockey sur Gazon - Documentation Complète

**Status**: ✅ **PRODUCTION READY**  
**Base URL**: `https://api-ffhockey-sur-gazon.fly.dev`  
**Dernière mise à jour**: 25 novembre 2025  
**Déploiement**: Fly.io | **Base de données**: Firebase Realtime Database  

---

## 📑 Table des matières

1. [Championnats disponibles](#-championnats-disponibles)
2. [Endpoints Classements & Matchs](#-endpoints-classements--matchs)
3. [Endpoints Live Score](#-endpoints-live-score)
4. [Webhooks](#-webhooks)
5. [Overlays HTML](#-overlays-html)
6. [Authentification](#-authentification)
7. [Exemples pratiques](#-exemples-pratiques)
8. [Performance](#-performance--caching)

---

## 📋 Championnats disponibles

### 🌾 Gazon (Outdoor)

| Championnat | Route | ManifId | Matchs |
|---|---|---|---|
| **Elite Hommes** | `/api/v1/gazon/elite-hommes/` | 4399 | 28+ |
| **Elite Femmes** | `/api/v1/gazon/elite-femmes/` | 4404 | 45+ |

### 🏛️ Salle (Indoor)

| Championnat | Route | ManifId | Matchs |
|---|---|---|---|
| **Elite Femmes Salle** | `/api/v1/salle/elite-femmes/` | 4403 | Var. |
| **N2 Hommes Salle Zone 3** | `/api/v1/salle/nationale-2-hommes-zone-3/` | 4430 | Var. |

### 🎯 Autres

| Championnat | Route | Matchs |
|---|---|---|
| **Carquefou 1SH** | `/api/v1/carquefou-1sh/` | 10+ |
| **Carquefou 2SH** | `/api/v1/carquefou-2sh/` | 10+ |
| **U14 Garçons** | `/api/v1/interligues-u14-garcons/` | 20+ |
| **U14 Filles** | `/api/v1/interligues-u14-filles/` | 18+ |

---

## 🏆 Endpoints Classements & Matchs

Chaque championnat expose deux endpoints pour les données FFHockey:

### GET Classement
```bash
GET /api/v1/{discipline}/{championship}/classement
```

**Exemple**:
```bash
curl https://api-ffhockey-sur-gazon.fly.dev/api/v1/gazon/elite-hommes/classement
```

**Réponse**:
```json
{
  "success": true,
  "data": [
    {
      "equipe": "BLANC MESNIL HC",
      "matchs_joues": 12,
      "victoires": 10,
      "matchs_nuls": 0,
      "defaites": 2,
      "points_pour": 145,
      "points_contre": 98,
      "difference": 47,
      "points": 30
    }
  ],
  "count": 8,
  "championship": "elite-hommes-gazon",
  "discipline": "gazon"
}
```

### GET Matchs
```bash
GET /api/v1/{discipline}/{championship}/matchs
```

**Exemple**:
```bash
curl https://api-ffhockey-sur-gazon.fly.dev/api/v1/gazon/elite-hommes/matchs
```

**Réponse**:
```json
{
  "success": true,
  "data": [
    {
      "renc_id": "42115",
      "equipe1_nom": "BLANC MESNIL HC",
      "equipe2_nom": "CAM92",
      "date": "2025-12-15T18:00:00",
      "lieu": "Stade Nautique",
      "score_equipe1": 8,
      "score_equipe2": 3,
      "statut": "FINISHED"
    }
  ],
  "count": 28,
  "championship": "elite-hommes-gazon",
  "discipline": "gazon"
}
```

**Statuts possibles**: `SCHEDULED`, `FINISHED`, `CANCELLED`

---

## 🔴 Endpoints Live Score

Matchs en direct gérés via Firebase:

### GET Tous les matchs
```bash
GET /api/v1/live/matches
```

Récupère tous les matchs en direct (~100+)

### GET Un match spécifique
```bash
GET /api/v1/live/match/{match_id}
```

**Exemple**:
```bash
curl https://api-ffhockey-sur-gazon.fly.dev/api/v1/live/match/elite-femmes_193082
```

### PUT Mettre à jour le score
```bash
PUT /api/v1/live/match/{match_id}/score?admin_token=YOUR_TOKEN
```

**Body**:
```json
{
  "score_domicile": 5,
  "score_exterieur": 3
}
```

⚠️ **Déclenche automatiquement les webhooks enregistrés**

### GET Status Firebase
```bash
GET /api/v1/live/status
```

Vérifie la connexion à Firebase

---

## 🔔 Webhooks

### POST Enregistrer un webhook
```bash
POST /api/v1/webhooks/match-update?webhook_url=https://example.com/my-webhook
```

**Réponse**:
```json
{
  "success": true,
  "webhook_id": "27012f60",
  "webhook_url": "https://example.com/my-webhook"
}
```

**Payload reçu** (lors d'une mise à jour de score):
```json
{
  "match_id": "match123",
  "score_domicile": 5,
  "score_exterieur": 3,
  "updated_at": 1762379112,
  "event_type": "score_updated"
}
```

### GET Lister les webhooks
```bash
GET /api/v1/webhooks/list
```

### DELETE Supprimer un webhook
```bash
DELETE /api/v1/webhooks/match-update/{webhook_id}
```

---

## 🎨 Overlays HTML

Prêts à utiliser dans OBS ou autres outils de streaming:

### Score Simple (Équipes + Score + Date)
```
GET /score-simple.html?championship=elite-femmes&renc_id=193082
```

### Score Minimaliste
```
GET /score-only.html?championship=elite-femmes&renc_id=193082
```

---

## 🔐 Authentification

Les endpoints sensibles (PUT, POST) nécessitent:

```bash
?admin_token=YOUR_TOKEN
```

**Tokens**:
- Local: Fichier `.env` (`ADMIN_PASSWORD`)
- Production: Variable `ADMIN_PASSWORD` sur Fly.io

---

## 💡 Exemples pratiques

### 1️⃣ Récupérer le classement Elite Hommes Gazon
```bash
curl https://api-ffhockey-sur-gazon.fly.dev/api/v1/gazon/elite-hommes/classement | json_pp
```

### 2️⃣ Récupérer les matchs Elite Femmes Gazon
```bash
curl https://api-ffhockey-sur-gazon.fly.dev/api/v1/gazon/elite-femmes/matchs | json_pp
```

### 3️⃣ Mettre à jour un score en direct
```bash
curl -X PUT \
  "https://api-ffhockey-sur-gazon.fly.dev/api/v1/live/match/elite-femmes_193082/score?admin_token=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"score_domicile": 4, "score_exterieur": 1}'
```

### 4️⃣ Enregistrer un webhook
```bash
curl -X POST \
  "https://api-ffhockey-sur-gazon.fly.dev/api/v1/webhooks/match-update?webhook_url=https://my-app.com/updates"
```

### 5️⃣ Afficher un overlay dans OBS
```
https://api-ffhockey-sur-gazon.fly.dev/score-simple.html?championship=elite-femmes&renc_id=193082
```

---

## ⚡ Performance & Caching

- **Classement/Matchs**: TTL 5 minutes (FastAPI Cache)
- **Temps de réponse**: 50-150ms généralement
- **Webhooks**: Exécutés en parallèle (non-bloquant)

---

**Créée par**: Équipe Hockey API  
**Déploiement**: Fly.io  
**Repository**: github.com/quentinmd/api-FFHockey-sur-gazon
