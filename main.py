"""
API FastAPI pour le Hockey sur Gazon Français
Endpoints pour accéder aux données de la FFH
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from scraper import (
    get_ranking, get_matches, 
    get_ranking_femmes, get_matches_femmes,
    get_classement_carquefou_1sh, get_matchs_carquefou_1sh,
    get_classement_carquefou_2sh, get_matchs_carquefou_2sh,
    get_matchs_carquefou_sd
)


# Création de l'instance FastAPI
app = FastAPI(
    title="Hockey sur Gazon France API",
    description="API pour accéder aux données du hockey sur gazon français (championnats de la FFH)",
    version="1.0.0"
)


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
    
    Returns:
        Liste des matchs avec leurs résultats et statuts.
    
    Raises:
        HTTPException: Si la source de données est indisponible (code 503).
    """
    matches_data = get_matches()
    
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


if __name__ == "__main__":
    import uvicorn
    # Lancer le serveur sur http://127.0.0.1:8000
    # Accédez à http://127.0.0.1:8000/docs pour la documentation interactive
    uvicorn.run(app, host="127.0.0.1", port=8000)
