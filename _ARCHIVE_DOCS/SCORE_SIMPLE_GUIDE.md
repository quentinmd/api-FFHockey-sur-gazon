# 🎬 Score Simple - URL Overlay Prête à l'emploi

## ⚡ Usage ultra-simple

L'API fournit une URL prête à copier/coller dans OBS. **Pas d'interface, juste le score.**

```
http://localhost:8000/score-simple.html
```

---

## 📋 Formats disponibles

### 1️⃣ Score par défaut (Premier match Elite Hommes)
```
http://localhost:8000/score-simple.html
```
✅ Affiche le premier match d'Elite Hommes  
✅ Se met à jour automatiquement (5 sec)

### 2️⃣ Score d'un match spécifique (par ID)
```
http://localhost:8000/score-simple.html?championship=elite-hommes&match_id=match_001
```
Paramètres:
- `championship`: elite-hommes, elite-femmes, salle-elite-femmes, carquefou-1sh, carquefou-2sh, carquefou-sd
- `match_id`: L'ID du match dans votre système

### 3️⃣ Score par RencId (ID FFH)
```
http://localhost:8000/score-simple.html?renc_id=12345
```
✅ Affiche le match avec ce rencId  
✅ Plus facile si vous avez le numéro FFH

---

## 🎬 Intégration OBS

### Étape 1 : Ajouter source
```
OBS → Ajouter source → Navigateur
```

### Étape 2 : Configuration
```
Name: Score Hockey
URL: http://localhost:8000/score-simple.html
Width: 1280
Height: 200
```

### Étape 3 : Positionner
```
Placer l'overlay où vous voulez sur la vidéo
```

### Étape 4 : C'est parti!
```
✅ Score affichée et mise à jour en direct
```

---

## 🎨 Caractéristiques

✅ **Fond transparent** - Parfait pour OBS  
✅ **Auto-update** - Toutes les 5 secondes  
✅ **Animations** - Flash sur changement de score  
✅ **Responsive** - S'adapte à toutes les résolutions  
✅ **Simple** - Juste le score, rien d'autre  
✅ **Sans contrôles** - Pas de dropdown, pas de bouton  

---

## 📊 Exemple d'URL pour chaque championnat

```bash
# Elite Hommes (premier match)
http://localhost:8000/score-simple.html?championship=elite-hommes

# Elite Femmes (premier match)
http://localhost:8000/score-simple.html?championship=elite-femmes

# Salle Elite Femmes (premier match)
http://localhost:8000/score-simple.html?championship=salle-elite-femmes

# Carquefou 1SH (premier match)
http://localhost:8000/score-simple.html?championship=carquefou-1sh

# Carquefou 2SH (premier match)
http://localhost:8000/score-simple.html?championship=carquefou-2sh

# Carquefou SD (premier match)
http://localhost:8000/score-simple.html?championship=carquefou-sd
```

---

## 🔄 Comment ça fonctionne

```
┌─────────────────────────────────┐
│  OBS (Source Navigateur)        │
│  URL: score-simple.html         │
│                                 │
│  Team A    2 — 1    Team B      │
│  03/11 13:00                    │
└────────────┬────────────────────┘
             │
   Polling API (5 sec)
             │
┌────────────▼────────────────────┐
│  API FastAPI (main.py)          │
│  GET /api/v1/live/matches       │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│  Firebase                       │
│  /matches/{matchId}/            │
│  score_domicile: 2              │
│  score_exterieur: 1             │
│  equipe_domicile: "Team A"      │
│  equipe_exterieur: "Team B"     │
└─────────────────────────────────┘
```

---

## 💡 Cas d'usage

### Streaming simple
```
Copiez l'URL dans OBS et le score s'affiche en direct
```

### Multi-matchs
```
Créer plusieurs sources OBS avec URLs différentes
Chacune affiche un match différent
```

### Full-screen overlay
```
Score-simple.html en fullscreen sur un second écran
Affichage public du score
```

---

## ✅ Vérification rapide

1. Lancer l'API: `python main.py`
2. Ouvrir dans navigateur: `http://localhost:8000/score-simple.html`
3. Vous devriez voir le score du premier match
4. Copier l'URL dans OBS!

---

## 🎨 Personnalisation

Pour modifier:
- Les couleurs
- L'intervalle de polling (5 sec)
- La taille de la police

Éditez directement `score-simple.html`:

```javascript
// Modifier intervalle (ms)
const POLL_INTERVAL = 5000; // 5 sec

// Modifier couleurs
#00d084 → votre couleur primaire
#f5576c → votre couleur secondaire
```

---

## 📞 Support

| Besoin | Solution |
|--------|----------|
| Score d'Elite Hommes | `?championship=elite-hommes` |
| Score d'un match spécifique | `?match_id=match_001` |
| Score par RencId | `?renc_id=12345` |
| Modifier couleurs | Éditer score-simple.html |
| Modifier polling | Chercher POLL_INTERVAL |

---

## 🚀 Prêt!

```
1. python main.py
2. http://localhost:8000/score-simple.html
3. Copier URL dans OBS
4. 🎬 Streamer!
```

Bon streaming! 🏑✨
