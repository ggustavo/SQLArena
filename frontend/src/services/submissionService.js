import api, { USE_MOCK } from './api';
import { logCrudAction } from './auditService';

let lastSubmissionTime = 0;
const RATE_LIMIT_MS = 5000; // 5 segundos conforme Requisito 8

const STORAGE_KEY = 'sqlarena_submissions_history';

// Dados iniciais realistas para o histórico de submissões
const INITIAL_MOCK_HISTORY = [
  {
    submissionId: 'sub_init_1',
    questionId: 1,
    questionTitle: 'Top 5 Clientes com Maior Faturamento',
    difficulty: 'Médio',
    userId: 'user_101',
    query: `SELECT c.nome, SUM(p.valor_total) AS faturamento_total
FROM clientes c
JOIN pedidos p ON p.cliente_id = c.id
WHERE p.status = 'FINALIZADO'
GROUP BY c.id, c.nome
ORDER BY faturamento_total DESC, c.nome ASC
LIMIT 5;`,
    status: 'DONE',
    outcome: 'SUCCESS',
    errorMessage: null,
    columns: ['nome', 'faturamento_total'],
    rows: [
      { nome: 'Mariana Souza Lima', faturamento_total: '3100.20' },
      { nome: 'Ana Beatriz Rocha', faturamento_total: '2140.50' },
      { nome: 'Carlos Eduardo Mendes', faturamento_total: '450.00' },
    ],
    executionTimeMs: 42,
    pointsAwarded: 10,
    strictModeHashMatched: true,
    createdAt: new Date(Date.now() - 1000 * 60 * 8).toISOString(), // há 8 minutos
    finishedAt: new Date(Date.now() - 1000 * 60 * 8 + 42).toISOString(),
  },
  {
    submissionId: 'sub_init_2',
    questionId: 2,
    questionTitle: 'Total de Pedidos por Mês',
    difficulty: 'Médio',
    userId: 'user_101',
    query: `SELECT DATE_TRUNC('month', data_pedido) AS mes, COUNT(id) AS total_pedidos
FROM pedidos
GROUP BY mes;`,
    status: 'DONE',
    outcome: 'WRONG_ANSWER',
    errorMessage: 'Resultado divergente: A consulta retornou 12 linhas sem a cláusula ORDER BY exigida pelo gabarito estrito.',
    columns: ['mes', 'total_pedidos'],
    rows: [
      { mes: '2024-03-01 00:00:00', total_pedidos: 14 },
      { mes: '2024-01-01 00:00:00', total_pedidos: 22 },
      { mes: '2024-02-01 00:00:00', total_pedidos: 18 },
    ],
    executionTimeMs: 65,
    pointsAwarded: 0,
    strictModeHashMatched: false,
    createdAt: new Date(Date.now() - 1000 * 60 * 35).toISOString(), // há 35 minutos
    finishedAt: new Date(Date.now() - 1000 * 60 * 35 + 65).toISOString(),
  },
  {
    submissionId: 'sub_init_3',
    questionId: 3,
    questionTitle: 'Média Salarial por Departamento',
    difficulty: 'Difícil',
    userId: 'user_101',
    query: `SELECT d.nome, AVG(f.salario_base) AS media_salario
FROM departamentos d
JOIN funcionarios f ON f.dept_id = d.id
WHERE f.ativo = true
GROUP BY d.nome;`,
    status: 'DONE',
    outcome: 'ERROR',
    errorMessage: 'psql: error: column "f.dept_id" does not exist (LINE 3: JOIN funcionarios f ON f.dept_id = d.id)\nHINT: Perhaps you meant to reference the column "f.departamento_id".',
    columns: [],
    rows: [],
    executionTimeMs: 18,
    pointsAwarded: 0,
    strictModeHashMatched: false,
    createdAt: new Date(Date.now() - 1000 * 60 * 75).toISOString(), // há 1h 15m
    finishedAt: new Date(Date.now() - 1000 * 60 * 75 + 18).toISOString(),
  },
  {
    submissionId: 'sub_init_4',
    questionId: 1,
    questionTitle: 'Top 5 Clientes com Maior Faturamento',
    difficulty: 'Médio',
    userId: 'user_101',
    query: `SELECT c.nome, p.valor_total
FROM clientes c
JOIN pedidos p ON p.cliente_id = c.id;`,
    status: 'DONE',
    outcome: 'WRONG_ANSWER',
    errorMessage: 'Resultado divergente: Hash de resultado não coincide com o gabarito. Faltam agregações GROUP BY e filtro de status FINALIZADO.',
    columns: ['nome', 'valor_total'],
    rows: [
      { nome: 'Carlos Eduardo Mendes', valor_total: '150.00' },
      { nome: 'Carlos Eduardo Mendes', valor_total: '300.00' },
      { nome: 'Ana Beatriz Rocha', valor_total: '2140.50' },
    ],
    executionTimeMs: 38,
    pointsAwarded: 0,
    strictModeHashMatched: false,
    createdAt: new Date(Date.now() - 1000 * 60 * 120).toISOString(), // há 2 horas
    finishedAt: new Date(Date.now() - 1000 * 60 * 120 + 38).toISOString(),
  },
];

function getStoredHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(INITIAL_MOCK_HISTORY));
      return [...INITIAL_MOCK_HISTORY];
    }
    return JSON.parse(raw);
  } catch {
    return [...INITIAL_MOCK_HISTORY];
  }
}

function saveStoredHistory(historyList) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(historyList));
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('sqlarena:submission-updated'));
    }
  } catch (err) {
    console.error('Falha ao salvar histórico no localStorage:', err);
  }
}

// Armazenamento em memória das submissões ativas no polling
const activeSubmissionsQueue = new Map();

/**
 * Retorna o histórico de submissões com suporte a busca e filtros.
 */
export async function getSubmissionsHistory({ search = '', status = 'ALL' } = {}) {
  if (USE_MOCK) {
    await new Promise((res) => setTimeout(res, 60));
    const all = getStoredHistory();
    return all.filter((sub) => {
      const matchSearch =
        !search ||
        sub.questionTitle?.toLowerCase().includes(search.toLowerCase()) ||
        sub.query?.toLowerCase().includes(search.toLowerCase()) ||
        String(sub.questionId) === search.trim();

      const matchStatus =
        status === 'ALL' ||
        sub.outcome === status ||
        sub.status === status;

      return matchSearch && matchStatus;
    });
  }

  // --- Backend Real ---
  const response = await api.get('/submissions/history', {
    params: { search, status },
  });
  return response.data;
}

/**
 * Retorna as N submissões mais recentes (usado no modal/popover da Navbar).
 */
export async function getRecentSubmissions(limit = 5) {
  if (USE_MOCK) {
    const all = getStoredHistory();
    return all.slice(0, limit);
  }

  // --- Backend Real ---
  const response = await api.get('/submissions/recent', {
    params: { limit },
  });
  return response.data;
}

/**
 * Envia uma consulta SQL para avaliação (Requisito 9).
 * - Valida Rate Limit de 5 segundos.
 * - Registra a submissão com status 'QUEUED' / 'PROCESSING'.
 * - Retorna HTTP 202 Accepted com submissionId.
 */
export async function submitQuery({ questionId, questionTitle = 'Questão SQL', difficulty = 'Médio', sqlQuery, userId = 'user_101' }) {
  const now = Date.now();
  if (now - lastSubmissionTime < RATE_LIMIT_MS) {
    const waitSeconds = Math.ceil((RATE_LIMIT_MS - (now - lastSubmissionTime)) / 1000);
    throw new Error(
      `Rate Limit ativo: Aguarde mais ${waitSeconds}s antes de enviar outra consulta (Requisito 8: 1 submissão a cada 5s).`
    );
  }
  lastSubmissionTime = now;

  if (USE_MOCK) {
    await new Promise((res) => setTimeout(res, 200));

    const submissionId = `sub_${Date.now()}`;
    const cleanSql = sqlQuery.trim().toUpperCase();

    // Determina o desfecho da simulação baseado na query
    let outcome = 'SUCCESS';
    let errorMessage = null;
    let resultRows = [];
    let columns = [];

    if (!cleanSql.startsWith('SELECT')) {
      outcome = 'ERROR';
      errorMessage = 'psql: error: Permissão negada. Apenas comandos SELECT são permitidos na sandbox de execução.';
    } else if (cleanSql.includes('TABELA_INEXISTENTE') || cleanSql.includes('ERRO')) {
      outcome = 'ERROR';
      errorMessage = 'psql: error: relation "tabela_inexistente" does not exist (LINE 2: FROM tabela_inexistente)';
    } else if (!cleanSql.includes('ORDER BY')) {
      outcome = 'WRONG_ANSWER';
      errorMessage = 'Resultado divergente: A ordem das linhas não coincide com o gabarito canônico (Falta ORDER BY).';
      columns = ['nome', 'faturamento_total'];
      resultRows = [
        { nome: 'Carlos Eduardo Mendes', faturamento_total: '450.00' },
        { nome: 'Ana Beatriz Rocha', faturamento_total: '2140.50' },
        { nome: 'Mariana Souza Lima', faturamento_total: '3100.20' },
      ];
    } else {
      outcome = 'SUCCESS';
      columns = ['nome', 'faturamento_total'];
      resultRows = [
        { nome: 'Mariana Souza Lima', faturamento_total: '3100.20' },
        { nome: 'Ana Beatriz Rocha', faturamento_total: '2140.50' },
        { nome: 'Carlos Eduardo Mendes', faturamento_total: '450.00' },
      ];
    }

    const subEntry = {
      submissionId,
      questionId,
      questionTitle,
      difficulty,
      userId,
      query: sqlQuery,
      status: 'PROCESSING', // PROCESSING -> DONE
      outcome,
      errorMessage,
      columns,
      resultRows,
      executionTimeMs: Math.floor(Math.random() * 60) + 35,
      pointsAwarded: outcome === 'SUCCESS' ? 10 : 0,
      strictModeHashMatched: outcome === 'SUCCESS',
      createdAt: new Date().toISOString(),
      pollCount: 0,
    };

    activeSubmissionsQueue.set(submissionId, subEntry);

    // Salva no histórico como 'PROCESSING'
    const history = getStoredHistory();
    history.unshift({
      ...subEntry,
      outcome: null, // Ainda em processamento
    });
    saveStoredHistory(history);

    return {
      submissionId,
      status: 'ACCEPTED',
      message: 'Consulta enviada para fila de execução PostgreSQL.',
      estimatedPollIntervalMs: 500,
    };
  }

  // --- Backend Real ---
  const response = await api.post('/submissions', {
    question_id: questionId,
    sql_query: sqlQuery,
    questionTitle,
    difficulty,
  });

  const subData = response.data;
  try {
    const history = getStoredHistory();
    history.unshift({
      submissionId: subData.submissionId,
      questionId,
      questionTitle,
      difficulty,
      userId,
      query: sqlQuery,
      status: 'PROCESSING',
      outcome: null,
      createdAt: new Date().toISOString(),
    });
    saveStoredHistory(history);
  } catch (err) {
    console.warn('Erro ao salvar histórico local:', err);
  }

  return subData;
}

