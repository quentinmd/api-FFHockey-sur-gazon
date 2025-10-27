#!/usr/bin/env python3
"""
Checklist de vérification pour les notifications email
Exécutez ce script pour vérifier que tout est bien configuré
"""

import os
import json
from pathlib import Path

class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def check(condition, success_msg, error_msg):
    """Afficher un check mark ou un X"""
    if condition:
        print(f"{Color.GREEN}✅ {success_msg}{Color.RESET}")
        return True
    else:
        print(f"{Color.RED}❌ {error_msg}{Color.RESET}")
        return False

def main():
    print(f"\n{Color.BLUE}{'='*60}")
    print("🏑 CHECKLIST - Email Notifications Setup")
    print(f"{'='*60}{Color.RESET}\n")
    
    passed = 0
    total = 0
    
    # Check 1: Fichier .env
    print(f"{Color.BLUE}1. Configuration Gmail (.env){Color.RESET}")
    total += 1
    if check(os.path.exists(".env"), 
             ".env existe", 
             ".env MANQUANT - Créez-le avec GMAIL_EMAIL et GMAIL_PASSWORD"):
        passed += 1
        
        # Vérifier les variables
        os.environ.get("GMAIL_EMAIL") and print(f"   {Color.GREEN}✓ GMAIL_EMAIL défini{Color.RESET}")
        os.environ.get("GMAIL_PASSWORD") and print(f"   {Color.GREEN}✓ GMAIL_PASSWORD défini{Color.RESET}")
    print()
    
    # Check 2: Fichiers Python
    print(f"{Color.BLUE}2. Fichiers Backend{Color.RESET}")
    total += 1
    if check(os.path.exists("main.py"), 
             "main.py existe",
             "main.py MANQUANT"):
        passed += 1
        
        # Vérifier que les imports sont dans main.py
        with open("main.py", "r") as f:
            content = f.read()
            has_dotenv = "load_dotenv" in content
            has_subscribe = "/api/v1/subscribe" in content
            has_email_func = "send_match_finished_email" in content
            
            print(f"   {Color.GREEN if has_dotenv else Color.RED}{'✓' if has_dotenv else '✗'} load_dotenv{Color.RESET}")
            print(f"   {Color.GREEN if has_subscribe else Color.RED}{'✓' if has_subscribe else '✗'} Endpoint /subscribe{Color.RESET}")
            print(f"   {Color.GREEN if has_email_func else Color.RED}{'✓' if has_email_func else '✗'} Fonction email{Color.RESET}")
    print()
    
    # Check 3: Fichiers React
    print(f"{Color.BLUE}3. Composants Frontend{Color.RESET}")
    total += 1
    has_all_files = True
    
    files_to_check = [
        ("Dashboard/src/components/Newsletter.jsx", "Newsletter component"),
        ("Dashboard/src/styles/Newsletter.css", "Newsletter CSS"),
        ("Dashboard/src/App.jsx", "App.jsx"),
    ]
    
    for file_path, desc in files_to_check:
        if os.path.exists(file_path):
            print(f"   {Color.GREEN}✓ {desc}{Color.RESET}")
        else:
            print(f"   {Color.RED}✗ {desc} MANQUANT{Color.RESET}")
            has_all_files = False
    
    if has_all_files:
        passed += 1
    print()
    
    # Check 4: Documentation
    print(f"{Color.BLUE}4. Documentation{Color.RESET}")
    total += 1
    doc_files = {
        "SETUP_EMAIL_RAPIDE.md": "Guide rapide (5 min)",
        "EMAIL_NOTIFICATIONS.md": "Documentation complète",
        "IMPLEMENTATION_SUMMARY.md": "Résumé technique",
        "EMAIL_SETUP_README.md": "README principal",
        "test_email_setup.py": "Script de test",
    }
    
    has_docs = True
    for doc, desc in doc_files.items():
        if os.path.exists(doc):
            print(f"   {Color.GREEN}✓ {desc}{Color.RESET}")
        else:
            print(f"   {Color.YELLOW}⚠ {desc} ({doc}){Color.RESET}")
            has_docs = False
    
    if has_docs:
        passed += 1
    print()
    
    # Check 5: Dépendances
    print(f"{Color.BLUE}5. Dépendances{Color.RESET}")
    total += 1
    dependencies = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("requests", "Requests"),
        ("dotenv", "python-dotenv"),
        ("smtplib", "SMTP (stdlib)"),
    ]
    
    all_deps = True
    for module, name in dependencies:
        try:
            __import__(module)
            print(f"   {Color.GREEN}✓ {name}{Color.RESET}")
        except ImportError:
            print(f"   {Color.RED}✗ {name} MANQUANT{Color.RESET}")
            all_deps = False
    
    if all_deps:
        passed += 1
    print()
    
    # Check 6: .gitignore
    print(f"{Color.BLUE}6. Sécurité (.gitignore){Color.RESET}")
    total += 1
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r") as f:
            gitignore_content = f.read()
            has_env = ".env" in gitignore_content
            has_json = "email_subscribers.json" in gitignore_content
            
            print(f"   {Color.GREEN if has_env else Color.YELLOW}{'✓' if has_env else '⚠'} .env dans .gitignore{Color.RESET}")
            print(f"   {Color.GREEN if has_json else Color.YELLOW}{'✓' if has_json else '⚠'} email_*.json dans .gitignore{Color.RESET}")
            
            if has_env and has_json:
                passed += 1
    print()
    
    # Résumé
    percentage = (passed / total) * 100
    status = Color.GREEN if percentage == 100 else Color.YELLOW if percentage >= 80 else Color.RED
    
    print(f"{Color.BLUE}{'='*60}")
    print(f"{status}Résumé: {passed}/{total} checks réussis ({percentage:.0f}%){Color.RESET}")
    print(f"{'='*60}{Color.RESET}\n")
    
    if percentage == 100:
        print(f"{Color.GREEN}✨ Tout est prêt ! Vous pouvez démarrer l'API ✨{Color.RESET}\n")
        print("Prochaines étapes:")
        print("1. Démarrer l'API: python3 main.py")
        print("2. Démarrer le dashboard: cd Dashboard && npm run dev")
        print("3. Aller sur http://localhost:5173")
        print("4. S'abonner via le formulaire email")
        print()
    elif percentage >= 80:
        print(f"{Color.YELLOW}⚠️  Il manque quelques éléments, voir les ❌ ci-dessus{Color.RESET}\n")
    else:
        print(f"{Color.RED}❌ Des éléments critiques manquent, veuillez suivre les instructions{Color.RESET}\n")
    
    # Liens vers la documentation
    print(f"{Color.BLUE}📚 Documentation:{Color.RESET}")
    print("   1. Démarrage rapide: SETUP_EMAIL_RAPIDE.md")
    print("   2. Documentation complète: EMAIL_NOTIFICATIONS.md")
    print("   3. Vue d'ensemble: EMAIL_SETUP_README.md")
    print()

if __name__ == "__main__":
    # Charger les variables d'environnement
    from dotenv import load_dotenv
    load_dotenv()
    
    main()
