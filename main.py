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
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
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
        sender_email = "notification@hockeyffh.fr"  # Doit être un email vérifié dans SendGrid
        
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
            # Transformer les données au format attendu par le Dashboard
            matches_formatted = []
            for match in matches_raw.values():
                formatted_match = {
                    "equipe_domicile": match.get("Equipe1", {}).get("EquipeNom", "TBD"),
                    "equipe_exterieur": match.get("Equipe2", {}).get("EquipeNom", "TBD"),
                    "score_domicile": match.get("Scores", {}).get("RencButsEqp1") or "",
                    "score_exterieur": match.get("Scores", {}).get("RencButsEqp2") or "",
                    "date": match.get("RencDateDerog", ""),
                    "statut": "FINISHED" if (match.get("Scores", {}).get("RencButsEqp1") and match.get("Scores", {}).get("RencButsEqp2")) else "SCHEDULED"
                }
                matches_formatted.append(formatted_match)
            return {"success": True, "data": matches_formatted, "count": len(matches_formatted)}
        else:
            return {"success": False, "data": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des matchs U14 Filles: {str(e)}")


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
            # Transformer les données au format attendu par le Dashboard
            matches_formatted = []
            for match in matches_raw.values():
                formatted_match = {
                    "equipe_domicile": match.get("Equipe1", {}).get("EquipeNom", "TBD"),
                    "equipe_exterieur": match.get("Equipe2", {}).get("EquipeNom", "TBD"),
                    "score_domicile": match.get("Scores", {}).get("RencButsEqp1") or "",
                    "score_exterieur": match.get("Scores", {}).get("RencButsEqp2") or "",
                    "date": match.get("RencDateDerog", ""),
                    "statut": "FINISHED" if (match.get("Scores", {}).get("RencButsEqp1") and match.get("Scores", {}).get("RencButsEqp2")) else "SCHEDULED"
                }
                matches_formatted.append(formatted_match)
            return {"success": True, "data": matches_formatted, "count": len(matches_formatted)}
        else:
            return {"success": False, "data": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des matchs U14 Garçons: {str(e)}")


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
        sender_email = "notification@hockeyffh.fr"
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


if __name__ == "__main__":
    import uvicorn
    # Lancer le serveur sur http://127.0.0.1:8000
    # Accédez à http://127.0.0.1:8000/docs pour la documentation interactive
    uvicorn.run(app, host="127.0.0.1", port=8000)
