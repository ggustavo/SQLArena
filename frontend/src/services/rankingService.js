import api from './api';

export async function getRanking() {
  const response = await api.get('/ranking');
  return response.data;
}