/**
 * Consulta o status da submissão (Polling assíncrono).
 */
export async function checkSubmissionStatus(submissionId) {
  if (USE_MOCK) {
    await new Promise((res) => setTimeout(res, 150));
    const sub = activeSubmissionsQueue.get(submissionId);
    if (!sub) {
      // Se não estiver na memória ativa, busca no histórico
      const stored = getStoredHistory().find((s) => s.submissionId === submissionId);
      if (stored) return stored;
      throw new Error('Submissão não encontrada');
    }

    sub.pollCount += 1;

    // Simula 1 ciclo de espera antes de concluir
    if (sub.pollCount < 2) {
      return {
        submissionId,
        status: 'PROCESSING',
      };
    }

    // Submissão concluída
    sub.status = 'DONE';
    sub.finishedAt = new Date().toISOString();

    // Atualiza o registro no localStorage
    const history = getStoredHistory();
    const idx = history.findIndex((s) => s.submissionId === submissionId);
    if (idx !== -1) {
      history[idx] = {
        ...history[idx],
        status: 'DONE',
        outcome: sub.outcome,
        errorMessage: sub.errorMessage,
        columns: sub.columns,
        rows: sub.resultRows,
        executionTimeMs: sub.executionTimeMs,
        pointsAwarded: sub.pointsAwarded,
        strictModeHashMatched: sub.strictModeHashMatched,
        finishedAt: sub.finishedAt,
      };
      saveStoredHistory(history);
    }

    await logCrudAction({
      actionType: 'SUBMIT_ANSWER',
      entityId: submissionId,
      userId: sub.userId,
      details: sub.outcome === 'SUCCESS' ? 'Consulta correta.' : 'Consulta incorreta/erro.',
    });

    return {
      submissionId,
      status: 'DONE',
      outcome: sub.outcome, // SUCCESS | WRONG_ANSWER | ERROR
      errorMessage: sub.errorMessage,
      columns: sub.columns,
      rows: sub.resultRows,
      executionTimeMs: sub.executionTimeMs,
      strictModeHashMatched: sub.strictModeHashMatched,
      pointsAwarded: sub.pointsAwarded,
    };
  }

  // --- Backend Real ---
  const response = await api.get(`/submissions/${submissionId}/status`);
  const statusData = response.data;

  if (statusData && statusData.status === 'DONE') {
    try {
      const history = getStoredHistory();
      const idx = history.findIndex((s) => s.submissionId === submissionId);
      if (idx !== -1) {
        history[idx] = {
          ...history[idx],
          ...statusData,
        };
        saveStoredHistory(history);
      }
    } catch (err) {
      console.warn('Erro ao atualizar histórico local:', err);
    }
  }

  return statusData;
}

/**
 * Retorna o SQL da última submissão enviada pelo usuário para uma questão específica,
 * ou null caso o usuário ainda não tenha respondido essa questão.
 */
export function getLastSubmittedSql(questionId) {
  if (!questionId) return null;
  try {
    const history = getStoredHistory();
    // Como getStoredHistory() ordena as mais recentes no topo (unshift),
    // a primeira correspondência é a última submissão do aluno
    const match = history.find(
      (sub) => Number(sub.questionId) === Number(questionId) && typeof sub.query === 'string' && sub.query.trim().length > 0
    );
    return match ? match.query : null;
  } catch (err) {
    console.error('Erro ao buscar última submissão da questão:', err);
    return null;
  }
}

