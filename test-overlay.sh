#!/bin/bash

# 🎬 TEST SCORE OVERLAY - Vérification complète

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🎬 VÉRIFICATION SCORE OVERLAY OBS - Test Complet         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Couleurs pour le terminal
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

TEST_COUNT=0
PASS_COUNT=0
FAIL_COUNT=0

# Fonction pour tester
test_result() {
    local test_name=$1
    local result=$2
    TEST_COUNT=$((TEST_COUNT + 1))
    
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

# Test 1: Vérifier que score-overlay.html existe
echo -e "\n${BLUE}📋 Test 1: Fichiers existants${NC}"
echo "─────────────────────────────────────────────────"

if [ -f "score-overlay.html" ]; then
    SIZE=$(du -h score-overlay.html | cut -f1)
    echo -e "${GREEN}✅${NC} score-overlay.html existe ($SIZE)"
    test_result "Fichier HTML présent" 0
else
    echo -e "${RED}❌${NC} score-overlay.html manquant"
    test_result "Fichier HTML présent" 1
fi

if [ -f "main.py" ]; then
    echo -e "${GREEN}✅${NC} main.py existe"
    test_result "Fichier main.py présent" 0
else
    echo -e "${RED}❌${NC} main.py manquant"
    test_result "Fichier main.py présent" 1
fi

# Test 2: Vérifier la syntaxe Python
echo -e "\n${BLUE}🔧 Test 2: Syntaxe Python${NC}"
echo "─────────────────────────────────────────────────"

if command -v python3 &> /dev/null; then
    if python3 -m py_compile main.py 2>/dev/null; then
        echo -e "${GREEN}✅${NC} Syntaxe Python valide"
        test_result "Syntaxe main.py" 0
    else
        echo -e "${RED}❌${NC} Erreur de syntaxe dans main.py"
        test_result "Syntaxe main.py" 1
    fi
else
    echo -e "${YELLOW}⚠️${NC} python3 non trouvé, skipping"
fi

# Test 3: Vérifier le contenu du HTML
echo -e "\n${BLUE}📄 Test 3: Contenu HTML${NC}"
echo "─────────────────────────────────────────────────"

if grep -q "overlay-container\|score-banner" score-overlay.html; then
    echo -e "${GREEN}✅${NC} Containers d'overlay trouvés dans HTML"
    test_result "Containers overlay présents" 0
else
    echo -e "${RED}❌${NC} Containers overlay manquants"
    test_result "Containers overlay présents" 1
fi

if grep -q "POLL_INTERVAL" score-overlay.html; then
    echo -e "${GREEN}✅${NC} Polling configuré dans HTML"
    test_result "POLL_INTERVAL présent" 0
else
    echo -e "${RED}❌${NC} POLL_INTERVAL manquant"
    test_result "POLL_INTERVAL présent" 1
fi

if grep -q "elite-hommes\|elite-femmes" score-overlay.html; then
    echo -e "${GREEN}✅${NC} Championnats configurés"
    test_result "Championnats présents" 0
else
    echo -e "${RED}❌${NC} Championnats manquants"
    test_result "Championnats présents" 1
fi

# Test 4: Vérifier que main.py a la route d'overlay
echo -e "\n${BLUE}🛣️  Test 4: Route API${NC}"
echo "─────────────────────────────────────────────────"

if grep -q "score-overlay.html" main.py; then
    echo -e "${GREEN}✅${NC} Route /score-overlay.html dans main.py"
    test_result "Route overlay présente" 0
else
    echo -e "${RED}❌${NC} Route overlay absente de main.py"
    test_result "Route overlay présente" 1
fi

if grep -q "FileResponse\|HTMLResponse" main.py; then
    echo -e "${GREEN}✅${NC} Imports FastAPI présents"
    test_result "Imports FastAPI corrects" 0
else
    echo -e "${RED}❌${NC} Imports FastAPI manquants"
    test_result "Imports FastAPI corrects" 1
fi

# Test 5: Vérifier la documentation
echo -e "\n${BLUE}📚 Test 5: Documentation${NC}"
echo "─────────────────────────────────────────────────"

if [ -f "SCORE_OVERLAY_GUIDE.md" ]; then
    echo -e "${GREEN}✅${NC} SCORE_OVERLAY_GUIDE.md présent"
    test_result "Guide complet présent" 0
else
    echo -e "${RED}❌${NC} SCORE_OVERLAY_GUIDE.md manquant"
    test_result "Guide complet présent" 1
fi

if [ -f "README_OVERLAY.md" ]; then
    echo -e "${GREEN}✅${NC} README_OVERLAY.md présent"
    test_result "Vue d'ensemble présente" 0
else
    echo -e "${RED}❌${NC} README_OVERLAY.md manquant"
    test_result "Vue d'ensemble présente" 1
fi

if [ -f "OVERLAY_QUICKSTART.md" ]; then
    echo -e "${GREEN}✅${NC} OVERLAY_QUICKSTART.md présent"
    test_result "Quickstart présent" 0
else
    echo -e "${RED}❌${NC} OVERLAY_QUICKSTART.md manquant"
    test_result "Quickstart présent" 1
fi

# Test 6: Vérifier les environnements virtuels
echo -e "\n${BLUE}🐍 Test 6: Environnement Python${NC}"
echo "─────────────────────────────────────────────────"

if [ -d ".venv/bin" ]; then
    echo -e "${GREEN}✅${NC} Environnement virtuel présent"
    test_result "Venv présent" 0
else
    echo -e "${RED}❌${NC} Environnement virtuel manquant"
    test_result "Venv présent" 1
fi

# Test 7: Vérifier les dépendances fastapi
echo -e "\n${BLUE}📦 Test 7: Dépendances${NC}"
echo "─────────────────────────────────────────────────"

if grep -q "fastapi\|FileResponse" main.py; then
    echo -e "${GREEN}✅${NC} FastAPI utilisé correctement"
    test_result "FastAPI intégration" 0
else
    echo -e "${RED}❌${NC} FastAPI non intégré correctement"
    test_result "FastAPI intégration" 1
fi

# Résumé
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                     📊 RÉSUMÉ DES TESTS                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Total tests: $TEST_COUNT"
echo -e "Réussis: ${GREEN}$PASS_COUNT${NC}"
echo -e "Échoués: ${RED}$FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ TOUS LES TESTS RÉUSSIS!${NC}"
    echo ""
    echo "Prêt à utiliser!"
    echo ""
    echo "Prochaines étapes:"
    echo "  1. Lancer l'API: python main.py"
    echo "  2. Ouvrir: http://localhost:8000/score-overlay.html"
    echo "  3. Configurer dans OBS"
    echo "  4. Streamer!"
    exit 0
else
    echo -e "${RED}❌ Certains tests ont échoué.${NC}"
    echo ""
    echo "Vérifier:"
    echo "  - Tous les fichiers sont présents"
    echo "  - La syntaxe Python est correcte"
    echo "  - Les fichiers sont à la bonne location"
    exit 1
fi
