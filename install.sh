#!/bin/bash
# Installation locale de développement

echo "🔧 Installation du projet FFHockey Live Score"
echo "=============================================="
echo ""

# Aller dans le dossier du projet
cd "$(dirname "$0")"

# 1. Python venv
echo "1️⃣  Configuration Python..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ Virtual env créé"
fi

source .venv/bin/activate
pip install -r requirements.txt
echo "✅ Dépendances Python installées"

# 2. Dashboard Node
echo ""
echo "2️⃣  Configuration Dashboard..."
cd Dashboard
npm install
echo "✅ Dépendances Node installées"
cd ..

# 3. Firebase key
echo ""
echo "3️⃣  Vérification Firebase..."
if [ ! -f "firebase_key.json" ]; then
    echo "⚠️  firebase_key.json non trouvé"
    echo "   Placez votre clé Firebase dans le dossier racine"
else
    echo "✅ firebase_key.json trouvé"
fi

# 4. .env
echo ""
echo "4️⃣  Configuration .env..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
FIREBASE_DB_URL=https://api-ffhockey-default-rtdb.europe-west1.firebasedatabase.app
FIREBASE_KEY_PATH=firebase_key.json
ADMIN_PASSWORD=admin123
EOF
    echo "✅ .env créé"
else
    echo "✅ .env existe déjà"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ INSTALLATION TERMINÉE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Démarrer le développement:"
echo ""
echo "Terminal 1 - API FastAPI:"
echo "  python3 main.py"
echo "  # Accessible à http://localhost:8000"
echo ""
echo "Terminal 2 - Dashboard React:"
echo "  cd Dashboard && npm run dev"
echo "  # Accessible à http://localhost:5173"
echo ""
echo "📝 Documentation:"
echo "  • README.md - Vue d'ensemble"
echo "  • DEPLOYMENT_FLYIO.md - Déploiement"
echo "  • DEPLOYMENT_SUMMARY.md - Résumé complet"
