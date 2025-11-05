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
    get_matchs_carquefou_sd
)

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# ============================================
# FIREBASE INITIALIZATION
# ============================================

# Initialiser Firebase Admin SDK
FIREBASE_ENABLED = False
try:
    cred = None
    
    # Méthode 1: Firebase key JSON en variable d'environnement
    firebase_key_json = os.environ.get("FIREBASE_KEY")
    if firebase_key_json:
        try:
            import json
            firebase_key_dict = json.loads(firebase_key_json)
            cred = credentials.Certificate(firebase_key_dict)
            print("✅ Firebase key loaded from FIREBASE_KEY environment variable")
        except Exception as e:
            print(f"❌ Error parsing FIREBASE_KEY JSON: {str(e)}")
    
    # Méthode 2: Fichier firebase_key.json local
    if not cred:
        firebase_key_path = os.environ.get("FIREBASE_KEY_PATH", "firebase_key.json")
        if os.path.exists(firebase_key_path):
            cred = credentials.Certificate(firebase_key_path)
            print("✅ Firebase key loaded from firebase_key.json file")
    
    # Initialiser l'app si on a une clé
    if cred:
        firebase_admin.initialize_app(cred, {
            'databaseURL': os.environ.get(
                "FIREBASE_DB_URL", 
                "https://api-ffhockey.firebaseio.com"
            )
        })
        FIREBASE_ENABLED = True
        print("✅ Firebase Admin SDK initialized successfully")
    else:
        print("⚠️  Firebase key not found - Live score disabled")
        
except Exception as e:
    FIREBASE_ENABLED = False
    print(f"⚠️  Firebase initialization failed: {str(e)}")

