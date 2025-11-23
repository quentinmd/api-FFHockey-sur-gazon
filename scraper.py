"""
Scraper pour l'API de Hockey sur Gazon Français
Récupère les données depuis l'API interne de la FFH
"""

import requests
import re
from typing import List, Dict


def _normalize_team_name(team_name: str) -> str:
    """
    Normalise le nom d'une équipe en supprimant les numéros de poule.
    Ex: "CARQUEFOU HC 3" -> "CARQUEFOU HC"
    Mais garde les numéros qui font partie du nom: "CA MONTROUGE 92" -> "CA MONTROUGE 92"
    
    Args:
        team_name: Le nom de l'équipe à normaliser
    
    Returns:
        str: Le nom normalisé
    """
    if not team_name:
        return team_name
    
    # Pattern: " X" où X est un nombre SEUL (1-9) à la fin
    # Ceci ciblera les numéros de poule (1-9) mais pas des codes comme "92"
    normalized = re.sub(r'\s+[1-9]\s*$', '', team_name.strip())
    return normalized


def _calculate_ranking(manif_id: str) -> List[Dict]:
    """
    Fonction interne pour calculer le classement à partir d'un ManifId.
    
    Args:
        manif_id: L'identifiant de la manifestation (championnats)
    
    Returns:
        List[Dict]: Liste des équipes avec leurs informations de classement.
    """
    try:
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
        params = {
            "SaisonAnnee": "2026",
            "ManifId": manif_id
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Vérifier la structure de la réponse
        if data.get("ResponseCode") != "200":
            print(f"Erreur API: {data.get('ResponseMessage')}")
            return []
        
        rencontres_data = data.get("Response", {})
        rencontres_array = rencontres_data.get("RencontresArray", {})
        
        # Dictionnaire pour cumuler les statistiques par équipe
        teams_stats = {}
        
        # Parcourir toutes les rencontres
        for match_id, match_data in rencontres_array.items():
            scores = match_data.get("Scores", {})
            
            # Vérifier si le match a un résultat saisi
            if not scores.get("RencScoresSaisieDate"):
                continue
            
            equipe1_data = match_data.get("Equipe1", {})
            equipe2_data = match_data.get("Equipe2", {})
            
            equipe1_name = equipe1_data.get("EquipeNom", "")
            equipe2_name = equipe2_data.get("EquipeNom", "")
            
            but1 = int(scores.get("RencButsEqp1") or 0)
            but2 = int(scores.get("RencButsEqp2") or 0)
            
            # Initialiser les équipes si nécessaire
            if equipe1_name not in teams_stats:
                teams_stats[equipe1_name] = {
                    "joues": 0, "gagnes": 0, "nuls": 0, "perdus": 0,
                    "buts_pour": 0, "buts_contre": 0, "points": 0
                }
            if equipe2_name not in teams_stats:
                teams_stats[equipe2_name] = {
                    "joues": 0, "gagnes": 0, "nuls": 0, "perdus": 0,
                    "buts_pour": 0, "buts_contre": 0, "points": 0
                }
            
            # Mise à jour des statistiques
            teams_stats[equipe1_name]["joues"] += 1
            teams_stats[equipe2_name]["joues"] += 1
            
            teams_stats[equipe1_name]["buts_pour"] += but1
            teams_stats[equipe1_name]["buts_contre"] += but2
            
            teams_stats[equipe2_name]["buts_pour"] += but2
            teams_stats[equipe2_name]["buts_contre"] += but1
            
            if but1 > but2:
                teams_stats[equipe1_name]["gagnes"] += 1
                teams_stats[equipe1_name]["points"] += 3
                teams_stats[equipe2_name]["perdus"] += 1
            elif but2 > but1:
                teams_stats[equipe2_name]["gagnes"] += 1
                teams_stats[equipe2_name]["points"] += 3
                teams_stats[equipe1_name]["perdus"] += 1
            else:
                teams_stats[equipe1_name]["nuls"] += 1
                teams_stats[equipe1_name]["points"] += 1
                teams_stats[equipe2_name]["nuls"] += 1
                teams_stats[equipe2_name]["points"] += 1
        
        # Créer la liste de classement triée
        ranking_list = []
        for position, (team_name, stats) in enumerate(
            sorted(teams_stats.items(), key=lambda x: (-x[1]["points"], -(x[1]["buts_pour"] - x[1]["buts_contre"]))),
            1
        ):
            ranking_dict = {
                "position": position,
                "equipe": team_name,
                "points": stats["points"],
                "joues": stats["joues"],
                "gagnes": stats["gagnes"],
                "nuls": stats["nuls"],
                "perdus": stats["perdus"],
                "buts_pour": stats["buts_pour"],
                "buts_contre": stats["buts_contre"],
                "difference": stats["buts_pour"] - stats["buts_contre"]
            }
            ranking_list.append(ranking_dict)
        
        return ranking_list
        
    except requests.exceptions.Timeout:
        print(f"Erreur: Timeout lors de la récupération du classement (ManifId: {manif_id})")
        return []
    except requests.exceptions.ConnectionError:
        print("Erreur: Impossible de se connecter à l'API de la FFH")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"Erreur HTTP: {e.response.status_code}")
        return []
    except (ValueError, KeyError) as e:
        print(f"Erreur lors du parsing JSON: {e}")
        return []
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return []


