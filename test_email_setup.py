#!/usr/bin/env python3
"""
Script de test pour vérifier le setup des notifications email
"""

import json
import os
from pathlib import Path

def check_env():
    """Vérifier si le fichier .env existe et les variables sont chargées"""
    print("\n🔍 Vérification du fichier .env...")
    print("-" * 50)
    
    if os.path.exists(".env"):
        print("✅ Fichier .env trouvé")
        
        # Vérifier les variables
        if os.environ.get("GMAIL_EMAIL"):
            print(f"✅ GMAIL_EMAIL: {os.environ.get('GMAIL_EMAIL')}")
        else:
            print("⚠️  GMAIL_EMAIL non défini")
        
        if os.environ.get("GMAIL_PASSWORD"):
            pwd = os.environ.get("GMAIL_PASSWORD")
            masked = pwd[:4] + "*" * (len(pwd) - 8) + pwd[-4:]
            print(f"✅ GMAIL_PASSWORD: {masked}")
        else:
            print("⚠️  GMAIL_PASSWORD non défini")
    else:
        print("❌ Fichier .env introuvable")
        print("   Créez-le avec: GMAIL_EMAIL=... et GMAIL_PASSWORD=...")

def check_json_files():
    """Vérifier les fichiers de stockage JSON"""
    print("\n📁 Vérification des fichiers de données...")
    print("-" * 50)
    
    # Subscribers
    if os.path.exists("email_subscribers.json"):
        with open("email_subscribers.json", "r") as f:
            subscribers = json.load(f)
        print(f"✅ email_subscribers.json: {len(subscribers)} abonné(s)")
        if subscribers:
            for email in subscribers:
                print(f"   - {email}")
    else:
        print("⚠️  email_subscribers.json inexistant (créé au premier abonnement)")
    
    # Notified matches
    if os.path.exists("notified_matches.json"):
        with open("notified_matches.json", "r") as f:
            matches = json.load(f)
        print(f"✅ notified_matches.json: {len(matches)} match(s) notifié(s)")
    else:
        print("⚠️  notified_matches.json inexistant (créé au premier match)")

def check_imports():
    """Vérifier les imports nécessaires"""
    print("\n📦 Vérification des dépendances...")
    print("-" * 50)
    
    imports = {
        "fastapi": "FastAPI",
        "uvicorn": "Uvicorn",
        "requests": "Requests",
        "dotenv": "python-dotenv",
        "smtplib": "SMTP (stdlib)",
    }
    
    for module, name in imports.items():
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} - À installer: pip install {name.lower()}")

def test_email_format():
    """Afficher un exemple d'email"""
    print("\n📧 Exemple d'email qui sera envoyé...")
    print("-" * 50)
    
    example = """
    De: hockey.france@gmail.com
    Pour: user@gmail.com
    Objet: 🏑 Fin de match: Paris HC vs Nantes HC
    
    ┌─────────────────────────────────────────┐
    │         ⚽ Fin de Match                 │
    │     Notificateur Hockey                 │
    ├─────────────────────────────────────────┤
    │                                         │
    │  Compétition: Elite Hommes              │
    │  Date: sam. 17/10/2025 à 20:00          │
    │                                         │
    │       Paris HC          5 - 3           │
    │                    Nantes HC            │
    │                                         │
    │  Le match entre Paris HC et Nantes HC   │
    │  s'est terminé sur le score de 5 - 3.  │
    │                                         │
    └─────────────────────────────────────────┘
    """
    print(example)

def main():
    """Exécuter tous les checks"""
    print("\n" + "="*50)
    print("🏑 Email Notifications - Test de Configuration")
    print("="*50)
    
    # Charger les variables d'environnement
    from dotenv import load_dotenv
    load_dotenv()
    
    # Exécuter les checks
    check_env()
    check_json_files()
    check_imports()
    test_email_format()
    
    print("\n" + "="*50)
    print("✅ Vérification terminée!")
    print("="*50)
    print("\n📖 Pour la documentation complète:")
    print("   - SETUP_EMAIL_RAPIDE.md (guide rapide)")
    print("   - EMAIL_NOTIFICATIONS.md (doc complète)")
    print("   - IMPLEMENTATION_SUMMARY.md (résumé technique)")
    print("\n")

if __name__ == "__main__":
    main()
