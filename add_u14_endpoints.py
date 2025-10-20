#!/usr/bin/env python3
"""
Script pour ajouter les endpoints U14 Filles et U14 Garçons à main.py
"""

import re

# Code à injecter
NEW_ENDPOINTS = '''
# ============================================
# INTERLIGUES U14 (NOUVELLES COMPÉTITIONS)
# ============================================

import requests

@app.get("/api/v1/interligues-u14-filles/matchs", tags=["Interligues U14"], summary="Matchs U14 Filles")
def get_matchs_interligues_u14_filles():
    """
    Récupère les matchs des Interligues U14 Filles (Championnat de France des Régions).
    
    Returns:
        Liste des matchs U14 Filles
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
            matches = data["Response"].get("RencontresArray", {})
            return {"status": "success", "data": list(matches.values())}
        else:
            return {"status": "error", "message": "Aucun match trouvé"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des matchs U14 Filles: {str(e)}")

@app.get("/api/v1/interligues-u14-garcons/matchs", tags=["Interligues U14"], summary="Matchs U14 Garçons")
def get_matchs_interligues_u14_garcons():
    """
    Récupère les matchs des Interligues U14 Garçons (Championnat de France des Régions).
    
    Returns:
        Liste des matchs U14 Garçons
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
            matches = data["Response"].get("RencontresArray", {})
            return {"status": "success", "data": list(matches.values())}
        else:
            return {"status": "error", "message": "Aucun match trouvé"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des matchs U14 Garçons: {str(e)}")

'''

# Lire le fichier main.py
with open('main.py', 'r') as f:
    content = f.read()

# Injecter le code AVANT @app.post("/api/v1/subscribe"
content = content.replace(
    '@app.post("/api/v1/subscribe"',
    NEW_ENDPOINTS + '\n# ============================================\n# NOTIFICATIONS EMAIL\n# ============================================\n\n@app.post("/api/v1/subscribe"'
)

# Écrire le fichier modifié
with open('main.py', 'w') as f:
    f.write(content)

print("✅ Endpoints U14 ajoutés avec succès à main.py!")
print(f"📊 Nouveau nombre de lignes: {len(content.split(chr(10)))}")