def get_classement_poule(poule_id: str) -> List[Dict]:
    """
    Récupère le classement d'une poule spécifique.
    
    Args:
        poule_id: L'identifiant de la poule (ex: "11510" pour Carquefou HC poule A)
    
    Returns:
        List[Dict]: Liste des équipes avec leurs statistiques de classement dans la poule.
    """
    try:
        url = "https://championnats.ffhockey.org/rest2/Championnats/ClassementEquipes"
        params = {
            "SaisonAnnee": "2026",
            "PouleId": poule_id
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("ResponseCode") != "200":
            print(f"Erreur API: {data.get('ResponseMessage')}")
            return []
        
        classement_data = data.get("Response", {}).get("Classement", {})
        classement_lignes = classement_data.get("ClassmentLignes", [])
        
        ranking_list = []
        for ligne in classement_lignes:
            equipe = ligne.get("Equipe", {})
            ranking_dict = {
                "position": int(ligne.get("ClassmPos", 0)),
                "equipe": equipe.get("EquipeNom", ""),
                "points": int(ligne.get("ClassmPts", 0)),
                "joues": int(ligne.get("ClassmMatchJ", 0)),
                "gagnes": int(ligne.get("ClassmMatchG", 0)),
                "nuls": int(ligne.get("ClassmMatchN", 0)),
                "perdus": int(ligne.get("ClassmMatchP", 0)),
                "buts_pour": int(ligne.get("ClassmButP", 0)),
                "buts_contre": int(ligne.get("ClassmButC", 0)),
                "difference": int(ligne.get("ClassmDiff", 0))
            }
            ranking_list.append(ranking_dict)
        
        return ranking_list
        
    except requests.exceptions.Timeout:
        print(f"Erreur: Timeout lors de la récupération du classement de la poule {poule_id}")
        return []
    except requests.exceptions.ConnectionError:
        print("Erreur: Impossible de se connecter à l'API de la FFH")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"Erreur HTTP: {e.response.status_code}")
        return []
    except (ValueError, KeyError) as e:
        print(f"Erreur lors du parsing JSON: {e}")
        return []
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return []


