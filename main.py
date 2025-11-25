"""
API FastAPI pour le Hockey sur Gazon Français
Endpoints pour accéder aux données de la FFH
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import json
import os
import re
import hashlib
import time
from functools import wraps
from cachetools import TTLCache
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, db, auth
from scraper import (
    get_ranking, get_matches, 
    get_ranking_femmes, get_matches_femmes,
    get_classement_carquefou_1sh, get_matchs_carquefou_1sh,
    get_classement_carquefou_2sh, get_matchs_carquefou_2sh,
    get_matchs_carquefou_sd,
    get_classement_salle_elite_femmes, get_matchs_salle_elite_femmes,
    get_ranking_n2_salle_zone3, get_matches_n2_salle_zone3
)

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# ============================================
# FIREBASE INITIALIZATION
# ============================================

# Initialiser Firebase Admin SDK
FIREBASE_ENABLED = False
db = None

try:
    cred = None
    firebase_key_loaded_from = None
    
    # Méthode 1: Firebase key JSON en variable d'environnement (Fly.io)
    firebase_key_json = os.environ.get("FIREBASE_KEY")
    if firebase_key_json:
        try:
            firebase_key_dict = json.loads(firebase_key_json)
            cred = credentials.Certificate(firebase_key_dict)
            firebase_key_loaded_from = "FIREBASE_KEY environment variable (Fly.io)"
            print("✅ Firebase key loaded from FIREBASE_KEY environment variable")
        except Exception as e:
            print(f"❌ Error parsing FIREBASE_KEY JSON: {str(e)}")
    
    # Méthode 2: Fichier firebase_key.json local (développement local)
    if not cred:
        firebase_key_path = os.environ.get("FIREBASE_KEY_PATH", "firebase_key.json")
        if os.path.exists(firebase_key_path):
            try:
                cred = credentials.Certificate(firebase_key_path)
                firebase_key_loaded_from = f"firebase_key.json file at {firebase_key_path}"
                print(f"✅ Firebase key loaded from {firebase_key_path}")
            except Exception as e:
                print(f"❌ Error loading firebase_key.json: {str(e)}")
    
    # Initialiser l'app si on a une clé
    if cred:
        try:
            # Récupérer l'URL de la base de données
            firebase_db_url = os.environ.get(
                "FIREBASE_DB_URL", 
                "https://api-ffhockey.firebaseio.com"
            )
            
            print(f"🔐 Initializing Firebase with database: {firebase_db_url}")
            
            # Initialiser Firebase Admin SDK
            firebase_app = firebase_admin.initialize_app(cred, {
                'databaseURL': firebase_db_url
            })
            
            FIREBASE_ENABLED = True
            print(f"✅ Firebase Admin SDK initialized successfully!")
            print(f"✅ Firebase credentials loaded from: {firebase_key_loaded_from}")
            print(f"✅ Firebase database URL: {firebase_db_url}")
            
        except Exception as init_error:
            FIREBASE_ENABLED = False
            print(f"❌ Firebase initialization failed: {str(init_error)}")
            print(f"   Error type: {type(init_error).__name__}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
    else:
        print("⚠️  Firebase key not found - Live score disabled")
        print("   Make sure FIREBASE_KEY environment variable is set or firebase_key.json file exists")
        
except Exception as e:
    FIREBASE_ENABLED = False
    db = None
    print(f"⚠️  Firebase initialization failed at top level: {str(e)}")
    import traceback
    print(f"   Traceback: {traceback.format_exc()}")

# Cache en mémoire pour les matchs live (fallback si Firebase échoue)
LIVE_MATCHES_CACHE = {}

# Webhooks - Liste des URLs pour recevoir les notifications de mise à jour
REGISTERED_WEBHOOKS = {}

app = FastAPI(
    title="🏑 Hockey sur Gazon France API",
    description="""
    ## API Officielle du Hockey sur Gazon Français
    
    Accédez aux données des championnats et compétitions FFH en temps réel.
    
    ### 📋 Endpoints disponibles:
    
    - **Elite Hommes/Femmes** : Classements et matchs
    - **Interligues U14** : Garçons et Filles - Championnat de France des Régions
    - **Carquefou HC** : Données du club local (1SH, 2SH, SD)
    - **Salle Elite Femmes** : Tournaments 2025-2026
    
    """,
    version="1.0.0",
    openapi_tags=[
        {
            "name": "Elite Hommes",
            "description": "Championnats Elite Hommes - Gazon"
        },
        {
            "name": "Elite Femmes",
            "description": "Championnats Elite Femmes - Gazon"
        },
        {
            "name": "Salle Elite Femmes",
            "description": "Tournaments Elite Femmes en Salle - Décembre 2025 & Janvier 2026"
        },
        {
            "name": "Interligues U14",
            "description": "Championnat de France des Régions U14 - Garçons et Filles"
        },
        {
            "name": "Carquefou HC",
            "description": "Données spécifiques du club Carquefou HC"
        },
        {
            "name": "Notifications",
            "description": "Gestion des abonnements aux notifications par email"
        },
        {
            "name": "Santé",
            "description": "Endpoints de vérification de disponibilité"
        }
    ]
)

# Configuration CORS pour accepter les requêtes depuis n'importe quelle origine
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Accepte toutes les origines
    allow_credentials=True,
    allow_methods=["*"],  # Accepte tous les méthodes HTTP
    allow_headers=["*"],  # Accepte tous les headers
)

# Ajouter GZip compression pour les réponses > 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)

# ============================================
# SYSTÈME DE CACHE
# ============================================

# Cache pour les données dynamiques (classements, matchs) - 5 minutes TTL
cache_dynamic = TTLCache(maxsize=100, ttl=300)

# Cache pour les données statiques - 1 heure TTL
cache_static = TTLCache(maxsize=50, ttl=3600)

def cache_with_ttl(cache_store, ttl=None):
    """
    Décorateur pour cacher les résultats avec TTL
    
    Args:
        cache_store: Le cache à utiliser (cache_dynamic ou cache_static)
        ttl: Optionnel, sinon utilise le TTL du cache
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Créer une clé de cache basée sur le nom de la fonction et les arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Vérifier si le résultat est en cache
            if cache_key in cache_store:
                return cache_store[cache_key]
            
            # Appeler la fonction et mettre en cache
            result = await func(*args, **kwargs)
            cache_store[cache_key] = result
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Créer une clé de cache basée sur le nom de la fonction et les arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Vérifier si le résultat est en cache
            if cache_key in cache_store:
                return cache_store[cache_key]
            
            # Appeler la fonction et mettre en cache
            result = func(*args, **kwargs)
            cache_store[cache_key] = result
            return result
        
        # Retourner le wrapper approprié selon que la fonction est async
        if hasattr(func, '__awaitable__'):
            return async_wrapper
        return sync_wrapper
    return decorator



scheduler = BackgroundScheduler()

