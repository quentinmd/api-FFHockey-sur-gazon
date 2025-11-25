# 🏑 Explication - Système de Scores en Direct

## 📋 Vue d'ensemble

J'ai ajouté un système complet de **matchs en direct avec mise à jour des scores** dans cette API FastAPI de Hockey sur Gazon.

---

## 🎯 Fonctionnalités principales

### 1. **Overlay Score Simple** (`score-simple.html`)
- Affiche le score complet d'un match
- Noms des deux équipes
- Heure du match
- **Mise à jour autonome** : seulement les scores changent (pas tout le cadre)
- Animation sur les scores qui changent
- Transparent pour OBS

**Paramètres URL :**
```
?championship=elite-femmes&renc_id=193082
```

### 2. **Overlay Score Only** (`score-only.html`)
- Affiche **SEULEMENT les 2 scores** côte à côte
- Chaque score avec le nom de l'équipe
- Très minimaliste
- Parfait pour les overlays OBS simples

**Paramètres URL :**
```
?championship=elite-femmes&renc_id=193082
```

### 3. **Routes API**
- `GET /api/v1/elite-hommes/matchs` - Tous les matchs Elite Hommes
- `GET /api/v1/elite-femmes/matchs` - Tous les matchs Elite Femmes
- `GET /api/v1/salle/elite-femmes/matchs` - Matchs Salle Elite Femmes

---

## 🔄 Comment fonctionne la mise à jour des scores

### **Frontend (JavaScript dans les HTML)**

```javascript
// Configuration
const API_BASE = 'http://localhost:8000/api/v1';
const POLL_INTERVAL = 5000; // 5 secondes

// Polling toutes les 5 secondes
setInterval(fetchMatch, POLL_INTERVAL);
```

**Logique clé :**
1. **Première requête** : Crée le cadre HTML complet (équipes, temps, scores)
2. **Requêtes suivantes** : Mises à jour UNIQUEMENT les nombres de score
3. **Détection de changement** : Compare les anciens scores avec les nouveaux
4. **Animation** : Flash + scale si le score a changé
5. **Rechargement minimal** : Le DOM n'est modifié que là où c'est nécessaire

### **Backend (FastAPI)**

```python
# LIVE SCORE ENDPOINTS (FIREBASE)

@app.get("/api/v1/{championship}/matchs")
async def get_matches(championship: str):
    # Récupère les matchs depuis Firebase
    # Chaque match contient:
    # - equipe_domicile
    # - equipe_exterieur
    # - score_domicile
    # - score_exterieur
    # - date
    # - rencId
    return {"data": matches_list}
```

---

## 📊 Structure des données

### **Structure d'un match retourné par l'API**

```json
{
  "rencId": "193082",
  "date": "2025-09-14 13:00:00",
  "equipe_domicile": "PHC MARCQ-EN-BAROEUL",
  "equipe_exterieur": "CARQUEFOU HC",
  "score_domicile": 2,
  "score_exterieur": 0,
  "statut": "FINISHED",
  "championship": "elite-femmes"
}
```

### **Paramètres supportés**

| Paramètre | Type | Exemple | Fonction |
|-----------|------|---------|----------|
| `championship` | string | `elite-femmes` | Sélectionne le championnat |
| `renc_id` | string | `193082` | Affiche ce match spécifique |
| `match_id` | string | `match_001` | Alternative pour match spécifique |

**Championnats disponibles :**
- `elite-hommes`
- `elite-femmes`
- `salle-elite-femmes`

---

## 🔧 Optimisations appliquées

### **1. Mise à jour intelligente du DOM**

```javascript
// ❌ Avant : Remplacer tout le HTML à chaque fois
container.innerHTML = newHTML; // Rafraîchit tout

// ✅ Après : Modifier seulement les scores
if (existingContainer) {
    const domBox = existingContainer.querySelector('#score-domicile');
    domBox.querySelector('.score-number').textContent = scoreDomicile;
    // Le reste du DOM reste inchangé
}
```

**Bénéfice :**
- Pas de scintillement
- Performance améliorée
- Animations fluides uniquement sur les scores

### **2. Détection intelligente des changements**

