import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Classement from './components/Classement';
import Matchs from './components/Matchs';
import CompetitionSelector from './components/CompetitionSelector';
import Newsletter from './components/Newsletter';
import './App.css';

function App() {
  const COMPETITIONS = {
    'elite-hommes': 'Elite Hommes',
    'elite-femmes': 'Elite Femmes',
    'carquefou-1sh': 'Carquefou 1SH',
    'carquefou-2sh': 'Carquefou 2SH',
    'carquefou-sd': 'Carquefou SD'
  };

  const API_BASE = 'http://localhost:8000/api/v1';

  const [selectedCompetition, setSelectedCompetition] = useState('elite-hommes');
  const [classement, setClassement] = useState(null);
  const [matchs, setMatchs] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('classement');

  useEffect(() => {
    fetchData(selectedCompetition);
  }, [selectedCompetition]);

  const fetchData = async (competitionId) => {
    setLoading(true);
    setError(null);
    setClassement(null);
    setMatchs(null);

    try {
      const promises = [];

      if (competitionId === 'elite-hommes') {
        promises.push(axios.get(`${API_BASE}/elite-hommes/classement`));
        promises.push(axios.get(`${API_BASE}/elite-hommes/matchs`));
      } else if (competitionId === 'elite-femmes') {
        promises.push(axios.get(`${API_BASE}/elite-femmes/classement`));
        promises.push(axios.get(`${API_BASE}/elite-femmes/matchs`));
      } else if (competitionId === 'carquefou-1sh') {
        promises.push(axios.get(`${API_BASE}/carquefou/1sh/classement`));
        promises.push(axios.get(`${API_BASE}/carquefou/1sh/matchs`));
      } else if (competitionId === 'carquefou-2sh') {
        promises.push(axios.get(`${API_BASE}/carquefou/2sh/classement`));
        promises.push(axios.get(`${API_BASE}/carquefou/2sh/matchs`));
      } else if (competitionId === 'carquefou-sd') {
        promises.push(axios.get(`${API_BASE}/carquefou/sd/matchs`));
      }

      const results = await Promise.all(promises);

      if (competitionId === 'carquefou-sd') {
        setMatchs(results[0].data.data);
      } else {
        setClassement(results[0].data.data);
        setMatchs(results[1].data.data);
      }

      setActiveTab('classement');
    } catch (err) {
      console.error('Erreur:', err);
      setError('Erreur lors du chargement des données.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🏑 FFH Hockey Dashboard</h1>
        <p>Suivez les championnats français de hockey sur gazon</p>
      </header>

      <main className="app-main">
        <CompetitionSelector
          competitions={COMPETITIONS}
          selected={selectedCompetition}
          onSelect={setSelectedCompetition}
        />

        {loading ? (
          <div className="loading">
            <div className="spinner"></div>
            <p>Chargement des données...</p>
          </div>
        ) : error ? (
          <div className="error">
            <p>{error}</p>
          </div>
        ) : (
          <div>
            <div className="tabs">
              {selectedCompetition !== 'carquefou-sd' && (
                <button
                  className={`tab-button ${activeTab === 'classement' ? 'active' : ''}`}
                  onClick={() => setActiveTab('classement')}
                >
                  Classement
                </button>
              )}
              <button
                className={`tab-button ${activeTab === 'matchs' ? 'active' : ''}`}
                onClick={() => setActiveTab('matchs')}
              >
                Matchs
              </button>
            </div>

            <div className="tab-content">
              {activeTab === 'classement' && classement && (
                <Classement data={classement} competition={COMPETITIONS[selectedCompetition]} />
              )}
              {activeTab === 'matchs' && matchs && (
                <Matchs data={matchs} competition={COMPETITIONS[selectedCompetition]} />
              )}
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <Newsletter />
        <p>© 2024 FFH Hockey Dashboard</p>
      </footer>
    </div>
  );
}

export default App;
