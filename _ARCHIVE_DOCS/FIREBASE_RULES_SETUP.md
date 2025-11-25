# 🔧 Configuration des Règles de Sécurité Firebase

## Problème
L'erreur `404 Not Found` lors de l'écriture sur la Realtime Database indique que les règles de sécurité bloquent l'accès.

## Solution

### 1️⃣ Allez sur Firebase Console
https://console.firebase.google.com/project/api-ffhockey/database/rules

### 2️⃣ Cliquez sur l'onglet "Règles"

### 3️⃣ Remplacez le contenu par :

```json
{
  "rules": {
    ".read": false,
    ".write": false,
    "matches": {
      ".read": true,
      ".write": "root.child('admin_users').child(auth.uid).exists() || !auth.uid",
      "$matchId": {
        ".validate": "newData.hasChildren(['score_domicile', 'score_exterieur', 'scorers', 'cards', 'statut', 'last_updated'])",
        "score_domicile": {
          ".validate": "newData.isNumber()"
        },
        "score_exterieur": {
          ".validate": "newData.isNumber()"
        },
        "scorers": {
          ".validate": "newData.isArray()"
        },
        "cards": {
          ".validate": "newData.isArray()"
        },
        "statut": {
          ".validate": "newData.isString()"
        },
        "last_updated": {
          ".validate": "newData.isNumber()"
        }
      }
    }
  }
}
```

### 4️⃣ Ou utilisez une version PERMISSIVE pour développement :

⚠️ **NE PAS UTILISER EN PRODUCTION**

```json
{
  "rules": {
    ".read": true,
    ".write": true
  }
}
```

### 5️⃣ Cliquez sur "Publier"

### 6️⃣ Attendez la confirmation

## Après avoir mis à jour les règles

Testez avec :
```bash
curl -X POST "http://localhost:8000/api/v1/live/match/match_001/init?admin_token=admin123" \
  -H "Content-Type: application/json"
```

Vous devriez voir :
```json
{
  "success": true,
  "message": "Match match_001 initialisé",
  "match_id": "match_001"
}
```

## En cas de doute

1. Vérifiez que la Realtime Database **existe** dans Firebase Console
2. Assurez-vous que le projet est **api-ffhockey**
3. Vérifiez que vous êtes admin Firebase
4. Essayez de recharger la page Firebase Console
5. Tentez de relancer l'API