# Cache en mémoire pour les matchs live (fallback si Firebase échoue)
LIVE_MATCHES_CACHE = {}

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
            ("u14-garcons", f"{api_url}/api/v1/interligues-u14-garcons/matchs", "U14 Garçons"),
            ("u14-garcons-a", f"{api_url}/api/v1/interligues-u14-garcons-poule-a/matchs", "U14 Garçons Poule A"),
            ("u14-garcons-b", f"{api_url}/api/v1/interligues-u14-garcons-poule-b/matchs", "U14 Garçons Poule B"),
            ("u14-filles", f"{api_url}/api/v1/interligues-u14-filles/matchs", "U14 Filles"),
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
            detail="La source de données de la FFH est actuellement indisponible."
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
    Les données sont actuellement des valeurs par défaut (0 point) en attente des résultats des tournois.
    
    Équipes du championnat:
    - HC Grenoble, IH Lambersart, AS Villeurbanne EL, PHC Marcq en Baroeul
    - Cambrai HC, Blanc Mesnil SH, Carquefou HC, La Baule OHC
    - CA Montrouge 92, Villa Primrose
    
    Returns:
        Liste des équipes avec leurs statistiques (0 point pour l'instant)
    """
    try:
        # Équipes du championnat Elite Femmes Salle
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
        
        # Initialiser le classement avec 0 point
        classement = []
        for rank, team in enumerate(teams, 1):
            classement.append({
                "rang": rank,
                "equipe": team,
                "points": 0,
                "matchs_joues": 0,
                "victoires": 0,
                "nuls": 0,
                "defaites": 0,
                "buts_pour": 0,
                "buts_contre": 0,
                "difference_buts": 0,
                "statut": "avant tournoi"
            })
        
        return {
            "success": True,
            "data": classement,
            "count": len(classement),
            "discipline": "salle",
            "categorie": "Elite Femmes",
            "note": "Données initiales (0 point). Seront mises à jour après les tournois de décembre et janvier."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du classement Elite Femmes Salle: {str(e)}")


@app.get("/api/v1/salle/elite-femmes/matchs", tags=["Salle Elite Femmes"], summary="Matchs Elite Femmes Salle")
async def endpoint_matchs_elite_femmes_salle():
    """
    Récupère la liste des matchs de l'élite femmes en salle.
    Les données sont actuellement manuelles en attente de confirmation FFHockey.
    
    Tournois:
    - 13/14 décembre (lieu à confirmer)
    - 3/4 janvier (Carquefou - Salle de la Mainguais)
    
    Returns:
        Liste des matchs Elite Femmes Salle avec données manuelles
    """
    try:
        # Données manuelles des tournois Elite Femmes Salle
        matches_data = [
            # Tournoi 1 - 13/14 décembre (Villeurbanne)
            {
                "equipe_domicile": "HC Grenoble",
                "equipe_exterieur": "IH Lambersart",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-13 13:00:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("HC Grenoble", "IH Lambersart", "2025-12-13 13:00:00", 1),
                "source": "manual"
            },
            {
                "equipe_domicile": "AS Villeurbanne EL",
                "equipe_exterieur": "PHC Marcq en Baroeul",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-13 14:05:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("AS Villeurbanne EL", "PHC Marcq en Baroeul", "2025-12-13 14:05:00", 2),
                "source": "manual"
            },
            {
                "equipe_domicile": "Cambrai HC",
                "equipe_exterieur": "Blanc Mesnil SH",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-13 15:10:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("Cambrai HC", "Blanc Mesnil SH", "2025-12-13 15:10:00", 3),
                "source": "manual"
            },
            {
                "equipe_domicile": "Carquefou HC",
                "equipe_exterieur": "La Baule OHC",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-13 16:15:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("Carquefou HC", "La Baule OHC", "2025-12-13 16:15:00", 4),
                "source": "manual"
            },
            {
                "equipe_domicile": "IH Lambersart",
                "equipe_exterieur": "CA Montrouge 92",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-13 17:20:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("IH Lambersart", "CA Montrouge 92", "2025-12-13 17:20:00", 5),
                "source": "manual"
            },
            {
                "equipe_domicile": "PHC Marcq en Baroeul",
                "equipe_exterieur": "HC Grenoble",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-13 18:25:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("PHC Marcq en Baroeul", "HC Grenoble", "2025-12-13 18:25:00", 6),
                "source": "manual"
            },
            {
                "equipe_domicile": "AS Villeurbanne EL",
                "equipe_exterieur": "Villa Primrose",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-13 19:30:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("AS Villeurbanne EL", "Villa Primrose", "2025-12-13 19:30:00", 7),
                "source": "manual"
            },
            {
                "equipe_domicile": "Cambrai HC",
                "equipe_exterieur": "La Baule OHC",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-13 20:35:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("Cambrai HC", "La Baule OHC", "2025-12-13 20:35:00", 8),
                "source": "manual"
            },
            # Dimanche 14 décembre (Villeurbanne)
            {
                "equipe_domicile": "Blanc Mesnil SH",
                "equipe_exterieur": "Carquefou HC",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-14 09:00:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("Blanc Mesnil SH", "Carquefou HC", "2025-12-14 09:00:00", 9),
                "source": "manual"
            },
            {
                "equipe_domicile": "La Baule OHC",
                "equipe_exterieur": "Villa Primrose",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-14 10:05:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("La Baule OHC", "Villa Primrose", "2025-12-14 10:05:00", 10),
                "source": "manual"
            },
            {
                "equipe_domicile": "PHC Marcq en Baroeul",
                "equipe_exterieur": "IH Lambersart",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-14 11:10:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("PHC Marcq en Baroeul", "IH Lambersart", "2025-12-14 11:10:00", 11),
                "source": "manual"
            },
            {
                "equipe_domicile": "AS Villeurbanne EL",
                "equipe_exterieur": "CA Montrouge 92",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-14 12:15:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("AS Villeurbanne EL", "CA Montrouge 92", "2025-12-14 12:15:00", 12),
                "source": "manual"
            },
            {
                "equipe_domicile": "Carquefou HC",
                "equipe_exterieur": "Cambrai HC",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-14 13:20:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("Carquefou HC", "Cambrai HC", "2025-12-14 13:20:00", 13),
                "source": "manual"
            },
            {
                "equipe_domicile": "Blanc Mesnil SH",
                "equipe_exterieur": "Villa Primrose",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-14 14:25:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("Blanc Mesnil SH", "Villa Primrose", "2025-12-14 14:25:00", 14),
                "source": "manual"
            },
            {
                "equipe_domicile": "HC Grenoble",
                "equipe_exterieur": "CA Montrouge 92",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2025-12-14 15:30:00",
                "statut": "SCHEDULED",
                "tournoi": "13/14 décembre - Villeurbanne",
                "lieu": "Villeurbanne",
                "rencId": generate_renc_id("HC Grenoble", "CA Montrouge 92", "2025-12-14 15:30:00", 15),
                "source": "manual"
            },
            
            # Tournoi 2 - 3/4 janvier (Carquefou - Salle de la Mainguais)
            {
                "equipe_domicile": "La Baule OHC",
                "equipe_exterieur": "PHC Marcq en Baroeul",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-03 13:00:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("La Baule OHC", "PHC Marcq en Baroeul", "2026-01-03 13:00:00", 16),
                "source": "manual"
            },
            {
                "equipe_domicile": "Carquefou HC",
                "equipe_exterieur": "CA Montrouge 92",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-03 14:05:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("Carquefou HC", "CA Montrouge 92", "2026-01-03 14:05:00", 17),
                "source": "manual"
            },
            {
                "equipe_domicile": "HC Grenoble",
                "equipe_exterieur": "Cambrai HC",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-03 15:10:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("HC Grenoble", "Cambrai HC", "2026-01-03 15:10:00", 18),
                "source": "manual"
            },
            {
                "equipe_domicile": "Blanc Mesnil SH",
                "equipe_exterieur": "PHC Marcq en Baroeul",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-03 16:15:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("Blanc Mesnil SH", "PHC Marcq en Baroeul", "2026-01-03 16:15:00", 19),
                "source": "manual"
            },
            {
                "equipe_domicile": "IH Lambersart",
                "equipe_exterieur": "AS Villeurbanne EL",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-03 17:20:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("IH Lambersart", "AS Villeurbanne EL", "2026-01-03 17:20:00", 20),
                "source": "manual"
            },
            {
                "equipe_domicile": "Villa Primrose",
                "equipe_exterieur": "Cambrai HC",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-03 18:25:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("Villa Primrose", "Cambrai HC", "2026-01-03 18:25:00", 21),
                "source": "manual"
            },
            {
                "equipe_domicile": "Carquefou HC",
                "equipe_exterieur": "HC Grenoble",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-03 19:30:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("Carquefou HC", "HC Grenoble", "2026-01-03 19:30:00", 22),
                "source": "manual"
            },
            {
                "equipe_domicile": "AS Villeurbanne EL",
                "equipe_exterieur": "Blanc Mesnil SH",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-03 20:35:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("AS Villeurbanne EL", "Blanc Mesnil SH", "2026-01-03 20:35:00", 23),
                "source": "manual"
            },
            # Dimanche 4 janvier
            {
                "equipe_domicile": "Villa Primrose",
                "equipe_exterieur": "IH Lambersart",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-04 09:00:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("Villa Primrose", "IH Lambersart", "2026-01-04 09:00:00", 24),
                "source": "manual"
            },
            {
                "equipe_domicile": "Cambrai HC",
                "equipe_exterieur": "CA Montrouge 92",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-04 10:05:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("Cambrai HC", "CA Montrouge 92", "2026-01-04 10:05:00", 25),
                "source": "manual"
            },
            {
                "equipe_domicile": "HC Grenoble",
                "equipe_exterieur": "AS Villeurbanne EL",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-04 11:10:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("HC Grenoble", "AS Villeurbanne EL", "2026-01-04 11:10:00", 26),
                "source": "manual"
            },
            {
                "equipe_domicile": "IH Lambersart",
                "equipe_exterieur": "La Baule OHC",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-04 12:15:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("IH Lambersart", "La Baule OHC", "2026-01-04 12:15:00", 27),
                "source": "manual"
            },
            {
                "equipe_domicile": "Carquefou HC",
                "equipe_exterieur": "PHC Marcq en Baroeul",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-04 13:20:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("Carquefou HC", "PHC Marcq en Baroeul", "2026-01-04 13:20:00", 28),
                "source": "manual"
            },
            {
                "equipe_domicile": "Villa Primrose",
                "equipe_exterieur": "CA Montrouge 92",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-04 14:25:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("Villa Primrose", "CA Montrouge 92", "2026-01-04 14:25:00", 29),
                "source": "manual"
            },
            {
                "equipe_domicile": "La Baule OHC",
                "equipe_exterieur": "Blanc Mesnil SH",
                "score_domicile": "",
                "score_exterieur": "",
                "date": "2026-01-04 15:30:00",
                "statut": "SCHEDULED",
                "tournoi": "3/4 janvier - Carquefou",
                "lieu": "Salle de la Mainguais",
                "rencId": generate_renc_id("La Baule OHC", "Blanc Mesnil SH", "2026-01-04 15:30:00", 30),
                "source": "manual"
            },
        ]
        
        return {
            "success": True,
            "data": matches_data,
            "count": len(matches_data),
            "discipline": "salle",
            "categorie": "Elite Femmes",
            "note": "Données manuelles en attente de confirmation FFHockey."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des matchs Elite Femmes Salle: {str(e)}")


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

@app.get("/api/v1/interligues-u14-filles/classement", tags=["Interligues U14"], summary="Classement U14 Filles")
def get_classement_interligues_u14_filles():
    """
    Récupère le classement calculé des Interligues U14 Filles.
    Calcul automatique: Victoire=3pts, Nul=1pt, Défaite=0pts
    Critères de départage: Différence de buts
    
    Returns:
        Classement des équipes U14 Filles
    """
    return calculate_classement_u14_filles()


@app.get("/api/v1/interligues-u14-filles/matchs", tags=["Interligues U14"], summary="Matchs U14 Filles")
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


@app.get("/api/v1/interligues-u14-garcons/matchs", tags=["Interligues U14"], summary="Matchs U14 Garçons")
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


@app.get("/api/v1/interligues-u14-garcons-poule-a/matchs", tags=["Interligues U14"])
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


@app.get("/api/v1/interligues-u14-garcons-poule-b/matchs", tags=["Interligues U14"])
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


@app.get("/api/v1/interligues-u14-garcons/phases", tags=["Interligues U14"])
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


@app.get("/api/v1/interligues-u14-garcons/poules/{phase_id}", tags=["Interligues U14"])
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
                    "ManifId": "4400",
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
                    poule_info["source"] = "manual"  # Indiquer que c'est une donnée manuelle
                    
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
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des poules: {str(e)}")


@app.get("/api/v1/interligues-u14-filles/phases", tags=["Interligues U14"])
async def get_interligues_u14_filles_phases():
    """
    Récupère les phases (groupes, finale) des Interligues U14 Filles.
    Permet de suivre l'évolution de la compétition.
    """
    try:
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerPhases"
        params = {
            "SaisonAnnee": "2026",
            "ManifId": "4401"  # U14 Filles
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
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des phases U14 Filles: {str(e)}")


@app.get("/api/v1/interligues-u14-filles/poules/{phase_id}", tags=["Interligues U14"])
async def get_interligues_u14_filles_poules(phase_id: str):
    """
    Récupère les poules (matchups) pour une phase spécifique des Interligues U14 Filles.
    Les rencontres s'ajoutent automatiquement dès que les équipes sont désignées.
    Inclut les données manuelles en attente de confirmation FFHockey.
    
    Args:
        phase_id: L'identifiant de la phase (ex: 7182 pour finale)
        
    Returns:
        Liste des poules avec leurs rencontres
        
    Example:
        /api/v1/interligues-u14-filles/poules/7182
    """
    try:
        # D'abord récupérer les poules
        poules_url = "https://championnats.ffhockey.org/rest2/Championnats/ListerPoules"
        poules_params = {
            "SaisonAnnee": "2026",
            "ManifId": "4401",  # U14 Filles
            "PhaseId": phase_id
        }
        
        poules_response = requests.get(poules_url, params=poules_params, timeout=10)
        poules_response.raise_for_status()
        poules_data = poules_response.json()
        
        if poules_data.get("ResponseCode") != "200":
            return {"success": False, "data": [], "count": 0}
        
        poules_raw = poules_data.get("Response", {}).get("PoulesArray", {})
        poules_formatted = []
        
        # Données manuelles pour les finales du 30/10 (en attente de confirmation)
        matches_finales_30oct = [
            ("11702", "Places 1 et 2", [
                create_placeholder_match("Finale du Championnat", "2025-10-30", "12:30", "La Boulie"),
            ]),
            ("11703", "Places 3 et 4", [
                create_placeholder_match("Match pour la médaille de bronze", "2025-10-30", "10:10", "La Boulie"),
            ]),
            ("11704", "Places 5 et 6", [
                create_placeholder_match("Classement 5e/6e place", "2025-10-30", "10:40", "Asnières"),
            ]),
        ]
        
        # Mapper les poules avec les matchs manuels
        poules_mapping = {poule_id: (libelle, matches) for poule_id, libelle, matches in matches_finales_30oct}
        
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
                    poule_info["source"] = "manual"  # Indiquer que c'est une donnée manuelle
                    
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


# ============================================
# ENDPOINTS EMAIL NOTIFICATIONS
# ============================================

@app.post("/api/v1/subscribe", tags=["Notifications"])
async def subscribe_email(subscription: EmailSubscription):
    """
    S'abonner aux notifications de fin de match par email.
    
    Args:
        subscription: Objet contenant l'email de l'abonné
        
    Returns:
        Confirmation de l'abonnement
    """
    global email_subscribers
    
    email = subscription.email.lower().strip()
    
    # Validation simple de l'email
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Email invalide")
    
    email_subscribers.add(email)
    save_subscribers(email_subscribers)
    
    return {
        "success": True,
        "message": f"Abonné avec succès à {email}",
        "total_subscribers": len(email_subscribers)
    }


@app.delete("/api/v1/unsubscribe", tags=["Notifications"])
async def unsubscribe_email(subscription: EmailSubscription):
    """
    Se désabonner des notifications de fin de match par email.
    
    Args:
        subscription: Objet contenant l'email à désabonner
        
    Returns:
        Confirmation de la désinscription
    """
    global email_subscribers
    
    email = subscription.email.lower().strip()
    
    if email in email_subscribers:
        email_subscribers.remove(email)
        save_subscribers(email_subscribers)
    
    return {
        "success": True,
        "message": f"Désinscrit avec succès: {email}",
        "total_subscribers": len(email_subscribers)
    }


@app.get("/api/v1/notifications/stats", tags=["Notifications"])
async def notification_stats():
    """
    Obtenir les statistiques des notifications.
    
    Returns:
        Nombre d'abonnés et de matchs notifiés
    """
    return {
        "total_subscribers": len(email_subscribers),
        "total_notified_matches": len(notified_matches),
        "subscribers": list(email_subscribers) if email_subscribers else []
    }


@app.get("/api/v1/debug/email-test", tags=["Debug"])
async def debug_email_test():
    """
    Endpoint de test pour déboguer les emails avec SendGrid.
    Envoie un email de test et affiche tous les logs.
    """
    from datetime import datetime
    
    sendgrid_api_key = os.environ.get("SENDGRID_API_KEY")
    
    debug_info = {
        "timestamp": str(datetime.now()),
        "sendgrid_configured": bool(sendgrid_api_key),
        "api_key_length": len(sendgrid_api_key) if sendgrid_api_key else 0,
        "subscribers": list(email_subscribers),
        "test_result": None,
        "error": None
    }
    
    if not sendgrid_api_key:
        debug_info["error"] = "SENDGRID_API_KEY not configured on Render!"
        return debug_info
    
    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        sender_email = "quentin.mouraud@carquefouhockeyclub.com"  # Email expéditeur vérifié dans SendGrid
        recipient = list(email_subscribers)[0] if email_subscribers else "test@example.com"
        
        debug_info["test_result"] = f"Creating SendGrid message..."
        
        html = f"""
        <html><body style="font-family: Arial; background: #667eea; padding: 20px;">
        <div style="background: white; padding: 20px; border-radius: 10px;">
        <h2>✅ Test d'Email - Hockey API SendGrid</h2>
        <p>Cet email de test prouve que le système fonctionne!</p>
        <p><strong>Heure:</strong> {datetime.now()}</p>
        <p><strong>De:</strong> {sender_email}</p>
        <p><strong>À:</strong> {recipient}</p>
        </div></body></html>
        """
        
        message = Mail(
            from_email=sender_email,
            to_emails=recipient,
            subject="✅ Test d'Email - Hockey API SendGrid",
            html_content=html
        )
        
        debug_info["test_result"] = "Sending via SendGrid..."
        response = sg.send(message)
        
        debug_info["test_result"] = f"✅ Email envoyé! Status: {response.status_code}"
        debug_info["response_code"] = response.status_code
        
    except Exception as e:
        debug_info["error"] = f"Error: {str(e)}"
    
    return debug_info


@app.get("/api/v1/test/send-notification-u14-filles", tags=["Debug"])
async def test_send_notification_u14_filles():
    """
    Endpoint de test pour forcer l'envoi d'une notification avec un match réel des U14 Filles.
    Récupère le premier match terminé et envoie l'email.
    """
    import requests
    
    try:
        # Récupérer les matchs U14 Filles (ManifId: 4401)
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
        params = {
            "SaisonAnnee": "2026",
            "ManifId": "4401"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        test_result = {
            "timestamp": str(__import__('datetime').datetime.now()),
            "status": "pending",
            "message": None,
            "email_sent": False,
            "match_found": False,
            "match_info": None
        }
        
        if data.get("ResponseCode") == "200" and "Response" in data:
            matches_raw = data["Response"].get("RencontresArray", {})
            
            # Chercher le premier match terminé
            for match in matches_raw.values():
                but1 = match.get("Scores", {}).get("RencButsEqp1")
                but2 = match.get("Scores", {}).get("RencButsEqp2")
                
                if but1 is not None and but2 is not None:  # Match terminé
                    equipe1 = match.get("Equipe1", {}).get("EquipeNom", "TBD")
                    equipe2 = match.get("Equipe2", {}).get("EquipeNom", "TBD")
                    
                    test_match = {
                        "equipe_domicile": equipe1,
                        "equipe_exterieur": equipe2,
                        "score_domicile": but1,
                        "score_exterieur": but2,
                        "date": match.get("RencDateDerog", ""),
                        "statut": "FINISHED",
                        "rencId": match.get("RencId", "")
                    }
                    
                    test_result["match_found"] = True
                    test_result["match_info"] = test_match
                    
                    # Envoyer l'email
                    if email_subscribers:
                        success = send_match_finished_email(
                            email_subscribers,
                            test_match,
                            "U14 Filles - TEST"
                        )
                        
                        test_result["email_sent"] = success
                        test_result["status"] = "success" if success else "error"
                        test_result["message"] = f"Email envoyé à {len(email_subscribers)} abonné(s)" if success else "Erreur lors de l'envoi"
                    else:
                        test_result["status"] = "error"
                        test_result["message"] = "Aucun abonné configuré"
                    
                    break
            
            if not test_result["match_found"]:
                test_result["status"] = "no_match"
                test_result["message"] = "Aucun match terminé trouvé dans les U14 Filles"
        else:
            test_result["status"] = "error"
            test_result["message"] = "Erreur lors de la récupération des matchs"
        
        return test_result
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Exception: {str(e)}"
        }


@app.get("/api/v1/test/send-notification-interligues", tags=["Debug"])
async def test_send_notification_interligues():
    """
    Endpoint de test pour forcer l'envoi d'une notification avec un match réel des Interligues.
    Récupère le premier match terminé et envoie l'email.
    """
    import requests
    
    try:
        # Récupérer les matchs U14 Garçons
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
        params = {
            "SaisonAnnee": "2026",
            "ManifId": "4400"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        test_result = {
            "timestamp": str(__import__('datetime').datetime.now()),
            "status": "pending",
            "message": None,
            "email_sent": False,
            "match_found": False,
            "match_info": None
        }
        
        if data.get("ResponseCode") == "200" and "Response" in data:
            matches_raw = data["Response"].get("RencontresArray", {})
            
            # Chercher le premier match terminé
            for match in matches_raw.values():
                but1 = match.get("Scores", {}).get("RencButsEqp1")
                but2 = match.get("Scores", {}).get("RencButsEqp2")
                
                if but1 and but2:  # Match terminé
                    equipe1 = match.get("Equipe1", {}).get("EquipeNom", "TBD")
                    equipe2 = match.get("Equipe2", {}).get("EquipeNom", "TBD")
                    
                    test_match = {
                        "equipe_domicile": equipe1,
                        "equipe_exterieur": equipe2,
                        "score_domicile": but1,
                        "score_exterieur": but2,
                        "date": match.get("RencDateDerog", ""),
                        "statut": "FINISHED"
                    }
                    
                    test_result["match_found"] = True
                    test_result["match_info"] = test_match
                    
                    # Envoyer l'email
                    if email_subscribers:
                        success = send_match_finished_email(
                            email_subscribers,
                            test_match,
                            "U14 Garçons - TEST"
                        )
                        
                        test_result["email_sent"] = success
                        test_result["status"] = "success" if success else "error"
                        test_result["message"] = f"Email envoyé à {len(email_subscribers)} abonné(s)" if success else "Erreur lors de l'envoi"
                    else:
                        test_result["status"] = "error"
                        test_result["message"] = "Aucun abonné configuré"
                    
                    break
            
            if not test_result["match_found"]:
                test_result["status"] = "no_match"
                test_result["message"] = "Aucun match terminé trouvé dans les Interligues U14 Garçons"
        else:
            test_result["status"] = "error"
            test_result["message"] = "Erreur lors de la récupération des matchs"
        
        return test_result
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Erreur: {str(e)}",
            "email_sent": False
        }


# ============================================
# ENDPOINTS - FEUILLE DE MATCH & OFFICIELS
# ============================================

# ============================================
# PARSING FUNCTIONS - MATCH SHEET DATA
# ============================================

def parse_players_table_from_html(html_content):
    """
    Parse la table des joueurs depuis le HTML de la feuille de match.
    Extrait le nom complet et le numéro de maillot de chaque joueur.
    
    Args:
        html_content: Le contenu HTML de la feuille de match
        
    Returns:
        Dict avec équipes et leurs joueurs
    """
    players_data = {
        "team1": {"nom": "", "joueurs": {}},
        "team2": {"nom": "", "joueurs": {}}
    }
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Chercher les noms des équipes
        team_names = re.findall(r'<p><strong>NOM : <\/strong>([^<]+)<\/p>', html_content)
        if len(team_names) >= 2:
            players_data["team1"]["nom"] = team_names[0].strip()
            players_data["team2"]["nom"] = team_names[1].strip()
        
        # Trouver la table des joueurs (chercher toutes les tables et trouver celle avec classe "orbe")
        all_tables = soup.find_all('table')
        player_table = None
        
        for table in all_tables:
            table_classes = table.get('class', [])
            # Vérifier si la classe "orbe" est présente
            if any('orbe' in str(cls) for cls in table_classes):
                player_table = table
                break
        
        if player_table:
            tbody = player_table.find('tbody')
            
            if tbody:
                rows = tbody.find_all('tr')
                
                # Chaque ligne a 8 colonnes (2 équipes x 4 colonnes)
                # Team1: Col 0-3 (licence, maillot, nom, cartons)
                # Team2: Col 4-7 (licence, maillot, nom, cartons)
                
                for row in rows:
                    cells = row.find_all('td')
                    
                    if len(cells) >= 8:
                        # Team1
                        maillot_cell_t1 = cells[1].get_text(strip=True)
                        nom_cell_t1 = cells[2].get_text(strip=True)
                        
                        # Team2
                        maillot_cell_t2 = cells[5].get_text(strip=True)
                        nom_cell_t2 = cells[6].get_text(strip=True)
                        
                        # Extraire les numéros de maillot
                        maillot_match_t1 = re.match(r'(\d+)', maillot_cell_t1)
                        if maillot_match_t1 and nom_cell_t1:
                            maillot_t1 = int(maillot_match_t1.group(1))
                            players_data["team1"]["joueurs"][maillot_t1] = nom_cell_t1
                        
                        maillot_match_t2 = re.match(r'(\d+)', maillot_cell_t2)
                        if maillot_match_t2 and nom_cell_t2:
                            maillot_t2 = int(maillot_match_t2.group(1))
                            players_data["team2"]["joueurs"][maillot_t2] = nom_cell_t2
    
    except Exception as e:
        print(f"Error parsing players table: {str(e)}")
    
    return players_data


def parse_scorers_from_html(html_content):
    """
    Parse les buteurs depuis le HTML de la feuille de match.
    Extrait les numéros de maillot, noms complets et compte les buts marqués.
    Importante: Match les buteurs à chaque équipe par l'ordre dans le HTML sans filtrer.
    
    Args:
        html_content: Le contenu HTML de la feuille de match
        
    Returns:
        Dict avec les buteurs structurés par équipe avec noms
    """
    scorers = {
        "team1": {
            "nom_equipe": "Équipe 1",
            "buteurs": []
        },
        "team2": {
            "nom_equipe": "Équipe 2",
            "buteurs": []
        }
    }
    
    try:
        # Récupérer les données des joueurs
        players_data = parse_players_table_from_html(html_content)
        scorers["team1"]["nom_equipe"] = players_data["team1"]["nom"]
        scorers["team2"]["nom_equipe"] = players_data["team2"]["nom"]
        
        # Chercher les sections "Buteurs :" SANS FILTRER (garder l'ordre original)
        buteurs_pattern = r'<strong>Buteurs : <\/strong>([^<]*)'
        buteurs_matches = re.findall(buteurs_pattern, html_content)
        
        # IMPORTANT: Ne pas filtrer! Garder l'ordre original du HTML
        # Index 0 = Team1, Index 1 = Team2 (même si vides)
        if len(buteurs_matches) >= 2:
            # Première équipe (index 0)
            buteurs_team1 = buteurs_matches[0].strip()
            if buteurs_team1 and '&nbsp;' not in buteurs_team1:
                numbers = re.findall(r'N°(\d+)\s*\(x(\d+)\)', buteurs_team1)
                for num, count in numbers:
                    num = int(num)
                    nom_joueur = players_data["team1"]["joueurs"].get(num, f"Joueur N°{num}")
                    scorers["team1"]["buteurs"].append({
                        "numero_maillot": num,
                        "nom": nom_joueur,
                        "buts": int(count)
                    })
            
            # Deuxième équipe (index 1)
            buteurs_team2 = buteurs_matches[1].strip()
            if buteurs_team2 and '&nbsp;' not in buteurs_team2:
                numbers = re.findall(r'N°(\d+)\s*\(x(\d+)\)', buteurs_team2)
                for num, count in numbers:
                    num = int(num)
                    nom_joueur = players_data["team2"]["joueurs"].get(num, f"Joueur N°{num}")
                    scorers["team2"]["buteurs"].append({
                        "numero_maillot": num,
                        "nom": nom_joueur,
                        "buts": int(count)
                    })
        elif len(buteurs_matches) == 1:
            buteurs_team1 = buteurs_matches[0].strip()
            if buteurs_team1 and '&nbsp;' not in buteurs_team1:
                numbers = re.findall(r'N°(\d+)\s*\(x(\d+)\)', buteurs_team1)
                for num, count in numbers:
                    num = int(num)
                    nom_joueur = players_data["team1"]["joueurs"].get(num, f"Joueur N°{num}")
                    scorers["team1"]["buteurs"].append({
                        "numero_maillot": num,
                        "nom": nom_joueur,
                        "buts": int(count)
                    })
    
    except Exception as e:
        print(f"Error parsing scorers: {str(e)}")
    
    return scorers



def parse_cards_from_html(html_content):
    """
    Parse les cartons depuis le HTML de la feuille de match.
    Identifie les cartons verts, jaunes et rouges avec noms et équipes.
    """
    cards = {
        "team1": {
            "nom_equipe": "Équipe 1",
            "jaune": [],
            "rouge": [],
            "vert": []
        },
        "team2": {
            "nom_equipe": "Équipe 2",
            "jaune": [],
            "rouge": [],
            "vert": []
        }
    }
    
    try:
        players_data = parse_players_table_from_html(html_content)
        cards["team1"]["nom_equipe"] = players_data["team1"]["nom"]
        cards["team2"]["nom_equipe"] = players_data["team2"]["nom"]
        
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = soup.find_all('table', {'class': 'orbe'})
        
        if len(tables) >= 1:
            player_table = tables[0]
            tbody = player_table.find('tbody')
            
            if tbody:
                rows = tbody.find_all('tr')
                total_rows = len(rows)
                
                for i, row in enumerate(rows):
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        maillot_cell = cells[1].get_text(strip=True)
                        nom_cell = cells[2].get_text(strip=True)
                        carton_cell = cells[3]
                        
                        nom = nom_cell.strip()
                        carton_html = str(carton_cell)
                        team = "team1" if i < total_rows // 2 else "team2"
                        
                        maillot_match = re.match(r'(\d+)', maillot_cell)
                        maillot = int(maillot_match.group(1)) if maillot_match else None
                        
                        if 'CartonRouge' in carton_html or 'txt-orange' in carton_html:
                            cards[team]["rouge"].append({"nom": nom, "numero_maillot": maillot})
                        elif 'CartonJaune' in carton_html:
                            cards[team]["jaune"].append({"nom": nom, "numero_maillot": maillot})
                        
                        if 'txt-vert' in carton_html or 'txt-vert' in str(cells[2]):
                            if not any(c["nom"] == nom for c in cards[team]["vert"]):
                                cards[team]["vert"].append({"nom": nom, "numero_maillot": maillot})
        
        vert_pattern = r'<strong class="txt-vert">([A-Z ]+)<\/strong>'
        verts = re.findall(vert_pattern, html_content)
        cards["team1"]["vert"] = []
        cards["team2"]["vert"] = []
        verts_per_team = len(verts) // 2
        for i, vert_name in enumerate(verts):
            team = "team1" if i < verts_per_team else "team2"
            cards[team]["vert"].append({"nom": vert_name.strip()})
        
    except Exception as e:
        print(f"Error parsing cards: {str(e)}")
        vert_pattern = r'<strong class="txt-vert">([A-Z ]+)<\/strong>'
        verts = re.findall(vert_pattern, html_content)
        cards["team1"]["vert"] = []
        cards["team2"]["vert"] = []
        verts_per_team = len(verts) // 2
        for i, vert_name in enumerate(verts):
            team = "team1" if i < verts_per_team else "team2"
            cards[team]["vert"].append({"nom": vert_name.strip()})
    
    return cards



def get_match_info_from_api(renc_id):
    """
    Récupère les infos du match depuis l'API ListerRencontres.
    Cherche dans tous les ManifId disponibles.
    
    Args:
        renc_id: L'identifiant de la rencontre
        
    Returns:
        Dict avec date, horaire, équipes et scores
    """
    match_info = {
        "date": None,
        "horaire": None,
        "terrain": None,
        "team1": {
            "nom": None,
            "buts": None
        },
        "team2": {
            "nom": None,
            "buts": None
        }
    }
    
    try:
        import requests
        
        # List de ManifId à tester (U14 et autres)
        manif_ids = ["4400", "4401", "4402", "4403", "4404", "4405"]  # U14 M, U14 F, etc.
        
        for manif_id in manif_ids:
            try:
                url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
                params = {
                    "SaisonAnnee": "2026",
                    "ManifId": manif_id
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data.get("ResponseCode") != "200":
                    continue
                
                # Chercher le match avec le bon RencId
                matches = data.get("Response", {}).get("RencontresArray", {})
                if str(renc_id) in matches:
                    match = matches[str(renc_id)]
                    
                    # Extraire les noms des équipes
                    team1 = match.get("Equipe1", {})
                    team2 = match.get("Equipe2", {})
                    
                    match_info["team1"]["nom"] = team1.get("EquipeNom", "").strip() or None
                    match_info["team2"]["nom"] = team2.get("EquipeNom", "").strip() or None
                    
                    # Extraire les scores
                    scores = match.get("Scores", {})
                    score1 = scores.get("RencButsEqp1")
                    score2 = scores.get("RencButsEqp2")
                    
                    if score1:
                        try:
                            match_info["team1"]["buts"] = int(score1)
                        except:
                            pass
                    if score2:
                        try:
                            match_info["team2"]["buts"] = int(score2)
                        except:
                            pass
                    
                    # Extraire date et horaire
                    date_str = match.get("RencDateDerog", "")  # Format: "2025-10-29 11:20:00"
                    if date_str:
                        try:
                            from datetime import datetime
                            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                            match_info["date"] = dt.strftime("%d/%m/%Y")
                            match_info["horaire"] = dt.strftime("%H:%M")
                        except:
                            pass
                    
                    # Si on a au moins trouvé le match, on retourne
                    return match_info
                    
            except:
                continue
        
        return match_info
        
    except Exception as e:
        return match_info


def extract_match_info_from_html(html_content):
    """
    Extrait les informations du match depuis la feuille de match HTML.
    Récupère: date, horaire, terrain, équipes et scores.
    
    Args:
        html_content: Le contenu HTML de la feuille de match
        
    Returns:
        Dict avec les infos du match (None si HTML vide/inexistant)
    """
    match_info = {
        "date": None,
        "horaire": None,
        "terrain": None,
        "team1": {
            "nom": None,
            "buts": None
        },
        "team2": {
            "nom": None,
            "buts": None
        }
    }
    
    # Si le HTML est vide ou None, retourner les valeurs par défaut (None)
    if not html_content or html_content is None or not html_content.strip():
        return match_info
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Récupérer les paragraphes
        paragraphs = soup.find_all('p')
        
        # Le deuxième paragraphe (index 1) contient date, horaire, terrain
        if len(paragraphs) > 1:
            info_para = paragraphs[1].get_text()
            # Extraire la date
            date_match = re.search(r'Date\s*:\s*(\d+/\d+/\d+)', info_para)
            if date_match:
                match_info["date"] = date_match.group(1)
            
            # Extraire l'horaire
            time_match = re.search(r'Horaire\s*:\s*(\d+:\d+)', info_para)
            if time_match:
                match_info["horaire"] = time_match.group(1)
            
            # Extraire le terrain
            terrain_match = re.search(r'Terrain\s*:\s*([^\n]+?)(?:\n|$)', info_para)
            if terrain_match:
                match_info["terrain"] = terrain_match.group(1).strip()
        
        # Récupérer les noms des équipes et les buts
        team_names = re.findall(r'<strong>NOM\s*:\s*<\/strong>([^<]+)<', html_content)
        
        if len(team_names) >= 2:
            match_info["team1"]["nom"] = team_names[0].strip()
            match_info["team2"]["nom"] = team_names[1].strip()
        
        # Extraire les scores
        # Pattern: "Buts en chiffres : X"
        scores = re.findall(r'Buts en chiffres\s*:\s*(\d+)', html_content)
        # Les scores sont simplement team1, team2 (pas de buts concédés dans cette extraction)
        if len(scores) >= 2:
            match_info["team1"]["buts"] = int(scores[0])
            match_info["team2"]["buts"] = int(scores[1])
    
    except Exception as e:
        print(f"Error extracting match info: {str(e)}")
    
    return match_info


@app.get("/api/v1/match/{renc_id}/buteurs", tags=["Feuille de Match"], summary="Buteurs du match")
async def get_match_scorers(renc_id: str):
    """
    Récupère la liste structurée des buteurs pour un match spécifique.
    Parse la feuille de match et extrait les numéros de maillot et les buts marqués.
    
    Args:
        renc_id: L'identifiant de la rencontre (RencId)
        
    Returns:
        JSON structuré avec les buteurs par équipe et leurs buts
        
    Example:
        /api/v1/match/196053/buteurs
    """
    try:
        import requests
        
        # Récupérer la feuille de match
        url = "https://championnats.ffhockey.org/rest2/Championnats/FeuilleDeMatchHTML"
        params = {
            "SaisonAnnee": "2026",
            "RencId": renc_id
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("ResponseCode") != "200":
            raise HTTPException(
                status_code=404,
                detail=f"Erreur lors de la récupération de la feuille de match: {data.get('ResponseMessage')}"
            )
        
        html_content = data.get("Response", {}).get("RenduHTML", "")
        scorers = parse_scorers_from_html(html_content)
        
        return {
            "success": True,
            "renc_id": renc_id,
            "data": scorers
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout lors de la récupération des buteurs")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Impossible de se connecter à l'API FFH")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/api/v1/match/{renc_id}/cartons", tags=["Feuille de Match"], summary="Cartons du match")
async def get_match_cards(renc_id: str):
    """
    Récupère la liste structurée des cartons pour un match spécifique.
    Parse la feuille de match et extrait les cartons verts, jaunes et rouges.
    
    Args:
        renc_id: L'identifiant de la rencontre (RencId)
        
    Returns:
        JSON structuré avec les cartons par type et équipe
        
    Example:
        /api/v1/match/196053/cartons
    """
    try:
        import requests
        
        # Récupérer la feuille de match
        url = "https://championnats.ffhockey.org/rest2/Championnats/FeuilleDeMatchHTML"
        params = {
            "SaisonAnnee": "2026",
            "RencId": renc_id
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("ResponseCode") != "200":
            raise HTTPException(
                status_code=404,
                detail=f"Erreur lors de la récupération de la feuille de match: {data.get('ResponseMessage')}"
            )
        
        html_content = data.get("Response", {}).get("RenduHTML", "")
        cards = parse_cards_from_html(html_content)
        
        return {
            "success": True,
            "renc_id": renc_id,
            "data": cards
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout lors de la récupération des cartons")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Impossible de se connecter à l'API FFH")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/api/v1/match/{renc_id}/officiels", tags=["Feuille de Match"], summary="Officiels du match")
async def get_match_officials(renc_id: str, manif_id: str = ""):
    """
    Récupère les officiels (arbitres, délégués, etc.) pour un match spécifique.
    Inclut aussi les informations du match: équipes, date, heure, terrain, scores.
    
    Args:
        renc_id: L'identifiant de la rencontre (RencId)
        manif_id: L'identifiant optionnel de la manifestation
        
    Returns:
        Objet avec infos du match et liste des officiels avec leurs fonctions
        
    Example:
        /api/v1/match/196053/officiels
    """
    try:
        import requests
        
        # D'abord récupérer les infos du match depuis la feuille de match
        sheet_url = "https://championnats.ffhockey.org/rest2/Championnats/FeuilleDeMatchHTML"
        sheet_params = {
            "SaisonAnnee": "2026",
            "RencId": renc_id
        }
        sheet_response = requests.get(sheet_url, params=sheet_params, timeout=10)
        sheet_response.raise_for_status()
        sheet_data = sheet_response.json()
        
        # Extraire les infos du match
        html_content = sheet_data.get("Response", {}).get("RenduHTML", "")
        match_info = extract_match_info_from_html(html_content)
        
        # Si la feuille de match n'est pas disponible, récupérer depuis ListerRencontres
        if not match_info["date"] and not match_info["team1"]["nom"]:
            match_info = get_match_info_from_api(renc_id)
        
        # Ensuite récupérer les officiels
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerOfficiels"
        params = {
            "SaisonAnnee": "2026",
            "RencId": renc_id,
            "ManifId": manif_id or "",
            "PersonneId": "",
            "LicenceCode": ""
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("ResponseCode") != "200":
            raise HTTPException(
                status_code=404,
                detail=f"Erreur lors de la récupération des officiels: {data.get('ResponseMessage')}"
            )
        
        officials_data = data.get("Response", {})
        officials_array = officials_data.get("OfficielsArray", {})
        
        # Transformer les données pour un format plus lisible
        officials_list = []
        for official_id, official_info in officials_array.items():
            fonction = official_info.get("Fonction", {})
            personne = official_info.get("Personne", {})
            
            officials_list.append({
                "fonction": fonction.get("FonctionLibelle", ""),
                "code_fonction": fonction.get("FonctionCode", ""),
                "nom": f"{personne.get('PersonneNom', '')} {personne.get('PersonnePrenom', '')}".strip(),
                "civilite": personne.get("PersonneCivilite", ""),
                "licence": personne.get("LicenceCode", ""),
                "personne_id": personne.get("PersonneId", "")
            })
        
        return {
            "success": True,
            "renc_id": renc_id,
            "match": {
                "date": match_info.get("date"),
                "horaire": match_info.get("horaire"),
                "terrain": match_info.get("terrain"),
                "team1": {
                    "nom": match_info.get("team1", {}).get("nom"),
                    "buts": match_info.get("team1", {}).get("buts")
                },
                "team2": {
                    "nom": match_info.get("team2", {}).get("nom"),
                    "buts": match_info.get("team2", {}).get("buts")
                }
            },
            "nb_officials": officials_data.get("NbOfficiels", 0),
            "officiels": officials_list
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout lors de la récupération des officiels")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Impossible de se connecter à l'API FFH")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/api/v1/match/{renc_id}/feuille-de-match", tags=["Feuille de Match"], summary="Feuille de match HTML")
async def get_match_sheet(renc_id: str):
    """
    Récupère la feuille de match (HTML) pour un match spécifique.
    Contient tous les détails du match: buteurs, cartons, joueurs, etc.
    
    Args:
        renc_id: L'identifiant de la rencontre (RencId)
        
    Returns:
        HTML de la feuille de match avec tous les détails du match
        
    Example:
        /api/v1/match/196053/feuille-de-match
    """
    try:
        import requests
        
        url = "https://championnats.ffhockey.org/rest2/Championnats/FeuilleDeMatchHTML"
        params = {
            "SaisonAnnee": "2026",
            "RencId": renc_id
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("ResponseCode") != "200":
            raise HTTPException(
                status_code=404,
                detail=f"Erreur lors de la récupération de la feuille de match: {data.get('ResponseMessage')}"
            )
        
        response_data = data.get("Response", {})
        html_content = response_data.get("RenduHTML", "")
        
        return {
            "success": True,
            "renc_id": renc_id,
            "html": html_content
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout lors de la récupération de la feuille de match")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Impossible de se connecter à l'API FFH")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# ============================================
# LIVE SCORE ENDPOINTS (FIREBASE)
# ============================================

def verify_admin_token(token: str) -> bool:
    """
    Vérifie le token admin (simple mot de passe pour MVP).
    À remplacer par JWT Firebase plus tard.
    """
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    return token == admin_password

@app.get("/api/v1/live/matches", tags=["Live Score"], summary="Récupérer tous les matchs live")
async def get_live_matches():
    """
    Récupère tous les matchs en direct depuis Firebase.
    
    Returns:
        Liste des matchs avec scores, scorers, cartons en temps réel.
    """
    if not FIREBASE_ENABLED:
        raise HTTPException(status_code=503, detail="Firebase non configuré")
    
    try:
        matches_ref = db.reference('matches')
        matches_data = matches_ref.get()
        
        if not matches_data:
            return {"success": True, "data": {}}
        
        return {
            "success": True,
            "data": matches_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Firebase: {str(e)}")


@app.post("/api/v1/live/match/{match_id}/init", tags=["Live Score"], summary="Initialiser un match")
async def init_live_match(match_id: str, admin_token: str = None):
    """
    Initialiser un nouveau match dans Firebase ou en cache.
    
    Args:
        match_id: ID unique du match
        admin_token: Token d'authentification admin
        
    Returns:
        Confirmation de la création
    """
    if not admin_token or not verify_admin_token(admin_token):
        raise HTTPException(status_code=401, detail="Token admin invalide")
    
    try:
        data = {
            'score_domicile': 0,
            'score_exterieur': 0,
            'scorers': [],
            'cards': [],
            'statut': 'SCHEDULED',
            'last_updated': int(time.time())
        }
        
        # Essayer Firebase en premier
        if FIREBASE_ENABLED:
            try:
                match_ref = db.reference(f'matches/{match_id}')
                match_ref.set(data)
                print(f"✅ Match {match_id} créé dans Firebase")
            except Exception as fb_error:
                print(f"⚠️ Firebase échoue ({str(fb_error)}), utilisation du cache")
                LIVE_MATCHES_CACHE[match_id] = data
        else:
            # Utiliser le cache local
            LIVE_MATCHES_CACHE[match_id] = data
            print(f"📝 Match {match_id} créé en cache local")
        
        return {
            "success": True,
            "message": f"Match {match_id} initialisé",
            "match_id": match_id,
            "data": data,
            "backend": "Firebase" if FIREBASE_ENABLED else "Cache local"
        }
    except Exception as e:
        print(f"Erreur init match: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/api/v1/live/match/{match_id}", tags=["Live Score"], summary="Récupérer un match live")
async def get_live_match(match_id: str):
    """
    Récupère un match spécifique depuis Firebase.
    
    Args:
        match_id: ID du match
        
    Returns:
        Données complètes du match (score, scorers, cartons)
    """
    if not FIREBASE_ENABLED:
        raise HTTPException(status_code=503, detail="Firebase non configuré")
    
    try:
        match_ref = db.reference(f'matches/{match_id}')
        match_data = match_ref.get()
        
        if not match_data:
            raise HTTPException(status_code=404, detail="Match non trouvé")
        
        return {
            "success": True,
            "match_id": match_id,
            "data": match_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Firebase: {str(e)}")


@app.put("/api/v1/live/match/{match_id}/score", tags=["Live Score"], summary="Mettre à jour le score")
async def update_match_score(match_id: str, score: ScoreUpdate, admin_token: str = None):
    """
    Mettre à jour le score d'un match en direct.
    
    Args:
        match_id: ID du match
        score: Les nouveaux scores (domicile et extérieur)
        admin_token: Token d'authentification admin (query param)
        
    Returns:
        Confirmation de la mise à jour
        
    Example:
        PUT /api/v1/live/match/match123/score?admin_token=admin123
        {"score_domicile": 5, "score_exterieur": 3}
    """
    if not admin_token or not verify_admin_token(admin_token):
        raise HTTPException(status_code=401, detail="Token admin invalide")
    
    try:
        # Essayer Firebase en premier
        if FIREBASE_ENABLED:
            try:
                match_ref = db.reference(f'matches/{match_id}')
                
                # Vérifier si le match existe (peut lever une exception 404)
                try:
                    existing_match = match_ref.get()
                except Exception as get_error:
                    # Si c'est une 404, considérez qu'il n'existe pas
                    if "404" in str(get_error):
                        existing_match = None
                    else:
                        raise
                
                if not existing_match:
                    # Créer le match avec structure initiale
                    match_ref.set({
                        'score_domicile': score.score_domicile,
                        'score_exterieur': score.score_exterieur,
                        'scorers': [],
                        'cards': [],
                        'statut': 'SCHEDULED',
                        'last_updated': int(time.time())
                    })
                    print(f"✅ Match {match_id} créé dans Firebase")
                else:
                    # Mettre à jour le score existant
                    match_ref.update({
                        'score_domicile': score.score_domicile,
                        'score_exterieur': score.score_exterieur,
                        'last_updated': int(time.time())
                    })
                    print(f"✅ Score {match_id} mis à jour dans Firebase")
                backend = "Firebase"
            except Exception as fb_error:
                print(f"❌ Firebase échoue pour score: {type(fb_error).__name__}: {str(fb_error)}")
                import traceback
                traceback.print_exc()
                if match_id not in LIVE_MATCHES_CACHE:
                    LIVE_MATCHES_CACHE[match_id] = {
                        'score_domicile': 0, 'score_exterieur': 0,
                        'scorers': [], 'cards': [], 'statut': 'SCHEDULED',
                        'last_updated': int(time.time())
                    }
                LIVE_MATCHES_CACHE[match_id]['score_domicile'] = score.score_domicile
                LIVE_MATCHES_CACHE[match_id]['score_exterieur'] = score.score_exterieur
                LIVE_MATCHES_CACHE[match_id]['last_updated'] = int(time.time())
                backend = "Cache"
        else:
            # Utiliser le cache
            if match_id not in LIVE_MATCHES_CACHE:
                LIVE_MATCHES_CACHE[match_id] = {
                    'score_domicile': 0, 'score_exterieur': 0,
                    'scorers': [], 'cards': [], 'statut': 'SCHEDULED',
                    'last_updated': int(time.time())
                }
            LIVE_MATCHES_CACHE[match_id]['score_domicile'] = score.score_domicile
            LIVE_MATCHES_CACHE[match_id]['score_exterieur'] = score.score_exterieur
            LIVE_MATCHES_CACHE[match_id]['last_updated'] = int(time.time())
            backend = "Cache"
        
        return {
            "success": True,
            "message": f"Score du match {match_id} mis à jour",
            "match_id": match_id,
            "score_domicile": score.score_domicile,
            "score_exterieur": score.score_exterieur,
            "backend": backend
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.post("/api/v1/live/match/{match_id}/scorer", tags=["Live Score"], summary="Ajouter un buteur")
async def add_scorer(match_id: str, scorer: ScorerUpdate, admin_token: str = None):
    """
    Ajouter un buteur à un match en direct.
    
    Args:
        match_id: ID du match
        scorer: Informations du buteur
        admin_token: Token d'authentification admin
        
    Returns:
        Confirmation de l'ajout
        
    Example:
        POST /api/v1/live/match/match123/scorer?admin_token=admin123
        {"joueur": "Dupont", "equipe": "domicile", "temps": 25}
    """
    if not admin_token or not verify_admin_token(admin_token):
        raise HTTPException(status_code=401, detail="Token admin invalide")
    
    try:
        new_scorer = {
            "joueur": scorer.joueur,
            "equipe": scorer.equipe,
            "temps": scorer.temps,
            "timestamp": int(time.time())
        }
        
        # Essayer Firebase en premier
        if FIREBASE_ENABLED:
            try:
                scorers_ref = db.reference(f'matches/{match_id}/scorers')
                current_scorers = scorers_ref.get() or []
                
                if isinstance(current_scorers, list):
                    current_scorers.append(new_scorer)
                else:
                    current_scorers = [new_scorer]
                
                scorers_ref.set(current_scorers)
                backend = "Firebase"
            except Exception as fb_error:
                print(f"⚠️ Firebase échoue pour scorer ({str(fb_error)}), utilisation du cache")
                if match_id not in LIVE_MATCHES_CACHE:
                    LIVE_MATCHES_CACHE[match_id] = {
                        'score_domicile': 0, 'score_exterieur': 0,
                        'scorers': [], 'cards': [], 'statut': 'SCHEDULED',
                        'last_updated': int(time.time())
                    }
                LIVE_MATCHES_CACHE[match_id]['scorers'].append(new_scorer)
                backend = "Cache"
        else:
            # Utiliser le cache
            if match_id not in LIVE_MATCHES_CACHE:
                LIVE_MATCHES_CACHE[match_id] = {
                    'score_domicile': 0, 'score_exterieur': 0,
                    'scorers': [], 'cards': [], 'statut': 'SCHEDULED',
                    'last_updated': int(time.time())
                }
            LIVE_MATCHES_CACHE[match_id]['scorers'].append(new_scorer)
            backend = "Cache"
        
        return {
            "success": True,
            "message": f"Buteur {scorer.joueur} ajouté pour l'équipe {scorer.equipe}",
            "match_id": match_id,
            "scorer": new_scorer,
            "backend": backend
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.post("/api/v1/live/match/{match_id}/card", tags=["Live Score"], summary="Ajouter un carton")
async def add_card(match_id: str, card: CardUpdate, admin_token: str = None):
    """
    Ajouter un carton (jaune ou rouge) à un match en direct.
    
    Args:
        match_id: ID du match
        card: Informations du carton
        admin_token: Token d'authentification admin
        
    Returns:
        Confirmation de l'ajout
        
    Example:
        POST /api/v1/live/match/match123/card?admin_token=admin123
        {"joueur": "Dupont", "equipe": "domicile", "temps": 45, "couleur": "jaune"}
    """
    if not FIREBASE_ENABLED:
        raise HTTPException(status_code=503, detail="Firebase non configuré")
    
    if not admin_token or not verify_admin_token(admin_token):
        raise HTTPException(status_code=401, detail="Token admin invalide")
    
    try:
        cards_ref = db.reference(f'matches/{match_id}/cards')
        current_cards = cards_ref.get() or []
        
        new_card = {
            "joueur": card.joueur,
            "equipe": card.equipe,
            "temps": card.temps,
            "couleur": card.couleur,
            "timestamp": int(time.time())
        }
        
        if isinstance(current_cards, list):
            current_cards.append(new_card)
        else:
            current_cards = [new_card]
        
        cards_ref.set(current_cards)
        
        return {
            "success": True,
            "message": f"Carton {card.couleur} donné à {card.joueur}",
            "match_id": match_id,
            "card": new_card
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Firebase: {str(e)}")


@app.put("/api/v1/live/match/{match_id}/status", tags=["Live Score"], summary="Mettre à jour le statut du match")
async def update_match_status(match_id: str, status: MatchStatusUpdate, admin_token: str = None):
    """
    Mettre à jour le statut d'un match (SCHEDULED, LIVE, FINISHED).
    
    Args:
        match_id: ID du match
        status: Nouveau statut
        admin_token: Token d'authentification admin
        
    Returns:
        Confirmation de la mise à jour
    """
    if not FIREBASE_ENABLED:
        raise HTTPException(status_code=503, detail="Firebase non configuré")
    
    if not admin_token or not verify_admin_token(admin_token):
        raise HTTPException(status_code=401, detail="Token admin invalide")
    
    try:
        match_ref = db.reference(f'matches/{match_id}')
        match_ref.update({
            'statut': status.statut,
            'last_updated': int(time.time())
        })
        
        return {
            "success": True,
            "message": f"Statut du match {match_id} changé à {status.statut}",
            "match_id": match_id,
            "statut": status.statut
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Firebase: {str(e)}")


@app.delete("/api/v1/live/match/{match_id}", tags=["Live Score"], summary="Supprimer un match live")
async def delete_match(match_id: str, admin_token: str = None):
    """
    Supprimer un match de Firebase.
    
    Args:
        match_id: ID du match à supprimer
        admin_token: Token d'authentification admin
        
    Returns:
        Confirmation de la suppression
    """
    if not FIREBASE_ENABLED:
        raise HTTPException(status_code=503, detail="Firebase non configuré")
    
    if not admin_token or not verify_admin_token(admin_token):
        raise HTTPException(status_code=401, detail="Token admin invalide")
    
    try:
        match_ref = db.reference(f'matches/{match_id}')
        match_ref.delete()
        
        return {
            "success": True,
            "message": f"Match {match_id} supprimé",
            "match_id": match_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Firebase: {str(e)}")


@app.post("/api/v1/live/import/championship/{championship}", tags=["Live Score"], summary="Importer matchs d'un championnat")
async def import_championship_matches(championship: str, admin_token: str = None):
    """
    ⚠️ NOTE: Cet endpoint utilise des données de démo pour éviter les timeouts.
    Pour les matchs réels, utilisez /api/v1/live/import-demo qui charge les données rapidement.
    
    Importe des matchs de démonstration dans Firebase pour un championnat spécifique.
    """
    if not admin_token or not verify_admin_token(admin_token):
        raise HTTPException(status_code=401, detail="Token admin invalide")
    
    try:
        # Données de démo pour chaque championnat
        demo_by_championship = {
            "elite-hommes": [
                {
                    "id": f"demo_elite_{i}",
                    "equipe_domicile": ["HC Grenoble", "Lambersart", "Nantes"][i % 3],
                    "equipe_exterieur": ["RCFH", "Montrouge", "Douai"][i % 3],
                    "score_domicile": 0,
                    "score_exterieur": 0,
                    "statut": "SCHEDULED"
                }
                for i in range(5)
            ],
            "elite-femmes": [
                {
                    "id": f"demo_femmes_{i}",
                    "equipe_domicile": ["Nantes", "Metz"][i % 2],
                    "equipe_exterieur": ["Villeurbanne", "Brest"][i % 2],
                    "score_domicile": 0,
                    "score_exterieur": 0,
                    "statut": "SCHEDULED"
                }
                for i in range(3)
            ],
            "u14-garcons": [
                {
                    "id": f"demo_u14g_{i}",
                    "equipe_domicile": f"Équipe Nord {i}",
                    "equipe_exterieur": f"Équipe Sud {i}",
                    "score_domicile": 0,
                    "score_exterieur": 0,
                    "statut": "SCHEDULED"
                }
                for i in range(4)
            ],
            "u14-filles": [
                {
                    "id": f"demo_u14f_{i}",
                    "equipe_domicile": f"Team A {i}",
                    "equipe_exterieur": f"Team B {i}",
                    "score_domicile": 0,
                    "score_exterieur": 0,
                    "statut": "SCHEDULED"
                }
                for i in range(3)
            ],
            "carquefou-1sh": [
                {
                    "id": "demo_carquefou_1sh",
                    "equipe_domicile": "Carquefou",
                    "equipe_exterieur": "Visiteur",
                    "score_domicile": 0,
                    "score_exterieur": 0,
                    "statut": "SCHEDULED"
                }
            ],
            "carquefou-2sh": [
                {
                    "id": "demo_carquefou_2sh",
                    "equipe_domicile": "Carquefou 2",
                    "equipe_exterieur": "Visiteur 2",
                    "score_domicile": 0,
                    "score_exterieur": 0,
                    "statut": "SCHEDULED"
                }
            ],
            "carquefou-sd": [
                {
                    "id": "demo_carquefou_sd",
                    "equipe_domicile": "Carquefou SD",
                    "equipe_exterieur": "Visiteur SD",
                    "score_domicile": 0,
                    "score_exterieur": 0,
                    "statut": "SCHEDULED"
                }
            ],
            "salle-elite-femmes": [
                {
                    "id": "demo_salle_1",
                    "equipe_domicile": "HC Grenoble",
                    "equipe_exterieur": "IH Lambersart",
                    "score_domicile": 0,
                    "score_exterieur": 0,
                    "statut": "SCHEDULED"
                }
            ]
        }
        
        if championship not in demo_by_championship:
            raise HTTPException(status_code=400, detail=f"Championnat {championship} non reconnu")
        
        matches_list = demo_by_championship[championship]
        championship_display = {
            "elite-hommes": "Elite Hommes",
            "elite-femmes": "Elite Femmes",
            "u14-garcons": "U14 Garçons",
            "u14-filles": "U14 Filles",
            "carquefou-1sh": "Carquefou 1SH",
            "carquefou-2sh": "Carquefou 2SH",
            "carquefou-sd": "Carquefou SD",
            "salle-elite-femmes": "Salle Elite Femmes"
        }
        display_name = championship_display.get(championship, championship)
        
        # Importer dans Firebase
        imported_count = 0
        created_matches = []
        
        if FIREBASE_ENABLED:
            matches_ref = db.reference('matches')
            
            # Parcourir les matchs
            for match in matches_list:
                try:
                    # Créer un ID unique
                    match_id = f"{championship}_{match.get('id', match.get('manifId', 'unknown'))}"
                    
                    # Créer la structure du match
                    match_data = {
                        'equipe_domicile': match.get('equipe_domicile', 'À définir'),
                        'equipe_exterieur': match.get('equipe_exterieur', 'À définir'),
                        'score_domicile': match.get('score_domicile', 0),
                        'score_exterieur': match.get('score_exterieur', 0),
                        'scorers': [],
                        'cards': [],
                        'statut': match.get('statut', 'SCHEDULED'),
                        'championship': championship,
                        'display_name': display_name,
                        'last_updated': int(time.time())
                    }
                    
                    # Écrire dans Firebase
                    matches_ref.child(match_id).set(match_data)
                    imported_count += 1
                    created_matches.append({
                        'match_id': match_id,
                        'home': match_data['equipe_domicile'],
                        'away': match_data['equipe_exterieur']
                    })
                    print(f"✅ {match_data['equipe_domicile']} vs {match_data['equipe_exterieur']}")
                    
                except Exception as import_error:
                    print(f"⚠️ Erreur import match: {str(import_error)}")
                    continue
        else:
            # Utiliser le cache local
            for match in matches_list:
                try:
                    match_id = f"{championship}_{match.get('id', match.get('manifId', 'unknown'))}"
                    match_data = {
                        'equipe_domicile': match.get('equipe_domicile', 'À définir'),
                        'equipe_exterieur': match.get('equipe_exterieur', 'À définir'),
                        'score_domicile': match.get('score_domicile', 0),
                        'score_exterieur': match.get('score_exterieur', 0),
                        'scorers': [],
                        'cards': [],
                        'statut': match.get('statut', 'SCHEDULED'),
                        'championship': championship,
                        'display_name': display_name,
                        'last_updated': int(time.time())
                    }
                    LIVE_MATCHES_CACHE[match_id] = match_data
                    imported_count += 1
                    created_matches.append({
                        'match_id': match_id,
                        'home': match_data['equipe_domicile'],
                        'away': match_data['equipe_exterieur']
                    })
                except Exception as cache_error:
                    print(f"⚠️ Erreur cache: {str(cache_error)}")
                    continue
        
        print(f"✅ {imported_count} matchs importés pour {display_name}")
        
        return {
            "success": True,
            "message": f"{imported_count} matchs importés pour {display_name}",
            "championship": championship,
            "imported_count": imported_count,
            "matches": created_matches[:5]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur import: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur import: {str(e)}")





@app.post("/api/v1/live/import-demo", tags=["Live Score"], summary="Importer matchs de démo")
async def import_demo_matches(admin_token: str = None):
    """
    Importer des matchs de démonstration dans Firebase.
    Utile pour tester le Dashboard sans scraper l'API FFH.
    
    Args:
        admin_token: Token d'authentification admin
        
    Returns:
        Nombre de matchs importés
    """
    if not admin_token or not verify_admin_token(admin_token):
        raise HTTPException(status_code=401, detail="Token admin invalide")
    
    try:
        # Créer des matchs de démo
        demo_matches = [
            {
                'id': 'demo_elite_1',
                'championship': 'elite-hommes',
                'display_name': 'Elite Hommes',
                'equipe_domicile': 'HC Grenoble',
                'equipe_exterieur': 'Lambersart',
                'score_domicile': 0,
                'score_exterieur': 0,
                'scorers': [],
                'cards': [],
                'statut': 'SCHEDULED',
                'last_updated': int(time.time())
            },
            {
                'id': 'demo_elite_femmes_1',
                'championship': 'elite-femmes',
                'display_name': 'Elite Femmes',
                'equipe_domicile': 'Nantes',
                'equipe_exterieur': 'Villeneuve d\'Ascq',
                'score_domicile': 0,
                'score_exterieur': 0,
                'scorers': [],
                'cards': [],
                'statut': 'SCHEDULED',
                'last_updated': int(time.time())
            },
            {
                'id': 'demo_u14_1',
                'championship': 'u14-garcons',
                'display_name': 'U14 Garçons',
                'equipe_domicile': 'Équipe Nord',
                'equipe_exterieur': 'Équipe Sud',
                'score_domicile': 0,
                'score_exterieur': 0,
                'scorers': [],
                'cards': [],
                'statut': 'SCHEDULED',
                'last_updated': int(time.time())
            },
            {
                'id': 'demo_carquefou_1',
                'championship': 'carquefou-1sh',
                'display_name': 'Carquefou 1SH',
                'equipe_domicile': 'Carquefou',
                'equipe_exterieur': 'Visiteur',
                'score_domicile': 0,
                'score_exterieur': 0,
                'scorers': [],
                'cards': [],
                'statut': 'SCHEDULED',
                'last_updated': int(time.time())
            }
        ]
        
        # Importer dans Firebase
        if FIREBASE_ENABLED:
            matches_ref = db.reference('matches')
            for match in demo_matches:
                try:
                    matches_ref.child(match['id']).set(match)
                    print(f"✅ Match démo {match['id']} créé")
                except Exception as e:
                    print(f"⚠️ Erreur import {match['id']}: {str(e)}")
        else:
            # Utiliser le cache local
            for match in demo_matches:
                LIVE_MATCHES_CACHE[match['id']] = match
        
        return {
            "success": True,
            "message": f"{len(demo_matches)} matchs de démo importés",
            "count": len(demo_matches),
            "matches": [m['id'] for m in demo_matches]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.post("/api/v1/live/import-real/{championship}", tags=["Live Score"], summary="Importer vrais matchs d'un championnat")
async def import_real_championship(championship: str, admin_token: str = None):
    """
    Alias pour /api/v1/live/import/championship/{championship}
    Importe les vrais matchs d'un championnat dans Firebase.
    Les données proviennent du cache FFHockey API.
    """
    if not admin_token or not verify_admin_token(admin_token):
        raise HTTPException(status_code=401, detail="Token admin invalide")
    
    # Rediriger vers l'endpoint existant qui charge les vrais données
    return await import_championship_matches(championship, admin_token)


@app.post("/api/v1/live/import-real-data/{championship}", tags=["Live Score"], summary="Importer VRAIS matchs depuis FFH API")
async def import_real_data(championship: str, admin_token: str = None):
    """
    Importe les VRAIS matchs depuis l'API FFHockey (pas de démo).
    ✨ AMÉLIORATIONS:
    - Élimine les doublons (vérifie les matchs existants dans Firebase)
    - Filtre les matchs de test/démo
    - Trie par dates proches et prochaines
    - Ignore les équipes invalides (test, simulation, etc.)
    
    Championnats supportés:
    - elite-hommes
    - elite-femmes
    - u14-garcons
    - u14-filles
    - carquefou-1sh, carquefou-2sh, carquefou-sd
    - salle-elite-femmes
    """
    if not admin_token or not verify_admin_token(admin_token):
        raise HTTPException(status_code=401, detail="Token admin invalide")
    
    try:
        print(f"📥 Chargement des VRAIS matchs pour {championship}")
        
        # Récupérer les vrais matchs depuis le cache FFH
        matches_list = []
        
        if championship == "elite-hommes":
            matches_list = get_matches_cached() or []
        elif championship == "elite-femmes":
            matches_list = get_matches_femmes_cached() or []
        elif championship == "u14-garcons":
            matches_list = get_matchs_interligues_u14_garcons() or []
        elif championship == "u14-filles":
            matches_list = get_matchs_interligues_u14_filles() or []
        elif championship == "carquefou-1sh":
            matches_list = get_matchs_carquefou_1sh_cached() or []
        elif championship == "carquefou-2sh":
            matches_list = get_matchs_carquefou_2sh_cached() or []
        elif championship == "carquefou-sd":
            matches_list = get_matchs_carquefou_sd_cached() or []
        elif championship == "salle-elite-femmes":
            # Salle Elite Femmes: pas de données disponibles dans l'API FFH
            # L'utilisateur doit créer les matchs manuellement via le Dashboard
            matches_list = []
        else:
            raise HTTPException(status_code=400, detail=f"Championnat {championship} non reconnu")
        
        championship_display = {
            "elite-hommes": "Elite Hommes",
            "elite-femmes": "Elite Femmes", 
            "u14-garcons": "U14 Garçons",
            "u14-filles": "U14 Filles",
            "carquefou-1sh": "Carquefou 1SH",
            "carquefou-2sh": "Carquefou 2SH",
            "carquefou-sd": "Carquefou SD",
            "salle-elite-femmes": "Salle Elite Femmes"
        }
        display_name = championship_display.get(championship, championship)
        
        # 🔍 FILTRER LES MATCHS DE TEST ET INVALIDES
        filtered_matches = []
        test_keywords = ['test', 'demo', 'simulation', 'simulation-', 'test-', 'exempt', '?', 'à définir']
        
        for match in matches_list:
            home = str(match.get('equipe_domicile', '')).lower().strip()
            away = str(match.get('equipe_exterieur', '')).lower().strip()
            
            # Vérifier si c'est un match de test
            is_test = any(keyword in home or keyword in away for keyword in test_keywords)
            
            if not is_test and home and away and home != away:
                filtered_matches.append(match)
        
        # 📅 TRIER PAR DATES PROCHES (matchs futurs d'abord, puis récents)
        from datetime import datetime
        now = datetime.now()
        
        def get_sort_key(match):
            date_str = match.get('date', '')
            try:
                match_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                if match_date < now:
                    return (1, abs((now - match_date).total_seconds()))  # Matchs passés: après
                else:
                    return (0, (match_date - now).total_seconds())  # Matchs futurs: avant
            except:
                return (2, 0)  # Pas de date: à la fin
        
        filtered_matches.sort(key=get_sort_key)
        
        # 📱 Récupérer les matchs EXISTANTS dans Firebase
        existing_match_keys = set()
        if FIREBASE_ENABLED:
            try:
                matches_ref = db.reference('matches')
                existing_data = matches_ref.get()
                if existing_data:
                    for match_id in existing_data.keys():
                        # Extraire la clé (rrncId, id ou manifId) de l'ID Firebase
                        if '_' in match_id:
                            key_part = match_id.split('_', 1)[1]
                            existing_match_keys.add(key_part)
            except Exception as e:
                print(f"⚠️ Erreur lecture matchs existants: {str(e)}")
        
        # ✅ IMPORTER DANS FIREBASE (SANS DOUBLONS)
        imported_count = 0
        created_matches = []
        skipped_duplicates = 0
        
        if FIREBASE_ENABLED and filtered_matches:
            matches_ref = db.reference('matches')
            
            for match in filtered_matches[:100]:  # Augmenter à 100 pour avoir plus de choix
                try:
                    # Créer l'identifiant unique
                    unique_id = match.get('rencId', match.get('id', match.get('manifId', None)))
                    
                    if not unique_id:
                        continue
                    
                    # ❌ VÉRIFIER LES DOUBLONS
                    if str(unique_id) in existing_match_keys:
                        skipped_duplicates += 1
                        print(f"⏭️ Doublon ignoré: {match.get('equipe_domicile')} vs {match.get('equipe_exterieur')}")
                        continue
                    
                    match_id = f"{championship}_{unique_id}"
                    
                    # Structurer les données
                    match_data = {
                        'equipe_domicile': match.get('equipe_domicile', 'À définir'),
                        'equipe_exterieur': match.get('equipe_exterieur', 'À définir'),
                        'score_domicile': match.get('score_domicile') or 0,
                        'score_exterieur': match.get('score_exterieur') or 0,
                        'scorers': [],
                        'cards': [],
                        'statut': match.get('statut', 'SCHEDULED'),
                        'championship': championship,
                        'display_name': display_name,
                        'date': match.get('date', ''),
                        'last_updated': int(time.time()),
                        'rencId': str(unique_id)  # Stocker l'ID pour éviter les doublons
                    }
                    
                    # Écrire dans Firebase
                    matches_ref.child(match_id).set(match_data)
                    imported_count += 1
                    created_matches.append({
                        'match_id': match_id,
                        'home': match_data['equipe_domicile'],
                        'away': match_data['equipe_exterieur'],
                        'date': match.get('date', '')
                    })
                    print(f"✅ {match_data['equipe_domicile']} vs {match_data['equipe_exterieur']} ({match.get('date', 'S/O')})")
                except Exception as e:
                    print(f"⚠️ Erreur import: {str(e)}")
                    continue
        else:
            if not filtered_matches:
                print(f"⚠️ Pas de matchs trouvés pour {championship} après filtrage")
        
        # Message personnalisé selon le championnat
        if championship == "salle-elite-femmes" and imported_count == 0:
            message = f"ℹ️ {display_name}: Pas de données disponibles dans l'API FFH. Créez les matchs manuellement via '➕ Créer un match personnalisé'"
        else:
            message = f"✅ {imported_count} VRAIS matchs importés pour {display_name}"
        
        return {
            "success": True,
            "message": message,
            "championship": championship,
            "imported_count": imported_count,
            "skipped_duplicates": skipped_duplicates,
            "matches": created_matches[:5],
            "note": f"Total de {len(filtered_matches)} matchs filtrés (sur {len(matches_list)} disponibles)",
            "details": f"{skipped_duplicates} doublons ignorés"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    # Lancer le serveur sur http://127.0.0.1:8000
    # Accédez à http://127.0.0.1:8000/docs pour la documentation interactive
    uvicorn.run(app, host="127.0.0.1", port=8000)