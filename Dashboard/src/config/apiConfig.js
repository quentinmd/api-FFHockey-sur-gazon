// Configuration de l'API selon l'environnement
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const ADMIN_PASSWORD = import.meta.env.VITE_ADMIN_PASSWORD || 'admin123';

export const apiConfig = {
  baseURL: API_URL,
  adminPassword: ADMIN_PASSWORD,
  endpoints: {
    importDemo: `${API_URL}/api/v1/live/import-demo`,
    importChampionship: `${API_URL}/api/v1/live/import/championship`,
    importRealData: `${API_URL}/api/v1/live/import-real-data`,
    matches: `${API_URL}/api/v1/live/matches`,
    match: (matchId) => `${API_URL}/api/v1/live/match/${matchId}`,
    updateScore: (matchId) => `${API_URL}/api/v1/live/match/${matchId}/score`,
    addScorer: (matchId) => `${API_URL}/api/v1/live/match/${matchId}/scorer`,
    addCard: (matchId) => `${API_URL}/api/v1/live/match/${matchId}/card`,
    updateStatus: (matchId) => `${API_URL}/api/v1/live/match/${matchId}/status`,
    deleteMatch: (matchId) => `${API_URL}/api/v1/live/match/${matchId}`
  }
};

export default apiConfig;
