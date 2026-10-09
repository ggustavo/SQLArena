import api from './api';

export async function getUsers(search = '') {
  const response = await api.get('/users', { params: { search } });
  return response.data;
}

export async function setUserRole(id, role) {
  const response = await api.patch(`/users/${encodeURIComponent(id)}/role`, { role });
  return response.data;
}
