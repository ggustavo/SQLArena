import api, { USE_MOCK } from './api';

const INITIAL_AUDIT_LOGS = [
  {
    action_id: "act-101",
    action_type: "CREATE_EXERCISE",
    entity: "exercise",
    entity_id: "exercise_1",
    user_id: "professor_01",
    created_at: new Date().toISOString(),
    details: "Criado exercício 'Top 5 Clientes com Maior Faturamento'.",
  },
  {
    action_id: "act-102",
    action_type: "PUBLISH_EXERCISE",
    entity: "exercise",
    entity_id: "exercise_1",
    user_id: "professor_01",
    created_at: new Date().toISOString(),
    details: "Exercício publicado para os alunos.",
  },
];

let auditLogsMemory = [...INITIAL_AUDIT_LOGS];

/**
 * Consulta a lista de ações de CRUD registradas.
 */
export async function getCrudAuditLogs(limit = 50) {
  if (USE_MOCK) {
    await new Promise((res) => setTimeout(res, 200));
    return auditLogsMemory.slice(0, limit);
  }

  // --- Backend Real ---
  const response = await api.get('/audit/logs', { params: { limit } });
  return response.data;
}

/**
 * Registra um evento de auditoria.
 */
export async function logCrudAction({ actionType, entityId, details, userId = 'sistema' }) {
  const newLog = {
    action_id: `act-${Date.now().toString(36)}`,
    action_type: actionType,
    entity: 'exercise',
    entity_id: entityId,
    user_id: userId,
    created_at: new Date().toISOString(),
    details: details || '',
  };

  auditLogsMemory.unshift(newLog);

  if (!USE_MOCK) {
    try {
      await api.post('/audit/logs', newLog);
    } catch (err) {
      console.warn('Falha ao sincronizar log com backend real:', err);
    }
  }

  return newLog;
}
