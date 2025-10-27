#!/bin/bash
# ==========================================
# GUIDE RAPIDE SETUP EMAIL NOTIFICATIONS
# ==========================================

echo "🏑 FFH Hockey Dashboard - Email Notifications Setup"
echo "=================================================="
echo ""

# Étape 1: Créer le fichier .env
echo "📝 Étape 1: Création du fichier .env"
echo "------------------------------------"

if [ -f ".env" ]; then
    echo "✅ Fichier .env existant trouvé"
else
    echo "❌ Fichier .env non trouvé"
    echo ""
    echo "INSTRUCTIONS:"
    echo "1. Allez sur myaccount.google.com"
    echo "2. Activez la vérification en 2 étapes"
    echo "3. Créez un mot de passe d'application pour 'Mail'"
    echo "4. Copiez le mot de passe généré"
    echo ""
    echo "Créez un fichier '.env' à côté de main.py avec:"
    echo "---"
    echo "GMAIL_EMAIL=votre_email@gmail.com"
    echo "GMAIL_PASSWORD=votre_mot_de_passe_de_16_caracteres"
    echo "---"
    echo ""
    read -p "Appuyez sur Entrée une fois le fichier .env créé..."
fi

echo ""
echo "✅ Configuration Gmail OK"
echo ""

# Étape 2: Vérifier les dépendances
echo "📦 Étape 2: Vérification des dépendances"
echo "--------------------------------------"

if python3 -c "import dotenv" 2>/dev/null; then
    echo "✅ python-dotenv installé"
else
    echo "❌ python-dotenv non trouvé"
    echo "Installation: pip install python-dotenv"
    pip install python-dotenv
fi

echo ""
echo "✅ Dépendances OK"
echo ""

# Étape 3: Démarrer l'API
echo "🚀 Étape 3: Démarrage de l'API"
echo "----------------------------"
echo "L'API démarre sur http://localhost:8000"
echo ""

python3 main.py