def get_matchs_poule(poule_id: str) -> List[Dict]:
    """
    Récupère les matchs d'une poule spécifique.
    
    Args:
        poule_id: L'identifiant de la poule (ex: "11510" pour Carquefou HC poule A)
    
    Returns:
        List[Dict]: Liste des matchs avec leurs informations.
    """
    try:
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
        params = {
            "SaisonAnnee": "2026",
            "PouleId": poule_id
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("ResponseCode") != "200":
            print(f"Erreur API: {data.get('ResponseMessage')}")
            return []
        
        rencontres_data = data.get("Response", {})
        rencontres_array = rencontres_data.get("RencontresArray", {})
        
        matches_list = []
        
        for match_id, match_data in rencontres_array.items():
            renc_id = match_data.get("RencId", "")
            renc_date = match_data.get("RencDateDerog", "")
            
            equipe1_data = match_data.get("Equipe1", {})
            equipe2_data = match_data.get("Equipe2", {})
            
            equipe1_name = equipe1_data.get("EquipeNom", "")
            equipe2_name = equipe2_data.get("EquipeNom", "")
            
            scores = match_data.get("Scores", {})
            but1 = int(scores.get("RencButsEqp1") or 0) if scores.get("RencButsEqp1") else None
            but2 = int(scores.get("RencButsEqp2") or 0) if scores.get("RencButsEqp2") else None
            
            # Déterminer le statut du match
            if scores.get("RencScoresSaisieDate"):
                statut = "FINISHED"
            elif match_data.get("RencNonJoue") == "O":
                statut = "NOT_PLAYED"
            else:
                statut = "SCHEDULED"
            
            match_dict = {
                "rencId": str(renc_id),
                "date": str(renc_date),
                "equipe_domicile": str(equipe1_name),
                "equipe_exterieur": str(equipe2_name),
                "score_domicile": but1 if but1 is not None else None,
                "score_exterieur": but2 if but2 is not None else None,
                "statut": statut
            }
            matches_list.append(match_dict)
        
        return matches_list
        
    except requests.exceptions.Timeout:
        print(f"Erreur: Timeout lors de la récupération des matchs de la poule {poule_id}")
        return []
    except requests.exceptions.ConnectionError:
        print("Erreur: Impossible de se connecter à l'API de la FFH")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"Erreur HTTP: {e.response.status_code}")
        return []
    except (ValueError, KeyError) as e:
        print(f"Erreur lors du parsing JSON: {e}")
        return []
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return []


# Raccourcis pour Carquefou HC 1 Seniors Hommes (PouleId: 11510)
def get_classement_carquefou_1sh() -> List[Dict]:
    """Récupère le classement de Carquefou HC 1 Seniors Hommes."""
    return get_classement_poule("11510")


def get_matchs_carquefou_1sh() -> List[Dict]:
    """Récupère les matchs de Carquefou HC 1 Seniors Hommes."""
    matches = get_matchs_poule("11510")
    # Filtrer pour ne conserver que les matchs impliquant Carquefou HC 1
    filtered_matches = []
    for match in matches:
        domicile = match.get("equipe_domicile", "").upper()
        exterieur = match.get("equipe_exterieur", "").upper()
        # Chercher "CARQUEFOU HC 1" dans le nom de l'équipe (avec ou sans suffixe)
        if "CARQUEFOU HC 1" in domicile or "CARQUEFOU HC 1" in exterieur:
            # Normaliser les noms d'équipes Carquefou seulement (supprimer U17, etc.)
            if "CARQUEFOU" in domicile:
                match["equipe_domicile"] = re.sub(r'\s+U\d+\s*$', '', match["equipe_domicile"].strip())
                match["equipe_domicile"] = _normalize_team_name(match["equipe_domicile"])
            if "CARQUEFOU" in exterieur:
                match["equipe_exterieur"] = re.sub(r'\s+U\d+\s*$', '', match["equipe_exterieur"].strip())
                match["equipe_exterieur"] = _normalize_team_name(match["equipe_exterieur"])
            filtered_matches.append(match)
    return filtered_matches


# Raccourcis pour Carquefou HC 2 Seniors Hommes (PouleId: 11511)
def get_classement_carquefou_2sh() -> List[Dict]:
    """Récupère le classement de Carquefou HC 2 Seniors Hommes."""
    return get_classement_poule("11511")


