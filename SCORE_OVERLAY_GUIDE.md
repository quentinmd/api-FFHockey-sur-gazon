# 🎬 Guide OBS Score Overlay - Hockey Salle

## 📺 Vue d'ensemble

Cet overlay affiche les scores en direct des matchs de hockey salle depuis votre API FFHockey. Il est conçu pour être intégré dans OBS Studio en tant que source navigateur.

**Caractéristiques:**
- ✅ Affichage temps réel du score
- ✅ Animations fluides sur les changements de score
- ✅ Sélection du match à afficher
- ✅ Fond transparent pour la surimpression vidéo
- ✅ Responsive et prêt pour OBS
- ✅ Indicateur de statut de connexion

---

## 🚀 Mise en place rapide

### Étape 1 : Vérifier que l'API fonctionne

```bash
# Depuis le dossier du projet
cd "/Users/qm/Library/CloudStorage/OneDrive-EcolesGaliléoGlobalEducationFrance/CHC - Code/V1 - API"

# Lancer l'API
source .venv/bin/activate
python main.py
```

L'API doit être accessible sur `http://localhost:8000`

### Étape 2 : Accéder à l'overlay

**Localement (développement):**
```
http://localhost:8000/score-overlay.html
```

**Sur le réseau (pour OBS depuis un autre PC):**
```
http://<votre-ip>:8000/score-overlay.html
```

Pour trouver votre IP :
```bash
# macOS/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig
```

### Étape 3 : Configurer dans OBS

1. **Ouvrir OBS Studio**
2. **Ajouter une nouvelle source :**
   - Clic droit sur votre scène → Ajouter une source
   - Sélectionner **Navigateur** (Browser)
   
3. **Configurer la source :**
   - Nom: `Score Overlay Hockey`
   - URL: `http://localhost:8000/score-overlay.html`
   - Largeur: `1280`
   - Hauteur: `200`
   - Cocher: ✅ "Rafraîchir la page quand celle-ci n'est pas visible"

4. **Positionner sur l'overlay vidéo :**
   - Déplacer et redimensionner comme vous le souhaitez
   - Le fond transparent s'adapte automatiquement

5. **Mode plein écran OBS (optionnel) :**
   - Cliquer sur le bouton "🎬 OBS Mode" dans l'overlay
   - Les contrôles se cachent, parfait pour le streaming !

---

## 🎨 Guide d'utilisation

### Contrôles

**1. Sélectionner un championnat** 
- Dropdown "Championnat"
- Championnats disponibles:
  - 🏑 Elite Hommes
  - 👩 Elite Femmes
  - 🏛️ Salle Elite Femmes
  - 🏆 Carquefou 1SH
  - Carquefou 2SH
  - Carquefou SD

**2. Sélectionner le match**
- Dropdown "Match à afficher"
- S'auto-remplit en fonction du championnat
- Le premier match est auto-sélectionné

**3. Mode OBS**
- Bouton "🎬 OBS Mode"
- Masque les contrôles et passe en fullscreen
- Idéal pour le streaming en direct

### Affichage du score

**Format:**
```
ÉQUIPE DOMICILE  |  SCORE  |  ÉQUIPE EXTÉRIEURE
                    00 — 00
              Date et statut du match
```

**Statuts affichés:**
- ⏳ À venir (SCHEDULED)
- 🔴 EN DIRECT (LIVE) - Animation pulsante
- ✅ Terminé (FINISHED)
- ⏸️ Suspendu (PAUSED)

