#!/usr/bin/env python3
"""
Script pour tester l'envoi d'email manuellement
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Récupère les variables d'env
gmail_email = os.environ.get("GMAIL_EMAIL")
gmail_password = os.environ.get("GMAIL_PASSWORD")

print("=" * 60)
print("TEST D'ENVOI D'EMAIL MANUEL")
print("=" * 60)

# Vérifie les credentials
print("\n1️⃣ Vérification des credentials Gmail:")
if gmail_email:
    print(f"   ✅ GMAIL_EMAIL: {gmail_email}")
else:
    print("   ❌ GMAIL_EMAIL: NON CONFIGURÉ")

if gmail_password:
    print(f"   ✅ GMAIL_PASSWORD: configuré (masqué)")
else:
    print("   ❌ GMAIL_PASSWORD: NON CONFIGURÉ")

# Vérifie les abonnés
print("\n2️⃣ Vérification des abonnés:")
try:
    with open("email_subscribers.json", "r") as f:
        import json
        subscribers = json.load(f)
        print(f"   ✅ Abonnés trouvés: {subscribers}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

# Teste l'endpoint
print("\n3️⃣ Appel de l'API pour obtenir les matchs terminés:")
try:
    response = requests.get("http://127.0.0.1:8000/api/v1/elite-hommes/matchs")
    if response.status_code == 200:
        data = response.json()
        finished = [m for m in data.get("data", []) if m.get("statut") == "FINISHED"]
        print(f"   ✅ {len(finished)} matchs terminés trouvés")
        if finished:
            m = finished[0]
            print(f"      Exemple: {m.get('equipe_domicile')} vs {m.get('equipe_exterieur')}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

# Teste les stats
print("\n4️⃣ Statistiques de notification:")
try:
    response = requests.get("http://127.0.0.1:8000/api/v1/notifications/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"   ✅ Abonnés: {stats.get('total_subscribers')}")
        print(f"   ✅ Matchs notifiés: {stats.get('total_notified_matches')}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

print("\n" + "=" * 60)
print("Pour déboguer les emails:")
print("1. Vérifier que GMAIL_EMAIL et GMAIL_PASSWORD sont configurés sur Render")
print("2. Vérifier que le fichier email_subscribers.json est au bon format")
print("3. Relancer l'API après correction")
print("=" * 60)
