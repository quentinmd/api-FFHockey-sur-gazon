#!/usr/bin/env python
"""
Client simple pour tester l'API
"""
import json
from scraper import get_ranking, get_matches

print("\n" + "="*60)
print("CLASSEMENT - ELITE HOMMES 2025/2026")
print("="*60)

ranking = get_ranking()
for team in ranking[:5]:
    print(f"{team['position']:2d}. {team['equipe']:<25} {team['points']:3d} pts - "
          f"{team['joues']}J {team['gagnes']}G {team['nuls']}N {team['perdus']}P "
          f"({team['buts_pour']}-{team['buts_contre']})")

print("\n" + "="*60)
print("DERNIERS MATCHS")
print("="*60)

matches = get_matches()
finished = [m for m in matches if m['statut'] == 'FINISHED']
for match in finished[-5:]:
    if match['score_domicile'] is not None:
        print(f"{match['date']}: {match['equipe_domicile']:<25} {match['score_domicile']} - "
              f"{match['score_exterieur']} {match['equipe_exterieur']}")

print("\n✅ Succès!")
