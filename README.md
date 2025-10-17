# Hockey sur Gazon France - API

Une API FastAPI pour accéder aux données du hockey sur gazon français depuis la FFH (Fédération Française de Hockey).

## 📋 Description

Cette API fournit un accès structuré aux données des championnats de hockey sur gazon français, notamment :
- **Classement** : Position actuelle des équipes, points, statistiques
- **Matchs** : Liste des rencontres avec résultats et statuts

## 🚀 Installation

### Prérequis
- Python 3.8+
- pip

### Configuration

1. **Installer les dépendances** :
```bash
pip install -r requirements.txt
```

2. **Lancer l'API** :
```bash
python main.py
```

L'API sera accessible à `http://127.0.0.1:8000`

## 📚 Endpoints

### 1. Classement
- **URL** : `/api/v1/elite-hommes/classement`
- **Méthode** : `GET`
- **Description** : Récupère le classement actuel de l'élite hommes
- **Réponse** :
```json
{
  "success": true,
  "data": [
    {
      "position": 1,
      "equipe": "Montpellier",
      "points": 30,
      "joues": 10,
      "gagnes": 10,
      "nuls": 0,
      "perdus": 0,
      "buts_pour": 45,
      "buts_contre": 15,
      "difference": 30
    }
  ],
  "count": 10
}
```

### 2. Matchs
- **URL** : `/api/v1/elite-hommes/matchs`
- **Méthode** : `GET`
- **Description** : Récupère la liste des matchs de l'élite hommes
- **Réponse** :
```json
{
  "success": true,
  "data": [
    {
      "id_match": "123456",
      "date": "2025-10-18T18:00:00",
      "equipe_domicile": "Montpellier",
      "equipe_exterieur": "Toulouse",
      "score_domicile": 3,
      "score_exterieur": 2,
      "statut": "FINISHED"
    }
  ],
  "count": 5
}
```

### 3. Santé (Health Check)
- **URL** : `/health`
- **Méthode** : `GET`
- **Description** : Vérifie l'état de l'API

### 4. Documentation interactive
- **URL** : `/docs`
- **Méthode** : Accès navigateur
- **Description** : Documentation Swagger interactive de tous les endpoints

## 📁 Structure du Projet

```
.
├── main.py              # Application FastAPI principale
├── scraper.py           # Fonctions de récupération des données
├── requirements.txt     # Dépendances Python
└── README.md            # Ce fichier
```

## 🔧 Fonctionnement

### `scraper.py`
Ce fichier contient les fonctions de récupération des données depuis l'API interne de la FFH :
- `get_ranking()` : Récupère et formate le classement
- `get_matches()` : Récupère et formate les matchs

### `main.py`
Ce fichier contient l'application FastAPI avec les endpoints publics.

## ⚠️ Gestion des Erreurs

Si la source de données FFH n'est pas disponible, l'API retourne :
```json
{
  "detail": "La source de données de la FFH est actuellement indisponible."
}
```
Avec le code de statut HTTP **503 (Service Unavailable)**.

## 🧪 Test de l'API

Une fois lancée, vous pouvez tester l'API via :

1. **Swagger UI** : http://127.0.0.1:8000/docs
2. **ReDoc** : http://127.0.0.1:8000/redoc
3. **curl** :
```bash
curl http://127.0.0.1:8000/api/v1/elite-hommes/classement
curl http://127.0.0.1:8000/api/v1/elite-hommes/matchs
```

## 📝 Notes

- L'API récupère les données depuis les endpoints internes de la FFH
- Les données sont transformées et formatées de manière cohérente
- La gestion d'erreurs est robuste (timeouts, erreurs de connexion, etc.)

## 📄 Licence

À définir selon vos besoins.