def get_matchs_carquefou_2sh() -> List[Dict]:
    """Récupère les matchs de Carquefou HC 2 Seniors Hommes."""
    matches = get_matchs_poule("11511")
    # Filtrer pour ne conserver que les matchs impliquant Carquefou HC 2
    filtered_matches = []
    for match in matches:
        domicile = match.get("equipe_domicile", "").upper()
        exterieur = match.get("equipe_exterieur", "").upper()
        # Chercher "CARQUEFOU HC 2" dans le nom de l'équipe (avec ou sans suffixe)
        if "CARQUEFOU HC 2" in domicile or "CARQUEFOU HC 2" in exterieur:
            # Normaliser les noms d'équipes Carquefou seulement (supprimer U17, etc.)
            if "CARQUEFOU" in domicile:
                match["equipe_domicile"] = re.sub(r'\s+U\d+\s*$', '', match["equipe_domicile"].strip())
                match["equipe_domicile"] = _normalize_team_name(match["equipe_domicile"])
            if "CARQUEFOU" in exterieur:
                match["equipe_exterieur"] = re.sub(r'\s+U\d+\s*$', '', match["equipe_exterieur"].strip())
                match["equipe_exterieur"] = _normalize_team_name(match["equipe_exterieur"])
            filtered_matches.append(match)
    return filtered_matches


def _get_matchs_by_team_name(manif_id: str, team_name_filter: str) -> List[Dict]:
    """
    Fonction interne pour récupérer les matchs d'une équipe spécifique au sein d'une manifestation.
    
    Args:
        manif_id: L'identifiant de la manifestation
        team_name_filter: Le nom ou partie du nom de l'équipe à filtrer
    
    Returns:
        List[Dict]: Liste des matchs de l'équipe avec leurs informations.
    """
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
            print(f"Erreur API: {data.get('ResponseMessage')}")
            return []
        
        rencontres_data = data.get("Response", {})
        rencontres_array = rencontres_data.get("RencontresArray", {})
        
        matches_list = []
        
        # Parcourir toutes les rencontres et filtrer par nom d'équipe
        for match_id, match_data in rencontres_array.items():
            equipe1_name = match_data.get("Equipe1", {}).get("EquipeNom", "")
            equipe2_name = match_data.get("Equipe2", {}).get("EquipeNom", "")
            
            # Filtrer si l'équipe recherchée joue
            if team_name_filter.upper() not in equipe1_name.upper() and team_name_filter.upper() not in equipe2_name.upper():
                continue
            
            renc_id = match_data.get("RencId", "")
            renc_date = match_data.get("RencDateDerog", "")
            
            scores = match_data.get("Scores", {})
            but1 = int(scores.get("RencButsEqp1") or 0) if scores.get("RencButsEqp1") else None
            but2 = int(scores.get("RencButsEqp2") or 0) if scores.get("RencButsEqp2") else None
            
            # Déterminer le statut du match
            if scores.get("RencScoresSaisieDate"):
                statut = "FINISHED"
            elif match_data.get("RencNonJoue") == "O":
                statut = "NOT_PLAYED"
            else:
                statut = "SCHEDULED"
            
            match_dict = {
                "rencId": str(renc_id),
                "date": str(renc_date),
                "equipe_domicile": str(equipe1_name),
                "equipe_exterieur": str(equipe2_name),
                "score_domicile": but1 if but1 is not None else None,
                "score_exterieur": but2 if but2 is not None else None,
                "statut": statut
            }
            matches_list.append(match_dict)
        
        return matches_list
        
    except requests.exceptions.Timeout:
        print(f"Erreur: Timeout lors de la récupération des matchs (ManifId: {manif_id})")
        return []
    except requests.exceptions.ConnectionError:
        print("Erreur: Impossible de se connecter à l'API de la FFH")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"Erreur HTTP: {e.response.status_code}")
        return []
    except (ValueError, KeyError) as e:
        print(f"Erreur lors du parsing JSON: {e}")
        return []
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return []