**Couleurs:**
- 🟢 Équipe domicile : Vert (#00d084)
- 🔴 Équipe extérieure : Rouge (#f5576c)
- Animations sur changement de score

---

## 🔄 Mise à jour temps réel

L'overlay **interroge l'API automatiquement toutes les 5 secondes** pour:
- Mettre à jour les scores
- Vérifier les changements de statut
- Détecter les nouveaux buts (animation)

**Indicateur de statut :**
- 🟢 Vert : Connecté
- 🟠 Orange : Chargement
- 🔴 Rouge : Erreur

Situé en haut à droite de l'écran.

---

## 🎬 Configuration OBS avancée

### 1. Optimiser les performances

Si l'overlay ralentit OBS :
- Réduire la largeur/hauteur de la source navigateur
- Augmenter le `POLL_INTERVAL` dans le code (actuellement 5000ms)
- Cocher "Utiliser des sources GPU" dans les paramètres OBS

### 2. Adapter l'apparence

**Modifier les dimensions dans OBS :**
- Petite bande : 1280 × 100
- Bande moyenne : 1280 × 180
- Grand affichage : 1920 × 250

**Adapter à votre résolution vidéo :**
- 1080p: 1280 × 200
- 720p: 960 × 150
- 480p: 640 × 100

### 3. Ajouter des filtres OBS

- **Couleur** : Ajuster la teinte si besoin
- **Flou** : Légèrement pour lisser les bords
- **Ombre** : Ajouter du relief au texte

---

## 🛠️ Personnalisation du code

### Modifier l'intervalle de polling

Dans `score-overlay.html`, ligne ~270:
```javascript
const POLL_INTERVAL = 5000; // 5 secondes
// Changer à : const POLL_INTERVAL = 10000; // 10 secondes
```

### Modifier les couleurs

Dans la section `<style>`, modifiez :
```css
/* Couleur vert par défaut */
--primary-color: #00d084;

/* Couleur rouge équipe extérieure */
--secondary-color: #f5576c;
```

### Ajouter vos logos d'équipes

Modifiez le template HTML pour ajouter des images :
```html
<div class="team domicile">
    <img src="logo-domicile.png" class="team-logo">
    <div class="team-name">${currentMatch.equipe_domicile}</div>
</div>
```

---

## 📱 Cas d'usage

### Streaming Twitch/YouTube
1. Ouvrir OBS avec votre vidéo
2. Ajouter l'overlay score
3. Positionner sur la vidéo (haut, bas, coin)
4. Cliquer "🎬 OBS Mode" pour masquer les contrôles
5. Lancer le stream !

### Affichage en salle
1. Configurer un PC/Raspberry avec l'URL de l'overlay
2. Afficher en fullscreen sur un écran TV
3. Maintient les scores à jour en temps réel

### Production d'événement
1. Utiliser OBS avec plusieurs sources (vidéo + caméras)
2. Ajouter l'overlay score sur la sortie principale
3. Switcher entre les caméras normalement
4. L'overlay reste visible et à jour

---

## 🐛 Dépannage

### L'overlay ne s'affiche pas

**Vérifier:**
1. L'API est lancée? Tester `curl http://localhost:8000/api/v1/live/matches`
2. L'URL est correcte? Vérifier la barre d'adresse
3. Un championnat est sélectionné? Sinon, message "Prêt pour OBS"
4. Console OBS : Vérifier les erreurs (F12 dans le navigateur)

### Le score ne se met pas à jour

**Vérifier:**
1. L'indicateur de statut est vert ?
2. Un match est sélectionné ?
3. Vérifier la console (F12) pour les erreurs CORS

### Les animations ne s'affichent pas

Vérifier que votre navigateur supporte les CSS animations :
- Chrome 43+ ✅
- Firefox 16+ ✅
- Safari 9+ ✅
- Edge 12+ ✅

---

## 📊 Structure API utilisée

L'overlay consomme :

```
GET /api/v1/live/matches?championship={championship}
```

**Réponse attendue:**
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

---

## 🔐 Sécurité

- ⚠️ L'overlay ne nécessite **pas d'authentification** pour afficher les scores
- Les scores sont en **lecture seule**
- Aucune modification de données possible via l'overlay
- Le token admin est **stocké localement** (n'est pas utilisé actuellement)

---

## 📈 Prochaines évolutions

- [ ] Affichage des buteurs
- [ ] Timeline des événements (buts, cartons)
- [ ] Son de notification à la fin d'un but
- [ ] Classement en direct (3 équipes en tête)
- [ ] Multi-matchs (affichage parallèle de plusieurs scores)
- [ ] Intégration statistiques avancées
- [ ] API pour contrôler l'overlay à distance

---

## ✅ Checklist avant streaming

- [ ] API lancée et accessible
- [ ] Score-overlay.html accessible
- [ ] Source navigateur créée dans OBS
- [ ] Championnat sélectionné
- [ ] Match en cours de sélection
- [ ] Fond transparent bien positionné
- [ ] Indicateur statut vert (🟢 connecté)
- [ ] Test du polling (vérifier que les scores se mettent à jour)
- [ ] "🎬 OBS Mode" cliqué pour masquer les contrôles
- [ ] 🎬 C'est parti!

---

## 📞 Support

Pour toute question ou suggestion :
- Vérifier le console (F12 / Outils de développement)
- Consulter les logs de l'API
- Vérifier la connectivité réseau
- Relancer l'API et OBS

Bon streaming ! 🎬🏑
