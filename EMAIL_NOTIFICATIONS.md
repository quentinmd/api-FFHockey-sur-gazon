# 📧 Configuration Notifications Email Gmail

## Overview
Le système envoie automatiquement un email à la fin de **chaque match terminé**. Quand le statut du match passe à `FINISHED`, tous les abonnés reçoivent une notification formatée en HTML.

## Architecture

### 1. **Backend (main.py)**
- **Endpoint d'abonnement**: `POST /api/v1/subscribe`
  - Accepte une adresse email
  - Stocke l'email dans `email_subscribers.json`
  
- **Endpoint de désinscription**: `DELETE /api/v1/unsubscribe`
  - Supprime l'email de la liste
  
- **Endpoint de statistiques**: `GET /api/v1/notifications/stats`
  - Affiche le nombre d'abonnés et de matchs notifiés

- **Détection automatique**: À chaque appel API `/api/v1/elite-hommes/matchs`, etc.
  - Vérifie les matchs `FINISHED` non notifiés
  - Envoie les emails via Gmail SMTP
  - Marque le match comme notifié dans `notified_matches.json`

### 2. **Frontend (Newsletter.jsx)**
- Formulaire React pour s'abonner/se désabonner
- Validation email côté client
- Feedback utilisateur avec messages de succès/erreur

### 3. **Stockage**
- `email_subscribers.json`: Liste des emails abonnés (persistent)
- `notified_matches.json`: Historique des matchs notifiés (évite les doublons)

## Setup Instructions

### Étape 1: Configurer Gmail

#### A. Activer la vérification en 2 étapes (obligatoire)
1. Accédez à [Google Account Security](https://myaccount.google.com/security)
2. Recherchez "Vérification en 2 étapes"
3. Activez-la si ce n'est pas déjà fait

#### B. Créer un mot de passe d'application
1. Dans les paramètres de sécurité, cherchez "Mots de passe d'application"
2. Sélectionnez:
   - Application: **Mail**
   - Appareil: **Windows (ou votre OS)**
3. Google génère un mot de passe de 16 caractères (sans espaces)
4. **Copiez ce mot de passe** (il apparaît une seule fois)

**Exemple**: `abcdefghijklmnop`

### Étape 2: Créer le fichier `.env`

Dans le dossier racine de l'API (à côté de `main.py`), créez un fichier `.env`:

```env
GMAIL_EMAIL=votre_email@gmail.com
GMAIL_PASSWORD=votre_mot_de_passe_application_de_16_caracteres
```

**Exemple concret**:
```env
GMAIL_EMAIL=hockey.france@gmail.com
GMAIL_PASSWORD=abcdefghijklmnop
```

### Étape 3: Charger les variables d'environnement

Mettez à jour `main.py` pour charger le fichier `.env`:

```python
from dotenv import load_dotenv
import os

load_dotenv()  # Charger le fichier .env

# Maintenant os.environ.get("GMAIL_EMAIL") fonctionne
```

Installez la dépendance:
```bash
pip install python-dotenv
```

Mettez à jour `requirements.txt`:
```
python-dotenv==1.0.0
```

### Étape 4: Intégrer le composant Newsletter

Dans `Dashboard/src/App.jsx`, importez et ajoutez le composant:

```jsx
import Newsletter from './components/Newsletter';

export default function App() {
  return (
    <div className="app">
      {/* ... autres composants ... */}
      <Newsletter />
    </div>
  );
}
```

## Flux de Notifications

```
1. Dashboard charge les matchs: GET /api/v1/elite-hommes/matchs
                                        ↓
2. Backend récupère les données de la FFH
                                        ↓
3. Backend vérifie chaque match:
   - Si statut = "FINISHED" ET pas encore notifié
                                        ↓
4. Email envoyé via Gmail SMTP à tous les abonnés
                                        ↓
5. Match marqué comme "notifié" dans notified_matches.json
```

## Fichier JSON des Abonnés

**email_subscribers.json**:
```json
[
  "user1@gmail.com",
  "user2@outlook.com",
  "coach@hockey.fr"
]
```

**notified_matches.json**:
```json
[
  "elite-hommes-Team A-Team B-2025-10-17T20:00:00Z",
  "elite-femmes-Team C-Team D-2025-10-18T18:30:00Z"
]
```

## Endpoints disponibles

### 1. S'abonner
```bash
curl -X POST http://localhost:8000/api/v1/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "user@gmail.com"}'
```

**Réponse**:
```json
{
  "success": true,
  "message": "Abonné avec succès à user@gmail.com",
  "total_subscribers": 3
}
```

### 2. Se désabonner
```bash
curl -X DELETE http://localhost:8000/api/v1/unsubscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "user@gmail.com"}'
```

### 3. Obtenir les statistiques
```bash
curl http://localhost:8000/api/v1/notifications/stats
```

**Réponse**:
```json
{
  "total_subscribers": 3,
  "total_notified_matches": 12,
  "subscribers": [
    "user1@gmail.com",
    "user2@outlook.com"
  ]
}
```

## Template Email

L'email envoyé contient:
- 🏑 Header avec dégradé violet
- Nom de la compétition (Ex: "Elite Hommes")
- Date du match
- **Équipe domicile vs Équipe extérieur**
- **Score final en gros caractères**
- Footer avec note de désinscription

**Exemple d'objet d'email**:
```
🏑 Fin de match: Paris HC vs Nantes HC
```

## Dépannage

### Erreur: "SMTP Authentication failed"
- ✓ Vérifiez que la vérification 2FA est activée
- ✓ Vérifiez le mot de passe app (copié sans espaces)
- ✓ Vérifiez que le fichier `.env` est dans le bon dossier

### Les emails ne s'envoient pas
- ✓ Vérifiez que les variables d'environnement sont chargées (`print(os.environ.get("GMAIL_EMAIL"))`)
- ✓ Vérifiez que l'email est dans `email_subscribers.json`
- ✓ Vérifiez les logs de l'API pour les erreurs

### Email vide ou sans formatage
- ✓ Vérifie que votre client email supporte le HTML
- ✓ Essayez avec un autre client (Gmail, Outlook, etc.)

## Sécurité

⚠️ **IMPORTANT**:
- Ne commitez JAMAIS le fichier `.env` dans Git
- Ajoutez `.env` à `.gitignore`
- Les mots de passe d'application Gmail sont sécurisés mais liés à votre compte

```gitignore
# .gitignore
.env
email_subscribers.json
notified_matches.json
__pycache__/
.venv/
*.pyc
```

## Performance

- Les emails s'envoient lors de l'appel API (pas de polling côté backend)
- Stockage JSON simple (peut être remplacé par une BD plus tard)
- Un email par match terminé, jamais dupliqué

## Améliorations Futures

- [ ] Ajouter une BD (SQLite/PostgreSQL) pour les abonnés
- [ ] Implémenter un polling backend (toutes les 30s) au lieu de dépendre des appels API
- [ ] Ajouter les préférences d'abonnement (par compétition)
- [ ] Ajouter la validation DKIM/SPF pour meilleure délivrabilité
- [ ] Template d'email personnalisable