# Raccourcis pour Carquefou HC Seniors Dames Elite
def get_matchs_carquefou_sd() -> List[Dict]:
    """Récupère les matchs de Carquefou HC Seniors Dames (Elite)."""
    matches = _get_matchs_by_team_name("4318", "CARQUEFOU")
    # Normaliser le nom de l'équipe Carquefou (enlever le numéro de poule)
    for match in matches:
        match["equipe_domicile"] = _normalize_team_name(match["equipe_domicile"])
        match["equipe_exterieur"] = _normalize_team_name(match["equipe_exterieur"])
        
        # Correction spécifique : CARQUEFOU HC U14F -> Carquefou HC
        if "CARQUEFOU HC U14F" in match["equipe_domicile"]:
            match["equipe_domicile"] = match["equipe_domicile"].replace("CARQUEFOU HC U14F", "Carquefou HC")
        if "CARQUEFOU HC U14F" in match["equipe_exterieur"]:
            match["equipe_exterieur"] = match["equipe_exterieur"].replace("CARQUEFOU HC U14F", "Carquefou HC")
            
    return matches


# ============================================
# Elite Femmes Salle (NEW)
# ManifId: 4403 (Saison 2026)
# ============================================

def get_classement_salle_elite_femmes() -> List[Dict]:
    """
    Récupère le classement calculé des Elite Femmes en Salle.
    Calcul automatique: Victoire=3pts, Nul=1pt, Défaite=0pts
    Critères de départage: Différence de buts
    """
    try:
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
        params = {
            "SaisonAnnee": "2026",
            "ManifId": "4403"  # Elite Femmes Salle
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("ResponseCode") != "200":
            print(f"Erreur API: {data.get('ResponseMessage')}")
            return []
        
        rencontres_array = data.get("Response", {}).get("RencontresArray", {})
        
        # Dictionnaire pour stocker les stats de chaque équipe
        standings = {}
        
        for match_data in rencontres_array.values():
            scores = match_data.get("Scores", {})
            
            # Vérifier si le match a un résultat saisi
            if not scores.get("RencScoresSaisieDate"):
                continue
            
            equipe1_nom = match_data.get("Equipe1", {}).get("EquipeNom", "")
            equipe2_nom = match_data.get("Equipe2", {}).get("EquipeNom", "")
            but1 = int(scores.get("RencButsEqp1") or 0)
            but2 = int(scores.get("RencButsEqp2") or 0)
            
            # Initialiser les équipes si nécessaire
            if equipe1_nom not in standings:
                standings[equipe1_nom] = {
                    "joues": 0, "gagnes": 0, "nuls": 0, "perdus": 0,
                    "buts_pour": 0, "buts_contre": 0, "points": 0
                }
            if equipe2_nom not in standings:
                standings[equipe2_nom] = {
                    "joues": 0, "gagnes": 0, "nuls": 0, "perdus": 0,
                    "buts_pour": 0, "buts_contre": 0, "points": 0
                }
            
            # Mise à jour des statistiques
            standings[equipe1_nom]["joues"] += 1
            standings[equipe2_nom]["joues"] += 1
            
            standings[equipe1_nom]["buts_pour"] += but1
            standings[equipe1_nom]["buts_contre"] += but2
            
            standings[equipe2_nom]["buts_pour"] += but2
            standings[equipe2_nom]["buts_contre"] += but1
            
            if but1 > but2:
                standings[equipe1_nom]["gagnes"] += 1
                standings[equipe1_nom]["points"] += 3
                standings[equipe2_nom]["perdus"] += 1
            elif but2 > but1:
                standings[equipe2_nom]["gagnes"] += 1
                standings[equipe2_nom]["points"] += 3
                standings[equipe1_nom]["perdus"] += 1
            else:
                standings[equipe1_nom]["nuls"] += 1
                standings[equipe1_nom]["points"] += 1
                standings[equipe2_nom]["nuls"] += 1
                standings[equipe2_nom]["points"] += 1
        
        # Créer la liste de classement triée
        classement = []
        for position, (team_name, stats) in enumerate(
            sorted(standings.items(), key=lambda x: (-x[1]["points"], -(x[1]["buts_pour"] - x[1]["buts_contre"]), -x[1]["buts_pour"])),
            1
        ):
            classement.append({
                "position": position,
                "equipe": team_name,
                "points": stats["points"],
                "joues": stats["joues"],
                "gagnes": stats["gagnes"],
                "nuls": stats["nuls"],
                "perdus": stats["perdus"],
                "buts_pour": stats["buts_pour"],
                "buts_contre": stats["buts_contre"],
                "difference": stats["buts_pour"] - stats["buts_contre"]
            })
        
        return classement
        
    except requests.exceptions.Timeout:
        print(f"Erreur: Timeout lors de la récupération du classement Elite Femmes Salle")
        return []
    except requests.exceptions.ConnectionError:
        print("Erreur: Impossible de se connecter à l'API de la FFH")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"Erreur HTTP: {e.response.status_code}")
        return []
    except (ValueError, KeyError) as e:
        print(f"Erreur lors du parsing JSON: {e}")
        return []
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return []


