"""
API FastAPI pour le Hockey sur Gazon Français
Endpoints pour accéder aux données de la FFH
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import re
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from bs4 import BeautifulSoup
from scraper import (
    get_ranking, get_matches, 
    get_ranking_femmes, get_matches_femmes,
    get_classement_carquefou_1sh, get_matchs_carquefou_1sh,
    get_classement_carquefou_2sh, get_matchs_carquefou_2sh,
    get_matchs_carquefou_sd
)

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()


# Création de l'instance FastAPI
app = FastAPI(
    title="Hockey sur Gazon France API",
    description="API pour accéder aux données du hockey sur gazon français (championnats de la FFH)",
    version="1.0.0"
)

# Configuration CORS pour accepter les requêtes depuis n'importe quelle origine
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Accepte toutes les origines
    allow_credentials=True,
    allow_methods=["*"],  # Accepte tous les méthodes HTTP
    allow_headers=["*"],  # Accepte tous les headers
)

# ============================================
# SCHEDULER - NOTIFICATIONS AUTOMATIQUES
# ============================================

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
    
    Args:
        matches_data: Liste des matchs
        competition_prefix: Préfixe pour l'ID unique (ex: "elite-hommes")
        competition_name: Nom de la compétition pour l'email
    """
    global notified_matches
    
    for match in matches_data:
        if match.get("statut") == "FINISHED":
            # Créer un identifiant unique pour le match
            match_id = f"{competition_prefix}-{match.get('equipe_domicile')}-{match.get('equipe_exterieur')}-{match.get('date')}"
            
            # Si le match n'a pas encore été notifié
            if match_id not in notified_matches:
                # Envoyer les emails
                send_match_finished_email(email_subscribers, match, competition_name)
                
                # Marquer comme notifié
                notified_matches.add(match_id)
                save_notified_matches(notified_matches)


@app.get("/api/v1/elite-hommes/classement", tags=["Classement"])
async def endpoint_classement():
    """
    Récupère le classement actuel de l'élite hommes.
    
    Returns:
        Liste des équipes avec leurs statistiques de classement.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    ranking_data = get_ranking()
    
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


@app.get("/api/v1/elite-hommes/matchs", tags=["Matchs"])
async def endpoint_matchs():
    """
    Récupère la liste des matchs de l'élite hommes.
    Détecte aussi les matchs nouvellement terminés et envoie des emails si nécessaire.
    
    Returns:
        Liste des matchs avec leurs résultats et statuts.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    global notified_matches
    
    matches_data = get_matches()
    
    if not matches_data:
        raise HTTPException(
            status_code=503,
            detail="La source de données de la FFH est actuellement indisponible."
        )
    
    # Vérifier les matchs nouvellement terminés
    for match in matches_data:
        if match.get("statut") == "FINISHED":
            # Créer un identifiant unique pour le match
            match_id = f"elite-hommes-{match.get('equipe_domicile')}-{match.get('equipe_exterieur')}-{match.get('date')}"
            
            # Si le match n'a pas encore été notifié
            if match_id not in notified_matches:
                # Envoyer les emails
                send_match_finished_email(email_subscribers, match, "Elite Hommes")
                
                # Marquer comme notifié
                notified_matches.add(match_id)
                save_notified_matches(notified_matches)
    
    return {
        "success": True,
        "data": matches_data,
        "count": len(matches_data)
    }


@app.get("/api/v1/elite-femmes/classement", tags=["Classement"])
async def endpoint_classement_femmes():
    """
    Récupère le classement actuel de l'élite femmes.
    
    Returns:
        Liste des équipes avec leurs statistiques de classement.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    ranking_data = get_ranking_femmes()
    
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


@app.get("/api/v1/elite-femmes/matchs", tags=["Matchs"])
async def endpoint_matchs_femmes():
    """
    Récupère la liste des matchs de l'élite femmes.
    
    Returns:
        Liste des matchs avec leurs résultats et statuts.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    matches_data = get_matches_femmes()
    
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
    matches_data = get_matchs_carquefou_sd()
    
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
    ranking_data = get_classement_carquefou_1sh()
    
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
    matches_data = get_matchs_carquefou_1sh()
    
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
    ranking_data = get_classement_carquefou_2sh()
    
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
    matches_data = get_matchs_carquefou_2sh()
    
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
        
        # Chercher les sections "Buteurs :"
        buteurs_pattern = r'<strong>Buteurs : <\/strong>([^<]*)'
        buteurs_matches = re.findall(buteurs_pattern, html_content)
        
        # Filtrer les résultats vides
        buteurs_valides = [b.strip() for b in buteurs_matches if b.strip() and '&nbsp;' not in b and b.strip() != '']
        
        if len(buteurs_valides) >= 2:
            # Première équipe
            buteurs_team1 = buteurs_valides[0].strip()
            if buteurs_team1:
                numbers = re.findall(r'N°(\d+)\s*\(x(\d+)\)', buteurs_team1)
                for num, count in numbers:
                    num = int(num)
                    nom_joueur = players_data["team1"]["joueurs"].get(num, f"Joueur N°{num}")
                    scorers["team1"]["buteurs"].append({
                        "numero_maillot": num,
                        "nom": nom_joueur,
                        "buts": int(count)
                    })
            
            # Deuxième équipe
            buteurs_team2 = buteurs_valides[1].strip()
            if buteurs_team2:
                numbers = re.findall(r'N°(\d+)\s*\(x(\d+)\)', buteurs_team2)
                for num, count in numbers:
                    num = int(num)
                    nom_joueur = players_data["team2"]["joueurs"].get(num, f"Joueur N°{num}")
                    scorers["team2"]["buteurs"].append({
                        "numero_maillot": num,
                        "nom": nom_joueur,
                        "buts": int(count)
                    })
        elif len(buteurs_valides) == 1:
            buteurs_team1 = buteurs_valides[0].strip()
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


async def get_match_officials(renc_id: str, manif_id: str = ""):
    """
    Récupère les officiels (arbitres, délégués, etc.) pour un match spécifique.
    
    Args:
        renc_id: L'identifiant de la rencontre (RencId)
        manif_id: L'identifiant optionnel de la manifestation
        
    Returns:
        Liste des officiels avec leurs fonctions et informations personnelles
        
    Example:
        /api/v1/match/196053/officiels
    """
    try:
        import requests
        
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
            "nb_officials": officials_data.get("NbOfficiels", 0),
            "data": officials_list
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


if __name__ == "__main__":
    import uvicorn
    # Lancer le serveur sur http://127.0.0.1:8000
    # Accédez à http://127.0.0.1:8000/docs pour la documentation interactive
    uvicorn.run(app, host="127.0.0.1", port=8000)
