import api, { USE_MOCK } from './api';

export const PREDEFINED_CATEGORIES = [
  {
    id: 1,
    name: "Agrupamento",
    slug: "agrupamento",
    description: "Cálculos em grupo: GROUP BY, HAVING, SUM, COUNT, AVG.",
  },
  {
    id: 2,
    name: "Condicional",
    slug: "condicional",
    description: "Lógica condicional: CASE WHEN, COALESCE e NULLIF.",
  },
  {
    id: 3,
    name: "Conjuntos",
    slug: "conjuntos",
    description: "Álgebra relacional: UNION, UNION ALL, INTERSECT, EXCEPT.",
  },
  {
    id: 4,
    name: "CTEs",
    slug: "ctes",
    description: "Common Table Expressions com a cláusula WITH.",
  },
  {
    id: 5,
    name: "Datas",
    slug: "datas",
    description: "Manipulação temporal: DATE, TIMESTAMP, DATE_TRUNC, EXTRACT, INTERVAL.",
  },
  {
    id: 6,
    name: "Distintos",
    slug: "distintos",
    description: "Desduplicação e unicidade de registros: DISTINCT e DISTINCT ON.",
  },
  {
    id: 7,
    name: "Filtragem",
    slug: "filtragem",
    description: "Filtros de registros com WHERE, IN, BETWEEN, LIKE e IS NULL.",
  },
  {
    id: 8,
    name: "Funções",
    slug: "funcoes",
    description: "Funções escalares, numéricas e utilitárias do PostgreSQL: ROUND, ABS, GREATEST.",
  },
  {
    id: 9,
    name: "Janelas",
    slug: "janelas",
    description: "Funções analíticas: OVER, PARTITION BY, ROW_NUMBER, DENSE_RANK.",
  },
  {
    id: 10,
    name: "JOINs",
    slug: "joins",
    description: "Relacionamentos entre tabelas: INNER, LEFT, RIGHT e FULL JOIN.",
  },
  {
    id: 11,
    name: "Subconsultas",
    slug: "subconsultas",
    description: "Consultas aninhadas: subqueries escalares e cláusulas EXISTS/IN.",
  },
  {
    id: 12,
    name: "Texto",
    slug: "texto",
    description: "Operações com strings: UPPER, LOWER, SUBSTRING, CONCAT, TRIM, LIKE.",
  },
];

/**
 * Busca todas as categorias disponíveis no sistema, sempre ordenadas alfabeticamente.
 */
export async function getCategories() {
  if (USE_MOCK) {
    await new Promise((res) => setTimeout(res, 60));
    return [...PREDEFINED_CATEGORIES].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
  }

  // --- Backend Real ---
  const response = await api.get('/categories');
  const data = Array.isArray(response.data) ? response.data : [];
  return data.sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
}
