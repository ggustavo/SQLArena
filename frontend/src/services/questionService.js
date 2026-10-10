import api, { USE_MOCK } from './api';
import { MOCK_QUESTIONS } from '../data/mockData';
import { logCrudAction } from './auditService';

// Mantém as questões em memória local para simular criação/edição em tempo de execução
let questionsCache = [...MOCK_QUESTIONS];

/**
 * Busca todas as questões disponíveis.
 * Alunos só veem status "PUBLISHED".
 * Professores veem "DRAFT", "READY" e "PUBLISHED".
 */
export async function getQuestions(userRole = 'STUDENT') {
  if (USE_MOCK) {
    await new Promise((res) => setTimeout(res, 100));
    return questionsCache.filter((q) => userRole === 'INSTRUCTOR' || q.publishedStatus === 'PUBLISHED');
  }

  // --- Backend Real ---
  const response = await api.get('/questions');
  return response.data;
}

/**
 * Busca detalhes de uma questão pelo ID (enunciado, tabelas, colunas).
 */
export async function getQuestionById(id) {
  if (USE_MOCK) {
    await new Promise((res) => setTimeout(res, 200));
    const found = questionsCache.find((q) => q.id === Number(id));
    if (!found) throw new Error('Questão não encontrada');
    return { ...found };
  }

  // --- Backend Real ---
  const response = await api.get(`/questions/${id}`);
  return response.data;
}

/**
 * Cria uma nova questão (Visão do Professor).
 * Recebe metadados e os arquivos SQL (schema.sql, data.sql, answer.sql, dataset.csv).
 */
export async function createQuestion(formData) {
  if (USE_MOCK) {
    await new Promise((res) => setTimeout(res, 800));

    let title, difficulty, categories, category, description, schemaSql, dataSql, answerSql;
    if (formData instanceof FormData) {
      title = formData.get('title');
      difficulty = formData.get('difficulty');
      const catsRaw = formData.get('categories');
      try {
        categories = catsRaw ? JSON.parse(catsRaw) : [];
      } catch {
        categories = catsRaw ? catsRaw.split(',').map((s) => s.trim()) : [];
      }
      category = formData.get('category') || (categories && categories[0]) || 'Geral';
      description = formData.get('description');
      schemaSql = formData.get('schema_sql') || '';
      dataSql = formData.get('data_sql') || '';
      answerSql = formData.get('answer_sql') || '';
    } else {
      ({ title, difficulty, categories, category, description, schemaSql, dataSql, answerSql } = formData);
    }

    // Validação do Requisito 5: answer.sql DEVE conter ORDER BY
    if (answerSql && !answerSql.toUpperCase().includes('ORDER BY')) {
      throw new Error(
        'Erro de Validação (Requisito 5): A consulta gabarito (answer.sql) DEVE conter cláusula ORDER BY para garantir determinismo.'
      );
    }

    const newId = Math.max(0, ...questionsCache.map((q) => q.id)) + 1;
    const newQuestion = {
      id: newId,
      title: title || `Questão SQL #${newId}`,
      difficulty: difficulty || 'Médio',
      categories: categories || (category ? [category] : ['Consultas Básicas']),
      category: (categories && categories[0]) || category || 'Geral',
      status: 'UNSOLVED',
      publishedStatus: 'READY',
      description: description || 'Descrição do exercício...',
      tables: (formData && !formData.get && formData.tables) || [
        {
          name: 'dados_exemplo',
          columns: [{ name: 'id', type: 'INT' }, { name: 'valor', type: 'TEXT' }],
          sampleRows: [{ id: 1, valor: 'Exemplo A' }],
        },
      ],
      schemaSql: schemaSql || '',
      dataSql: dataSql || '',
      answerSql: answerSql || '',
      xpReward: (formData && !formData.get && formData.xpReward) || 50,
      starterSql: `-- Escreva sua consulta SQL para resolver o problema\nSELECT * FROM autores;`,
    };

    questionsCache.unshift(newQuestion);

    // Registra log de criação de exercício
    await logCrudAction({
      actionType: 'CREATE_EXERCISE',
      entityId: `exercise_${newId}`,
      details: `Criada questão '${newQuestion.title}' com sucesso.`,
    });

    return newQuestion;
  }

  // --- Backend Real ---
  if (formData instanceof FormData) {
    const response = await api.post('/questions/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  const response = await api.post('/questions', formData);
  return response.data;
}

/**
 * Publica uma questão (muda status de READY para PUBLISHED).
 */
export async function publishQuestion(id) {
  if (USE_MOCK) {
    await new Promise((res) => setTimeout(res, 350));
    const q = questionsCache.find((item) => item.id === Number(id));
    if (!q) throw new Error('Questão não encontrada');
    q.publishedStatus = 'PUBLISHED';

    await logCrudAction({
      actionType: 'PUBLISH_EXERCISE',
      entityId: `exercise_${id}`,
      details: `Questão '${q.title}' publicada para os alunos.`,
    });

    return q;
  }

  const response = await api.post(`/questions/${id}/publish`);
  return response.data;
}

/**
 * Deleta uma questão.
 */
export async function deleteQuestion(id) {
  if (USE_MOCK) {
    await new Promise((res) => setTimeout(res, 400));
    questionsCache = questionsCache.filter((item) => item.id !== Number(id));

    await logCrudAction({
      actionType: 'DELETE_EXERCISE',
      entityId: `exercise_${id}`,
      details: `Questão #${id} removida do RDS e arquivos excluídos do S3. Mensagem DELETE enviada aos Workers.`,
    });

    return true;
  }

  const response = await api.delete(`/questions/${id}`);
  return response.data;
}
