#!/bin/bash
# Script pour préparer et committer les changements

echo "📝 Préparation du commit Git"
echo "============================"
echo ""

cd "$(dirname "$0")"

# Vérifier Git
if ! command -v git &> /dev/null; then
    echo "❌ Git non trouvé!"
    exit 1
fi

echo "📋 Fichiers modifiés:"
git status --short

echo ""
echo "🔍 Ajout des fichiers..."
git add -A

echo "✅ Fichiers staged"
echo ""

# Afficher les changements
echo "📝 Commits à faire:"
echo ""
echo "Types de changements:"
echo "  • API: Endpoint import-real-data pour vrais matchs FFH"
echo "  • Dashboard: Config API modulable, utilise vrais matchs"
echo "  • Deploy: Dockerfile, fly.toml, scripts de déploiement"
echo "  • Docs: DEPLOYMENT_FLYIO.md, DEPLOYMENT_SUMMARY.md, QUICKSTART_DEPLOY.sh"
echo ""

read -p "Décrire brièvement le changement (press ENTER pour default): " commit_msg

if [ -z "$commit_msg" ]; then
    commit_msg="feat: Add real match import from FFH API + Fly.io deployment ready

- Add /api/v1/live/import-real-data/{championship} endpoint
- Load 50+ real matches per championship from FFHockey API
- Update Dashboard to use real matches via apiConfig
- Add deploy-flyio.sh and DEPLOYMENT_FLYIO.md
- Add .env.production configuration
- API and Dashboard production-ready on Fly.io"
fi

git commit -m "$commit_msg"

echo ""
echo "✅ Commit effectué!"
echo ""
echo "📤 Prochaine étape: git push"
echo ""
echo "📊 Vérifier sur GitHub:"
echo "  https://github.com/quentinmd/api-FFHockey-sur-gazon"
