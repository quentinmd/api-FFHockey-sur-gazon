# 📧 Email Notifications - Configuration Rapide

## ⚡ Résumé

Le système envoie **automatiquement un email quand un match se termine** (statut = `FINISHED`).

## 🎯 Configuration en 3 étapes

### 1️⃣ Activer Gmail (5 minutes)

**A. Activer la vérification 2FA**
- Allez sur [https://myaccount.google.com/security](https://myaccount.google.com/security)
- Activez "Vérification en 2 étapes"

**B. Créer un mot de passe d'application**
- Dans "Mots de passe d'application"
- Sélectionnez: Application = **Mail**, Appareil = **Votre OS**
- Copiez le mot de passe de 16 caractères (ex: `abcd efgh ijkl mnop`)

### 2️⃣ Créer le fichier `.env`

Dans le dossier racine (à côté de `main.py`), créez un fichier `.env`:

```env
GMAIL_EMAIL=votre_email@gmail.com
GMAIL_PASSWORD=votre_mot_de_passe_de_16_caracteres
```

**Exemple**:
```env
GMAIL_EMAIL=hockey.france@gmail.com
GMAIL_PASSWORD=abcdefghijklmnop
```

### 3️⃣ Démarrer l'API et Dashboard

**Terminal 1 - API**:
```bash
cd /Users/qm/Library/CloudStorage/OneDrive-EcolesGaliléoGlobalEducationFrance/CHC\ -\ Code/V1\ -\ API
python3 main.py
```

**Terminal 2 - Dashboard**:
```bash
cd Dashboard
npm run dev
```

## 📱 Utiliser les notifications

1. Ouvrez le dashboard: http://localhost:5173
2. Scroll down jusqu'à la section "📧 Notifications par Email"
3. Entrez votre email
4. Cliquez "✉️ S'abonner"
5. **Terminé !** Vous recevrez un email à la fin de chaque match

## 📊 Fichiers générés

- `email_subscribers.json`: Liste des emails abonnés
- `notified_matches.json`: Historique des matchs notifiés (pour éviter les doublons)

## 🧪 Test rapide

```bash
# Voir les statistiques
curl http://localhost:8000/api/v1/notifications/stats

# Forcer un test (s'abonner)
curl -X POST http://localhost:8000/api/v1/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "test@gmail.com"}'
```

## ⚠️ Troubleshooting

**"SMTP Authentication failed"**
- ✓ Vérifiez le mot de passe app (copiez sans espaces)
- ✓ Vérifiez que la 2FA est activée

**"Les emails ne s'envoient pas"**
- ✓ Vérifiez que `.env` est dans le bon dossier (racine de l'API)
- ✓ Vérifiez les logs de l'API (Ctrl+C pour voir l'erreur exacte)
- ✓ Vérifiez que votre email est bien dans `email_subscribers.json`

**".env: No such file"**
- ✓ Le fichier `.env` doit être créé manuellement à côté de `main.py`
- ✓ Ne pas oublier le point au début du nom

## 📖 Documentation complète

Voir `EMAIL_NOTIFICATIONS.md` pour plus de détails sur:
- L'architecture complète
- Tous les endpoints disponibles
- Template d'email personnalisable
- Améliorations futures

## 🔐 Sécurité

⚠️ **Important**:
```bash
# Ajouter à .gitignore
echo ".env" >> .gitignore
echo "email_subscribers.json" >> .gitignore
echo "notified_matches.json" >> .gitignore
```

Ne commitez JAMAIS votre fichier `.env` contenant le mot de passe !

---

**Questions ?** Consultez `EMAIL_NOTIFICATIONS.md` pour la doc complète.
