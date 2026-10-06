import axios from 'axios';

/**
 * Flag global para alternar entre dados Mockados e Backend Real.
 * Definido como false para integração ponta a ponta com a API FastAPI.
 */
export const USE_MOCK = false;

/**
 * Instância configurada do Axios para chamadas HTTP ao FastAPI.
 * BaseURL aponta para a porta padrão do FastAPI (8000).
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Interceptor para injetar automaticamente o Token JWT nas requisições reais
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('sqlarena_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para tratamento uniforme de erros do FastAPI
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('sqlarena_token');
      localStorage.removeItem('sqlarena_user');
      // Redirecionar para login se necessário
    }
    return Promise.reject(error);
  }
);

export default api;
