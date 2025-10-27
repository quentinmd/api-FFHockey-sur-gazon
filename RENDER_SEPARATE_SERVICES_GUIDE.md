╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║     ✅ DÉPLOIEMENT: DEUX SERVICES RENDER SÉPARÉS (API + DASHBOARD)       ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

🎯 MODIFICATIONS EFFECTUÉES:

✅ App.jsx → API_BASE ajusté pour Render
✅ package.json → "serve" ajouté pour servir les fichiers statiques
✅ Dashboard/render.yaml → Configuration Render créée


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 PROCHAINES ÉTAPES:

ÉTAPE 1: Commit et Push sur GitHub
───────────────────────────────────

$ git add .
$ git commit -m "🚀 Setup separate Render services for API and Dashboard"
$ git push origin main

Attendez que le push soit terminé ✓


ÉTAPE 2: Service 1 - Vérifier votre API existante sur Render
─────────────────────────────────────────────────────────────

1. Allez sur https://dashboard.render.com
2. Cliquez sur votre service API existant (ex: "api-ffhockey")
3. Vérifiez les paramètres:

   ✓ Root directory: / (racine du projet)
   ✓ Build command: pip install -r requirements.txt
   ✓ Start command: gunicorn -k uvicorn.workers.UvicornWorker main:app
   ✓ Environment: Python

4. Ajoutez les variables d'environnement:
   Settings → Environment
   Ajoutez:
     - GMAIL_EMAIL = votre_email@gmail.com
     - GMAIL_PASSWORD = votre_mot_de_passe_app_google


ÉTAPE 3: Service 2 - Créer un nouveau service pour le Dashboard
────────────────────────────────────────────────────────────────

1. Allez sur https://dashboard.render.com
2. Cliquez "New +"
3. Sélectionnez "Web Service"
4. Connectez votre repo GitHub (même repo)
5. Remplissez les informations:

   Name: dashboard-ffhockey
   Environment: Node
   Build Command: npm install && npm run build
   Start Command: npx serve -s dist -l 3000
   Root Directory: Dashboard/

6. Cliquez "Create Web Service"
7. Attendez le build (~3-5 minutes)
8. Une fois "Live", Render vous donnera une URL!


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ RÉSULTAT FINAL:

Vous aurez deux services sur Render:

Service 1 - API:
  URL: https://api-ffhockey.onrender.com
  Endpoints: /api/v1/elite-hommes/matchs, /api/v1/subscribe, etc.
  Variables: GMAIL_EMAIL, GMAIL_PASSWORD

Service 2 - Dashboard:
  URL: https://dashboard-ffhockey.onrender.com (ou autre nom)
  Frontend: React
  Pointe vers: https://api-ffhockey.onrender.com/api/v1/*


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 ARCHITECTURE FINALE:

┌────────────────────────────────────────────────────────────┐
│ GitHub Repository (1 seul repo)                            │
│  ├── main.py                                               │
│  ├── scraper.py                                            │
│  ├── requirements.txt                                      │
│  ├── Dockerfile                                            │
│  ├── Procfile                                              │
│  └── Dashboard/                                            │
│      ├── package.json (+ serve)                            │
│      ├── render.yaml (NEW)                                 │
│      ├── src/                                              │
│      │   ├── App.jsx (API_BASE updated)                    │
│      │   └── components/                                   │
│      └── ...                                               │
└────────────────────────────────────────────────────────────┘

Render Infrastructure:

  Service 1: API
  ├── URL: https://api-ffhockey.onrender.com
  ├── Root: /
  ├── Build: pip install -r requirements.txt
  ├── Start: gunicorn -k uvicorn.workers.UvicornWorker main:app
  └── Env: GMAIL_EMAIL, GMAIL_PASSWORD

  Service 2: Dashboard
  ├── URL: https://dashboard-ffhockey.onrender.com
  ├── Root: Dashboard/
  ├── Build: npm install && npm run build
  ├── Start: npx serve -s dist -l 3000
  └── Env: NODE_ENV=production


User Access:
  Dashboard: https://dashboard-ffhockey.onrender.com
  API: https://api-ffhockey.onrender.com/api/v1/*


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ POINTS IMPORTANTS:

1. Les deux services déploient depuis le MÊME repo GitHub
   ✓ Quand vous faites git push, les deux services redéploient

2. Chaque service a sa propre URL
   ✓ API: api-ffhockey.onrender.com
   ✓ Dashboard: dashboard-ffhockey.onrender.com (ou le nom que vous choisissez)

3. Le Dashboard pointe automatiquement vers l'API Render en production
   ✓ App.jsx: if NODE_ENV=production → utilise https://api-ffhockey.onrender.com

4. Les emails fonctionnent une fois que GMAIL_EMAIL et GMAIL_PASSWORD sont configurés dans le Service API

5. Chaque fois que vous modifiez le code:
   $ git push → Les deux services redéploient automatiquement


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧪 TEST FINAL:

Une fois les deux services "Live":

1. Allez sur: https://dashboard-ffhockey.onrender.com
2. Vérifiez que les données se chargent (classement, matchs)
3. Testez la newsletter (inscrivez-vous avec email)
4. Attendez un match qui se termine
5. Vérifiez que vous recevez un email ✓


════════════════════════════════════════════════════════════════════════════════

BESOIN D'AIDE? Questions fréquentes:

Q: Mon Dashboard affiche "erreur de connexion API"?
A: Vérifiez que le Service API est "Live" et que l'URL Render est correcte

Q: L'API Render prend du temps à répondre?
A: Normal! Render désactive les services inactifs après 15 min. Attendez ~30s

Q: Comment je mets à jour le code?
A: Modifiez localement → git push → Les deux services redéploient auto

Q: Où je configure les variables GMAIL?
A: Service 1 (API) → Settings → Environment → Ajouter GMAIL_EMAIL et GMAIL_PASSWORD

Q: Le Dashboard est lent?
A: C'est normal pour Render gratuit. Cela s'améliore après le premier chargement


════════════════════════════════════════════════════════════════════════════════

SUIVI:

[ ] Modifier App.jsx ✓ (FAIT)
[ ] Ajouter serve à package.json ✓ (FAIT)
[ ] Créer Dashboard/render.yaml ✓ (FAIT)
[ ] git add . && git commit && git push
[ ] Vérifier Service 1 API sur Render (et ajouter variables Gmail)
[ ] Créer Service 2 Dashboard sur Render
[ ] Attendre les déploiements (~5-10 min)
[ ] Tester Dashboard sur https://dashboard-ffhockey.onrender.com
[ ] Tester emails (s'inscrire + attendre match)

════════════════════════════════════════════════════════════════════════════════
