# 🎬 Score Overlay OBS - Vue d'ensemble

## 📺 Qu'est-ce que c'est ?

Un **overlay de score en direct** pour OBS Studio qui affiche les scores des matchs de hockey salle en temps réel, directement sur votre flux de streaming.

**Utilisation idéale:**
- 🎬 Streamers (Twitch, YouTube)
- 📺 Diffusion d'événements sportifs
- 📊 Affichage public en salle (écran TV)
- 🏑 Retransmission de matchs

---

## 🚀 Démarrage rapide (2 minutes)

### 1. Lancer l'API

```bash
cd "/Users/qm/Library/CloudStorage/OneDrive-EcolesGaliléoGlobalEducationFrance/CHC - Code/V1 - API"
source .venv/bin/activate
python main.py
```

### 2. Accéder à l'overlay

```
http://localhost:8000/score-overlay.html
```

### 3. Configurer OBS

- Nouvelle source → **Navigateur**
- URL: `http://localhost:8000/score-overlay.html`
- Dimension: `1280 x 200`
- Positionner sur votre vidéo

### 4. Utiliser

1. Sélectionner un championnat
2. Choisir le match
3. Cliquer "🎬 OBS Mode"
4. Les scores se mettent à jour en direct !

---

## 📁 Fichiers du projet

```
├── score-overlay.html              # Page HTML/CSS/JS (overlay)
├── SCORE_OVERLAY_GUIDE.md          # Guide complet d'utilisation
├── main.py                         # API FastAPI
│   └── Route: /score-overlay.html  # Sert le fichier
└── README_OVERLAY.md               # Ce fichier
```

---

## 🎨 Caractéristiques

✅ **Temps réel** - Mise à jour toutes les 5 secondes  
✅ **Transparent** - Fond transparent pour surimpression vidéo  
✅ **Animations** - Flash sur changement de score  
✅ **Responsive** - Adaptable à toute résolution  
✅ **Multi-championnats** - Support de 6 championnats  
✅ **Statuts** - À venir, EN DIRECT, Terminé  
✅ **Contrôles** - Interface simple de sélection  
✅ **Mode OBS** - Masque les contrôles pour le streaming  

---

## 🔄 Flux de données

```
┌─────────────────────────────────┐
│   PAGE OVERLAY (HTML/JS)        │
│  score-overlay.html             │
│                                 │
│  • Polling API (5s)             │
│  • Affichage scores             │
│  • Animations                   │
└────────────┬────────────────────┘
             │
             │ GET /api/v1/live/matches
             │ ?championship=elite-hommes
             │
┌────────────▼────────────────────┐
│      API FASTAPI (main.py)      │
│                                 │
│  • Récupère matchs Firebase     │
│  • Retourne JSON                │
│  • Route: /score-overlay.html   │
│  • Route: /api/v1/live/matches  │
└────────────┬────────────────────┘
             │
             │
┌────────────▼────────────────────┐
│   FIREBASE REALTIME DATABASE    │
│                                 │
│  /matches/{matchId}/            │
│    • score_domicile             │
│    • score_exterieur            │
│    • statut                     │
│    • date                       │
└─────────────────────────────────┘
```

---

## 📊 Championnats supportés

| Champion. | Code | Données |
|-----------|------|---------|
| 🏑 Elite Hommes | `elite-hommes` | ✅ API FFH (90+ matchs) |
| 👩 Elite Femmes | `elite-femmes` | ✅ API FFH (50+ matchs) |
| 🏛️ Salle Elite Femmes | `salle-elite-femmes` | ✅ Manuelles (30 matchs) |
| 🏆 Carquefou 1SH | `carquefou-1sh` | ✅ Cachées |
| Carquefou 2SH | `carquefou-2sh` | ✅ Cachées |
| Carquefou SD | `carquefou-sd` | ✅ Cachées |

---

## 🎬 Configuration OBS Avancée

### Petite bande (score uniquement)
```
Dimension: 1280 x 100
Position: Haut, centré
```

### Bande moyenne (score + détails)
```
Dimension: 1280 x 200
Position: Haut, centré
```

### Grand affichage
```
Dimension: 1920 x 300
Position: Tiers inférieur
```