def check_all_matches_for_notifications():
    """
    Fonction appelée périodiquement pour vérifier tous les matchs
    et envoyer les notifications automatiquement.
    """
    print("⏰ [Scheduler] Vérification automatique des matchs terminés...")
    try:
        import requests
        
        # Récupérer l'URL de base depuis l'environnement ou utiliser localhost
        api_url = os.environ.get("API_URL", "http://localhost:8000")
        
        endpoints_to_check = [
            ("elite-hommes", f"{api_url}/api/v1/elite-hommes/matchs", "Elite Hommes"),
            ("elite-femmes", f"{api_url}/api/v1/elite-femmes/matchs", "Elite Femmes"),
            ("carquefou-1sh", f"{api_url}/api/v1/carquefou/1sh/matchs", "Carquefou 1SH"),
            ("carquefou-2sh", f"{api_url}/api/v1/carquefou/2sh/matchs", "Carquefou 2SH"),
            ("carquefou-sd", f"{api_url}/api/v1/carquefou/sd/matchs", "Carquefou SD"),
            ("n2-salle-zone3", f"{api_url}/api/v1/salle/nationale-2-hommes-zone-3/matchs", "N2 Hommes Salle Zone 3"),
            # ("u14-garcons", f"{api_url}/api/v1/interligues-u14-garcons/matchs", "U14 Garçons"),
            # ("u14-garcons-a", f"{api_url}/api/v1/interligues-u14-garcons-poule-a/matchs", "U14 Garçons Poule A"),
            # ("u14-garcons-b", f"{api_url}/api/v1/interligues-u14-garcons-poule-b/matchs", "U14 Garçons Poule B"),
            # ("u14-filles", f"{api_url}/api/v1/interligues-u14-filles/matchs", "U14 Filles"),
        ]
        
        for prefix, endpoint_url, comp_name in endpoints_to_check:
            try:
                response = requests.get(endpoint_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("data"):
                        matches = data.get("data", [])
                        print(f"  ✅ {comp_name}: {len(matches)} matchs vérifiés")
                        # Appeler la fonction pour vérifier et notifier les matchs terminés
                        check_and_notify_finished_matches(matches, prefix, comp_name)
                else:
                    print(f"  ❌ {comp_name}: Erreur {response.status_code}")
            except Exception as e:
                print(f"  ❌ {comp_name}: {str(e)}")
    except Exception as e:
        print(f"❌ [Scheduler] Erreur: {str(e)}")

# Ajouter le job qui s'exécute toutes les 30 minutes
scheduler.add_job(
    check_all_matches_for_notifications,
    trigger=IntervalTrigger(minutes=30),
    id='check_matches_notifications',
    name='Vérifier les matchs terminés toutes les 30 minutes',
    replace_existing=True
)

@app.on_event("startup")
async def start_scheduler():
    """Démarre le scheduler au lancement de l'API."""
    if not scheduler.running:
        scheduler.start()
        print("✅ [Scheduler] Démarré - Vérification toutes les 30 minutes")

@app.on_event("shutdown")
async def shutdown_scheduler():
    """Arrête le scheduler à l'arrêt de l'API."""
    if scheduler.running:
        scheduler.shutdown()
        print("❌ [Scheduler] Arrêté")

# ============================================
# CONFIGURATION EMAIL GMAIL
# ============================================

# Modèle pour la souscription email
class EmailSubscription(BaseModel):
    email: str

# ============================================
# MODELS POUR LIVE SCORE (FIREBASE)
# ============================================

class ScoreUpdate(BaseModel):
    """Modèle pour mettre à jour le score d'un match"""
    score_domicile: int
    score_exterieur: int

class ScorerUpdate(BaseModel):
    """Modèle pour ajouter un buteur"""
    joueur: str
    equipe: str  # "domicile" ou "exterieur"
    temps: int  # en minutes
    
class CardUpdate(BaseModel):
    """Modèle pour ajouter un carton"""
    joueur: str
    equipe: str  # "domicile" ou "exterieur"
    temps: int  # en minutes
    couleur: str  # "jaune" ou "rouge"

class MatchStatusUpdate(BaseModel):
    """Modèle pour mettre à jour le statut d'un match"""
    statut: str  # "SCHEDULED", "LIVE", "FINISHED"

# Stockage des emails abonnés (en fichier JSON pour persistence)
SUBSCRIBERS_FILE = "email_subscribers.json"
NOTIFIED_MATCHES_FILE = "notified_matches.json"

def load_subscribers():
    """Charge la liste des abonnés depuis le fichier."""
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_subscribers(subscribers):
    """Sauvegarde la liste des abonnés dans un fichier."""
    with open(SUBSCRIBERS_FILE, 'w') as f:
        json.dump(list(subscribers), f, indent=2)

def load_notified_matches():
    """Charge la liste des matchs notifiés."""
    if os.path.exists(NOTIFIED_MATCHES_FILE):
        try:
            with open(NOTIFIED_MATCHES_FILE, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_notified_matches(matches):
    """Sauvegarde la liste des matchs notifiés."""
    with open(NOTIFIED_MATCHES_FILE, 'w') as f:
        json.dump(list(matches), f, indent=2)

# Charger les données existantes
email_subscribers = load_subscribers()
notified_matches = load_notified_matches()

def format_match_data(match, include_renc_id=True):
    """
    Transforme les données brutes d'un match FFHockey en format standardisé.
    Ajoute le RencId pour permettre l'accès à la feuille de match.
    
    Args:
        match: Dictionnaire brut du match FFHockey
        include_renc_id: Si True, inclut le RencId dans les données formatées
        
    Returns:
        Dictionnaire formaté avec les champs standardisés
    """
    formatted = {
        "equipe_domicile": match.get("Equipe1", {}).get("EquipeNom", "TBD"),
        "equipe_exterieur": match.get("Equipe2", {}).get("EquipeNom", "TBD"),
        "score_domicile": match.get("Scores", {}).get("RencButsEqp1") or "",
        "score_exterieur": match.get("Scores", {}).get("RencButsEqp2") or "",
        "date": match.get("RencDateDerog", ""),
        "statut": "FINISHED" if (match.get("Scores", {}).get("RencButsEqp1") and match.get("Scores", {}).get("RencButsEqp2")) else "SCHEDULED"
    }
    
    # Ajouter le RencId si disponible
    if include_renc_id:
        formatted["rencId"] = match.get("RencId", "")
    
    return formatted

def create_placeholder_match(description, date, horaire, lieu=""):
    """
    Crée une rencontre placeholder avec infos manuelles.
    
    Args:
        description: Description du match (ex: "Île-de-France vs La Réunion")
        date: Date du match (ex: "2025-10-29")
        horaire: Horaire du match (ex: "09:00")
        lieu: Lieu du match (optionnel)
        
    Returns:
        Dictionnaire formaté comme un match
    """
    return {
        "equipe_domicile": "TBD",
        "equipe_exterieur": "TBD",
        "score_domicile": "",
        "score_exterieur": "",
        "date": f"{date} {horaire}:00",
        "statut": "SCHEDULED",
        "description": description,
        "lieu": lieu,
        "rencId": ""
    }

def get_phases_for_manifestation(manif_id):
    """
    Récupère les phases pour une manifestation donnée.
    
    Args:
        manif_id: L'ID de la manifestation
        
    Returns:
        Liste des phases formatées ou None si erreur
    """
    try:
        import requests
        
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerPhases"
        params = {
            "SaisonAnnee": "2026",
            "ManifId": manif_id
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("ResponseCode") == "200" and "Response" in data:
            phases_raw = data["Response"].get("PhasesArray", {})
            phases_formatted = []
            
            for phase_id, phase in phases_raw.items():
                phases_formatted.append({
                    "phase_id": phase.get("PhaseId"),
                    "libelle": phase.get("PhaseLib"),
                    "ordre": int(phase.get("PhaseOrdre", 0)),
                    "date_debut": phase.get("PhaseDateDebut"),
                    "date_fin": phase.get("PhaseDateFin"),
                    "type": phase.get("PhaseRencType")
                })
            
            # Trier par ordre
            phases_formatted.sort(key=lambda x: x["ordre"])
            return phases_formatted
        else:
            return None
            
    except Exception as e:
        print(f"❌ Erreur get_phases_for_manifestation({manif_id}): {str(e)}")
        return None

def get_poules_for_phase(manif_id, phase_id, poules_mapping=None):
    """
    Récupère les poules et rencontres pour une phase donnée.
    
    Args:
        manif_id: L'ID de la manifestation
        phase_id: L'ID de la phase
        poules_mapping: Dict optionnel {poule_id: (libelle, matches_manuels)} pour les données manuelles
        
    Returns:
        Liste des poules formatées
    """
    try:
        import requests
        
        poules_mapping = poules_mapping or {}
        
        poules_url = "https://championnats.ffhockey.org/rest2/Championnats/ListerPoules"
        poules_params = {
            "SaisonAnnee": "2026",
            "ManifId": manif_id,
            "PhaseId": phase_id
        }
        
        poules_response = requests.get(poules_url, params=poules_params, timeout=10)
        poules_response.raise_for_status()
        poules_data = poules_response.json()
        
        if poules_data.get("ResponseCode") != "200":
            return []
        
        poules_raw = poules_data.get("Response", {}).get("PoulesArray", {})
        poules_formatted = []
        
        # Pour chaque poule, récupérer les rencontres
        for poule_id, poule in poules_raw.items():
            poule_info = {
                "poule_id": poule.get("PouleId"),
                "libelle": poule.get("PouleLib"),
                "rencontres": []
            }
            
            # Récupérer les rencontres pour cette poule
            try:
                renc_url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
                renc_params = {
                    "SaisonAnnee": "2026",
                    "ManifId": manif_id,
                    "PouleId": poule_id
                }
                
                renc_response = requests.get(renc_url, params=renc_params, timeout=10)
                renc_response.raise_for_status()
                renc_data = renc_response.json()
                
                if renc_data.get("ResponseCode") == "200":
                    rencontres_raw = renc_data.get("Response", {}).get("RencontresArray", {})
                    
                    for match in rencontres_raw.values():
                        formatted_match = format_match_data(match, include_renc_id=True)
                        poule_info["rencontres"].append(formatted_match)
                
                # Si pas de rencontres de FFHockey, ajouter les données manuelles si disponibles
                if not poule_info["rencontres"] and poule_id in poules_mapping:
                    poule_info["rencontres"] = poules_mapping[poule_id][1]
                    poule_info["source"] = "manual"
                    
            except:
                # Si pas de rencontres FFHockey, ajouter les données manuelles
                if poule_id in poules_mapping:
                    poule_info["rencontres"] = poules_mapping[poule_id][1]
                    poule_info["source"] = "manual"
            
            poules_formatted.append(poule_info)
        
        return poules_formatted
        
    except Exception as e:
        print(f"❌ Erreur get_poules_for_phase({manif_id}, {phase_id}): {str(e)}")
        return []

def send_match_finished_email(subscribers, match_data, competition_name):
    """
    Envoie un email à tous les abonnés quand un match se termine via SendGrid.
    
    Args:
        subscribers: Set d'emails à notifier
        match_data: Dictionnaire avec les infos du match
        competition_name: Nom de la compétition
    """
    if not subscribers or not os.environ.get("SENDGRID_API_KEY"):
        return False
    
    try:
        # Récupérer la clé API SendGrid
        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        sender_email = "quentin.mouraud@carquefouhockeyclub.com"  # Email expéditeur (doit être vérifié dans SendGrid)
        
        # Préparer le contenu de l'email
        equipe_domicile = match_data.get("equipe_domicile", "?")
        equipe_exterieur = match_data.get("equipe_exterieur", "?")
        score_domicile = match_data.get("score_domicile", "?")
        score_exterieur = match_data.get("score_exterieur", "?")
        date = match_data.get("date", "?")
        
        # Créer le corps de l'email en HTML
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px;">
                <div style="background: white; border-radius: 10px; padding: 30px; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #764ba2; text-align: center;">⚽ Fin de Match - Notificateur Hockey</h2>
                    <hr style="border: none; border-top: 2px solid #667eea;">
                    
                    <p style="font-size: 14px; color: #666;">
                        <strong>Compétition:</strong> {competition_name}
                    </p>
                    
                    <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <div style="text-align: center;">
                            <p style="font-size: 14px; color: #666; margin: 5px 0;">Date: {date}</p>
                            <h1 style="color: #333; margin: 10px 0; font-size: 36px;">
                                <span style="color: #667eea;">{equipe_domicile}</span>
                                <span style="margin: 0 15px; color: #764ba2;">{score_domicile} - {score_exterieur}</span>
                                <span style="color: #667eea;">{equipe_exterieur}</span>
                            </h1>
                        </div>
                    </div>
                    
                    <p style="color: #666; font-size: 14px; line-height: 1.6;">
                        Le match entre <strong>{equipe_domicile}</strong> et <strong>{equipe_exterieur}</strong> 
                        s'est terminé sur le score de <strong>{score_domicile} - {score_exterieur}</strong>.
                    </p>
                    
                    <div style="background: #f0f0f0; padding: 15px; border-left: 4px solid #667eea; margin-top: 20px;">
                        <p style="margin: 0; color: #333; font-size: 12px;">
                            Vous recevez cet email car vous êtes abonné aux notifications de fin de match du Hockey FFH.
                        </p>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin-top: 30px;">
                    <p style="text-align: center; color: #999; font-size: 12px;">
                        © 2025 Hockey FFH Notificateur
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Envoyer à chaque abonné via SendGrid
        for recipient_email in subscribers:
            message = Mail(
                from_email=sender_email,
                to_emails=recipient_email,
                subject=f"🏑 Fin de match: {equipe_domicile} vs {equipe_exterieur}",
                html_content=html_content
            )
            
            response = sg.send(message)
            if response.status_code not in [200, 201, 202]:
                print(f"Erreur SendGrid {response.status_code}: {response.body}")
                return False
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'envoi d'email SendGrid: {str(e)}")
        return False


def check_and_notify_finished_matches(matches_data, competition_prefix, competition_name):
    """
    Fonction générique pour vérifier les matchs terminés et envoyer des emails.
    Évite les doublons en gardant trace des matchs déjà notifiés.
    
    Args:
        matches_data: Liste des matchs
        competition_prefix: Préfixe pour l'ID unique (ex: "elite-hommes")
        competition_name: Nom de la compétition pour l'email
    """
    global notified_matches
    
    for match in matches_data:
        if match.get("statut") == "FINISHED":
            # Créer un identifiant unique pour le match
            # Préférer RencId si disponible (plus fiable), sinon utiliser les noms d'équipes et la date
            if match.get("rencId"):
                match_id = f"{competition_prefix}-renc-{match.get('rencId')}"
            else:
                # Normaliser les noms pour éviter les doublons dus aux caractères spéciaux
                home_team = str(match.get('equipe_domicile', '')).lower().strip()
                away_team = str(match.get('equipe_exterieur', '')).lower().strip()
                match_date = str(match.get('date', '')).lower().strip()
                match_id = f"{competition_prefix}-{home_team}-{away_team}-{match_date}"
            
            # Si le match n'a pas encore été notifié
            if match_id not in notified_matches:
                # Envoyer les emails
                send_match_finished_email(email_subscribers, match, competition_name)
                
                # Marquer comme notifié
                notified_matches.add(match_id)
                save_notified_matches(notified_matches)
                print(f"✉️ [Notification] Match notifié: {match_id}")


def generate_renc_id(equipe_domicile, equipe_exterieur, date, seed=0):
    """
    Génère un ID de rencontre basé sur un hash des données du match.
    
    Args:
        equipe_domicile: Nom de l'équipe à domicile
        equipe_exterieur: Nom de l'équipe à l'extérieur
        date: Date du match (format YYYY-MM-DD HH:MM:SS)
        seed: Valeur de seed pour varier les IDs (par défaut 0)
        
    Returns:
        String ID numérique (entre 100000 et 999999)
    """
    # Créer une chaîne unique avec les données du match
    match_str = f"{equipe_domicile}|{equipe_exterieur}|{date}|{seed}".lower().strip()
    
    # Générer un hash MD5
    hash_obj = hashlib.md5(match_str.encode())
    hash_hex = hash_obj.hexdigest()
    
    # Convertir en entier et limiter à 6 chiffres (100000-999999)
    hash_int = int(hash_hex, 16)
    renc_id = 100000 + (hash_int % 900000)
    
    return str(renc_id)


# ============================================
# WRAPPERS DE CACHE POUR APPELS SCRAPER
# ============================================

def get_ranking_cached():
    """Wrapper avec cache pour get_ranking()"""
    cache_key = "ranking_elite_hommes"
    if cache_key not in cache_dynamic:
        result = get_ranking()
        cache_dynamic[cache_key] = result
    return cache_dynamic[cache_key]

def get_matches_cached():
    """Wrapper avec cache pour get_matches()"""
    cache_key = "matches_elite_hommes"
    if cache_key not in cache_dynamic:
        result = get_matches()
        cache_dynamic[cache_key] = result
    return cache_dynamic[cache_key]

def get_ranking_femmes_cached():
    """Wrapper avec cache pour get_ranking_femmes()"""
    cache_key = "ranking_elite_femmes"
    if cache_key not in cache_dynamic:
        result = get_ranking_femmes()
        cache_dynamic[cache_key] = result
    return cache_dynamic[cache_key]

def get_matches_femmes_cached():
    """Wrapper avec cache pour get_matches_femmes()"""
    cache_key = "matches_elite_femmes"
    if cache_key not in cache_dynamic:
        result = get_matches_femmes()
        cache_dynamic[cache_key] = result
    return cache_dynamic[cache_key]

def get_classement_carquefou_1sh_cached():
    """Wrapper avec cache pour get_classement_carquefou_1sh()"""
    cache_key = "classement_carquefou_1sh"
    if cache_key not in cache_dynamic:
        result = get_classement_carquefou_1sh()
        cache_dynamic[cache_key] = result
    return cache_dynamic[cache_key]

def get_matchs_carquefou_1sh_cached():
    """Wrapper avec cache pour get_matchs_carquefou_1sh()"""
    cache_key = "matchs_carquefou_1sh"
    if cache_key not in cache_dynamic:
        result = get_matchs_carquefou_1sh()
        cache_dynamic[cache_key] = result
    return cache_dynamic[cache_key]

def get_classement_carquefou_2sh_cached():
    """Wrapper avec cache pour get_classement_carquefou_2sh()"""
    cache_key = "classement_carquefou_2sh"
    if cache_key not in cache_dynamic:
        result = get_classement_carquefou_2sh()
        cache_dynamic[cache_key] = result
    return cache_dynamic[cache_key]

def get_matchs_carquefou_2sh_cached():
    """Wrapper avec cache pour get_matchs_carquefou_2sh()"""
    cache_key = "matchs_carquefou_2sh"
    if cache_key not in cache_dynamic:
        result = get_matchs_carquefou_2sh()
        cache_dynamic[cache_key] = result
    return cache_dynamic[cache_key]

def get_matchs_carquefou_sd_cached():
    """Wrapper avec cache pour get_matchs_carquefou_sd()"""
    cache_key = "matchs_carquefou_sd"
    if cache_key not in cache_dynamic:
        result = get_matchs_carquefou_sd()
        cache_dynamic[cache_key] = result
    return cache_dynamic[cache_key]


def get_classement_salle_elite_femmes_cached():
    """Wrapper avec cache pour get_classement_salle_elite_femmes()"""
    cache_key = "classement_salle_elite_femmes"
    if cache_key not in cache_dynamic:
        result = get_classement_salle_elite_femmes()
        cache_dynamic[cache_key] = result
    return cache_dynamic[cache_key]


def get_matchs_salle_elite_femmes_cached():
    """Wrapper avec cache pour get_matchs_salle_elite_femmes()"""
    cache_key = "matchs_salle_elite_femmes"
    if cache_key not in cache_dynamic:
        result = get_matchs_salle_elite_femmes()
        cache_dynamic[cache_key] = result
    return cache_dynamic[cache_key]


def get_ranking_n2_salle_zone3_cached():
    """Wrapper avec cache pour get_ranking_n2_salle_zone3()"""
    cache_key = "ranking_n2_salle_zone3"
    if cache_key not in cache_dynamic:
        result = get_ranking_n2_salle_zone3()
        cache_dynamic[cache_key] = result
    return cache_dynamic[cache_key]


def get_matches_n2_salle_zone3_cached():
    """Wrapper avec cache pour get_matches_n2_salle_zone3()"""
    cache_key = "matches_n2_salle_zone3"
    if cache_key not in cache_dynamic:
        result = get_matches_n2_salle_zone3()
        cache_dynamic[cache_key] = result
    return cache_dynamic[cache_key]



async def endpoint_classement():
    """
    Récupère le classement actuel de l'élite hommes.
    
    Returns:
        Liste des équipes avec leurs statistiques de classement.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    ranking_data = get_ranking_cached()
    
    if not ranking_data:
        raise HTTPException(
            status_code=503,
            detail="La source de données de la FFH est actuellement indisponible."
        )
    
    return {
        "success": True,
        "data": ranking_data,
        "count": len(ranking_data)
    }


# ========================
# OVERLAY SCORE POUR OBS
# ========================

@app.get("/score-overlay.html", tags=["Overlay"], summary="Score Overlay pour OBS")
async def serve_score_overlay():
    """
    Serve la page HTML d'overlay de score pour OBS Studio.
    Affiche le score en direct des matchs de hockey salle avec fond transparent.
    
    Accédez via : http://localhost:8000/score-overlay.html
    
    Returns:
        Page HTML avec overlay de score (CSS + JavaScript intégré)
    """
    overlay_path = os.path.join(os.path.dirname(__file__), "score-overlay.html")
    
    if os.path.exists(overlay_path):
        return FileResponse(overlay_path, media_type="text/html")
    else:
        # Retourner un message d'erreur si le fichier n'existe pas
        return HTMLResponse(
            """
            <html>
                <head>
                    <title>Score Overlay - Erreur</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            background: #1a1a1a;
                            color: #fff;
                            margin: 0;
                        }
                        .error-box {
                            text-align: center;
                            background: rgba(255, 0, 0, 0.2);
                            padding: 40px;
                            border-radius: 10px;
                            border: 2px solid #ff5555;
                        }
                        h1 { color: #ff5555; }
                        p { color: #aaa; }
                    </style>
                </head>
                <body>
                    <div class="error-box">
                        <h1>⚠️ Fichier non trouvé</h1>
                        <p>score-overlay.html n'existe pas dans le répertoire de l'API</p>
                        <p style="font-size: 12px; margin-top: 20px;">
                            Assurez-vous que le fichier est présent à la racine du projet.
                        </p>
                    </div>
                </body>
            </html>
            """,
            status_code=404
        )


@app.get("/score-simple.html", tags=["Overlay"], summary="Score Simple - Juste le score")
async def serve_score_simple():
    """
    Serve la page HTML simple d'overlay de score.
    Affiche JUSTE le score du match sans contrôles.
    
    Paramètres URL:
    - ?championship=elite-hommes&match_id=match_001  (affiche ce match spécifique)
    - ?renc_id=12345  (affiche le match avec ce rencId)
    - aucun paramètre = premier match du championnat (défaut: elite-hommes)
    
    Exemples:
    - http://localhost:8000/score-simple.html
    - http://localhost:8000/score-simple.html?championship=elite-hommes&match_id=match_001
    - http://localhost:8000/score-simple.html?renc_id=12345
    
    Returns:
        Page HTML simple avec juste le score (se met à jour automatiquement)
    """
    simple_path = os.path.join(os.path.dirname(__file__), "score-simple.html")
    
    if os.path.exists(simple_path):
        return FileResponse(simple_path, media_type="text/html")
    else:
        return HTMLResponse(
            """
            <html>
                <head>
                    <title>Score Simple - Erreur</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            background: #1a1a1a;
                            color: #fff;
                            margin: 0;
                        }
                        .error-box {
                            text-align: center;
                            background: rgba(255, 0, 0, 0.2);
                            padding: 40px;
                            border-radius: 10px;
                            border: 2px solid #ff5555;
                        }
                        h1 { color: #ff5555; }
                        p { color: #aaa; }
                    </style>
                </head>
                <body>
                    <div class="error-box">
                        <h1>⚠️ Fichier non trouvé</h1>
                        <p>score-simple.html n'existe pas dans le répertoire de l'API</p>
                    </div>
                </body>
            </html>
            """,
            status_code=404
        )


@app.get("/score-only.html", tags=["Overlay"], summary="Score Uniquement - Seulement les chiffres")
async def serve_score_only():
    """
    Serve la page HTML avec SEULEMENT les scores des deux équipes.
    Format: ÉQUIPE1 — SCORE1 | SCORE2 — ÉQUIPE2
    Idéal pour les très petits overlays OBS.
    
    Paramètres URL (même que score-simple.html):
    - ?championship=elite-femmes&renc_id=193082
    - ?championship=elite-hommes
    - ?renc_id=12345
    
    Exemples:
    - http://localhost:8000/score-only.html
    - http://localhost:8000/score-only.html?championship=elite-femmes&renc_id=193082
    
    Returns:
        Page HTML ultra-minimaliste avec juste les scores et noms d'équipes
    """
    only_path = os.path.join(os.path.dirname(__file__), "score-only.html")
    
    if os.path.exists(only_path):
        return FileResponse(only_path, media_type="text/html")
    else:
        return HTMLResponse(
            """
            <html>
                <head>
                    <title>Score Only - Erreur</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            background: #1a1a1a;
                            color: #fff;
                            margin: 0;
                        }
                        .error-box {
                            text-align: center;
                            background: rgba(255, 0, 0, 0.2);
                            padding: 40px;
                            border-radius: 10px;
                            border: 2px solid #ff5555;
                        }
                        h1 { color: #ff5555; }
                        p { color: #aaa; }
                    </style>
                </head>
                <body>
                    <div class="error-box">
                        <h1>⚠️ Fichier non trouvé</h1>
                        <p>score-only.html n'existe pas dans le répertoire de l'API</p>
                    </div>
                </body>
            </html>
            """,
            status_code=404
        )


@app.get("/api/v1/elite-hommes/matchs", tags=["Elite Hommes"])
async def endpoint_matchs():
    """
    Récupère la liste des matchs de l'élite hommes.
    Détecte aussi les matchs nouvellement terminés et envoie des emails si nécessaire.
    
    Returns:
        Liste des matchs avec leurs résultats et statuts.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    matches_data = get_matches_cached()
    
    if not matches_data:
        raise HTTPException(
            status_code=503,
            detail="La source de données de la FFH est actuellement indisponible."
        )
    
    # Vérifier les matchs nouvellement terminés et envoyer notifications
    check_and_notify_finished_matches(matches_data, "elite-hommes", "Elite Hommes")
    
    return {
        "success": True,
        "data": matches_data,
        "count": len(matches_data)
    }


@app.get("/api/v1/elite-femmes/classement", tags=["Elite Femmes"])
async def endpoint_classement_femmes():
    """
    Récupère le classement actuel de l'élite femmes.
    
    Returns:
        Liste des équipes avec leurs statistiques de classement.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    ranking_data = get_ranking_femmes_cached()
    
    if not ranking_data:
        raise HTTPException(
            status_code=503,
            detail="La source de données de la FFH est actuellement indisponible."
        )
    
    return {
        "success": True,
        "data": ranking_data,
        "count": len(ranking_data)
    }


@app.get("/api/v1/elite-femmes/matchs", tags=["Elite Femmes"])
async def endpoint_matchs_femmes():
    """
    Récupère la liste des matchs de l'élite femmes.
    
    Returns:
        Liste des matchs avec leurs résultats et statuts.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    matches_data = get_matches_femmes_cached()
    
    if not matches_data:
        raise HTTPException(
            status_code=503,
            detail="La source de données est actuellement indisponible."
        )
    
    return {
        "success": True,
        "data": matches_data,
        "count": len(matches_data)
    }


@app.get("/api/v1/salle/elite-femmes/classement", tags=["Salle Elite Femmes"], summary="Classement Elite Femmes Salle")
async def endpoint_classement_elite_femmes_salle():
    """
    Récupère le classement de l'élite femmes en salle.
    Les données sont calculées automatiquement depuis les matchs réels FFHockey.
    Système de points: Victoire=3pts, Nul=1pt, Défaite=0pts
    Critères de départage: Différence de buts, puis buts marqués
    
    Championnat 2025-2026:
    - Tournoi 1 : 13/14 décembre (Villeurbanne)
    - Tournoi 2 : 3/4 janvier (Carquefou)
    
    Équipes: HC Grenoble, IH Lambersart, AS Villeurbanne EL, PHC Marcq en Baroeul,
    Cambrai HC, Blanc Mesnil SH, Carquefou HC, La Baule OHC, CA Montrouge 92, Villa Primrose
    
    Returns:
        Classement calculé des équipes Elite Femmes Salle
    """
    try:
        ranking_data = get_classement_salle_elite_femmes_cached()
        
        if not ranking_data:
            # Si pas de matchs joués encore, retourner les équipes avec 0 point
            teams = [
                "HC Grenoble",
                "IH Lambersart",
                "AS Villeurbanne EL",
                "PHC Marcq en Baroeul",
                "Cambrai HC",
                "Blanc Mesnil SH",
                "Carquefou HC",
                "La Baule OHC",
                "CA Montrouge 92",
                "Villa Primrose"
            ]
            
            classement = []
            for rank, team in enumerate(teams, 1):
                classement.append({
                    "position": rank,
                    "equipe": team,
                    "points": 0,
                    "joues": 0,
                    "gagnes": 0,
                    "nuls": 0,
                    "perdus": 0,
                    "buts_pour": 0,
                    "buts_contre": 0,
                    "difference": 0
                })
            
            return {
                "success": True,
                "data": classement,
                "count": len(classement),
                "discipline": "salle",
                "categorie": "Elite Femmes",
                "note": "Classement initial (0 matchs joués). Données en direct depuis FFHockey."
            }
        
        return {
            "success": True,
            "data": ranking_data,
            "count": len(ranking_data),
            "discipline": "salle",
            "categorie": "Elite Femmes",
            "note": "Classement calculé depuis les matchs réels FFHockey."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du classement Elite Femmes Salle: {str(e)}")


@app.get("/api/v1/salle/elite-femmes/matchs", tags=["Salle Elite Femmes"], summary="Matchs Elite Femmes Salle")
async def endpoint_matchs_elite_femmes_salle():
    """
    Récupère la liste des matchs réels de l'élite femmes en salle depuis FFHockey.
    Sauvegarde automatiquement les matchs dans Firebase pour synchronisation en direct.
    
    Données actualisées depuis les URLs officielles FFHockey:
    - Phases: https://championnats.ffhockey.org/rest2/Championnats/ListerPhases?SaisonAnnee=2026&ManifId=4403
    - Matchs: https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres?...&ManifId=4403
    - Classements: https://championnats.ffhockey.org/rest2/Championnats/ClassementEquipes?...&PouleId=11712
    - Journées: https://championnats.ffhockey.org/rest2/Championnats/ListerJournees?...&PouleId=11712
    
    Championnat 2025-2026:
    - Tournoi 1 : 13/14 décembre (Villeurbanne)
    - Tournoi 2 : 3/4 janvier (Carquefou - Salle de la Mainguais)
    
    Returns:
        Liste des matchs Elite Femmes Salle avec données réelles FFHockey
    """
    try:
        matches_data = get_matchs_salle_elite_femmes_cached()
        
        # ✅ Sauvegarder automatiquement dans Firebase
        print(f"🔍 FIREBASE_ENABLED: {FIREBASE_ENABLED}")
        if FIREBASE_ENABLED:
            try:
                from firebase_admin import db as firebase_db
                print(f"📤 Début de sauvegarde de {len(matches_data)} matchs...")
                for i, match in enumerate(matches_data):
                    match_id = f"salle-elite-femmes_{match.get('rencId', match.get('id', ''))}"
                    match_data = {
                        "championship": "salle-elite-femmes",
                        "equipe_domicile": match.get("equipe_domicile", "?"),
                        "equipe_exterieur": match.get("equipe_exterieur", "?"),
                        "score_domicile": match.get("score_domicile") or 0,
                        "score_exterieur": match.get("score_exterieur") or 0,
                        "statut": match.get("statut", "SCHEDULED"),
                        "date": match.get("date", ""),
                        "rencId": match.get("rencId", match.get("id", "")),
                        "last_updated": int(time.time())
                    }
                    if i < 2:
                        print(f"   Envoi {i+1}: {match_id}")
                    firebase_db.reference(f'matches/{match_id}').set(match_data)
                print(f"✅ {len(matches_data)} matchs Elite Femmes Salle sauvegardés dans Firebase")
            except Exception as firebase_error:
                print(f"⚠️  Erreur Firebase (non-bloquante): {str(firebase_error)}")
                import traceback
                print(traceback.format_exc())
        else:
            print(f"⚠️  Firebase désactivé - Pas de sauvegarde")
        
        # Vérifier et notifier les matchs terminés
        check_and_notify_finished_matches(matches_data, "salle-elite-femmes", "Elite Femmes Salle")
        
        return {
            "success": True,
            "data": matches_data,
            "count": len(matches_data),
            "discipline": "salle",
            "categorie": "Elite Femmes",
            "note": "✅ Données réelles depuis FFHockey (ManifId: 4403) + Firebase sync"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des matchs Elite Femmes Salle: {str(e)}")


@app.post("/api/v1/debug/sync-salle-elite-femmes", tags=["Debug"])
async def debug_sync_salle_elite_femmes():
    """
    Endpoint de debug pour forcer la synchronisation des matchs Salle Elite Femmes vers Firebase.
    """
    # Vider la cache d'abord
    cache_dynamic.pop("matchs_salle_elite_femmes", None)
    
    matches_data = get_matchs_salle_elite_femmes_cached()
    
    sync_count = 0
    errors = []
    
    if FIREBASE_ENABLED:
        try:
            from firebase_admin import db as firebase_db
            for match in matches_data:
                try:
                    match_id = f"salle-elite-femmes_{match.get('rencId', match.get('id', ''))}"
                    
                    # DEBUG: Vérifier les types
                    score_d = match.get("score_domicile")
                    score_e = match.get("score_exterieur")
                    
                    # Conversion sûre
                    score_d_final = score_d if score_d is not None else 0
                    score_e_final = score_e if score_e is not None else 0
                    
                    match_data = {
                        "championship": "salle-elite-femmes",
                        "equipe_domicile": match.get("equipe_domicile", "?"),
                        "equipe_exterieur": match.get("equipe_exterieur", "?"),
                        "score_domicile": score_d_final,
                        "score_exterieur": score_e_final,
                        "statut": match.get("statut", "SCHEDULED"),
                        "date": match.get("date", ""),
                        "rencId": match.get("rencId", match.get("id", "")),
                        "last_updated": int(time.time())
                    }
                    firebase_db.reference(f'matches/{match_id}').set(match_data)
                    sync_count += 1
                except Exception as e:
                    errors.append(f"{match.get('rencId')}: {type(e).__name__}: {str(e)}")
                    # DEBUG: Ajouter la stack trace
                    import traceback
                    errors.append(traceback.format_exc())
        except Exception as e:
            errors.append(f"Firebase error: {str(e)}")
    else:
        errors.append("Firebase not enabled")
    
    return {
        "success": len(errors) == 0,
        "synced_count": sync_count,
        "total_matches": len(matches_data),
        "errors": errors[:10]  # Limiter à 10 erreurs
    }


# --- Endpoints N2 Hommes Salle - Zone 3 ---

@app.get("/api/v1/salle/nationale-2-hommes-zone-3/classement", tags=["N2 Hommes Salle Zone 3"])
def get_n2_salle_zone3_classement():
    """
    Retourne le classement pour le championnat Nationale 2 Hommes Salle - Zone 3.
    """
    try:
        data = get_ranking_n2_salle_zone3_cached()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/salle/nationale-2-hommes-zone-3/matchs", tags=["N2 Hommes Salle Zone 3"])
def get_n2_salle_zone3_matchs():
    """
    Retourne la liste des matchs pour le championnat Nationale 2 Hommes Salle - Zone 3.
    """
    try:
        matches_data = get_matches_n2_salle_zone3_cached()
        
        # Sauvegarder automatiquement dans Firebase
        if FIREBASE_ENABLED:
            try:
                from firebase_admin import db as firebase_db
                for match in matches_data:
                    match_id = f"n2-salle-zone3_{match.get('rencId', match.get('id', ''))}"
                    match_data = {
                        "championship": "n2-salle-zone3",
                        "equipe_domicile": match.get("equipe_domicile", "?"),
                        "equipe_exterieur": match.get("equipe_exterieur", "?"),
                        "score_domicile": match.get("score_domicile") or 0,
                        "score_exterieur": match.get("score_exterieur") or 0,
                        "statut": match.get("statut", "SCHEDULED"),
                        "date": match.get("date", ""),
                        "rencId": match.get("rencId", match.get("id", "")),
                        "last_updated": int(time.time())
                    }
                    firebase_db.reference(f'matches/{match_id}').set(match_data)
            except Exception as firebase_error:
                print(f"⚠️  Erreur Firebase (non-bloquante): {str(firebase_error)}")
        
        # Vérifier et notifier les matchs terminés
        check_and_notify_finished_matches(matches_data, "n2-salle-zone3", "N2 Hommes Salle Zone 3")
        
        return {
            "success": True,
            "data": matches_data,
            "count": len(matches_data),
            "discipline": "salle",
            "categorie": "N2 Hommes Zone 3"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/carquefou/sd/matchs", tags=["Carquefou HC"])
async def endpoint_matchs_carquefou_sd():
    """
    Récupère la liste des matchs de Carquefou HC Seniors Dames (Elite).
    Envoie aussi des emails pour les matchs nouvellement terminés.
    
    Returns:
        Liste des matchs avec leurs résultats et statuts.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    matches_data = get_matchs_carquefou_sd_cached()
    
    if not matches_data:
        raise HTTPException(
            status_code=503,
            detail="La source de données de la FFH est actuellement indisponible."
        )
    
    # Vérifier et notifier les matchs terminés
    check_and_notify_finished_matches(matches_data, "carquefou-sd", "Carquefou SD")
    
    return {
        "success": True,
        "data": matches_data,
        "count": len(matches_data)
    }


@app.get("/api/v1/carquefou/1sh/classement", tags=["Carquefou HC"])
async def endpoint_classement_carquefou_1sh():
    """
    Récupère le classement de Carquefou HC 1 Seniors Hommes.
    
    Returns:
        Liste des équipes avec leurs statistiques de classement.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    ranking_data = get_classement_carquefou_1sh_cached()
    
    if not ranking_data:
        raise HTTPException(
            status_code=503,
            detail="La source de données de la FFH est actuellement indisponible."
        )
    
    return {
        "success": True,
        "data": ranking_data,
        "count": len(ranking_data)
    }


@app.get("/api/v1/carquefou/1sh/matchs", tags=["Carquefou HC"])
async def endpoint_matchs_carquefou_1sh():
    """
    Récupère la liste des matchs de Carquefou HC 1 Seniors Hommes.
    
    Returns:
        Liste des matchs avec leurs résultats et statuts.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    matches_data = get_matchs_carquefou_1sh_cached()
    
    if not matches_data:
        raise HTTPException(
            status_code=503,
            detail="La source de données de la FFH est actuellement indisponible."
        )
    
    return {
        "success": True,
        "data": matches_data,
        "count": len(matches_data)
    }


@app.get("/api/v1/carquefou/2sh/classement", tags=["Carquefou HC"])
async def endpoint_classement_carquefou_2sh():
    """
    Récupère le classement de Carquefou HC 2 Seniors Hommes.
    
    Returns:
        Liste des équipes avec leurs statistiques de classement.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    ranking_data = get_classement_carquefou_2sh_cached()
    
    if not ranking_data:
        raise HTTPException(
            status_code=503,
            detail="La source de données de la FFH est actuellement indisponible."
        )
    
    return {
        "success": True,
        "data": ranking_data,
        "count": len(ranking_data)
    }


@app.get("/api/v1/carquefou/2sh/matchs", tags=["Carquefou HC"])
async def endpoint_matchs_carquefou_2sh():
    """
    Récupère la liste des matchs de Carquefou HC 2 Seniors Hommes.
    
    Returns:
        Liste des matchs avec leurs résultats et statuts.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    matches_data = get_matchs_carquefou_2sh_cached()
    
    if not matches_data:
        raise HTTPException(
            status_code=503,
            detail="La source de données de la FFH est actuellement indisponible."
        )
    
    return {
        "success": True,
        "data": matches_data,
        "count": len(matches_data)
    }


@app.get("/", tags=["Santé"])
async def root():
    """
    Endpoint de vérification de la santé de l'API.
    """
    return {
        "message": "Bienvenue sur l'API Hockey sur Gazon France",
        "version": "1.0.0",
        "endpoints": {
            "elite_hommes": {
                "classement": "/api/v1/elite-hommes/classement",
                "matchs": "/api/v1/elite-hommes/matchs"
            },
            "elite_femmes": {
                "classement": "/api/v1/elite-femmes/classement",
                "matchs": "/api/v1/elite-femmes/matchs"
            },
            "carquefou_sd_elite": {
                "matchs": "/api/v1/carquefou/sd/matchs"
            },
            "carquefou_1_poule_a": {
                "classement": "/api/v1/carquefou/1sh/classement",
                "matchs": "/api/v1/carquefou/1sh/matchs"
            },
            "carquefou_2_poule_b": {
                "classement": "/api/v1/carquefou/2sh/classement",
                "matchs": "/api/v1/carquefou/2sh/matchs"
            },
            "documentation": "/docs"
        }
    }


@app.get("/health", tags=["Santé"])
async def health_check():
    """
    Endpoint de santé pour les vérifications de disponibilité.
    """
    return {
        "status": "healthy",
        "message": "L'API est en ligne et fonctionnelle"
    }


# ============================================
# INTERLIGUES U14 (NOUVELLES COMPÉTITIONS)
# ============================================

import requests

@app.get("/api/v1/interligues-u14-filles/classement", tags=["Interligues U14"], include_in_schema=False, summary="Classement U14 Filles")
def get_classement_interligues_u14_filles():
    """
    Récupère le classement calculé des Interligues U14 Filles.
    Calcul automatique: Victoire=3pts, Nul=1pt, Défaite=0pts
    Critères de départage: Différence de buts
    
    Returns:
        Classement des équipes U14 Filles
    """
    return calculate_classement_u14_filles()


@app.get("/api/v1/interligues-u14-filles/matchs", tags=["Interligues U14"], include_in_schema=False, summary="Matchs U14 Filles")
def get_matchs_interligues_u14_filles():
    """
    Récupère les matchs des Interligues U14 Filles (Championnat de France des Régions).
    
    Returns:
        Liste des matchs U14 Filles avec format standardisé
    """
    try:
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
        params = {
            "SaisonAnnee": "2026",
            "ManifId": "4401",  # U14 Filles
            "PhaseId": "",
            "PouleId": "",
            "TournId": "",
            "JourId": "",
            "StructureCodeParticipante": "",
            "EqpId": "",
            "EqpIdDomicile": "",
            "StructureCodeDomicile": "",
            "EqpIdVisiteurs": "",
            "StructureCodeVisiteurs": "",
            "StructureCodeTerrain": "",
            "StructureCodeLieuPratique": ""
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("ResponseCode") == "200" and "Response" in data:
            matches_raw = data["Response"].get("RencontresArray", {})
            # Transformer les données au format attendu par le Dashboard avec RencId
            matches_formatted = []
            for match in matches_raw.values():
                formatted_match = format_match_data(match, include_renc_id=True)
                matches_formatted.append(formatted_match)
            return {"success": True, "data": matches_formatted, "count": len(matches_formatted)}
        else:
            return {"success": False, "data": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des matchs U14 Filles: {str(e)}")


def calculate_classement_u14_filles():
    """
    Calcule le classement des U14 Filles à partir des matchs.
    Règles: Victoire = 3pts, Nul = 1pt, Défaite = 0pts
    Critères de départage: Différence de buts
    """
    try:
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
        params = {
            "SaisonAnnee": "2026",
            "ManifId": "4401"  # U14 Filles
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("ResponseCode") == "200" and "Response" in data:
            matches_raw = data["Response"].get("RencontresArray", {})
            
            # Dictionnaire pour stocker les stats de chaque équipe
            standings = {}
            
            for match in matches_raw.values():
                # Récupérer les infos du match
                equipe1_nom = match.get("Equipe1", {}).get("EquipeNom", "TBD")
                equipe2_nom = match.get("Equipe2", {}).get("EquipeNom", "TBD")
                but1 = match.get("Scores", {}).get("RencButsEqp1")
                but2 = match.get("Scores", {}).get("RencButsEqp2")
                
                # Ignorer les matchs non joués (pas de score)
                if not but1 or not but2:
                    continue
                
                but1 = int(but1)
                but2 = int(but2)
                
                # Initialiser les équipes si pas encore dans le classement
                if equipe1_nom not in standings:
                    standings[equipe1_nom] = {
                        "equipe": equipe1_nom,
                        "joues": 0,
                        "gagnees": 0,
                        "nulles": 0,
                        "perdues": 0,
                        "buts_pour": 0,
                        "buts_contre": 0,
                        "points": 0
                    }
                
                if equipe2_nom not in standings:
                    standings[equipe2_nom] = {
                        "equipe": equipe2_nom,
                        "joues": 0,
                        "gagnees": 0,
                        "nulles": 0,
                        "perdues": 0,
                        "buts_pour": 0,
                        "buts_contre": 0,
                        "points": 0
                    }
                
                # Mettre à jour les stats
                standings[equipe1_nom]["joues"] += 1
                standings[equipe1_nom]["buts_pour"] += but1
                standings[equipe1_nom]["buts_contre"] += but2
                
                standings[equipe2_nom]["joues"] += 1
                standings[equipe2_nom]["buts_pour"] += but2
                standings[equipe2_nom]["buts_contre"] += but1
                
                # Calculer les points
                if but1 > but2:  # Équipe 1 gagne
                    standings[equipe1_nom]["gagnees"] += 1
                    standings[equipe1_nom]["points"] += 3
                    standings[equipe2_nom]["perdues"] += 1
                elif but2 > but1:  # Équipe 2 gagne
                    standings[equipe2_nom]["gagnees"] += 1
                    standings[equipe2_nom]["points"] += 3
                    standings[equipe1_nom]["perdues"] += 1
                else:  # Match nul
                    standings[equipe1_nom]["nulles"] += 1
                    standings[equipe1_nom]["points"] += 1
                    standings[equipe2_nom]["nulles"] += 1
                    standings[equipe2_nom]["points"] += 1
            
            # Calculer la différence de buts et trier
            classement = []
            for equipe in standings.values():
                equipe["difference_buts"] = equipe["buts_pour"] - equipe["buts_contre"]
                classement.append(equipe)
            
            # Trier par: Points DESC, Différence de buts DESC, Buts marqués DESC
            classement.sort(key=lambda x: (-x["points"], -x["difference_buts"], -x["buts_pour"]))
            
            return {"success": True, "data": classement, "count": len(classement)}
        else:
            return {"success": False, "data": [], "count": 0}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul du classement U14 Filles: {str(e)}")


# ============================================
# ENDPOINTS GÉNÉRIQUES - GAZON & SALLE
# ============================================
# Ces endpoints supportent à la fois Gazon et Salle
# Gazon: /api/v1/gazon/u14-garcons/phases
# Salle: /api/v1/salle/u14-garcons/phases (quand les données arriveront)

# Mapping discipline -> ManifIds
MANIFESTATION_IDS = {
    "gazon": {
        "u14-garcons": "4400",
        "u14-filles": "4401",
    },
    "salle": {
        "u14-garcons": "",  # À remplir quand les données arriveront
        "u14-filles": "",   # À remplir quand les données arriveront
    }
}

@app.get("/api/v1/{discipline}/u14-garcons/phases", tags=["Interligues U14 - Générique"], include_in_schema=False)
async def get_u14_garcons_phases_generic(discipline: str):
    """
    Récupère les phases des Interligues U14 Garçons pour une discipline donnée.
    
    Args:
        discipline: "gazon" ou "salle"
        
    Returns:
        Liste des phases
        
    Example:
        /api/v1/gazon/u14-garcons/phases
    """
    discipline = discipline.lower()
    if discipline not in MANIFESTATION_IDS or "u14-garcons" not in MANIFESTATION_IDS[discipline]:
        raise HTTPException(status_code=400, detail=f"Discipline '{discipline}' non supportée. Utilisez 'gazon' ou 'salle'.")
    
    manif_id = MANIFESTATION_IDS[discipline]["u14-garcons"]
    if not manif_id:
        raise HTTPException(status_code=503, detail=f"Les données pour {discipline} U14 Garçons ne sont pas encore disponibles.")
    
    phases = get_phases_for_manifestation(manif_id)
    if phases is None:
        raise HTTPException(status_code=503, detail="Impossible de récupérer les phases.")
    
    return {
        "success": True,
        "data": phases,
        "count": len(phases),
        "discipline": discipline,
        "categorie": "U14 Garçons"
    }

@app.get("/api/v1/{discipline}/u14-garcons/poules/{phase_id}", tags=["Interligues U14 - Générique"], include_in_schema=False)
async def get_u14_garcons_poules_generic(discipline: str, phase_id: str):
    """
    Récupère les poules et rencontres pour une phase des Interligues U14 Garçons.
    
    Args:
        discipline: "gazon" ou "salle"
        phase_id: L'ID de la phase
        
    Returns:
        Liste des poules avec leurs rencontres
        
    Example:
        /api/v1/gazon/u14-garcons/poules/7174
    """
    discipline = discipline.lower()
    if discipline not in MANIFESTATION_IDS or "u14-garcons" not in MANIFESTATION_IDS[discipline]:
        raise HTTPException(status_code=400, detail=f"Discipline '{discipline}' non supportée. Utilisez 'gazon' ou 'salle'.")
    
    manif_id = MANIFESTATION_IDS[discipline]["u14-garcons"]
    if not manif_id:
        raise HTTPException(status_code=503, detail=f"Les données pour {discipline} U14 Garçons ne sont pas encore disponibles.")
    
    # Données manuelles pour gazon uniquement (en attente de confirmation pour salle)
    poules_mapping_gazon = {
        "11694": ("Demi-Finale 1A vs 2B", [
            create_placeholder_match("Île-de-France vs La Réunion", "2025-10-29", "09:00"),
        ]),
        "11695": ("Demi-Finale 1B vs 2A", [
            create_placeholder_match("Hauts-de-France vs Normandie", "2025-10-29", "10:10"),
        ]),
        "11696": ("Demi-Finale 3A vs 4B", [
            create_placeholder_match("Nouvelle Aquitaine vs Auvergne-Rhône-Alpes", "2025-10-29", "11:20"),
        ]),
        "11697": ("Demi-Finale 4A vs 3B", [
            create_placeholder_match("Pays de la Loire vs Occitanie", "2025-10-29", "12:30"),
        ]),
    }
    
    poules_mapping = poules_mapping_gazon if discipline == "gazon" else {}
    poules = get_poules_for_phase(manif_id, phase_id, poules_mapping)
    
    return {
        "success": True,
        "data": poules,
        "count": len(poules),
        "discipline": discipline,
        "categorie": "U14 Garçons",
        "phase_id": phase_id,
        "note": "Les données manuelles (source: manual) seront confirmées/remplacées dès que FFHockey les fournie."
    }

@app.get("/api/v1/{discipline}/u14-filles/phases", tags=["Interligues U14 - Générique"], include_in_schema=False)
async def get_u14_filles_phases_generic(discipline: str):
    """
    Récupère les phases des Interligues U14 Filles pour une discipline donnée.
    
    Args:
        discipline: "gazon" ou "salle"
        
    Returns:
        Liste des phases
        
    Example:
        /api/v1/gazon/u14-filles/phases
    """
    discipline = discipline.lower()
    if discipline not in MANIFESTATION_IDS or "u14-filles" not in MANIFESTATION_IDS[discipline]:
        raise HTTPException(status_code=400, detail=f"Discipline '{discipline}' non supportée. Utilisez 'gazon' ou 'salle'.")
    
    manif_id = MANIFESTATION_IDS[discipline]["u14-filles"]
    if not manif_id:
        raise HTTPException(status_code=503, detail=f"Les données pour {discipline} U14 Filles ne sont pas encore disponibles.")
    
    phases = get_phases_for_manifestation(manif_id)
    if phases is None:
        raise HTTPException(status_code=503, detail="Impossible de récupérer les phases.")
    
    return {
        "success": True,
        "data": phases,
        "count": len(phases),
        "discipline": discipline,
        "categorie": "U14 Filles"
    }

@app.get("/api/v1/{discipline}/u14-filles/poules/{phase_id}", tags=["Interligues U14 - Générique"], include_in_schema=False)
async def get_u14_filles_poules_generic(discipline: str, phase_id: str):
    """
    Récupère les poules et rencontres pour une phase des Interligues U14 Filles.
    
    Args:
        discipline: "gazon" ou "salle"
        phase_id: L'ID de la phase
        
    Returns:
        Liste des poules avec leurs rencontres
        
    Example:
        /api/v1/gazon/u14-filles/poules/7182
    """
    discipline = discipline.lower()
    if discipline not in MANIFESTATION_IDS or "u14-filles" not in MANIFESTATION_IDS[discipline]:
        raise HTTPException(status_code=400, detail=f"Discipline '{discipline}' non supportée. Utilisez 'gazon' ou 'salle'.")
    
    manif_id = MANIFESTATION_IDS[discipline]["u14-filles"]
    if not manif_id:
        raise HTTPException(status_code=503, detail=f"Les données pour {discipline} U14 Filles ne sont pas encore disponibles.")
    
    # Données manuelles pour gazon uniquement
    poules_mapping_gazon = {
        "11702": ("Places 1 et 2", [
            create_placeholder_match("Finale du Championnat", "2025-10-30", "12:30", "La Boulie"),
        ]),
        "11703": ("Places 3 et 4", [
            create_placeholder_match("Match pour la médaille de bronze", "2025-10-30", "10:10", "La Boulie"),
        ]),
        "11704": ("Places 5 et 6", [
            create_placeholder_match("Classement 5e/6e place", "2025-10-30", "10:40", "Asnières"),
        ]),
    }
    
    poules_mapping = poules_mapping_gazon if discipline == "gazon" else {}
    poules = get_poules_for_phase(manif_id, phase_id, poules_mapping)
    
    return {
        "success": True,
        "data": poules,
        "count": len(poules),
        "discipline": discipline,
        "categorie": "U14 Filles",
        "phase_id": phase_id,
        "note": "Les données manuelles (source: manual) seront confirmées/remplacées dès que FFHockey les fournie."
    }


@app.get("/api/v1/interligues-u14-garcons/matchs", tags=["Interligues U14"], include_in_schema=False, summary="Matchs U14 Garçons")
def get_matchs_interligues_u14_garcons():
    """
    Récupère les matchs des Interligues U14 Garçons (Championnat de France des Régions).
    
    Returns:
        Liste des matchs U14 Garçons avec format standardisé
    """
    try:
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
        params = {
            "SaisonAnnee": "2026",
            "ManifId": "4400",  # U14 Garçons
            "PhaseId": "",
            "PouleId": "",
            "TournId": "",
            "JourId": "",
            "StructureCodeParticipante": "",
            "EqpId": "",
            "EqpIdDomicile": "",
            "StructureCodeDomicile": "",
            "EqpIdVisiteurs": "",
            "StructureCodeVisiteurs": "",
            "StructureCodeTerrain": "",
            "StructureCodeLieuPratique": ""
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("ResponseCode") == "200" and "Response" in data:
            matches_raw = data["Response"].get("RencontresArray", {})
            # Transformer les données au format attendu par le Dashboard avec RencId
            matches_formatted = []
            for match in matches_raw.values():
                formatted_match = format_match_data(match, include_renc_id=True)
                # Ajouter le champ poule s'il existe
                formatted_match["poule"] = match.get("Poule", {}).get("PouleLib", "")
                matches_formatted.append(formatted_match)
            return {"success": True, "data": matches_formatted, "count": len(matches_formatted)}
        else:
            return {"success": False, "data": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des matchs U14 Garçons: {str(e)}")


@app.get("/api/v1/interligues-u14-garcons-poule-a/matchs", tags=["Interligues U14"], include_in_schema=False)
async def get_matchs_interligues_u14_garcons_poule_a():
    """
    Récupère les matchs des Interligues U14 Garçons - POULE A uniquement.
    """
    try:
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
        params = {
            "SaisonAnnee": "2026",
            "ManifId": "4400"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("ResponseCode") == "200" and "Response" in data:
            matches_raw = data["Response"].get("RencontresArray", {})
            # Filtrer et transformer les données pour Poule A seulement avec RencId
            matches_formatted = []
            for match in matches_raw.values():
                # Filtrer par Poule A
                if match.get("Poule", {}).get("PouleLib") == "Poule A":
                    formatted_match = format_match_data(match, include_renc_id=True)
                    formatted_match["poule"] = match.get("Poule", {}).get("PouleLib", "")
                    matches_formatted.append(formatted_match)
            
            # Vérifier les matchs terminés et envoyer des notifications
            check_and_notify_finished_matches(matches_formatted, "u14-garcons-a", "U14 Garçons - Poule A")
            
            return {"success": True, "data": matches_formatted, "count": len(matches_formatted)}
        else:
            return {"success": False, "data": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des matchs U14 Garçons Poule A: {str(e)}")


@app.get("/api/v1/interligues-u14-garcons-poule-b/matchs", tags=["Interligues U14"], include_in_schema=False)
async def get_matchs_interligues_u14_garcons_poule_b():
    """
    Récupère les matchs des Interligues U14 Garçons - POULE B uniquement.
    """
    try:
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
        params = {
            "SaisonAnnee": "2026",
            "ManifId": "4400"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("ResponseCode") == "200" and "Response" in data:
            matches_raw = data["Response"].get("RencontresArray", {})
            # Filtrer et transformer les données pour Poule B seulement
            matches_formatted = []
            for match in matches_raw.values():
                # Filtrer par Poule B
                if match.get("Poule", {}).get("PouleLib") == "Poule B":
                    matches_formatted.append(format_match_data(match))
            
            # Vérifier les matchs terminés et envoyer des notifications
            check_and_notify_finished_matches(matches_formatted, "u14-garcons-b", "U14 Garçons - Poule B")
            
            return {"success": True, "data": matches_formatted, "count": len(matches_formatted)}
        else:
            return {"success": False, "data": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des matchs U14 Garçons Poule B: {str(e)}")


@app.get("/api/v1/interligues-u14-garcons/phases", tags=["Interligues U14"], include_in_schema=False)
async def get_interligues_u14_garcons_phases():
    """
    Récupère les phases (groupes, 1/2 finales, finales) des Interligues U14 Garçons.
    Permet de suivre l'évolution de la compétition.
    """
    try:
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerPhases"
        params = {
            "SaisonAnnee": "2026",
            "ManifId": "4400"  # U14 Garçons
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("ResponseCode") == "200" and "Response" in data:
            phases_raw = data["Response"].get("PhasesArray", {})
            phases_formatted = []
            
            for phase_id, phase in phases_raw.items():
                phases_formatted.append({
                    "phase_id": phase.get("PhaseId"),
                    "libelle": phase.get("PhaseLib"),
                    "ordre": int(phase.get("PhaseOrdre", 0)),
                    "date_debut": phase.get("PhaseDateDebut"),
                    "date_fin": phase.get("PhaseDateFin"),
                    "type": phase.get("PhaseRencType")
                })
            
            # Trier par ordre
            phases_formatted.sort(key=lambda x: x["ordre"])
            
            return {
                "success": True,
                "data": phases_formatted,
                "count": len(phases_formatted)
            }
        else:
            return {"success": False, "data": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des phases: {str(e)}")


@app.get("/api/v1/interligues-u14-garcons/poules/{phase_id}", tags=["Interligues U14"], include_in_schema=False)
async def get_interligues_u14_garcons_poules(phase_id: str):
    """
    Récupère les poules (matchups) pour une phase spécifique des Interligues U14 Garçons.
    Les rencontres s'ajoutent automatiquement dès que les équipes sont désignées.
    Inclut les données manuelles en attente de confirmation FFHockey.
    
    Args:
        phase_id: L'identifiant de la phase (ex: 7174 pour 1/2 finales)
        
    Returns:
        Liste des poules avec leurs rencontres
        
    Example:
        /api/v1/interligues-u14-garcons/poules/7174
    """
    try:
        # D'abord récupérer les poules
        poules_url = "https://championnats.ffhockey.org/rest2/Championnats/ListerPoules"
        poules_params = {
            "SaisonAnnee": "2026",
            "ManifId": "4400",  # U14 Garçons
            "PhaseId": phase_id
        }
        
        poules_response = requests.get(poules_url, params=poules_params, timeout=10)
        poules_response.raise_for_status()
        poules_data = poules_response.json()
        
        if poules_data.get("ResponseCode") != "200":
            return {"success": False, "data": [], "count": 0}
        
        poules_raw = poules_data.get("Response", {}).get("PoulesArray", {})
        poules_formatted = []
        
        # Données manuelles pour les demi-finales du 29/10 (en attente de confirmation)
        matches_demi_finales_29oct = [
            ("11694", "Demi-Finale 1A vs 2B", [
                create_placeholder_match("Île-de-France vs La Réunion", "2025-10-29", "09:00"),
            ]),
            ("11695", "Demi-Finale 1B vs 2A", [
                create_placeholder_match("Hauts-de-France vs Normandie", "2025-10-29", "10:10"),
            ]),
            ("11696", "Demi-Finale 3A vs 4B", [
                create_placeholder_match("Nouvelle Aquitaine vs Auvergne-Rhône-Alpes", "2025-10-29", "11:20"),
            ]),
            ("11697", "Demi-Finale 4A vs 3B", [
                create_placeholder_match("Pays de la Loire vs Occitanie", "2025-10-29", "12:30"),
            ]),
        ]
        
        # Données manuelles pour les matchs du 30/10 (finales et classements)
        matches_finales_30oct = [
            ("11702", "Match pour la 7e/8e place", [
                create_placeholder_match("Classement 7e/8e place", "2025-10-30", "09:30", "Asnières"),
            ]),
            ("11703", "Match pour la 5e/6e place", [
                create_placeholder_match("Classement 5e/6e place", "2025-10-30", "09:00", "La Boulie"),
            ]),
            ("11704", "Match pour la médaille de Bronze", [
                create_placeholder_match("Match Bronze", "2025-10-30", "11:20", "La Boulie"),
            ]),
            ("11705", "Finale du Championnat", [
                create_placeholder_match("Finale", "2025-10-30", "13:40", "La Boulie"),
            ]),
        ]
        
        # Mapper les poules avec les matchs manuels
        poules_mapping = {poule_id: (libelle, matches) for poule_id, libelle, matches in matches_demi_finales_29oct + matches_finales_30oct}
        
        # Pour chaque poule, récupérer les rencontres
        for poule_id, poule in poules_raw.items():
            poule_info = {
                "poule_id": poule.get("PouleId"),
                "libelle": poule.get("PouleLib"),
                "rencontres": []
            }
            
            # Récupérer les rencontres pour cette poule
            try:
                renc_url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
                renc_params = {
                    "SaisonAnnee": "2026",
                    "ManifId": "4401",
                    "PouleId": poule_id
                }
                
                renc_response = requests.get(renc_url, params=renc_params, timeout=10)
                renc_response.raise_for_status()
                renc_data = renc_response.json()
                
                if renc_data.get("ResponseCode") == "200":
                    rencontres_raw = renc_data.get("Response", {}).get("RencontresArray", {})
                    
                    for match in rencontres_raw.values():
                        formatted_match = format_match_data(match, include_renc_id=True)
                        poule_info["rencontres"].append(formatted_match)
                
                # Si pas de rencontres de FFHockey, ajouter les données manuelles si disponibles
                if not poule_info["rencontres"] and poule_id in poules_mapping:
                    poule_info["rencontres"] = poules_mapping[poule_id][1]
                    poule_info["source"] = "manual"
                    
            except:
                # Si pas de rencontres FFHockey, ajouter les données manuelles
                if poule_id in poules_mapping:
                    poule_info["rencontres"] = poules_mapping[poule_id][1]
                    poule_info["source"] = "manual"
            
            poules_formatted.append(poule_info)
        
        return {
            "success": True,
            "data": poules_formatted,
            "count": len(poules_formatted),
            "note": "Les données manuelles (source: manual) seront confirmées/remplacées dès que FFHockey les fournie."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des poules U14 Filles: {str(e)}")