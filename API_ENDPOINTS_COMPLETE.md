# 🚀 API Hockey sur Gazon - Endpoints Complets

**Date**: 5 novembre 2025  
**Status**: ✅ **PRODUCTION READY**  
**Base URL Production**: `https://api-ffhockey-sur-gazon.fly.dev`  
**Base URL Local**: `http://localhost:8000`  

---

## 📊 LIVE SCORE ENDPOINTS

### 1️⃣ Récupérer TOUS les matchs en direct
```bash
GET /api/v1/live/matches
```

**Description**: Retourne les 100+ matchs en direct depuis Firebase

**Réponse**:
```json
{
  "success": true,
  "data": {
    "elite-femmes_193081": {
      "championship": "elite-femmes",
      "equipe_domicile": "CA MONTROUGE 92",
      "equipe_exterieur": "RACING CLUB DE FRANCE",
      "score_domicile": 1,
      "score_exterieur": 1,
      "statut": "FINISHED"
    },
    ...
  }
}
```

---

### 2️⃣ Récupérer UN match spécifique ⭐ **NOUVEAU**
```bash
GET /api/v1/live/match/{match_id}
```

**Description**: Récupère rapidement UN match sans charger tous les 100+

**Exemple**:
```bash
curl https://api-ffhockey-sur-gazon.fly.dev/api/v1/live/match/elite-femmes_193082
```

**Réponse**:
```json
{
  "success": true,
  "match_id": "elite-femmes_193082",
  "data": {
    "championship": "elite-femmes",
    "equipe_domicile": "PHC MARCQ-EN-BAROEUL",
    "equipe_exterieur": "CARQUEFOU HC",
    "score_domicile": 3,
    "score_exterieur": 0,
    "statut": "FINISHED"
  }
}
```

---

### 3️⃣ Récupérer matchs d'un championnat ⭐ **NOUVEAU**
```bash
GET /api/v1/live/matches/by-championship/{championship}
```

**Description**: Retourne uniquement les matchs d'un championnat spécifique

**Exemples**:
```bash
# Elite Femmes
curl https://api-ffhockey-sur-gazon.fly.dev/api/v1/live/matches/by-championship/elite-femmes

# Elite Hommes
curl https://api-ffhockey-sur-gazon.fly.dev/api/v1/live/matches/by-championship/elite-hommes
```

**Réponse**:
```json
{
  "success": true,
  "championship": "elite-femmes",
  "count": 50,
  "data": {
    "elite-femmes_193081": {...},
    "elite-femmes_193082": {...}
  }
}
```

---

### 4️⃣ Mettre à jour le score d'un match
```bash
PUT /api/v1/live/match/{match_id}/score?admin_token=admin123
```

**Body**:
```json
{
  "score_domicile": 5,
  "score_exterieur": 3
}
```

**Exemple**:
```bash
curl -X PUT \
  "http://localhost:8000/api/v1/live/match/match123/score?admin_token=admin123" \
  -H "Content-Type: application/json" \
  -d '{"score_domicile": 5, "score_exterieur": 3}'
```

**Réponse**:
```json
{
  "success": true,
  "message": "Score du match match123 mis à jour",
  "score_domicile": 5,
  "score_exterieur": 3,
  "backend": "Firebase",
  "webhooks_notified": 2
}
```

⚠️ **Important**: 
- Remplacer `admin_token` par le vrai token (env: `ADMIN_PASSWORD`)
- Déclenche automatiquement les webhooks enregistrés

---

### 5️⃣ Vérifier le statut Firebase
```bash
GET /api/v1/live/status
```

**Réponse**:
```json
{
  "status": "OK",
  "firebase_connected": true,
  "message": "Firebase est configuré et connecté"
}
```

---

## 🔔 WEBHOOKS ENDPOINTS ⭐ **NOUVEAUX**

### 6️⃣ Enregistrer un webhook
```bash
POST /api/v1/webhooks/match-update?webhook_url=https://example.com/my-webhook
```

**Description**: Enregistre une URL pour recevoir les notifications de mise à jour

**Exemple**:
```bash
curl -X POST \
  "https://api-ffhockey-sur-gazon.fly.dev/api/v1/webhooks/match-update?webhook_url=https://webhook.site/test"
```

**Réponse**:
```json
{
  "success": true,
  "message": "Webhook enregistré avec succès",
  "webhook_id": "27012f60",
  "webhook_url": "https://webhook.site/test"
}
```

💡 **Quand est appelé ?**  
À chaque fois qu'un score est mis à jour via PUT `/api/v1/live/match/{match_id}/score`

**Payload reçu au webhook**:
```json
{
  "match_id": "match123",
  "score_domicile": 5,
  "score_exterieur": 3,
  "updated_at": 1762379112,
  "event_type": "score_updated"
}
```

---

### 7️⃣ Lister les webhooks enregistrés
```bash
GET /api/v1/webhooks/list
```

