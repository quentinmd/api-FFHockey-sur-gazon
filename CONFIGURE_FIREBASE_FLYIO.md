# 🚀 Configuration Firebase sur Fly.io - Guide Sécurisé

## ❌ Problème
L'API retourne : `{"detail":"Firebase non configuré"}`

## ✅ Solution

Vous devez ajouter votre clé Firebase en tant que **secret** sur Fly.io (elle ne sera pas exposée dans le code).

### Étape 1 : Aller sur le dashboard Fly.io

1. Ouvrez : **https://fly.io/dashboard**
2. Connectez-vous si nécessaire
3. Sélectionnez votre app **`api-ffhockey-sur-gazon`**

### Étape 2 : Ajouter la variable d'environnement

1. Allez dans l'onglet **Settings**
2. Cliquez sur **Secrets** (dans le menu gauche)
3. Cliquez sur **+ Add Secret**

### Étape 3 : Configurer Firebase Key

**Nom du secret :**
```
FIREBASE_KEY
```

**Valeur du secret :**
1. Sur votre ordinateur, ouvrez le fichier `firebase_key.json` local
2. Copiez **tout le contenu JSON** (Ctrl+A puis Ctrl+C)
3. Collez-le dans le champ "Valeur" sur Fly

> ⚠️ **IMPORTANT** : Copiez-collez le JSON exactement comme il est. Ne modifiez rien.

### Étape 4 : Sauvegarder

1. Cliquez sur **+ Add Secret**
2. Fly redéploiera automatiquement votre app (2-3 minutes)

### Étape 5 : Vérifier que ça marche

Attendez que le déploiement soit terminé, puis testez :

```bash
curl https://api-ffhockey-sur-gazon.fly.dev/api/v1/elite-femmes/matchs
```

Vous devriez voir les matchs en JSON au lieu de l'erreur Firebase ! ✅

---

## 🔍 Vérifier les logs

Pour voir si Firebase s'est initialisé correctement :

1. Dashboard Fly → App `api-ffhockey-sur-gazon`
2. Onglet **Monitoring** → **Logs**
3. Cherchez les messages :
   - ✅ `Firebase key loaded from FIREBASE_KEY environment variable`
   - ✅ `Firebase Admin SDK initialized successfully`

Si vous voyez ces messages = Firebase fonctionne ! 🎉

---

## ❓ Aide - Ça ne marche toujours pas ?

### Vérifier que le secret a bien été ajouté

1. Dashboard Fly → app `api-ffhockey-sur-gazon` → Settings → Secrets
2. Vous devriez voir `FIREBASE_KEY` dans la liste

### Le JSON n'est pas valide ?

1. Testez le JSON en local d'abord avec un outil comme https://jsonlint.com/
2. Assurez-vous qu'il n'y a pas d'erreurs de syntaxe
3. Vérifiez que tous les `"` sont présents

### Redéployer manuellement

1. Dashboard Fly → app `api-ffhockey-sur-gazon`
2. Onglet **Deploy**
3. Bouton **Deploy again**

### Lire les logs détaillés

Dashboard Fly → app → Monitoring → Logs → cherchez les erreurs Firebase

---

## ✅ URLs de test une fois Firebase configuré

```bash
# Tous les matchs Elite Femmes
curl https://api-ffhockey-sur-gazon.fly.dev/api/v1/elite-femmes/matchs

# Score simple overlay
https://api-ffhockey-sur-gazon.fly.dev/score-simple.html?championship=elite-femmes&renc_id=193082

# Score only overlay (2 scores côte à côte)
https://api-ffhockey-sur-gazon.fly.dev/score-only.html?championship=elite-femmes&renc_id=193082
```

---

## 🔒 Sécurité

✅ **Chez vous en local :**
- Gardez `firebase_key.json` **JAMAIS** commité sur GitHub
- Vérifiez que `.gitignore` contient :
  ```
  firebase_key.json
  .env
  ```

✅ **Sur Fly.io :**
- La clé est stockée de manière sécurisée
- Elle n'est PAS visible dans l'interface
- Elle n'est injectée QUE dans les variables d'environnement

✅ **Dans le code :**
- L'API cherche d'abord la variable `FIREBASE_KEY` (utilisée sur Fly)
- Ensuite le fichier `firebase_key.json` (utilisé en local)
- Si rien n'est trouvé, Firebase est désactivé
