# Configuration pour Live Score Platform

## 🚀 Variables d'Environnement

### Backend FastAPI (.env)
```
# Firebase Configuration
FIREBASE_DB_URL=https://api-ffhockey.firebaseio.com
FIREBASE_KEY_PATH=firebase_key.json

# Admin Security
ADMIN_PASSWORD=admin123

# Autres configurations existantes...
```

### Frontend React (.env)
```
VITE_REACT_APP_API_URL=http://localhost:8000
VITE_REACT_APP_ADMIN_PASSWORD=admin123
```

## 🔐 Sécurité

### Obtenir Firebase Service Account Key
1. Aller sur https://console.firebase.google.com
2. Sélectionner votre projet `api-ffhockey`
3. Aller à **Paramètres du projet** → **Comptes de service**
4. Cliquer **Générer une nouvelle clé privée**
5. Télécharger le JSON
6. Renommer et placer dans le dossier API: `firebase_key.json`

### Sécuriser Firebase Realtime Database
Dans Firebase Console:
```json
{
  "rules": {
    "matches": {
      ".read": true,
      ".write": "auth.uid != null"
    }
  }
}
```

## 📦 Installation

### Backend
```bash
pip install firebase-admin==6.2.0
```

### Frontend
```bash
npm install firebase
```

## 🔄 Architecture Live Score

```
CLIENT (React Dashboard)
    ↓
PUT /api/v1/live/match/{id}/score?admin_token=XXX
    ↓
FASTAPI BACKEND
    ↓
Firebase Admin SDK
    ↓
Firebase Realtime DB
    ↓
Notify all listeners in real-time
```

## 📍 Endpoints Disponibles

### GET - Récupérer les données
- `GET /api/v1/live/matches` - Tous les matchs
- `GET /api/v1/live/match/{match_id}` - Un match spécifique

### PUT - Modifier
- `PUT /api/v1/live/match/{match_id}/score?admin_token=XXX`
  ```json
  {"score_domicile": 5, "score_exterieur": 3}
  ```
- `PUT /api/v1/live/match/{match_id}/status?admin_token=XXX`
  ```json
  {"statut": "LIVE"}
  ```

### POST - Ajouter
- `POST /api/v1/live/match/{match_id}/scorer?admin_token=XXX`
  ```json
  {"joueur": "Dupont", "equipe": "domicile", "temps": 25}
  ```
- `POST /api/v1/live/match/{match_id}/card?admin_token=XXX`
  ```json
  {"joueur": "Dupont", "equipe": "domicile", "temps": 45, "couleur": "jaune"}
  ```

### DELETE - Supprimer
- `DELETE /api/v1/live/match/{match_id}?admin_token=XXX`

## 🎯 Utilisation

### Démarrer Backend
```bash
python main.py
```

### Démarrer Frontend
```bash
cd Dashboard
npm run dev
```

### Accéder au Dashboard
```
http://localhost:5173/live-score-admin
```

### Connexion
- **Mot de passe**: `admin123` (configurable via `.env`)

## 🔄 Structure Firebase

```
api-ffhockey/
└── matches/
    └── match123/
        ├── equipe_domicile: "Team A"
        ├── equipe_exterieur: "Team B"
        ├── score_domicile: 5
        ├── score_exterieur: 3
        ├── statut: "LIVE"
        ├── scorers: [
        │   {"joueur": "Dupont", "equipe": "domicile", "temps": 25},
        │   {"joueur": "Martin", "equipe": "exterieur", "temps": 40}
        │ ]
        ├── cards: [
        │   {"joueur": "Dupont", "equipe": "domicile", "temps": 45, "couleur": "jaune"}
        │ ]
        └── last_updated: 1699017600
```

## 🚀 Prochaines Étapes

- [ ] Remplacer simple password par JWT Firebase
- [ ] Ajouter WebSockets pour real-time updates
- [ ] Implémenter les règles de sécurité Firebase
- [ ] Ajouter historique complet des modifications
- [ ] Notifications email/SMS pour fin de match
