#!/bin/bash

# Test Script pour Live Score Platform
# Utilisation: bash test_live_score.sh

API_URL="http://localhost:8000"
ADMIN_TOKEN="admin123"

echo "🏑 TEST LIVE SCORE PLATFORM"
echo "============================"
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Récupérer tous les matchs
echo -e "${YELLOW}[TEST 1]${NC} GET /api/v1/live/matches"
curl -s "$API_URL/api/v1/live/matches" | jq '.' || echo "❌ Erreur"
echo ""

# Test 2: Récupérer un match spécifique
echo -e "${YELLOW}[TEST 2]${NC} GET /api/v1/live/match/{match_id}"
echo "Note: Remplacer match_id par un ID réel"
curl -s "$API_URL/api/v1/live/match/match_001" | jq '.' || echo "❌ Erreur"
echo ""

# Test 3: Mettre à jour un score
echo -e "${YELLOW}[TEST 3]${NC} PUT /api/v1/live/match/match_001/score"
echo "Mise à jour: Team1 3-2 Team2"
curl -s -X PUT \
  "$API_URL/api/v1/live/match/match_001/score?admin_token=$ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "score_domicile": 3,
    "score_exterieur": 2
  }' | jq '.'
echo ""

# Test 4: Ajouter un buteur
echo -e "${YELLOW}[TEST 4]${NC} POST /api/v1/live/match/match_001/scorer"
echo "Buteur: Dupont (équipe domicile, minute 25)"
curl -s -X POST \
  "$API_URL/api/v1/live/match/match_001/scorer?admin_token=$ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "joueur": "Dupont",
    "equipe": "domicile",
    "temps": 25
  }' | jq '.'
echo ""

# Test 5: Ajouter un carton
echo -e "${YELLOW}[TEST 5]${NC} POST /api/v1/live/match/match_001/card"
echo "Carton: Dupont (jaune, équipe domicile, minute 45)"
curl -s -X POST \
  "$API_URL/api/v1/live/match/match_001/card?admin_token=$ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "joueur": "Dupont",
    "equipe": "domicile",
    "temps": 45,
    "couleur": "jaune"
  }' | jq '.'
echo ""

# Test 6: Mettre à jour le statut
echo -e "${YELLOW}[TEST 6]${NC} PUT /api/v1/live/match/match_001/status"
echo "Statut: LIVE"
curl -s -X PUT \
  "$API_URL/api/v1/live/match/match_001/status?admin_token=$ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "statut": "LIVE"
  }' | jq '.'
echo ""

# Test 7: Récupérer le match mis à jour
echo -e "${YELLOW}[TEST 7]${NC} GET /api/v1/live/match/match_001 (après mise à jour)"
curl -s "$API_URL/api/v1/live/match/match_001" | jq '.'
echo ""

# Test 8: Test d'authentification (token invalide)
echo -e "${YELLOW}[TEST 8]${NC} Test authentification (token invalide)"
echo "Expected: 401 Unauthorized"
curl -s -X PUT \
  "$API_URL/api/v1/live/match/match_001/score?admin_token=invalid_token" \
  -H "Content-Type: application/json" \
  -d '{
    "score_domicile": 5,
    "score_exterieur": 3
  }' | jq '.detail'
echo ""

echo -e "${GREEN}✅ Tests terminés!${NC}"
echo ""
echo "📝 Notes:"
echo "  - Remplacer 'match_001' par des IDs réels depuis Firebase"
echo "  - Assurez-vous que l'API est démarrée (python main.py)"
echo "  - Firebase doit être configuré avec firebase_key.json"
echo ""
