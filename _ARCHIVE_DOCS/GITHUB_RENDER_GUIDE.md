# 🚀 GUIDE: Rajouter les Emails sur GitHub + Render

## 📊 Situation actuelle

**Ce que vous avez:**
- ✅ API FastAPI sur Render
- ✅ Requirements.txt avec python-dotenv
- ✅ Dockerfile, Procfile (pour Render)
- ✅ Dashboard quelque part (local ou Vercel)

**Ce que vous avez créé (LOCAL):**
- ✅ Endpoints email dans main.py
- ✅ Composant Newsletter React
- ✅ Documentation complète
- ✅ Scripts de test

---

## ✅ CE QU'IL FAUT RAJOUTER SUR GITHUB

### 1. **METTRE À JOUR main.py** (CRITIQUE)

Votre ancien `main.py` + nouveaux endpoints email

Fichiers à mettre à jour/ajouter:
- `main.py` (modifier - endpoints email dedans)
- `requirements.txt` (vérifier que python-dotenv est là)

### 2. **AJOUTER Dashboard/** (CRITIQUE)

```
Dashboard/
├── src/
│   ├── components/
│   │   └── Newsletter.jsx ← NEW
│   ├── styles/
│   │   └── Newsletter.css ← NEW
│   └── App.jsx ← MODIFIED (ajouter Newsletter)
```

### 3. **DOCUMENTATION** (IMPORTANT)

À ajouter dans le repo racine:
- `SETUP_EMAIL_RAPIDE.md`
- `EMAIL_NOTIFICATIONS.md`
- `EMAIL_SETUP_README.md`
- `IMPLEMENTATION_SUMMARY.md`
- `GITHUB_ET_EMAIL.md`

### 4. **CONFIGURATION** (IMPORTANT)

- `.env.example` ← NOUVEAU (template Gmail)

### 5. **SCRIPTS** (OPTIONNEL)

- `check_email_setup.py`
- `test_email_setup.py`

---

## 📋 COMMANDES POUR AJOUTER SUR GITHUB

```bash
# Allez dans le dossier du repo
cd /Users/qm/Library/CloudStorage/OneDrive-EcolesGaliléoGlobalEducationFrance/CHC\ -\ Code/V1\ -\ API

# Vérifiez l'état
git status

# Ajoutez tous les fichiers
git add .

# Vérifiez avant de commiter
git status
# → Le .env NE doit PAS être listé (il est dans .gitignore)
# → email_subscribers.json NE doit PAS être listé

# Commitez
git commit -m "✨ Feat: Email notifications avec Gmail + Dashboard"

# Poussez sur GitHub
git push origin main
```

---

## 🎯 APRÈS AVOIR PUSHÉ: CONFIGURER RENDER

### Étape 1: Allez sur Render Dashboard
https://dashboard.render.com

### Étape 2: Allez sur votre service API
1. Cliquez sur votre API (ex: "api-FFHockey-sur-gazon")
2. Allez dans l'onglet "Environment"

### Étape 3: Ajoutez les variables Gmail
Cliquez sur "Add Environment Variable" et créez 2 variables:

**Variable 1:**
- Key: `GMAIL_EMAIL`
- Value: `votre_email@gmail.com`

**Variable 2:**
- Key: `GMAIL_PASSWORD`
- Value: `votre_mot_de_passe_app_google_16_caracteres`

### Étape 4: Sauvegardez et redéployez
1. Cliquez "Save"
2. Render redéploie automatiquement
3. Attendez quelques minutes que le déploiement finisse

---

## 🔄 COMMENT ÇA MARCHE AVEC RENDER

**Avant (sans emails):**
```
git push → Render redéploie → API sans endpoints email
```

**Après (avec emails):**
```
git push → Render redéploie → API avec endpoints email + variables Gmail
         → Les emails marchent si GMAIL_EMAIL et GMAIL_PASSWORD sont configurées
```

