import React, { useState, useEffect } from 'react';
import { ref, get, update } from 'firebase/database';
import { database } from '../config/firebaseConfig';
import '../styles/LiveScoreAdmin.css';

export default function LiveScoreAdmin() {
  const [adminPassword, setAdminPassword] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [matches, setMatches] = useState([]);
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [formData, setFormData] = useState({
    score_domicile: 0,
    score_exterieur: 0,
    joueur: '',
    equipe: 'domicile',
    temps: 0,
    couleur: 'jaune'
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  // Charger les matchs depuis Firebase
  const loadMatches = async () => {
    try {
      const matchesRef = ref(database, 'matches');
      const snapshot = await get(matchesRef);
      if (snapshot.exists()) {
        setMatches(Object.entries(snapshot.val()).map(([id, data]) => ({ id, ...data })));
      }
    } catch (error) {
      console.error('Erreur chargement matchs:', error);
      setMessage('❌ Erreur lors du chargement des matchs');
    }
  };

  // Authentification admin
  const handleLogin = (e) => {
    e.preventDefault();
    // Simple password check (à remplacer par JWT)
    if (adminPassword === 'admin123') {
      setIsAuthenticated(true);
      setMessage('✅ Authentifié');
      loadMatches();
    } else {
      setMessage('❌ Mot de passe incorrect');
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setAdminPassword('');
    setSelectedMatch(null);
    setMessage('');
  };

  // Mettre à jour le score via API
  const updateScore = async () => {
    if (!selectedMatch) return;
    
    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/live/match/${selectedMatch.id}/score?admin_token=${adminPassword}`,
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
      if (data.success) {
        setMessage('✅ Score mis à jour!');
        loadMatches();
      } else {
        setMessage('❌ Erreur: ' + data.detail);
      }
    } catch (error) {
      setMessage('❌ Erreur réseau: ' + error.message);
    }
    setLoading(false);
  };

  // Ajouter un buteur via API
  const addScorer = async () => {
    if (!selectedMatch || !formData.joueur) return;
    
    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/live/match/${selectedMatch.id}/scorer?admin_token=${adminPassword}`,
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
        setMessage('✅ Buteur ajouté!');
        setFormData({ ...formData, joueur: '', temps: 0 });
        loadMatches();
      } else {
        setMessage('❌ Erreur: ' + data.detail);
      }
    } catch (error) {
      setMessage('❌ Erreur réseau: ' + error.message);
    }
    setLoading(false);
  };

  // Ajouter un carton via API
  const addCard = async () => {
    if (!selectedMatch || !formData.joueur) return;
    
    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/live/match/${selectedMatch.id}/card?admin_token=${adminPassword}`,
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
        setMessage('✅ Carton ajouté!');
        setFormData({ ...formData, joueur: '', temps: 0 });
        loadMatches();
      } else {
        setMessage('❌ Erreur: ' + data.detail);
      }
    } catch (error) {
      setMessage('❌ Erreur réseau: ' + error.message);
    }
    setLoading(false);
  };

  if (!isAuthenticated) {
    return (
      <div className="admin-container">
        <div className="login-box">
          <h1>🔐 Dashboard Admin Live Score</h1>
          <form onSubmit={handleLogin}>
            <input
              type="password"
              placeholder="Mot de passe admin"
              value={adminPassword}
              onChange={(e) => setAdminPassword(e.target.value)}
              required
            />
            <button type="submit">Se connecter</button>
          </form>
          {message && <p className="message">{message}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="admin-container">
      <div className="admin-header">
        <h1>🏑 Dashboard Admin Live Score</h1>
        <button className="logout-btn" onClick={handleLogout}>Déconnexion</button>
      </div>

      {message && <p className={`message ${message.includes('✅') ? 'success' : 'error'}`}>{message}</p>}

      <div className="admin-layout">
        {/* Sélection du match */}
        <div className="matches-list">
          <h2>📋 Matchs Disponibles</h2>
          <div className="match-items">
            {matches.map((match) => (
              <div
                key={match.id}
                className={`match-item ${selectedMatch?.id === match.id ? 'active' : ''}`}
                onClick={() => {
                  setSelectedMatch(match);
                  setFormData({
                    score_domicile: match.score_domicile || 0,
                    score_exterieur: match.score_exterieur || 0,
                    joueur: '',
                    equipe: 'domicile',
                    temps: 0,
                    couleur: 'jaune'
                  });
                }}
              >
                <div className="match-score">
                  <strong>{match.equipe_domicile || 'Équipe 1'}</strong>
                  <span className="score">{match.score_domicile || 0} - {match.score_exterieur || 0}</span>
                  <strong>{match.equipe_exterieur || 'Équipe 2'}</strong>
                </div>
                <small>{match.statut || 'SCHEDULED'}</small>
              </div>
            ))}
          </div>
        </div>

        {/* Formulaires de modification */}
        {selectedMatch && (
          <div className="editor-panel">
            <h2>✏️ Éditer: {selectedMatch.equipe_domicile} vs {selectedMatch.equipe_exterieur}</h2>

            {/* Score */}
            <section className="editor-section">
              <h3>📊 Mettre à jour le Score</h3>
              <div className="score-inputs">
                <div>
                  <label>{selectedMatch.equipe_domicile}</label>
                  <input
                    type="number"
                    min="0"
                    value={formData.score_domicile}
                    onChange={(e) => setFormData({ ...formData, score_domicile: e.target.value })}
                  />
                </div>
                <span className="vs">vs</span>
                <div>
                  <label>{selectedMatch.equipe_exterieur}</label>
                  <input
                    type="number"
                    min="0"
                    value={formData.score_exterieur}
                    onChange={(e) => setFormData({ ...formData, score_exterieur: e.target.value })}
                  />
                </div>
              </div>
              <button onClick={updateScore} disabled={loading}>
                {loading ? '⏳ Mise à jour...' : '✅ Mettre à jour le score'}
              </button>
            </section>

            {/* Buteur */}
            <section className="editor-section">
              <h3>⚽ Ajouter un Buteur</h3>
              <input
                type="text"
                placeholder="Nom du joueur"
                value={formData.joueur}
                onChange={(e) => setFormData({ ...formData, joueur: e.target.value })}
              />
              <div className="scorer-inputs">
                <select
                  value={formData.equipe}
                  onChange={(e) => setFormData({ ...formData, equipe: e.target.value })}
                >
                  <option value="domicile">{selectedMatch.equipe_domicile}</option>
                  <option value="exterieur">{selectedMatch.equipe_exterieur}</option>
                </select>
                <input
                  type="number"
                  min="0"
                  max="90"
                  placeholder="Temps (min)"
                  value={formData.temps}
                  onChange={(e) => setFormData({ ...formData, temps: e.target.value })}
                />
              </div>
              <button onClick={addScorer} disabled={loading}>
                {loading ? '⏳ Ajout...' : '⚽ Ajouter le buteur'}
              </button>
            </section>

            {/* Carton */}
            <section className="editor-section">
              <h3>🟨 Ajouter un Carton</h3>
              <input
                type="text"
                placeholder="Nom du joueur"
                value={formData.joueur}
                onChange={(e) => setFormData({ ...formData, joueur: e.target.value })}
              />
              <div className="card-inputs">
                <select
                  value={formData.equipe}
                  onChange={(e) => setFormData({ ...formData, equipe: e.target.value })}
                >
                  <option value="domicile">{selectedMatch.equipe_domicile}</option>
                  <option value="exterieur">{selectedMatch.equipe_exterieur}</option>
                </select>
                <input
                  type="number"
                  min="0"
                  max="90"
                  placeholder="Temps (min)"
                  value={formData.temps}
                  onChange={(e) => setFormData({ ...formData, temps: e.target.value })}
                />
                <select
                  value={formData.couleur}
                  onChange={(e) => setFormData({ ...formData, couleur: e.target.value })}
                >
                  <option value="jaune">🟨 Jaune</option>
                  <option value="rouge">🟥 Rouge</option>
                </select>
              </div>
              <button onClick={addCard} disabled={loading}>
                {loading ? '⏳ Ajout...' : '🟨 Ajouter le carton'}
              </button>
            </section>

            {/* Affichage des données actuelles */}
            <section className="editor-section">
              <h3>📈 Données Actuelles</h3>
              <div className="current-data">
                <p><strong>Statut:</strong> {selectedMatch.statut}</p>
                {selectedMatch.scorers && selectedMatch.scorers.length > 0 && (
                  <div>
                    <strong>Buteurs:</strong>
                    <ul>
                      {selectedMatch.scorers.map((s, i) => (
                        <li key={i}>{s.joueur} ({s.temps}') - {s.equipe}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {selectedMatch.cards && selectedMatch.cards.length > 0 && (
                  <div>
                    <strong>Cartons:</strong>
                    <ul>
                      {selectedMatch.cards.map((c, i) => (
                        <li key={i}>{c.joueur} ({c.temps}') - {c.couleur}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
