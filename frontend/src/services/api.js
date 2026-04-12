import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
});

export const CITY_NAMES = [
  'Ropar', 'Chandigarh', 'Ludhiana',
  'Patiala', 'Jalandhar', 'Ambala', 'Shimla',
];

export const DEFAULT_CITY = 'Ropar';

/** Health-check */
export const getHealth = async () => {
  const { data } = await api.get('/health');
  return data;
};

/**
 * Current live conditions for all 7 nodes.
 * Returns: { nodes: { Ropar: {...}, Chandigarh: {...}, ... } }
 */
export const getCurrentConditions = async () => {
  const { data } = await api.get('/current');
  return data.nodes;            // keyed by city name
};

/**
 * 48-hour Graph-LSTM forecast for all 7 nodes.
 * Returns: { metadata, current, forecast }
 * forecast[city] = [ { hour, temperature_2m, ... } × 48 ]
 */
export const getGraphForecast = async () => {
  const { data } = await api.get('/forecast');
  return data;
};

export default api;
