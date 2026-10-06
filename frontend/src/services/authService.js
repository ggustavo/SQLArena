import api, { USE_MOCK } from './api';
import { MOCK_ACCOUNTS } from '../data/mockData';

const STORAGE_KEY_USER = 'sqlarena_user';
const STORAGE_KEY_TOKEN = 'sqlarena_token';

/**
 * Autenticação por e-mail e senha.
 */
export async function login(email, password) {
  if (USE_MOCK) {
    await new Promise((res) => setTimeout(res, 200));

    const cleanEmail = (email || '').trim().toLowerCase();
    const account = MOCK_ACCOUNTS[cleanEmail] || {
      id: `user_${Date.now()}`,
      name: cleanEmail.split('@')[0],
      email: cleanEmail,
      role: 'STUDENT',
      score: 0,
      solvedCount: 0,
      streakDays: 0,
    };

    const token = 'jwt-token-sqlarena-' + Date.now();
    localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(account));
    localStorage.setItem(STORAGE_KEY_TOKEN, token);
    return { user: account, token };
  }

  // --- Backend Real ---
  const response = await api.post('/auth/login', { email, password });
  const { user, token } = response.data;
  localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(user));
  localStorage.setItem(STORAGE_KEY_TOKEN, token);
  return { user, token };
}

/**
 * Retorna o usuário logado atualmente (da memória / localStorage).
 */
export function getCurrentUser() {
  const saved = localStorage.getItem(STORAGE_KEY_USER);
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch {
      return null;
    }
  }
  return null; // Por padrão, se não logou, vai para a tela de login!
}

/**
 * Encerra a sessão atual.
 */
export async function logout() {
  localStorage.removeItem(STORAGE_KEY_USER);
  localStorage.removeItem(STORAGE_KEY_TOKEN);
  return true;
}
