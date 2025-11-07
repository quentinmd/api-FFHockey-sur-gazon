import React, { useState, useEffect } from 'react';
import { ref, get, onValue, update } from 'firebase/database';
import { database } from '../config/firebaseConfig';
import apiConfig from '../config/apiConfig';
import '../styles/LiveScoreAdminV2.css';

export default function LiveScoreAdminV2() {
  const [adminPassword, setAdminPassword] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [matches, setMatches] = useState([]);
  const [filteredMatches, setFilteredMatches] = useState([]);
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [selectedChampionship, setSelectedChampionship] = useState('all');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [customManifId, setCustomManifId] = useState('');
  const [homeTeam, setHomeTeam] = useState('');
  const [awayTeam, setAwayTeam] = useState('');
  const [formData, setFormData] = useState({
    score_domicile: 0,
    score_exterieur: 0,
    joueur: '',
    equipe: 'domicile',
    temps: 0,
    couleur: 'jaune'
  });

  // Championnats disponibles (U14 terminés - enlever du dashboard)
  const championships = [
    { id: 'all', label: '📋 Tous les matchs' },
    { id: 'elite-hommes', label: '🏑 Elite Hommes' },
    { id: 'elite-femmes', label: '👩 Elite Femmes' },
    { id: 'carquefou-1sh', label: '🏆 Carquefou 1SH' },
    { id: 'carquefou-2sh', label: 'Carquefou 2SH' },
    { id: 'carquefou-sd', label: 'Carquefou SD' },
    { id: 'salle-elite-femmes', label: '🏛️ Salle Elite Femmes' }
  ];

  // Couleurs de cartons
  const cardColors = [
    { value: 'vert', label: '🟢 Vert' },
    { value: 'jaune', label: '🟡 Jaune' },
    { value: 'rouge', label: '🔴 Rouge' }
  ];

  // Charger les matchs depuis Firebase en temps réel
  useEffect(() => {
    if (!isAuthenticated) return;

    const matchesRef = ref(database, 'matches');
    const unsubscribe = onValue(matchesRef, (snapshot) => {
      if (snapshot.exists()) {
        const data = Object.entries(snapshot.val()).map(([id, match_data]) => ({
          id,
          ...match_data
        }));
        setMatches(data);
        filterMatches(data, selectedChampionship);
      } else {
        setMatches([]);
        setFilteredMatches([]);
      }
    }, (error) => {
      console.error('Erreur Firebase:', error);
      setMessage('❌ Erreur chargement matchs: ' + error.message);
    });

    return () => unsubscribe();
  }, [isAuthenticated, selectedChampionship]);

  // Filtrer les matchs par championnat
  const filterMatches = (allMatches, championship) => {
    if (championship === 'all') {
      setFilteredMatches(allMatches);
    } else {
      setFilteredMatches(
        allMatches.filter(m => m.championship === championship)
      );
    }
  };

  // Authentification
  const handleLogin = (e) => {
    e.preventDefault();
    if (adminPassword === 'admin123') {
      setIsAuthenticated(true);
      setMessage('✅ Authentifié');
    } else {
      setMessage('❌ Mot de passe incorrect');
    }
  };

  // Déconnexion
  const handleLogout = () => {
    setIsAuthenticated(false);
    setAdminPassword('');
    setSelectedMatch(null);
    setMessage('');
  };

  // Importer matchs d'un championnat
  const handleImportChampionship = async () => {
    if (!selectedChampionship || selectedChampionship === 'all') {
      setMessage('❌ Sélectionnez un championnat');
      return;
    }

    setLoading(true);
    try {
      // Utiliser l'endpoint des VRAIS matchs pour charger les données réelles
      const response = await fetch(
        `${apiConfig.endpoints.importRealData}/${selectedChampionship}?admin_token=${apiConfig.adminPassword}`,
        { 
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }
      );
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        const champLabel = championships.find(c => c.id === selectedChampionship)?.label || selectedChampionship;
        let detailMessage = `✅ ${data.imported_count} VRAIS matchs importés pour ${champLabel}!`;
        if (data.skipped_duplicates > 0) {
          detailMessage += ` (${data.skipped_duplicates} doublons ignorés)`;
        }
        setMessage(detailMessage);
      } else {
        setMessage(`❌ ${data.detail || 'Erreur lors de l\'import'}`);
      }
    } catch (error) {
      console.error('Erreur import:', error);
      setMessage('❌ Erreur: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Mettre à jour le score
  const updateScore = async () => {
    if (!selectedMatch) return;

    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/live/match/${selectedMatch.id}/score?admin_token=admin123`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            score_domicile: parseInt(formData.score_domicile),
            score_exterieur: parseInt(formData.score_exterieur)
          })
        }
      );
      const data = await response.json();
      setMessage(data.success ? '✅ Score mis à jour' : '❌ Erreur: ' + data.detail);
    } catch (error) {
      setMessage('❌ Erreur: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Ajouter un buteur
  const addScorer = async () => {
    if (!selectedMatch || !formData.joueur) {
      setMessage('❌ Remplissez tous les champs');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/live/match/${selectedMatch.id}/scorer?admin_token=admin123`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            joueur: formData.joueur,
            equipe: formData.equipe,
            temps: parseInt(formData.temps)
          })
        }
      );
      const data = await response.json();
      
      if (data.success) {
        setMessage('✅ Buteur ajouté');
        setFormData({ ...formData, joueur: '', temps: 0 });
      } else {
        setMessage('❌ Erreur: ' + data.detail);
      }
    } catch (error) {
      setMessage('❌ Erreur: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Ajouter un carton
  const addCard = async () => {
    if (!selectedMatch || !formData.joueur) {
      setMessage('❌ Remplissez tous les champs');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/live/match/${selectedMatch.id}/card?admin_token=admin123`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            joueur: formData.joueur,
            equipe: formData.equipe,
            temps: parseInt(formData.temps),
            couleur: formData.couleur
          })
        }
      );
      const data = await response.json();
      
      if (data.success) {
        setMessage('✅ Carton ajouté');
        setFormData({ ...formData, joueur: '', temps: 0 });
      } else {
        setMessage('❌ Erreur: ' + data.detail);
      }
    } catch (error) {
      setMessage('❌ Erreur: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Mettre à jour les noms d'équipes
  const updateTeamNames = async () => {
    if (!selectedMatch || (!homeTeam && !awayTeam)) {
      setMessage('❌ Entrez au moins un nom d\'équipe');
      return;
    }

    setLoading(true);
    try {
      const matchRef = ref(database, `matches/${selectedMatch.id}`);
      const updateData = {};
      
      if (homeTeam) updateData.equipe_domicile = homeTeam;
      if (awayTeam) updateData.equipe_exterieur = awayTeam;
      
      await update(matchRef, updateData);
      
      setMessage('✅ Noms d\'équipes mis à jour');
      setHomeTeam('');
      setAwayTeam('');
      
      // Actualiser le match sélectionné
      if (homeTeam) selectedMatch.equipe_domicile = homeTeam;
      if (awayTeam) selectedMatch.equipe_exterieur = awayTeam;
      
    } catch (error) {
      setMessage('❌ Erreur: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Créer un match avec ManifId personnalisé
  const createCustomMatch = async () => {
    if (!selectedChampionship || selectedChampionship === 'all') {
      setMessage('❌ Sélectionnez un championnat');
      return;
    }
    if (!customManifId || !homeTeam || !awayTeam) {
      setMessage('❌ Entrez ManifId, équipe domicile et équipe extérieur');
      return;
    }

    setLoading(true);
    try {
      const matchId = `${selectedChampionship}_${customManifId}`;
      const matchRef = ref(database, `matches/${matchId}`);
      
      const newMatch = {
        equipe_domicile: homeTeam,
        equipe_exterieur: awayTeam,
        score_domicile: 0,
        score_exterieur: 0,
        scorers: [],
        cards: [],
        statut: 'SCHEDULED',
        championship: selectedChampionship,
        date: new Date().toISOString().split('T')[0] + ' 20:00:00',
        rencId: customManifId,
        last_updated: Math.floor(Date.now() / 1000)
      };

      await update(matchRef, newMatch);
      
      setMessage(`✅ Match créé: ${homeTeam} vs ${awayTeam} (ID: ${customManifId})`);
      setCustomManifId('');
      setHomeTeam('');
      setAwayTeam('');
    } catch (error) {
      console.error('Erreur création:', error);
      setMessage('❌ Erreur: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="auth-container">
        <div className="auth-box">
          <h2>🔐 Admin Live Score</h2>
          <form onSubmit={handleLogin}>
            <input
              type="password"
              placeholder="Mot de passe admin"
              value={adminPassword}
              onChange={(e) => setAdminPassword(e.target.value)}
            />
            <button type="submit">Se connecter</button>
          </form>
          {message && <p className={message.includes('❌') ? 'error' : 'success'}>{message}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="live-score-admin-v2">
      <div className="header">
        <h1>⚽ Dashboard Admin Live Score</h1>
        <button onClick={handleLogout} className="logout-btn">Déconnexion</button>
      </div>

      {message && (
        <div className={`message ${message.includes('❌') ? 'error' : 'success'}`}>
          {message}
        </div>
      )}

      {/* Section Import */}
      <div className="section import-section">
        <h2>📥 Importer des matchs</h2>
        <div className="import-controls">
          <select
            value={selectedChampionship}
            onChange={(e) => {
              setSelectedChampionship(e.target.value);
              filterMatches(matches, e.target.value);
            }}
          >
            {championships.map(c => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>
          <button 
            onClick={handleImportChampionship}
            disabled={loading}
            className="import-btn"
          >
            {loading ? '⏳ Chargement...' : '🏒 IMPORTER VRAIS MATCHS'}
          </button>
        </div>
      </div>

      {/* Section Créer Match Personnalisé */}
      <div className="section custom-match-section">
        <h2>➕ Créer un match personnalisé</h2>
        <div className="custom-match-form">
          <select
            value={selectedChampionship}
            onChange={(e) => setSelectedChampionship(e.target.value)}
            disabled={loading}
          >
            {championships.filter(c => c.id !== 'all').map(c => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="ManifId personnalisé (ex: match-001)"
            value={customManifId}
            onChange={(e) => setCustomManifId(e.target.value)}
            disabled={loading}
          />
          <input
            type="text"
            placeholder="Équipe domicile"
            value={homeTeam}
            onChange={(e) => setHomeTeam(e.target.value)}
            disabled={loading}
          />
          <input
            type="text"
            placeholder="Équipe extérieur"
            value={awayTeam}
            onChange={(e) => setAwayTeam(e.target.value)}
            disabled={loading}
          />
          <button
            onClick={createCustomMatch}
            disabled={loading}
            className="create-match-btn"
          >
            {loading ? '⏳ Création...' : '✨ Créer le match'}
          </button>
        </div>
      </div>

      <div className="main-content">
        {/* Liste des matchs */}
        <div className="section matches-section">
          <h2>📋 Matchs ({filteredMatches.length})</h2>
          <div className="matches-list">
            {filteredMatches.map(match => (
              <div
                key={match.id}
                className={`match-card ${selectedMatch?.id === match.id ? 'selected' : ''}`}
                onClick={() => {
                  setSelectedMatch(match);
                  setFormData({ ...formData, score_domicile: match.score_domicile, score_exterieur: match.score_exterieur });
                }}
              >
              <div className="score">
                <div className="score-top">
                  <span className="team-home">{match.equipe_domicile}</span>
                  <span className="score-text">{match.score_domicile} - {match.score_exterieur}</span>
                </div>
                <span className="team-away">{match.equipe_exterieur}</span>
              </div>
              <div className="status">{match.statut}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Détails du match */}
        {selectedMatch && (
          <div className="section match-details">
            <h2>⚙️ Détails du match</h2>

            {/* Noms d'équipes */}
            <div className="team-names">
              <h3>👥 Noms des équipes</h3>
              <div className="form-group">
                <input
                  type="text"
                  placeholder="Équipe domicile"
                  value={homeTeam || selectedMatch.equipe_domicile}
                  onChange={(e) => setHomeTeam(e.target.value)}
                />
                <input
                  type="text"
                  placeholder="Équipe extérieur"
                  value={awayTeam || selectedMatch.equipe_exterieur}
                  onChange={(e) => setAwayTeam(e.target.value)}
                />
                <button onClick={updateTeamNames} disabled={loading}>💾 Enregistrer</button>
              </div>
            </div>

            {/* Scores */}
            <div className="score-editor">
              <h3>📊 Scores</h3>
              <div className="form-group">
                <div className="input-group">
                  <label>Domicile</label>
                  <input
                    type="number"
                    min="0"
                    value={formData.score_domicile}
                    onChange={(e) => setFormData({ ...formData, score_domicile: e.target.value })}
                  />
                </div>
                <div className="input-group">
                  <label>Extérieur</label>
                  <input
                    type="number"
                    min="0"
                    value={formData.score_exterieur}
                    onChange={(e) => setFormData({ ...formData, score_exterieur: e.target.value })}
                  />
                </div>
                <button onClick={updateScore} disabled={loading}>✅ Mettre à jour</button>
              </div>
            </div>

            {/* Buteurs */}
            <div className="scorers-section">
              <h3>⚽ Buteurs</h3>
              <div className="form-group">
                <input
                  type="text"
                  placeholder="Nom du joueur"
                  value={formData.joueur}
                  onChange={(e) => setFormData({ ...formData, joueur: e.target.value })}
                />
                <select
                  value={formData.equipe}
                  onChange={(e) => setFormData({ ...formData, equipe: e.target.value })}
                >
                  <option value="domicile">Domicile</option>
                  <option value="exterieur">Extérieur</option>
                </select>
                <input
                  type="number"
                  placeholder="Temps (min)"
                  min="0"
                  max="90"
                  value={formData.temps}
                  onChange={(e) => setFormData({ ...formData, temps: e.target.value })}
                />
                <button onClick={addScorer} disabled={loading}>⚽ Ajouter</button>
              </div>
              <div className="scorers-list">
                {selectedMatch.scorers?.map((scorer, idx) => (
                  <div key={idx} className="scorer-badge">
                    <span className="badge-team" style={{
                      backgroundColor: scorer.equipe === 'domicile' ? '#667eea' : '#764ba2'
                    }}>
                      {scorer.equipe === 'domicile' ? '🏠' : '🚌'}
                    </span>
                    <span className="badge-text">{scorer.joueur} ({scorer.temps}\')</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Cartons */}
            <div className="cards-section">
              <h3>🟡 Cartons</h3>
              <div className="form-group">
                <input
                  type="text"
                  placeholder="Nom du joueur"
                  value={formData.joueur}
                  onChange={(e) => setFormData({ ...formData, joueur: e.target.value })}
                />
                <select
                  value={formData.equipe}
                  onChange={(e) => setFormData({ ...formData, equipe: e.target.value })}
                >
                  <option value="domicile">Domicile</option>
                  <option value="exterieur">Extérieur</option>
                </select>
                <input
                  type="number"
                  placeholder="Temps (min)"
                  min="0"
                  max="90"
                  value={formData.temps}
                  onChange={(e) => setFormData({ ...formData, temps: e.target.value })}
                />
                <select
                  value={formData.couleur}
                  onChange={(e) => setFormData({ ...formData, couleur: e.target.value })}
                >
                  {cardColors.map(c => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
                <button onClick={addCard} disabled={loading}>🟡 Ajouter</button>
              </div>
              <div className="cards-list">
                {selectedMatch.cards?.map((card, idx) => (
                  <div key={idx} className={`card-badge card-${card.couleur}`}>
                    <span className="badge-team" style={{
                      backgroundColor: card.equipe === 'domicile' ? '#667eea' : '#764ba2'
                    }}>
                      {card.equipe === 'domicile' ? '🏠' : '🚌'}
                    </span>
                    <span className="badge-text">{card.joueur} ({card.temps}\')</span>
                    <span className={`card-color card-${card.couleur}`}></span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
