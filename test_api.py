#!/usr/bin/env python
"""
Script de test pour vérifier le fonctionnement des fonctions scraper
"""

import sys
from scraper import get_ranking, get_matches

print("=" * 60)
print("TEST DE L'API HOCKEY SUR GAZON FRANCE")
print("=" * 60)

print("\n1️⃣  Test de get_ranking()...")
print("-" * 60)
try:
    ranking = get_ranking()
    if ranking:
        print(f"✅ Succès ! {len(ranking)} équipes récupérées")
        print("\nTop 3 du classement :")
        for team in ranking[:3]:
            print(f"  {team['position']}. {team['equipe']} - {team['points']} pts ({team['joues']} matchs)")
    else:
        print("❌ Erreur : Aucune donnée retournée")
        sys.exit(1)
except Exception as e:
    print(f"❌ Erreur : {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n2️⃣  Test de get_matches()...")
print("-" * 60)
try:
    matches = get_matches()
    if matches:
        print(f"✅ Succès ! {len(matches)} matchs récupérés")
        # Afficher les 3 premiers matchs avec résultats
        finished_matches = [m for m in matches if m['statut'] == 'FINISHED']
        print(f"\n{len(finished_matches)} matchs joués, {len(matches) - len(finished_matches)} à venir")
        if finished_matches:
            print("\n3 derniers matchs joués :")
            for match in finished_matches[-3:]:
                if match['score_domicile'] is not None:
                    print(f"  {match['equipe_domicile']} {match['score_domicile']} - {match['score_exterieur']} {match['equipe_exterieur']}")
                    print(f"    Date: {match['date']}")
    else:
        print("❌ Erreur : Aucune donnée retournée")
        sys.exit(1)
except Exception as e:
    print(f"❌ Erreur : {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ TOUS LES TESTS SONT PASSÉS !")
print("=" * 60)
