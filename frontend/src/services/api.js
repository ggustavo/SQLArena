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

/**
 * Converte caminhos relativos ou absolutos de avatar em URLs completas e seguras para renderização no navegador.
 * Evita erros de porta (5173 vs 8000), suporta pré-visualizações locais (blob/data) e anexa timestamp opcional
 * para evitar exibição de cache antigo após uploads.
 */
export function getAvatarUrl(avatarUrl, timestamp) {
  if (!avatarUrl) return null;
  const str = String(avatarUrl).trim();
  if (!str) return null;

  // URLs de dados ou blobs locais (preview em memória)
  if (
    str.startsWith('blob:') ||
    str.startsWith('data:')
  ) {
    return str;
  }

  let finalUrl = str;

  // Se for URL relativa, adiciona a base do backend
  if (!str.startsWith('http://') && !str.startsWith('https://')) {
    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    const origin = apiBase.replace(/\/api\/?$/, '');
    const cleanPath = str.startsWith('/') ? str : `/${str}`;
    finalUrl = `${origin}${cleanPath}`;
  }

  // Se foi passado timestamp, anexa como query param para quebra de cache
  if (timestamp) {
    const separator = finalUrl.includes('?') ? '&' : '?';
    finalUrl = `${finalUrl}${separator}t=${timestamp}`;
  }

  return finalUrl;
}

export default api;