def get_matchs_salle_elite_femmes() -> List[Dict]:
    """Récupère les matchs réels de l'Elite Femmes en Salle depuis la FFH."""
    return _get_matches_by_manif("4403")
def get_matches() -> List[Dict]:
    """Récupère les matchs de l'élite hommes."""
    return _get_matches_by_manif("4317")


def get_matches_femmes() -> List[Dict]:
    """Récupère les matchs de l'élite femmes."""
    return _get_matches_by_manif("4318")
def get_ranking() -> List[Dict]:
    """Récupère le classement de l'élite hommes."""
    return _calculate_ranking("4317")


def get_ranking_femmes() -> List[Dict]:
    """Récupère le classement de l'élite femmes."""
    return _calculate_ranking("4318")


def _get_matches_by_manif(manif_id: str) -> List[Dict]:
    """
    Fonction interne pour récupérer les matchs à partir d'un ManifId.
    
    Args:
        manif_id: L'identifiant de la manifestation (championnats)
    
    Returns:
        List[Dict]: Liste des matchs avec leurs informations.
    """
    try:
        url = "https://championnats.ffhockey.org/rest2/Championnats/ListerRencontres"
        params = {
            "SaisonAnnee": "2026",
            "ManifId": manif_id
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Vérifier la structure de la réponse
        if data.get("ResponseCode") != "200":
            print(f"Erreur API: {data.get('ResponseMessage')}")
            return []
        
        rencontres_data = data.get("Response", {})
        rencontres_array = rencontres_data.get("RencontresArray", {})
        
        matches_list = []
        
        # Parcourir toutes les rencontres
        for match_id, match_data in rencontres_array.items():
            renc_id = match_data.get("RencId", "")
            renc_date = match_data.get("RencDateDerog", "")
            
            equipe1_data = match_data.get("Equipe1", {})
            equipe2_data = match_data.get("Equipe2", {})
            
            equipe1_name = equipe1_data.get("EquipeNom", "")
            equipe2_name = equipe2_data.get("EquipeNom", "")
            
            scores = match_data.get("Scores", {})
            but1 = int(scores.get("RencButsEqp1") or 0) if scores.get("RencButsEqp1") else None
            but2 = int(scores.get("RencButsEqp2") or 0) if scores.get("RencButsEqp2") else None
            
            # Déterminer le statut du match
            if scores.get("RencScoresSaisieDate"):
                statut = "FINISHED"
            elif match_data.get("RencNonJoue") == "O":
                statut = "NOT_PLAYED"
            else:
                statut = "SCHEDULED"
            
            match_dict = {
                "rencId": str(renc_id),
                "date": str(renc_date),
                "equipe_domicile": str(equipe1_name),
                "equipe_exterieur": str(equipe2_name),
                "score_domicile": but1 if but1 is not None else None,
                "score_exterieur": but2 if but2 is not None else None,
                "statut": statut
            }
            matches_list.append(match_dict)
        
        return matches_list
        
    except requests.exceptions.Timeout:
        print("Erreur: Timeout lors de la récupération des matchs")
        return []
    except requests.exceptions.ConnectionError:
        print("Erreur: Impossible de se connecter à l'API de la FFH")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"Erreur HTTP: {e.response.status_code}")
        return []
    except (ValueError, KeyError) as e:
        print(f"Erreur lors du parsing JSON: {e}")
        return []
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return []
