import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
});

export const getHealth = async () => {
    const response = await api.get('/health');
    return response.data;
};

export const searchLocation = async (query) => {
    const response = await api.get(`/locations/search?q=${query}`);
    return response.data.results;
};

export const getCurrentWeather = async (lat, lon) => {
    const response = await api.get(`/current/${lat}/${lon}`);
    return response.data;
};

export const getForecastWeather = async (lat, lon) => {
    const response = await api.get(`/forecast/${lat}/${lon}`);
    return response.data;
};

export default api;