### Avec filtres OBS
- Ombre chère: Ajouter du relief
- Flou: Légèrement pour lisser
- Couleur: Ajuster si besoin

---

## 🔧 Customization

### Modifier les couleurs

Dans `score-overlay.html`, section `<style>`:

```css
/* Couleur primaire (équipe domicile) */
#00d084  → Votre couleur

/* Couleur secondaire (équipe extérieure) */
#f5576c  → Votre couleur
```

### Modifier l'intervalle de polling

```javascript
const POLL_INTERVAL = 5000;  // 5 secondes
// Changer à 10000 pour 10 secondes
```

### Ajouter logos d'équipes

```html
<img src="logo-url.png" class="team-logo">
```

---

## 📱 API utilisée

### Endpoint principal

```
GET /api/v1/live/matches?championship={championship}
```

**Réponse:**
```json
{
  "success": true,
  "matches": [
    {
      "id": "unique-id",
      "equipe_domicile": "Team A",
      "equipe_exterieur": "Team B",
      "score_domicile": "2",
      "score_exterieur": "1",
      "date": "2025-12-13 13:00:00",
      "statut": "LIVE"
    }
  ]
}
```

### Statuts disponibles
- `SCHEDULED`: ⏳ À venir
- `LIVE`: 🔴 EN DIRECT
- `FINISHED`: ✅ Terminé
- `PAUSED`: ⏸️ Suspendu

---

## 🐛 Dépannage

| Problème | Solution |
|----------|----------|
| Overlay pas visible | Vérifier que l'API est lancée |
| Pas de score | Sélectionner un championnat ET un match |
| Scores non mis à jour | Vérifier l'indicateur statut (vert = OK) |
| CORS erreur | L'API doit avoir CORS activés (déjà configuré) |
| Fichier non trouvé | `score-overlay.html` doit être à la racine du projet |

---

## 📚 Documentation complète

Pour un guide détaillé (configuration OBS, personnalisation, cas d'usage avancés):

👉 Voir: [`SCORE_OVERLAY_GUIDE.md`](./SCORE_OVERLAY_GUIDE.md)

---

## 💡 Cas d'usage

### Streaming Twitch
1. OBS + Score Overlay
2. Ajouter la source navigateur
3. Cliquer "🎬 OBS Mode"
4. Streamer avec les scores en direct

### Événement sportif
1. PC avec affichage fullscreen overlay
2. TV en salle affichant les scores
3. Mise à jour automatique

### Analyse/Production
1. Plusieurs PC avec différents matchs
2. Synchronisation temps réel
3. Dashboard de scoring

---

## 🔐 Sécurité

- ✅ Pas de données sensibles dans l'overlay
- ✅ Lecture seule (pas de modification possible)
- ✅ Accessible en local (pas d'exposition publique requise)
- ✅ CORS bien configurés

---

## 🚀 Prochaines améliorations

- [ ] Affichage des buteurs et assistants
- [ ] Timeline des événements (buts, cartons)
- [ ] Son de notification à la fin d'un but
- [ ] Classement en direct (3 equipes top)
- [ ] Multi-matchs simultanés
- [ ] Classements live
- [ ] Statistiques avancées
- [ ] Contrôle API distance

---

## ✅ Checklist avant streaming

- [ ] API en cours d'exécution
- [ ] Overlay accessible: `http://localhost:8000/score-overlay.html`
- [ ] Championnat sélectionné
- [ ] Match sélectionné
- [ ] Source navigateur créée dans OBS
- [ ] Dimension correcte (1280x200 conseillé)
- [ ] Fond transparent bien visible
- [ ] Indicateur statut 🟢 vert
- [ ] "🎬 OBS Mode" activé
- [ ] Test du polling (vérifier mise à jour)
- [ ] Prêt pour streaming! 🎬

---

## 📞 Support

En cas de problème:
1. Vérifier les logs API: `python main.py`
2. Ouvrir la console du navigateur (F12)
3. Vérifier la connexion réseau
4. Redémarrer l'API
5. Consulter le guide complet: [`SCORE_OVERLAY_GUIDE.md`](./SCORE_OVERLAY_GUIDE.md)

---

## 📄 Licence

Cette solution fait partie de l'API FFHockey. Disponible pour usage interne à Carquefou HC.

---

**Bon streaming! 🎬🏑**
