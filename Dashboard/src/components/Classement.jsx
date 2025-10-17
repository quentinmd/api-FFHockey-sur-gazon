import React from 'react';
import './Classement.css';

const Classement = ({ data, competition }) => {
  if (!data || data.length === 0) {
    return <div className="no-data">Aucun classement disponible</div>;
  }

  const leader = data[0];
  const avgPoints = (data.reduce((sum, team) => sum + (team.points || 0), 0) / data.length).toFixed(1);
  const totalGoals = data.reduce((sum, team) => sum + ((team.buts_pour || 0) - (team.buts_contre || 0)), 0);

  return (
    <div className="classement-container">
      <div className="classement-header">
        <h2>{competition}</h2>
        <p>{data.length} équipes</p>
      </div>

      <div className="classement-table-wrapper">
        <table className="classement-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Équipe</th>
              <th>Pts</th>
              <th>J</th>
              <th>G</th>
              <th>N</th>
              <th>P</th>
              <th>F</th>
              <th>C</th>
              <th>Diff</th>
            </tr>
          </thead>
          <tbody>
            {data.map((team, index) => {
              const diff = (team.buts_pour || 0) - (team.buts_contre || 0);
              return (
                <tr key={index} className={`position-${Math.min(index + 1, 3)}`}>
                  <td className="position">{team.position}</td>
                  <td className="team-name">{team.equipe}</td>
                  <td className="points">{team.points}</td>
                  <td>{team.joues}</td>
                  <td className="wins">{team.gagnes}</td>
                  <td className="draws">{team.nuls}</td>
                  <td className="losses">{team.perdus}</td>
                  <td className="goals-for">{team.buts_pour}</td>
                  <td className="goals-against">{team.buts_contre}</td>
                  <td className={`difference ${diff >= 0 ? 'positive' : 'negative'}`}>
                    {diff > 0 ? '+' : ''}{diff}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="stats">
        <div className="stat-card">
          <h3>Leader</h3>
          <p>{leader.equipe}</p>
          <span className="stat-value">{leader.points} pts</span>
        </div>
        <div className="stat-card">
          <h3>Moyenne points</h3>
          <p>Par équipe</p>
          <span className="stat-value">{avgPoints}</span>
        </div>
        <div className="stat-card">
          <h3>Différence totale</h3>
          <p>Buts</p>
          <span className="stat-value">{totalGoals > 0 ? '+' : ''}{totalGoals}</span>
        </div>
      </div>
    </div>
  );
};

export default Classement;