**Votre dashboard pointe toujours vers:** `https://votre-api.onrender.com`

---

## ✅ CHECKLIST FINAL

- [ ] Fichiers créés localement (vérifiez avec `git status`)
- [ ] `git add .` exécuté
- [ ] `.env` n'est PAS dans la liste (bon signe)
- [ ] `git commit -m "..."` exécuté
- [ ] `git push origin main` exécuté
- [ ] Fichiers visibles sur GitHub
- [ ] Variables Gmail ajoutées dans Render
- [ ] Render a redéployé l'API
- [ ] Dashboard pointe vers https://votre-api.onrender.com

---

## 📖 COMMENT TESTER

**Local (avant de pousser):**
```bash
python3 main.py  # Terminal 1
cd Dashboard && npm run dev  # Terminal 2
```
→ Allez sur http://localhost:5173, testez les emails

**Sur Render (après le déploiement):**
```bash
# La dashboard pointe vers l'URL Render
# Les emails utilisent les variables d'environnement Render
```

---

## ⚠️ IMPORTANT: SÉCURITÉ

**NE JAMAIS commiter:**
- `.env` (fichier local avec secrets) ← .gitignore le protège
- `email_subscribers.json` (données privées) ← .gitignore le protège
- `notified_matches.json` (historique) ← .gitignore le protège

**À TOUJOURS commiter:**
- `.env.example` (template seulement, pas les vrais secrets)
- `.gitignore` (pour montrer ce qui est protégé)
- `main.py` (code du backend)
- Composants et documentation

---

## 🚀 RÉSUMÉ EN 3 ÉTAPES

1. **Pusher sur GitHub:**
   ```bash
   git add .
   git commit -m "✨ Email notifications"
   git push origin main
   ```

2. **Configurer Render (via interface web):**
   - Settings → Environment
   - GMAIL_EMAIL et GMAIL_PASSWORD

3. **Redéployer Render:**
   - Cliquez "Deploy"
   - Attendez ~5-10 min
   - C'est prêt! ✅

---

## 📞 QUESTIONS COURANTES

**Q: Mes anciens endpoints vont disparaître?**
R: Non! Ils vont rester. Vous ajoutez JUSTE les nouveaux endpoints email.

**Q: Render va redéployer automatiquement?**
R: Oui, si vous configurez "Auto-Deploy from Git". Sinon, cliquez "Deploy" manuellement.

**Q: Les emails vont marcher immédiatement?**
R: Oui, une fois que Render a redéployé ET que les variables Gmail sont configurées.

**Q: Je dois faire quelque chose sur le dashboard/Vercel?**
R: Non, rien de spécial. Le dashboard pointe toujours vers la même URL Render.

---

## 📊 STRUCTURE FINAL DE VOTRE REPO

```
api-FFHockey-sur-gazon/
├── main.py ✅ (MODIFIÉ - avec endpoints email)
├── scraper.py ✅
├── requirements.txt ✅
├── .env.example ✨ (NOUVEAU)
├── .gitignore ✅
├── Dockerfile ✅
├── Procfile ✅
├── SETUP_EMAIL_RAPIDE.md ✨ (NOUVEAU)
├── EMAIL_NOTIFICATIONS.md ✨ (NOUVEAU)
├── GITHUB_ET_EMAIL.md ✨ (NOUVEAU)
├── check_email_setup.py ✨ (NOUVEAU)
│
└── Dashboard/ ✨ (NOUVEAU)
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx ✅ (MODIFIÉ)
        ├── main.jsx
        ├── components/
        │   ├── Newsletter.jsx ✨ (NOUVEAU)
        │   ├── Classement.jsx
        │   └── Matchs.jsx
        └── styles/
            ├── Newsletter.css ✨ (NOUVEAU)
            └── ...
```

---

**Besoin d'aide?** Consultez `GITHUB_ET_EMAIL.md` ou `SETUP_EMAIL_RAPIDE.md`

Bonne chance! 🚀
