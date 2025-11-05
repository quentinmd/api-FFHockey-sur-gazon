# 🚀 Configuration Firebase sur Fly.io

## ❌ Problème
L'API sur Fly.io retourne : `{"detail":"Firebase non configuré"}`

## ✅ Solution

Vous devez ajouter la clé Firebase en tant que variable d'environnement sur Fly.io.

### Étape 1 : Récupérer la clé Firebase

1. Ouvrez votre fichier `firebase_key.json` local
2. Copiez **tout le contenu JSON** du fichier

**Exemple :**
```json
{
  "type": "service_account",
  "project_id": "api-ffhockey",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  ...
}
```

### Étape 2 : Ajouter la variable d'environnement sur Fly.io

#### Option A : Via le CLI Fly (recommandé)

```bash
fly secrets set FIREBASE_KEY='<VOTRE_CLE_JSON_COMPLETE>' -a api-ffhockey-sur-gazon
```

**Remplacez `<VOTRE_CLE_JSON_COMPLETE>` par le contenu complet du firebase_key.json**

Exemple complet :
```bash
fly secrets set FIREBASE_KEY='{"type":"service_account","project_id":"api-ffhockey","private_key_id":"abc123","private_key":"-----BEGIN PRIVATE KEY-----\n...","client_email":"firebase-adminsdk@...","client_id":"123","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"..."}' -a api-ffhockey-sur-gazon
```

#### Option B : Via le dashboard Fly.io

1. Allez sur https://fly.io/dashboard
2. Sélectionnez votre app `api-ffhockey-sur-gazon`
3. Allez dans **Settings → Secrets**
4. Cliquez sur **+ Add Secret**
5. Nom : `FIREBASE_KEY`
6. Valeur : Collez le contenu complet du firebase_key.json
7. Cliquez **Save**

### Étape 3 : Vérifier la configuration

Après avoir ajouté la variable, Fly redéploiera automatiquement l'app.

Testez l'API :
```bash
curl https://api-ffhockey-sur-gazon.fly.dev/api/v1/live/matches
```

Vous devriez voir les matchs en JSON (pas l'erreur Firebase) ✅

### Étape 4 : Vérifier les logs

Pour voir si Firebase s'est initialisé correctement :

```bash
fly logs -a api-ffhockey-sur-gazon
```

Cherchez les messages :
- ✅ `Firebase key loaded from FIREBASE_KEY environment variable`
- ✅ `Firebase Admin SDK initialized successfully`

## 🔒 Sécurité

⚠️ **IMPORTANT** : Ne jamais commiter `firebase_key.json` sur GitHub !

Vérifiez que `.gitignore` contient :
```
firebase_key.json
.env
```

## 📝 Notes

- Le code API cherche d'abord la variable `FIREBASE_KEY`
- Si elle n'existe pas, il cherche le fichier `firebase_key.json` local
- Si rien n'est trouvé, Firebase est désactivé

## ❓ Aide

Si ça ne marche toujours pas :

1. Vérifiez que la clé JSON est valide (testez-la en local)
2. Assurez-vous qu'il n'y a pas d'erreurs de syntaxe JSON
3. Redéployez manuellement : `fly deploy -a api-ffhockey-sur-gazon`
4. Consultez les logs : `fly logs -a api-ffhockey-sur-gazon --follow`
