#!/bin/bash
# RÉSUMÉ SIMPLE: CE QU'IL FAUT FAIRE

echo "
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║              🚀 PRÊT POUR GITHUB + EMAIL NOTIFICATIONS                   ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 3 ÉTAPES POUR ÊTRE PRÊT:

ÉTAPE 1: CRÉER .env (LOCAL, CHEZ VOUS)
──────────────────────────────────────

Ouvrez un terminal et exécutez:

  \$ cd /Users/qm/Library/CloudStorage/OneDrive-EcolesGaliléoGlobalEducationFrance/CHC\\ -\\ Code/V1\\ -\\ API
  \$ cat > .env << 'ENVEOF'
  GMAIL_EMAIL=votre_email@gmail.com
  GMAIL_PASSWORD=votre_mot_de_passe_app_google_16_caracteres
  ENVEOF

⚠️  Remplacez:
    • votre_email@gmail.com → votre vraie adresse Gmail
    • votre_mot_de_passe_app_google_16_caracteres → le code que Google vous a donné


ÉTAPE 2: VÉRIFIER QUE TOUT EST OK
──────────────────────────────────

  \$ python3 check_email_setup.py

→ Doit afficher 5/6 checks réussis (le .env n'étant pas commité est normal)
→ Tous les imports doivent être OK


ÉTAPE 3: COMMITER SUR GITHUB
────────────────────────────

  \$ git status
  
  → Vérifiez que .env N'EST PAS listé (bon signe!)

  \$ git add .
  \$ git commit -m \"✨ Feat: Email notifications avec Gmail\"
  \$ git push origin main

✅ C'est fait! Tout est sur GitHub et sécurisé.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ CE QUI EST COMMITTÉ:

  ✓ main.py (avec les endpoints email)
  ✓ Newsletter.jsx (composant React)
  ✓ Newsletter.css (styling)
  ✓ App.jsx (intégration)
  ✓ Tous les fichiers de documentation
  ✓ Scripts de test
  ✓ .env.example (template seulement, pas les vrais secrets)
  ✓ .gitignore (met à jour pour protéger .env)


❌ CE QUI NE DOIT PAS ÊTRE COMMITTÉ:

  ✗ .env (vos credentials Gmail) → LOCAL SEULEMENT
  ✗ email_subscribers.json (données privées)
  ✗ notified_matches.json (historique local)
  ✗ .venv/ (virtual environment)
  ✗ __pycache__/ (fichiers compilés)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 APRÈS LE COMMIT, VOICI COMMENT LANCER LE SYSTÈME:

TERMINAL 1 - Lancer l'API:
──────────────────────────
  \$ source .venv/bin/activate
  \$ python3 main.py
  
  → L'API démarre sur http://localhost:8000

TERMINAL 2 - Lancer le dashboard:
──────────────────────────────────
  \$ cd Dashboard
  \$ npm run dev
  
  → Le dashboard démarre sur http://localhost:5173

DANS LE NAVIGATEUR:
──────────────────
  1. Allez sur http://localhost:5173
  2. Scrollez jusqu'à \"📧 Notifications par Email\"
  3. Entrez votre email
  4. Cliquez \"✉️ S'abonner\"
  5. Attendez la fin d'un match
  6. Vous recevrez un email! 🎉

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📖 DOCUMENTATION COMPLÈTE:

  • SETUP_EMAIL_RAPIDE.md ⭐ (5 min) - Configuration Gmail
  • EMAIL_NOTIFICATIONS.md (30 min) - Documentation complète
  • EMAIL_SETUP_README.md (15 min) - Vue d'ensemble

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ BRAVO! VOUS ÊTES PRÊT! 🎉

════════════════════════════════════════════════════════════════════════════
"
