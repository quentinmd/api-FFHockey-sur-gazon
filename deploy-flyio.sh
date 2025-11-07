#!/bin/bash
# Script de déploiement Fly.io complet

set -e

echo "🚀 Déploiement sur Fly.io"
echo "=========================="

# Vérifications
if ! command -v flyctl &> /dev/null; then
    echo "❌ flyctl non trouvé. Installez-le : brew install flyctl"
    exit 1
fi

# Aller dans le répertoire de l'API
cd "$(dirname "$0")"

# 1. Vérifier que firebase_key.json existe
if [ ! -f "firebase_key.json" ]; then
    echo "❌ firebase_key.json non trouvé!"
    exit 1
fi
echo "✅ firebase_key.json trouvé"

# 2. Configurer les secrets Fly
echo "🔐 Configuration des secrets Fly..."
fly secrets set \
    FIREBASE_DB_URL="https://api-ffhockey-default-rtdb.europe-west1.firebasedatabase.app" \
    ADMIN_PASSWORD="admin123" \
    --app api-ffhockey-sur-gazon 2>/dev/null || true

echo "✅ Secrets configurés"

# 3. Build et deploy
echo "📦 Build et déploiement..."
fly deploy --app api-ffhockey-sur-gazon

# 4. Vérifier le déploiement
echo "🔍 Vérification du déploiement..."
sleep 5

if fly status --app api-ffhockey-sur-gazon | grep -q "running"; then
    echo "✅ API déployée avec succès!"
    echo "🌐 URL: https://api-ffhockey-sur-gazon.fly.dev"
    echo ""
    echo "📝 Prochaines étapes:"
    echo "1. Tester l'API:"
    echo "   curl -X POST 'https://api-ffhockey-sur-gazon.fly.dev/api/v1/live/import-real-data/elite-hommes?admin_token=admin123'"
    echo ""
    echo "2. Déployer le Dashboard:"
    echo "   cd Dashboard && npm run build"
    echo "   Uploadez le dossier 'dist' sur Netlify/Vercel"
else
    echo "⚠️  Vérifiez le statut: fly status --app api-ffhockey-sur-gazon"
    echo "📋 Logs: fly logs --app api-ffhockey-sur-gazon"
fi
