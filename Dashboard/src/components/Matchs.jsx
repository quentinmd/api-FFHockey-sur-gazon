import React, { useState } from 'react';
import './Matchs.css';

const Matchs = ({ data, competition }) => {
  const [filterStatus, setFilterStatus] = useState('ALL');

  if (!data || data.length === 0) {
    return <div className="no-data">Aucun match disponible</div>;
  }

  const getMatchStatus = (match) => {
    if (match.statut === 'FINISHED' || match.statut === 1) return 'FINISHED';
    if (match.statut === 'NOT_PLAYED' || match.statut === 0) return 'NOT_PLAYED';
    return 'SCHEDULED';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Date indisponible';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('fr-FR', {
        weekday: 'short',
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  const formatTime = (timeString) => {
    if (!timeString) return '';
    try {
      const parts = timeString.split(' ');
      if (parts.length >= 2) {
        return parts[1].substring(0, 5); // Retourne HH:MM
      }
    } catch {
      return '';
    }
    return '';
  };

  const filteredMatches = filterStatus === 'ALL'
    ? data
    : data.filter(match => getMatchStatus(match) === filterStatus);

  const statusCounts = {
    FINISHED: data.filter(m => getMatchStatus(m) === 'FINISHED').length,
    SCHEDULED: data.filter(m => getMatchStatus(m) === 'SCHEDULED').length,
    NOT_PLAYED: data.filter(m => getMatchStatus(m) === 'NOT_PLAYED').length
  };

  return (
    <div className="matchs-container">
      <div className="matchs-header">
        <h2>{competition}</h2>
        <p>{filteredMatches.length} match(s)</p>
      </div>

      <div className="filter-section">
        <button
          className={`filter-btn ${filterStatus === 'ALL' ? 'active' : ''}`}
          onClick={() => setFilterStatus('ALL')}
        >
          Tous ({data.length})
        </button>
        <button
          className={`filter-btn ${filterStatus === 'FINISHED' ? 'active' : ''}`}
          onClick={() => setFilterStatus('FINISHED')}
        >
          Joués ({statusCounts.FINISHED})
        </button>
        <button
          className={`filter-btn ${filterStatus === 'SCHEDULED' ? 'active' : ''}`}
          onClick={() => setFilterStatus('SCHEDULED')}
        >
          À venir ({statusCounts.SCHEDULED})
        </button>
        <button
          className={`filter-btn ${filterStatus === 'NOT_PLAYED' ? 'active' : ''}`}
          onClick={() => setFilterStatus('NOT_PLAYED')}
        >
          Non joués ({statusCounts.NOT_PLAYED})
        </button>
      </div>

      <div className="matchs-list">
        {filteredMatches.length === 0 ? (
          <div className="no-matches">Aucun match avec ce filtre</div>
        ) : (
          filteredMatches.map((match, index) => {
            const status = getMatchStatus(match);
            const domicile = match.equipe_domicile || 'TBD';
            const visiteur = match.equipe_exterieur || 'TBD';
            const scoreA = match.score_domicile ?? '-';
            const scoreB = match.score_exterieur ?? '-';
            const date = formatDate(match.date);
            const time = formatTime(match.date || '');

            return (
              <div key={index} className={`match-card match-${status.toLowerCase()}`}>
                {time && <span className="match-time-badge">{time}</span>}
                <div className="match-date">
                  <span className="date">{date}</span>
                </div>

                <div className="match-teams">
                  <div className="team domicile">
                    <span className="team-name">{domicile}</span>
                  </div>

                  <div className="score">
                    <span className="score-value">{scoreA}</span>
                    <span className="separator">-</span>
                    <span className="score-value">{scoreB}</span>
                    <span className={`status-badge status-${status.toLowerCase()}`}>
                      {status === 'FINISHED' && 'Joué'}
                      {status === 'SCHEDULED' && 'À venir'}
                      {status === 'NOT_PLAYED' && 'Non joué'}
                    </span>
                  </div>

                  <div className="team visiteur">
                    <span className="team-name">{visiteur}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default Matchs;
