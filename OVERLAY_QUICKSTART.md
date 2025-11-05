# 🎬 QUICK START - Score Overlay OBS

## ⏱️ 2 minutes pour avoir votre overlay en direct

### Étape 1️⃣ : Lancer l'API (20 sec)

```bash
# Terminal 1: Aller au dossier
cd "/Users/qm/Library/CloudStorage/OneDrive-EcolesGaliléoGlobalEducationFrance/CHC - Code/V1 - API"

# Activer l'environnement virtuel
source .venv/bin/activate

# Lancer l'API
python main.py
```

✅ L'API est maintenant en cours d'exécution sur `http://localhost:8000`

---

### Étape 2️⃣ : Ouvrir l'overlay (5 sec)

Ouvrir dans votre navigateur :

```
http://localhost:8000/score-overlay.html
```

✅ Vous devriez voir une page avec "🎬 Prêt pour OBS"

---

### Étape 3️⃣ : Sélectionner un match (20 sec)

1. **Championnat** → Choisir `🏑 Elite Hommes` (ou autre)
2. **Match à afficher** → S'auto-remplit, choisir le premier
3. **Résultat** → Vous voyez le score et les équipes !

---

### Étape 4️⃣ : Configurer OBS (40 sec)

#### Si vous n'avez pas OBS encore
- Télécharger: https://obsproject.com
- Installer et lancer

#### Ajouter la source

1. **OBS Studio → Ajouter source (+)**
2. **Type:** Navigateur (Browser)
3. **Remplir:**
   - Nom: `Score Hockey`
   - URL: `http://localhost:8000/score-overlay.html`
   - Largeur: `1280`
   - Hauteur: `200`
4. **OK**

#### Positionner

1. Glisser le score sur votre vidéo
2. Redimensionner si besoin
3. Appuyer sur "🎬 OBS Mode" pour masquer les contrôles

✅ Votre overlay de score est maintenant en direct!

---

## 🎬 Vous êtes prêt!

| Action | Résultat |
|--------|----------|
| **Championnat change** | Scores se mettent à jour |
| **Match change** | Nouvel overlay immédiat |
| **Goal marqué** | Animation flash 💥 |
| **Statut change** | "EN DIRECT" / "Terminé" |

---

## 🎯 Cas d'usage communs

### Twitch/YouTube Streaming
```
OBS → Scène avec vidéo + overlay score sur le côté
→ Streamer normalement
→ Overlay se met à jour en direct
```

### Événement en salle
```
PC connecté en fullscreen
→ Navigateur en fullscreen avec overlay
→ TV/écran affiche les scores
```

### Production d'événement
```
Multi-sources dans OBS
→ Caméras + overlay score
→ Switcher entre les caméras
→ Overlay toujours visible
```

---

## 🔧 Petits problèmes?

| Problème | Solution |
|----------|----------|
| **Pas de score** | Vous avez sélectionné un match? |
| **"Prêt pour OBS"** | Sélectionner un championnat + match |
| **Ne se met pas à jour** | Vérifier le 🟢 statut (vert = OK) |
| **OBS pas d'image** | Réachargez la page (F5) |
| **API ne démarre pas** | `.venv/bin/activate` activé? |

---

## 📚 Besoin de plus?

- Guide complet: [`SCORE_OVERLAY_GUIDE.md`](./SCORE_OVERLAY_GUIDE.md)
- Vue d'ensemble: [`README_OVERLAY.md`](./README_OVERLAY.md)
- Code HTML/JS: [`score-overlay.html`](./score-overlay.html)

---

## ✅ Checklist rapide

- [ ] API lancée (`python main.py`)
- [ ] Overlay accessible (`http://localhost:8000/score-overlay.html`)
- [ ] Championnat + match sélectionnés
- [ ] Source navigateur dans OBS
- [ ] Positionnement sur vidéo OK
- [ ] Score visible ✅
- [ ] "🎬 OBS Mode" cliqué
- [ ] 🎬 C'est parti!

---

## 🚀 Bon streaming!

```
╔════════════════════════════════════╗
║  🏑 HOCKEY SALLE OVERLAY READY 🏑  ║
║                                    ║
║  Scores en direct sur votre flux   ║
║  Temps réel   •   Professionnel    ║
║  Transparent  •   Animé            ║
╚════════════════════════════════════╝
```

Cliquez sur "🎬 OBS Mode" et c'est parti! 🎬