**Réponse**:
```json
{
  "success": true,
  "count": 2,
  "webhooks": {
    "27012f60": {
      "url": "https://webhook.site/test",
      "registered_at": 1762379112.6235251,
      "active": true
    },
    "a1b2c3d4": {
      "url": "https://example.com/webhook",
      "registered_at": 1762379000,
      "active": true
    }
  }
}
```

---

### 8️⃣ Désenregistrer un webhook
```bash
DELETE /api/v1/webhooks/match-update/{webhook_id}
```

**Exemple**:
```bash
curl -X DELETE \
  "https://api-ffhockey-sur-gazon.fly.dev/api/v1/webhooks/match-update/27012f60"
```

**Réponse**:
```json
{
  "success": true,
  "message": "Webhook 27012f60 supprimé avec succès"
}
```

---

## 🎨 OVERLAY HTML ENDPOINTS

### Score Simple (Avec équipes + date)
```bash
GET /score-simple.html?championship=elite-femmes&renc_id=193082
```

### Score Uniquement (Minimaliste)
```bash
GET /score-only.html?championship=elite-femmes&renc_id=193082
```

---

## 📋 CHAMPIONNATS DISPONIBLES

| Championship | ID | Matches |
|---|---|---|
| Elite Hommes | `elite-hommes` | 50 |
| Elite Femmes | `elite-femmes` | 50 |
| Salle Elite Femmes | `salle-elite-femmes` | Var. |
| U14 Garçons | `interligues-u14-garcons` | 20+ |
| U14 Filles | `interligues-u14-filles` | 18+ |
| Carquefou 1SH | `carquefou-1sh` | 10 |
| Carquefou 2SH | `carquefou-2sh` | 10 |

---

## 🔐 AUTHENTIFICATION

Les endpoints sensibles (PUT, POST) nécessitent un token admin:

```bash
?admin_token=YOUR_TOKEN
```

**Où trouver le token ?**
- Local: Fichier `.env` ou `ADMIN_PASSWORD`
- Production: Variable `ADMIN_PASSWORD` sur Fly.io

---

## 💡 EXEMPLES D'UTILISATION

### 1. Afficher un overlay dans OBS
```
https://api-ffhockey-sur-gazon.fly.dev/score-simple.html?championship=elite-femmes&renc_id=193082
```

### 2. Récupérer le score actuel
```bash
curl https://api-ffhockey-sur-gazon.fly.dev/api/v1/live/match/elite-femmes_193082
```

### 3. Mettre à jour le score
```bash
curl -X PUT \
  "https://api-ffhockey-sur-gazon.fly.dev/api/v1/live/match/elite-femmes_193082/score?admin_token=admin123" \
  -H "Content-Type: application/json" \
  -d '{"score_domicile": 4, "score_exterieur": 1}'
```

### 4. Enregistrer un webhook pour notifications temps réel
```bash
curl -X POST \
  "https://api-ffhockey-sur-gazon.fly.dev/api/v1/webhooks/match-update?webhook_url=https://my-app.com/updates"
```

---

## 📊 RÉSUMÉ DES ENDPOINTS

| Méthode | Endpoint | Description | Status |
|---|---|---|---|
| GET | `/api/v1/live/matches` | Tous les matchs | ✅ |
| GET | `/api/v1/live/match/{match_id}` | Un match spécifique | ✅ **NOUVEAU** |
| GET | `/api/v1/live/matches/by-championship/{championship}` | Matchs par championnat | ✅ **NOUVEAU** |
| GET | `/api/v1/live/status` | Status Firebase | ✅ |
| PUT | `/api/v1/live/match/{match_id}/score` | Mettre à jour score | ✅ |
| POST | `/api/v1/webhooks/match-update` | Enregistrer webhook | ✅ **NOUVEAU** |
| GET | `/api/v1/webhooks/list` | Lister webhooks | ✅ **NOUVEAU** |
| DELETE | `/api/v1/webhooks/match-update/{webhook_id}` | Supprimer webhook | ✅ **NOUVEAU** |
| GET | `/score-simple.html` | Overlay score + infos | ✅ |
| GET | `/score-only.html` | Overlay score uniquement | ✅ |

---

## ⚡ PERFORMANCE

- **Récupérer tous les matchs**: ~100-200ms
- **Récupérer un match**: ~50-100ms ⚡
- **Filtrer par championship**: ~100-150ms ⚡
- **Mettre à jour score**: ~50-100ms + webhooks

**Webhooks**: Exécutés en parallèle (non-bloquant)

---

## 🎯 Prochaines Améliorations Possibles

- [ ] WebSockets pour temps réel pur
- [ ] Authentification JWT
- [ ] Panel Admin web
- [ ] Statistiques (meilleurs buteurs, etc.)
- [ ] Classements temps réel
- [ ] Rate limiting
- [ ] Caching avancé

---

**API créée et maintenue par**: Équipe Hockey API  
**Dernière mise à jour**: 5 novembre 2025  
**Déploiement**: Fly.io  
**Base de données**: Firebase Realtime Database
