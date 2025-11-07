#!/bin/bash

# Script pour lancer l'API FastAPI
# Usage: ./run-api.sh

cd "$(dirname "$0")"

echo "🚀 Lancement de l'API FFHockey..."
echo ""

# Vérifier si l'environnement virtuel existe
if [ ! -d ".venv" ]; then
    echo "❌ Environnement virtuel (.venv) non trouvé!"
    echo "Créez-le avec: python3 -m venv .venv"
    exit 1
fi

# Activer l'environnement virtuel
source .venv/bin/activate

echo "✅ Environnement virtuel activé"
echo ""

# Vérifier si main.py existe
if [ ! -f "main.py" ]; then
    echo "❌ Fichier main.py non trouvé!"
    exit 1
fi

# Vérifier le port 8000
echo "🔍 Vérification du port 8000..."
if lsof -i :8000 &>/dev/null; then
    echo "⚠️  Le port 8000 est déjà utilisé!"
    echo "Voulez-vous arrêter le processus existant? (y/n)"
    read -r response
    if [ "$response" = "y" ]; then
        lsof -i :8000 | awk 'NR>1 {print $2}' | xargs kill -9 2>/dev/null
        sleep 2
        echo "✅ Port libéré"
    fi
fi

echo ""
echo "🎬 Démarrage de l'API..."
echo "────────────────────────────────────────────────────"
echo ""
echo "L'API sera disponible sur:"
echo "  👉 http://localhost:8000"
echo ""
echo "Score simple:"
echo "  👉 http://localhost:8000/score-simple.html"
echo ""
echo "Docs:"
echo "  👉 http://localhost:8000/docs"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter"
echo ""
echo "────────────────────────────────────────────────────"
echo ""

# Lancer l'API
python main.py