```javascript
const domicileChanged = scoreDomicile !== lastScores.domicile;
if (domicileChanged) {
    // Lancer l'animation seulement si ça a changé
    domBox.classList.add('animation');
}
```

### **3. Polling à intervalle régulier**

```javascript
// Requête API toutes les 5 secondes
setInterval(fetchMatch, 5000);
```

**Avantages :**
- Les scores se mettent à jour régulièrement
- Pas d'overcharge serveur
- 12 requêtes par minute par client

---

## 🎨 Animations et styles

### **Animations CSS**

```css
@keyframes scoreFlash {
    0% { transform: scale(1.3); background: rgba(0, 208, 132, 0.4); }
    50% { transform: scale(1.15); }
    100% { transform: scale(1); }
}
```

### **Indicateur de connexion**

```css
.status.connected { background: #00d084; } /* ✅ Vert = connecté */
.status.loading { animation: pulse 1s infinite; } /* ⏳ Orange = en cours */
.status.error { background: #ff4444; } /* ❌ Rouge = erreur */
```

---

## 🚀 Utilisation

### **En local (développement)**

```bash
# Lancer l'API
python main.py

# Accéder à l'overlay
http://localhost:8000/score-simple.html?championship=elite-femmes&renc_id=193082
```

### **En production (Fly.io)**

```bash
# Score simple
https://api-ffhockey-sur-gazon.fly.dev/score-simple.html?championship=elite-femmes&renc_id=193082

# Score only
https://api-ffhockey-sur-gazon.fly.dev/score-only.html?championship=elite-femmes&renc_id=193082
```

### **Dans OBS**

1. Ajouter une source **Navigateur**
2. URL : `https://api-ffhockey-sur-gazon.fly.dev/score-simple.html?championship=elite-femmes&renc_id=193082`
3. Dimensions : `1280 x 200` (ajustable)
4. Cocher **Arrière-plan transparent**
5. Positionner sur le flux vidéo

---

## 🔌 Configuration Firebase

### **Local**
- Clé Firebase lue depuis `firebase_key.json`

### **Production (Fly.io)**
- Clé Firebase injectée via variable d'environnement `FIREBASE_KEY`
- Stockée de manière sécurisée

---

## 📝 Fichiers modifiés/créés

| Fichier | Type | Description |
|---------|------|-------------|
| `score-simple.html` | Frontend | Overlay complet avec scores |
| `score-only.html` | Frontend | Overlay scores uniquement |
| `main.py` | Backend | Routes `/score-simple.html` et `/score-only.html` |
| `CONFIGURE_FIREBASE_FLYIO.md` | Doc | Guide de config Firebase |
| `SCORE_SIMPLE_GUIDE.md` | Doc | Utilisation simple |

---

## ✨ Points clés pour une autre IA

### **1. Système de polling côté client**
- Appelle l'API toutes les 5 secondes
- Met à jour les scores si changement détecté
- Lance animation flash sur changement

### **2. Optimisation DOM**
- Première charge = crée la structure complète
- Mises à jour = modifie seulement les nombres
- Pas de rechargement complet du HTML

### **3. Transparence OBS**
- Background `rgba(0, 0, 0, 0)` = transparent
- Parfait pour overlay sur une vidéo
- Animation fluide en arrière-plan

### **4. Flexibilité des paramètres**
- Support `renc_id` (ID FFH)
- Support `match_id` (ID système)
- Cherche d'abord par paramètre, puis premier match du championnat

### **5. Gestion des erreurs**
- Messages d'erreur clairs
- Affiche l'URL API tentée
- Suggère les solutions (python main.py)

---

## 🎯 Cas d'usage

✅ **Overlay OBS en direct**
✅ **Affichage de scores automatique**
✅ **Stream live avec scores actualisés**
✅ **Tableau de bord simple**
✅ **Intégration à d'autres systèmes**

---

## 🔮 Améliorations futures possibles

- [ ] WebSockets au lieu de polling (temps réel)
- [ ] Support de plusieurs matchs simultanés
- [ ] Notifications sonores sur changement de score
- [ ] Historique des buts (buteurs + temps)
- [ ] Affichage du statut du match (EN DIRECT, TERMINÉ, PROGRAMMÉ)
- [ ] Chronométrage en direct
