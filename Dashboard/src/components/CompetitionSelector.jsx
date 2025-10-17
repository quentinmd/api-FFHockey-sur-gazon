import React from 'react';
import './CompetitionSelector.css';

const CompetitionSelector = ({ competitions, selected, onSelect }) => {
  const getCompetitionLabel = (id) => {
    const labels = {
      'elite-hommes': '🏑 Elite Hommes',
      'elite-femmes': '👩‍🤝‍👨 Elite Femmes',
      'carquefou-1sh': '🎯 Carquefou 1SH',
      'carquefou-2sh': '🎯 Carquefou 2SH',
      'carquefou-sd': '👩‍🤝‍👨 Carquefou SD'
    };
    return labels[id] || id;
  };

  const getCompetitionDescription = (id) => {
    const descriptions = {
      'elite-hommes': 'Championnat Elite Hommes',
      'elite-femmes': 'Championnat Elite Femmes',
      'carquefou-1sh': 'Poule A - 1ère Série Hommes',
      'carquefou-2sh': 'Poule B - 2ème Série Hommes',
      'carquefou-sd': 'Seniors Dames Elite'
    };
    return descriptions[id] || '';
  };

  return (
    <div className="competition-selector">
      <h3>Choisir une compétition</h3>
      <div className="selector-options">
        {Object.entries(competitions).map(([id, label]) => (
          <label key={id} className={`selector-option ${selected === id ? 'selected' : ''}`}>
            <input
              type="radio"
              name="competition"
              value={id}
              checked={selected === id}
              onChange={() => onSelect(id)}
            />
            <div className="option-content">
              <span className="option-label">{getCompetitionLabel(id)}</span>
              <span className="option-description">{getCompetitionDescription(id)}</span>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
};

export default CompetitionSelector;
