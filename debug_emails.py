#!/usr/bin/env python3
"""
Script de déboggage pour les emails - montre exactement ce qui se passe
"""

import os
import json
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("🔍 DÉBOGGAGE DES NOTIFICATIONS D'EMAIL")
print("=" * 70)

# 1️⃣ Vérifier les credentials
print("\n1️⃣ VÉRIFICATION DES CREDENTIALS GMAIL:")
print("-" * 70)
gmail_email = os.environ.get("GMAIL_EMAIL")
gmail_password = os.environ.get("GMAIL_PASSWORD")

print(f"GMAIL_EMAIL: {'✅ ' + gmail_email if gmail_email else '❌ NON CONFIGURÉ'}")
print(f"GMAIL_PASSWORD: {'✅ CONFIGURÉ (' + str(len(gmail_password)) + ' chars)' if gmail_password else '❌ NON CONFIGURÉ'}")

if not gmail_email or not gmail_password:
    print("\n⚠️  ERREUR: Variables Gmail manquantes!")
    print("   Ajoute GMAIL_EMAIL et GMAIL_PASSWORD dans Render Environment Variables")
    sys.exit(1)

# 2️⃣ Vérifier les abonnés
print("\n2️⃣ VÉRIFICATION DES ABONNÉS:")
print("-" * 70)
try:
    with open("email_subscribers.json", "r") as f:
        subscribers = json.load(f)
        if isinstance(subscribers, list):
            print(f"✅ Format correct (liste)")
            print(f"   Abonnés: {subscribers}")
        else:
            print(f"❌ Format incorrect (devrait être list, trouvé {type(subscribers).__name__})")
            print(f"   Contenu: {subscribers}")
except Exception as e:
    print(f"❌ Erreur: {e}")

# 3️⃣ Vérifier les matchs notifiés
print("\n3️⃣ VÉRIFICATION DES MATCHS NOTIFIÉS:")
print("-" * 70)
try:
    with open("notified_matches.json", "r") as f:
        notified = json.load(f)
        if isinstance(notified, list):
            print(f"✅ Format correct (liste)")
            print(f"   Matchs notifiés: {len(notified)}")
            if len(notified) > 0:
                print(f"   Exemples: {notified[:3]}")
        else:
            print(f"❌ Format incorrect (devrait être list, trouvé {type(notified).__name__})")
except Exception as e:
    print(f"❌ Erreur: {e}")

# 4️⃣ Tester l'envoi d'email
print("\n4️⃣ TEST D'ENVOI D'EMAIL:")
print("-" * 70)
try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    print("Connexion à Gmail SMTP...")
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(gmail_email, gmail_password)
    print("✅ Connexion réussie!")
    
    # Teste un email
    test_email = "quentin.mouraud@carquefouhockeyclub.com"
    message = MIMEMultipart("alternative")
    message["Subject"] = "🏑 Test d'Email - Hockey API"
    message["From"] = gmail_email
    message["To"] = test_email
    
    html = """
    <html><body style="font-family: Arial; background: #667eea;">
    <div style="background: white; padding: 20px; border-radius: 10px;">
    <h2>✅ Test d'Email - System Works!</h2>
    <p>Cet email de test prouve que le système de notifications fonctionne.</p>
    <p><strong>Date:</strong> """ + str(__import__('datetime').datetime.now()) + """</p>
    </div></body></html>
    """
    
    message.attach(MIMEText(html, "html"))
    server.sendmail(gmail_email, test_email, message.as_string())
    server.quit()
    
    print(f"✅ Email de test envoyé à {test_email}")
    print("   Vérifie ton inbox dans quelques secondes!")
    
except smtplib.SMTPAuthenticationError:
    print("❌ ERREUR: Les credentials Gmail sont incorrects!")
    print("   Vérifie GMAIL_EMAIL et GMAIL_PASSWORD sur Render")
except smtplib.SMTPException as e:
    print(f"❌ ERREUR SMTP: {e}")
except Exception as e:
    print(f"❌ ERREUR: {e}")

print("\n" + "=" * 70)
print("Fin du déboggage")
print("=" * 70)
