export const MOCK_ACCOUNTS = {
  "aluno@sqlarena.com": {
    id: "user_101",
    name: "Gustavo Santos",
    email: "aluno@sqlarena.com",
    role: "STUDENT",
    score: 0,
    solvedCount: 0,
    streakDays: 0,
  },
  "instrutor@sqlarena.com": {
    id: "user_001",
    name: "Carlos Silva",
    email: "instrutor@sqlarena.com",
    role: "INSTRUCTOR",
    score: 0,
    solvedCount: 0,
    streakDays: 0,
  },
};

export const MOCK_QUESTIONS = [
  {
    id: 1,
    title: "Top 5 Clientes com Maior Faturamento",
    difficulty: "Médio",
    categories: ["Agrupamento", "Filtragem", "JOINs"],
    category: "Agrupamento",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `A diretoria comercial precisa identificar os 5 clientes que geraram o maior volume financeiro em compras concluídas.

Escreva uma consulta SQL que retorne o **nome do cliente** e o **faturamento total** acumulado considerando apenas os pedidos com status \`'FINALIZADO'\`.

**Regras:**
- Ordene o resultado do maior faturamento para o menor.
- Em caso de empate no valor, ordene alfabeticamente pelo nome do cliente.
- Limite a saída aos 5 primeiros registros.`,
    schemaSql: `CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    cidade VARCHAR(50)
);

CREATE TABLE pedidos (
    id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL REFERENCES clientes(id),
    valor_total NUMERIC(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDENTE',
    data_pedido TIMESTAMP DEFAULT NOW()
);

CREATE TABLE itens_pedido (
    id SERIAL PRIMARY KEY,
    pedido_id INT NOT NULL REFERENCES pedidos(id),
    produto_nome VARCHAR(80) NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario NUMERIC(10,2) NOT NULL
);`,
    sampleTables: [
      {
        name: "clientes",
        columns: ["id", "nome", "email", "cidade"],
        rows: [
          { id: 1, nome: "Ana Beatriz Rocha", email: "ana.rocha@email.com", cidade: "São Paulo" },
          { id: 2, nome: "Carlos Eduardo Mendes", email: "cadu@email.com", cidade: "Curitiba" },
          { id: 3, nome: "Mariana Souza Lima", email: "mariana.lima@email.com", cidade: "Belo Horizonte" },
          { id: 4, nome: "Felipe Nogueira", email: "fnogueira@email.com", cidade: "Rio de Janeiro" },
          { id: 5, nome: "Juliana Paes Castro", email: "jcastro@email.com", cidade: "Porto Alegre" },
        ],
      },
      {
        name: "pedidos",
        columns: ["id", "cliente_id", "valor_total", "status", "data_pedido"],
        rows: [
          { id: 101, cliente_id: 1, valor_total: "1250.50", status: "FINALIZADO", data_pedido: "2026-03-01 10:30" },
          { id: 102, cliente_id: 2, valor_total: "450.00", status: "FINALIZADO", data_pedido: "2026-03-02 14:15" },
          { id: 103, cliente_id: 1, valor_total: "890.00", status: "FINALIZADO", data_pedido: "2026-03-05 09:12" },
          { id: 104, cliente_id: 3, valor_total: "3100.20", status: "FINALIZADO", data_pedido: "2026-03-06 18:40" },
          { id: 105, cliente_id: 4, valor_total: "150.00", status: "CANCELADO", data_pedido: "2026-03-07 11:00" },
        ],
      },
      {
        name: "itens_pedido",
        columns: ["id", "pedido_id", "produto_nome", "quantidade", "preco_unitario"],
        rows: [
          { id: 1, pedido_id: 101, produto_nome: "Monitor 27 pol", quantidade: 1, preco_unitario: "1250.50" },
          { id: 2, pedido_id: 102, produto_nome: "Teclado Mecânico", quantidade: 1, preco_unitario: "450.00" },
          { id: 3, pedido_id: 104, produto_nome: "Notebook Gamer", quantidade: 1, preco_unitario: "3100.20" },
        ],
      },
    ],
    starterSql: `-- Digite sua consulta SQL aqui
SELECT 
    c.nome, 
    SUM(p.valor_total) AS faturamento_total
FROM clientes c
JOIN pedidos p ON p.cliente_id = c.id
WHERE p.status = 'FINALIZADO'
GROUP BY c.id, c.nome
ORDER BY faturamento_total DESC, c.nome ASC
LIMIT 5;`,
    expectedColumns: ["nome", "faturamento_total"],
  },
  {
    id: 2,
    title: "Produtos com Estoque Abaixo da Média",
    difficulty: "Fácil",
    categories: ["Subconsultas", "Filtragem", "Funções"],
    category: "Subconsultas",
    status: "ATTEMPTED",
    publishedStatus: "PUBLISHED",
    description: `Identifique os produtos do estoque que precisam de reposição imediata.

Escreva uma consulta que retorne o **nome do produto** e a **quantidade em estoque** de todos os itens cujo estoque atual seja estritamente menor do que a média geral de estoque da loja.

**Regras:**
- Filtre apenas produtos com \`ativo = true\`.
- Ordene do menor estoque para o maior.`,
    schemaSql: `CREATE TABLE categorias (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) NOT NULL
);

CREATE TABLE produtos (
    id SERIAL PRIMARY KEY,
    categoria_id INT REFERENCES categorias(id),
    nome VARCHAR(80) NOT NULL,
    quantidade_estoque INT NOT NULL DEFAULT 0,
    preco NUMERIC(10,2) NOT NULL,
    ativo BOOLEAN DEFAULT true
);`,
    sampleTables: [
      {
        name: "categorias",
        columns: ["id", "nome"],
        rows: [
          { id: 1, nome: "Periféricos" },
          { id: 2, nome: "Monitores" },
        ],
      },
      {
        name: "produtos",
        columns: ["id", "categoria_id", "nome", "quantidade_estoque", "preco", "ativo"],
        rows: [
          { id: 1, categoria_id: 1, nome: "Teclado RGB", quantidade_estoque: 12, preco: "250.00", ativo: true },
          { id: 2, categoria_id: 1, nome: "Mouse Gamer", quantidade_estoque: 85, preco: "90.00", ativo: true },
          { id: 3, categoria_id: 2, nome: "Monitor 144Hz", quantidade_estoque: 4, preco: "1200.00", ativo: true },
          { id: 4, categoria_id: 1, nome: "Headset 7.1", quantidade_estoque: 35, preco: "320.00", ativo: true },
        ],
      },
    ],
    starterSql: `SELECT nome, quantidade_estoque
FROM produtos
WHERE ativo = true 
  AND quantidade_estoque < (SELECT AVG(quantidade_estoque) FROM produtos)
ORDER BY quantidade_estoque ASC;`,
    expectedColumns: ["nome", "quantidade_estoque"],
  },
  {
    id: 3,
    title: "Média Salarial por Departamento",
    difficulty: "Difícil",
    categories: ["Agrupamento", "Filtragem", "JOINs"],
    category: "Agrupamento",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `Gere um relatório executivo para o setor de Recursos Humanos.

A consulta deve retornar a **sigla do departamento**, o **total de colaboradores** e o **salário médio** formatado com duas casas decimais.

**Regras:**
- Considere apenas departamentos que possuam mais de 2 colaboradores vinculados.
- Ordene pelo salário médio em ordem decrescente.`,
    schemaSql: `CREATE TABLE departamentos (
    id SERIAL PRIMARY KEY,
    sigla VARCHAR(10) NOT NULL UNIQUE,
    nome VARCHAR(60) NOT NULL
);

CREATE TABLE colaboradores (
    id SERIAL PRIMARY KEY,
    departamento_id INT REFERENCES departamentos(id),
    nome VARCHAR(100) NOT NULL,
    salario NUMERIC(10,2) NOT NULL,
    data_admissao DATE NOT NULL
);`,
    sampleTables: [
      {
        name: "departamentos",
        columns: ["id", "sigla", "nome"],
        rows: [
          { id: 1, sigla: "TI", nome: "Tecnologia da Informação" },
          { id: 2, sigla: "MKT", nome: "Marketing & Growth" },
          { id: 3, sigla: "FIN", nome: "Financeiro" },
        ],
      },
      {
        name: "colaboradores",
        columns: ["id", "departamento_id", "nome", "salario", "data_admissao"],
        rows: [
          { id: 1, departamento_id: 1, nome: "Alice Silva", salario: "9500.00", data_admissao: "2023-01-15" },
          { id: 2, departamento_id: 1, nome: "Bruno Costa", salario: "8200.00", data_admissao: "2023-06-10" },
          { id: 3, departamento_id: 1, nome: "Carla Dias", salario: "11000.00", data_admissao: "2022-03-01" },
          { id: 4, departamento_id: 2, nome: "Daniel Ramos", salario: "4500.00", data_admissao: "2024-02-12" },
        ],
      },
    ],
    starterSql: `SELECT 
    d.sigla, 
    COUNT(c.id) AS total_colaboradores, 
    ROUND(AVG(c.salario), 2) AS salario_medio
FROM departamentos d
JOIN colaboradores c ON c.departamento_id = d.id
GROUP BY d.id, d.sigla
HAVING COUNT(c.id) > 2
ORDER BY salario_medio DESC;`,
    expectedColumns: ["sigla", "total_colaboradores", "salario_medio"],
  },
  {
    id: 4,
    title: "Clientes Sem Pedidos Realizados",
    difficulty: "Médio",
    categories: ["Condicional", "Filtragem", "JOINs"],
    category: "Condicional",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `A equipe de relacionamento precisa da lista de clientes cadastrados que nunca realizaram nenhum pedido na plataforma.

Escreva uma consulta que retorne o **nome** e o **e-mail** de todos os clientes sem pedidos associados, ordenados alfabeticamente pelo nome.`,
    schemaSql: `CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL
);

CREATE TABLE pedidos (
    id SERIAL PRIMARY KEY,
    cliente_id INT REFERENCES clientes(id),
    data_pedido TIMESTAMP NOT NULL
);`,
    sampleTables: [
      {
        name: "clientes",
        columns: ["id", "nome", "email"],
        rows: [
          { id: 1, nome: "Fernanda Lima", email: "fernanda@exemplo.com" },
          { id: 2, nome: "Gabriel Torres", email: "gabriel@exemplo.com" },
        ],
      },
      {
        name: "pedidos",
        columns: ["id", "cliente_id", "data_pedido"],
        rows: [
          { id: 1, cliente_id: 1, data_pedido: "2026-03-25" },
        ],
      },
    ],
    starterSql: `SELECT c.nome, c.email
FROM clientes c
LEFT JOIN pedidos p ON p.cliente_id = c.id
WHERE p.id IS NULL
ORDER BY c.nome ASC;`,
    expectedColumns: ["nome", "email"],
  },
  {
    id: 5,
    title: "Auditoria e Higienização de E-mails Duplicados",
    difficulty: "Difícil",
    categories: ["Agrupamento", "Distintos", "Filtragem", "Funções", "Janelas", "Texto"],
    category: "Agrupamento",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `A equipe de segurança e compliance precisa higienizar a base de contatos corporativos e detectar registros duplicados.

Escreva uma consulta SQL que:
1. Normalize o e-mail removendo espaços em branco (\`TRIM\`) e convertendo para minúsculas (\`LOWER\`).
2. Utilize a função de janela \`ROW_NUMBER() OVER (PARTITION BY ... ORDER BY id ASC)\` para numerar ocorrências duplicadas do mesmo e-mail normalizado.
3. Filtre apenas os registros de clientes ativos com domínios corporativos válidos (\`LIKE '%@empresa.com'\`).
4. Retorne o id, o nome em maiúsculas (\`UPPER\`), o e-mail limpo e a contagem da duplicidade.`,
    schemaSql: `CREATE TABLE contatos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    ativo BOOLEAN DEFAULT true,
    criado_em TIMESTAMP DEFAULT NOW()
);`,
    sampleTables: [
      {
        name: "contatos",
        columns: ["id", "nome", "email", "ativo", "criado_em"],
        rows: [
          { id: 1, nome: "João Silva", email: "  JOAO@empresa.com ", ativo: true, criado_em: "2026-01-10" },
          { id: 2, nome: "Joao S.", email: "joao@empresa.com", ativo: true, criado_em: "2026-01-15" },
          { id: 3, nome: "Maria Clara", email: "maria@empresa.com", ativo: true, criado_em: "2026-02-01" },
          { id: 4, nome: "Pedro Lima", email: "pedro@gmail.com", ativo: true, criado_em: "2026-02-10" },
        ],
      },
    ],
    starterSql: `SELECT 
    id,
    UPPER(nome) AS nome_formatado,
    LOWER(TRIM(email)) AS email_normalizado,
    ROW_NUMBER() OVER(PARTITION BY LOWER(TRIM(email)) ORDER BY id ASC) AS num_ocorrencia
FROM contatos
WHERE ativo = true
  AND LOWER(email) LIKE '%@empresa.com'
ORDER BY email_normalizado ASC, num_ocorrencia ASC;`,
    expectedColumns: ["id", "nome_formatado", "email_normalizado", "num_ocorrencia"],
  },
  {
    id: 6,
    title: "Análise de Cohort e Retenção Mensal de Compras",
    difficulty: "Difícil",
    categories: ["Agrupamento", "Condicional", "CTEs", "Datas", "Filtragem", "JOINs"],
    category: "Agrupamento",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `Gere uma análise de Cohort mensal para medir a taxa de retenção de clientes por safra de entrada.

Utilize CTEs (\`WITH\`) para:
1. Descobrir o mês da primeira compra de cada cliente usando \`DATE_TRUNC('month', MIN(data_pedido))\`.
2. Cruzar com todos os pedidos finalizados e calcular a diferença em meses entre o pedido atual e a safra de entrada.
3. Classificar com \`CASE WHEN\` pedidos de clientes 'Novos' (mês 0) vs 'Recorrentes' (mês > 0).
4. Agrupar por safra e retornar o total financeiro transacionado.`,
    schemaSql: `CREATE TABLE clientes_cohort (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL
);

CREATE TABLE pedidos_cohort (
    id SERIAL PRIMARY KEY,
    cliente_id INT REFERENCES clientes_cohort(id),
    valor NUMERIC(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    data_pedido TIMESTAMP NOT NULL
);`,
    sampleTables: [
      {
        name: "pedidos_cohort",
        columns: ["id", "cliente_id", "valor", "status", "data_pedido"],
        rows: [
          { id: 1, cliente_id: 1, valor: "200.00", status: "FINALIZADO", data_pedido: "2026-01-05 10:00" },
          { id: 2, cliente_id: 1, valor: "350.00", status: "FINALIZADO", data_pedido: "2026-02-12 15:30" },
          { id: 3, cliente_id: 2, valor: "150.00", status: "FINALIZADO", data_pedido: "2026-02-18 11:20" },
        ],
      },
    ],
    starterSql: `WITH primeira_compra AS (
    SELECT 
        cliente_id, 
        DATE_TRUNC('month', MIN(data_pedido)) AS safra_mes
    FROM pedidos_cohort
    WHERE status = 'FINALIZADO'
    GROUP BY cliente_id
)
SELECT 
    pc.safra_mes,
    CASE 
        WHEN DATE_TRUNC('month', p.data_pedido) = pc.safra_mes THEN 'Novo'
        ELSE 'Recorrente'
    END AS tipo_cliente,
    COUNT(p.id) AS total_pedidos,
    SUM(p.valor) AS receita_total
FROM pedidos_cohort p
JOIN primeira_compra pc ON pc.cliente_id = p.cliente_id
WHERE p.status = 'FINALIZADO'
GROUP BY pc.safra_mes, tipo_cliente
ORDER BY pc.safra_mes ASC, tipo_cliente ASC;`,
    expectedColumns: ["safra_mes", "tipo_cliente", "total_pedidos", "receita_total"],
  },
  {
    id: 7,
    title: "Ranking Trimestral de Vendedores com Bonificação",
    difficulty: "Médio",
    categories: ["Condicional", "Datas", "Funções", "Janelas", "JOINs"],
    category: "Condicional",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `A diretoria de vendas instituiu um programa de bonificação escalonada por trimestre do ano.

Escreva uma consulta que calcule:
1. O trimestre da venda usando \`EXTRACT(QUARTER FROM data_venda)\`.
2. A soma de vendas por vendedor e por trimestre.
3. O ranking dos vendedores em cada trimestre via \`DENSE_RANK() OVER (PARTITION BY trimestre ORDER BY total_vendas DESC)\`.
4. Uma coluna de bônus condicional (\`CASE WHEN rank = 1 THEN '15%' WHEN rank = 2 THEN '10%' ELSE '5%' END\`).`,
    schemaSql: `CREATE TABLE vendedores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(80) NOT NULL
);

CREATE TABLE vendas_trimestre (
    id SERIAL PRIMARY KEY,
    vendedor_id INT REFERENCES vendedores(id),
    valor NUMERIC(10,2) NOT NULL,
    data_venda DATE NOT NULL
);`,
    sampleTables: [
      {
        name: "vendedores",
        columns: ["id", "nome"],
        rows: [
          { id: 1, nome: "Bruno Sales" },
          { id: 2, nome: "Camila Vendas" },
        ],
      },
    ],
    starterSql: `SELECT 
    v.nome,
    EXTRACT(QUARTER FROM vt.data_venda) AS trimestre,
    SUM(vt.valor) AS total_vendas,
    DENSE_RANK() OVER (
        PARTITION BY EXTRACT(QUARTER FROM vt.data_venda) 
        ORDER BY SUM(vt.valor) DESC
    ) AS posicao,
    CASE 
        WHEN DENSE_RANK() OVER (PARTITION BY EXTRACT(QUARTER FROM vt.data_venda) ORDER BY SUM(vt.valor) DESC) = 1 THEN '15% Bonus'
        WHEN DENSE_RANK() OVER (PARTITION BY EXTRACT(QUARTER FROM vt.data_venda) ORDER BY SUM(vt.valor) DESC) = 2 THEN '10% Bonus'
        ELSE '5% Bonus'
    END AS faixa_bonus
FROM vendedores v
JOIN vendas_trimestre vt ON vt.vendedor_id = v.id
GROUP BY v.id, v.nome, trimestre
ORDER BY trimestre ASC, posicao ASC;`,
    expectedColumns: ["nome", "trimestre", "total_vendas", "posicao", "faixa_bonus"],
  },
  {
    id: 8,
    title: "Localização de Clientes VIP com Filtros Especiais",
    difficulty: "Médio",
    categories: ["Datas", "Distintos", "Filtragem", "Subconsultas", "Texto"],
    category: "Datas",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `Descubra clientes com alto engajamento recente e padrões específicos de e-mail.

Regras da consulta:
1. Obtenha a lista sem duplicatas (\`DISTINCT\`) de cidades e nomes de clientes.
2. Filtre clientes cujo e-mail contenha domínio parceiro (\`LIKE '%@parceiro.com'\` ou \`LIKE '%@tech.com'\`).
3. O cliente deve ter ao menos um pedido realizado no ano de 2026 (\`EXTRACT(YEAR FROM data_pedido) = 2026\`).
4. Utilize uma subconsulta para garantir que o cliente realizou compras com valor acima da média geral da plataforma.`,
    schemaSql: `CREATE TABLE clientes_vip (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL,
    cidade VARCHAR(60) NOT NULL
);

CREATE TABLE pedidos_vip (
    id SERIAL PRIMARY KEY,
    cliente_id INT REFERENCES clientes_vip(id),
    valor NUMERIC(10,2) NOT NULL,
    data_pedido DATE NOT NULL
);`,
    sampleTables: [
      {
        name: "clientes_vip",
        columns: ["id", "nome", "email", "cidade"],
        rows: [
          { id: 1, nome: "Lucas Moura", email: "lucas@tech.com", cidade: "Campinas" },
          { id: 2, nome: "Renata Abreu", email: "renata@parceiro.com", cidade: "Curitiba" },
        ],
      },
    ],
    starterSql: `SELECT DISTINCT 
    c.nome, 
    c.cidade, 
    LOWER(c.email) AS email_contato
FROM clientes_vip c
JOIN pedidos_vip p ON p.cliente_id = c.id
WHERE (c.email LIKE '%@tech.com' OR c.email LIKE '%@parceiro.com')
  AND EXTRACT(YEAR FROM p.data_pedido) = 2026
  AND p.valor > (SELECT AVG(valor) FROM pedidos_vip)
ORDER BY c.nome ASC;`,
    expectedColumns: ["nome", "cidade", "email_contato"],
  },
  {
    id: 9,
    title: "Consolidação de Catálogo: Sem Giro vs Mais Vendidos",
    difficulty: "Fácil",
    categories: ["Agrupamento", "Conjuntos", "Filtragem", "JOINs"],
    category: "Agrupamento",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `A equipe de compras precisa de um catálogo combinado unificando produtos sem giro e os campeões de venda em uma só listagem.

Utilize a operação de conjunto \`UNION ALL\` para unificar:
1. Bloco 1: Produtos com 0 pedidos vinculados (\`LEFT JOIN\` com \`pedido_id IS NULL\`), rotulados como 'Sem Giro'.
2. Bloco 2: Os 3 produtos com maior quantidade total vendida, rotulados como 'Top Vendas'.`,
    schemaSql: `CREATE TABLE catalogo_itens (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(80) NOT NULL,
    preco NUMERIC(10,2) NOT NULL
);

CREATE TABLE compras_itens (
    id SERIAL PRIMARY KEY,
    item_id INT REFERENCES catalogo_itens(id),
    quantidade INT NOT NULL
);`,
    sampleTables: [
      {
        name: "catalogo_itens",
        columns: ["id", "nome", "preco"],
        rows: [
          { id: 1, nome: "Mouse Sem Fio", preco: "120.00" },
          { id: 2, nome: "Cabo HDMI 2m", preco: "35.00" },
          { id: 3, nome: "Suporte Monitor", preco: "89.00" },
        ],
      },
    ],
    starterSql: `(SELECT 
    ci.nome, 
    'Sem Giro' AS categoria_status, 
    0 AS total_unidades
FROM catalogo_itens ci
LEFT JOIN compras_itens c ON c.item_id = ci.id
WHERE c.id IS NULL)
UNION ALL
(SELECT 
    ci.nome, 
    'Top Vendas' AS categoria_status, 
    SUM(c.quantidade) AS total_unidades
FROM catalogo_itens ci
JOIN compras_itens c ON c.item_id = ci.id
GROUP BY ci.id, ci.nome
ORDER BY total_unidades DESC
LIMIT 3)
ORDER BY categoria_status ASC, nome ASC;`,
    expectedColumns: ["nome", "categoria_status", "total_unidades"],
  },
  {
    id: 10,
    title: "Cidades Únicas com Entregas Concluídas",
    difficulty: "Fácil",
    categories: ["Distintos", "Filtragem"],
    category: "Distintos",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `A logística precisa da relação geográfica única de todos os municípios atendidos com entregas bem-sucedidas.

Escreva uma consulta com \`DISTINCT\` que retorne a coluna de cidade dos clientes com pedidos entregues (\`status = 'ENTREGUE'\`), ordenando alfabeticamente.`,
    schemaSql: `CREATE TABLE rotas_clientes (
    id SERIAL PRIMARY KEY,
    cidade VARCHAR(60) NOT NULL
);

CREATE TABLE entregas (
    id SERIAL PRIMARY KEY,
    cliente_id INT REFERENCES rotas_clientes(id),
    status VARCHAR(20) NOT NULL
);`,
    sampleTables: [
      {
        name: "rotas_clientes",
        columns: ["id", "cidade"],
        rows: [
          { id: 1, cidade: "Campinas" },
          { id: 2, cidade: "São Paulo" },
          { id: 3, cidade: "Campinas" },
        ],
      },
    ],
    starterSql: `SELECT DISTINCT rc.cidade
FROM rotas_clientes rc
JOIN entregas e ON e.cliente_id = rc.id
WHERE e.status = 'ENTREGUE'
ORDER BY rc.cidade ASC;`,
    expectedColumns: ["cidade"],
  },
  {
    id: 11,
    title: "Padronização e Formatação de Textos de Usuários",
    difficulty: "Fácil",
    categories: ["Texto"],
    category: "Texto",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `Normalização cadastral de dados textuais.

Escreva uma consulta SQL que retorne o identificador do usuário e uma coluna formatada contendo o nome completo em maiúsculas (\`UPPER\`) e o primeiro nome extraído com \`SPLIT_PART(nome, ' ', 1)\`.`,
    schemaSql: `CREATE TABLE cadastros_brutos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    bio TEXT
);`,
    sampleTables: [
      {
        name: "cadastros_brutos",
        columns: ["id", "nome", "bio"],
        rows: [
          { id: 1, nome: "Carlos Eduardo", bio: "Engenheiro de Dados" },
          { id: 2, nome: "Ana Beatriz", bio: "Analista de BI" },
        ],
      },
    ],
    starterSql: `SELECT 
    id,
    UPPER(TRIM(nome)) AS nome_completo,
    SPLIT_PART(TRIM(nome), ' ', 1) AS primeiro_nome
FROM cadastros_brutos
ORDER BY id ASC;`,
    expectedColumns: ["id", "nome_completo", "primeiro_nome"],
  },
  {
    id: 12,
    title: "Média Salarial por Departamento com Cláusula HAVING",
    difficulty: "Médio",
    categories: ["Agrupamento", "Filtragem", "Funções", "JOINs"],
    category: "Agrupamento",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `A diretoria de Recursos Humanos deseja identificar os departamentos mais onerosos da empresa.

Escreva uma consulta SQL que retorne o **nome do departamento**, a **quantidade de colaboradores ativos** e a **média salarial** (arredondada para 2 casas decimais com \`ROUND(..., 2)\`).

**Regras:**
- Considere apenas funcionários com \`ativo = true\`.
- Filtre via \`HAVING\` apenas os departamentos com média salarial superior a R$ 5.000,00 e que possuam no mínimo 2 colaboradores.
- Ordene pela média salarial em ordem decrescente, e em caso de empate, alfabeticamente pelo nome do departamento.`,
    schemaSql: `CREATE TABLE departamentos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(80) NOT NULL
);

CREATE TABLE funcionarios (
    id SERIAL PRIMARY KEY,
    departamento_id INT NOT NULL REFERENCES departamentos(id),
    nome VARCHAR(100) NOT NULL,
    salario NUMERIC(10,2) NOT NULL,
    ativo BOOLEAN DEFAULT true
);`,
    sampleTables: [
      {
        name: "departamentos",
        columns: ["id", "nome"],
        rows: [
          { id: 1, nome: "Engenharia de Software" },
          { id: 2, nome: "Marketing" },
          { id: 3, nome: "Ciência de Dados" },
        ],
      },
      {
        name: "funcionarios",
        columns: ["id", "departamento_id", "nome", "salario", "ativo"],
        rows: [
          { id: 1, departamento_id: 1, nome: "Lucas Lima", salario: "7500.00", ativo: true },
          { id: 2, departamento_id: 1, nome: "Paula Souza", salario: "8200.00", ativo: true },
          { id: 3, departamento_id: 2, nome: "Rodrigo Matos", salario: "3500.00", ativo: true },
          { id: 4, departamento_id: 3, nome: "Camila Duarte", salario: "9000.00", ativo: true },
          { id: 5, departamento_id: 3, nome: "Gabriel Ramos", salario: "6500.00", ativo: true },
        ],
      },
    ],
    starterSql: `SELECT 
    d.nome AS departamento,
    COUNT(f.id) AS quantidade_colaboradores,
    ROUND(AVG(f.salario), 2) AS media_salarial
FROM departamentos d
JOIN funcionarios f ON f.departamento_id = d.id
WHERE f.ativo = true
GROUP BY d.id, d.nome
HAVING AVG(f.salario) > 5000.00 AND COUNT(f.id) >= 2
ORDER BY media_salarial DESC, departamento ASC;`,
    expectedColumns: ["departamento", "quantidade_colaboradores", "media_salarial"],
  },
  {
    id: 13,
    title: "Comparativo de Vendas com Mês Anterior usando LAG",
    difficulty: "Difícil",
    categories: ["Datas", "Funções", "Janelas"],
    category: "Janelas",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `A equipe financeira precisa acompanhar a evolução mensal das receitas do e-commerce.

Utilize a função analítica de janela \`LAG()\` para obter o faturamento do mês anterior e calcular a diferença bruta (\`total_faturado - faturamento_anterior\`).

**Regras:**
- Para o primeiro mês registrado (sem histórico prévio), retorne 0 no faturamento anterior e 0 na diferença.
- Ordene cronologicamente pelo mês de referência.`,
    schemaSql: `CREATE TABLE vendas_mensais (
    id SERIAL PRIMARY KEY,
    mes_referencia DATE NOT NULL UNIQUE,
    total_faturado NUMERIC(12,2) NOT NULL
);`,
    sampleTables: [
      {
        name: "vendas_mensais",
        columns: ["id", "mes_referencia", "total_faturado"],
        rows: [
          { id: 1, mes_referencia: "2026-01-01", total_faturado: "45000.00" },
          { id: 2, mes_referencia: "2026-02-01", total_faturado: "52000.00" },
          { id: 3, mes_referencia: "2026-03-01", total_faturado: "49500.00" },
          { id: 4, mes_referencia: "2026-04-01", total_faturado: "61000.00" },
        ],
      },
    ],
    starterSql: `SELECT 
    mes_referencia,
    total_faturado,
    COALESCE(LAG(total_faturado) OVER (ORDER BY mes_referencia ASC), 0) AS faturamento_anterior,
    total_faturado - COALESCE(LAG(total_faturado) OVER (ORDER BY mes_referencia ASC), total_faturado) AS diferenca_mensal
FROM vendas_mensais
ORDER BY mes_referencia ASC;`,
    expectedColumns: ["mes_referencia", "total_faturado", "faturamento_anterior", "diferenca_mensal"],
  },
  {
    id: 14,
    title: "Clientes Recorrentes Sem Reclamações Abertas (NOT EXISTS)",
    difficulty: "Médio",
    categories: ["Filtragem", "Funções", "JOINs", "Subconsultas"],
    category: "Subconsultas",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `A gerência de Sucesso do Cliente deseja premiar clientes fiéis e satisfeitos.

Escreva uma consulta que retorne o **id do cliente**, o **nome** e a **quantidade de pedidos**, selecionando apenas quem realizou mais de 2 compras e que **NÃO** possua chamados de suporte abertos (\`status = 'ABERTO'\`).

**Regras:**
- Utilize \`NOT EXISTS\` para verificar os chamados de suporte.
- Ordene da maior quantidade de pedidos para a menor; em empate, pelo nome alfabeticamente.`,
    schemaSql: `CREATE TABLE clientes_loja (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL
);

CREATE TABLE pedidos_compra (
    id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL REFERENCES clientes_loja(id),
    valor NUMERIC(10,2) NOT NULL
);

CREATE TABLE suporte_chamados (
    id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL REFERENCES clientes_loja(id),
    assunto VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL
);`,
    sampleTables: [
      {
        name: "clientes_loja",
        columns: ["id", "nome", "email"],
        rows: [
          { id: 1, nome: "Beatriz Ramos", email: "beatriz@email.com" },
          { id: 2, nome: "Fernando Dias", email: "fernando@email.com" },
          { id: 3, nome: "Juliana Mendes", email: "juliana@email.com" },
        ],
      },
      {
        name: "pedidos_compra",
        columns: ["id", "cliente_id", "valor"],
        rows: [
          { id: 101, cliente_id: 1, valor: "250.00" },
          { id: 102, cliente_id: 1, valor: "180.00" },
          { id: 103, cliente_id: 1, valor: "400.00" },
          { id: 104, cliente_id: 2, valor: "520.00" },
          { id: 105, cliente_id: 3, valor: "110.00" },
        ],
      },
      {
        name: "suporte_chamados",
        columns: ["id", "cliente_id", "assunto", "status"],
        rows: [
          { id: 1, cliente_id: 2, assunto: "Atraso na entrega", status: "ABERTO" },
          { id: 2, cliente_id: 1, assunto: "Dúvida cadastral", status: "RESOLVIDO" },
        ],
      },
    ],
    starterSql: `SELECT 
    c.id AS cliente_id,
    c.nome,
    COUNT(p.id) AS total_pedidos
FROM clientes_loja c
JOIN pedidos_compra p ON p.cliente_id = c.id
WHERE NOT EXISTS (
    SELECT 1 
    FROM suporte_chamados s 
    WHERE s.cliente_id = c.id AND s.status = 'ABERTO'
)
GROUP BY c.id, c.nome
HAVING COUNT(p.id) > 2
ORDER BY total_pedidos DESC, c.nome ASC;`,
    expectedColumns: ["cliente_id", "nome", "total_pedidos"],
  },
  {
    id: 15,
    title: "Hierarquia de Gestão Organizacional com CTE Recursiva",
    difficulty: "Difícil",
    categories: ["CTEs", "Filtragem", "JOINs"],
    category: "CTEs",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `Mapeie toda a cadeia de liderança da empresa a partir do CEO (\`gestor_id IS NULL\`) até os colaboradores da base.

Construa uma consulta com \`WITH RECURSIVE\` que calcule a profundidade hierárquica (nível 1 para o CEO, nível 2 para diretores reportando ao CEO, nível 3 para gerentes, etc.).

**Regras:**
- Retorne as colunas: \`id\`, \`nome\`, \`cargo\` e \`nivel_hierarquia\`.
- Ordene pelo nível hierárquico ascendente e depois pelo nome do colaborador em ordem alfabética.`,
    schemaSql: `CREATE TABLE colaboradores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    cargo VARCHAR(80) NOT NULL,
    gestor_id INT REFERENCES colaboradores(id)
);`,
    sampleTables: [
      {
        name: "colaboradores",
        columns: ["id", "nome", "cargo", "gestor_id"],
        rows: [
          { id: 1, nome: "Helena Castro", cargo: "CEO", gestor_id: null },
          { id: 2, nome: "Marcelo Dantas", cargo: "Diretor de Tecnologia", gestor_id: 1 },
          { id: 3, nome: "Patricia Luz", cargo: "Diretora Comercial", gestor_id: 1 },
          { id: 4, nome: "Guilherme Santos", cargo: "Tech Lead", gestor_id: 2 },
          { id: 5, nome: "Larissa Faria", cargo: "Engenheira Sênior", gestor_id: 4 },
        ],
      },
    ],
    starterSql: `WITH RECURSIVE arvore_gestao AS (
    SELECT 
        id, 
        nome, 
        cargo, 
        gestor_id, 
        1 AS nivel_hierarquia
    FROM colaboradores
    WHERE gestor_id IS NULL

    UNION ALL

    SELECT 
        c.id, 
        c.nome, 
        c.cargo, 
        c.gestor_id, 
        ag.nivel_hierarquia + 1
    FROM colaboradores c
    JOIN arvore_gestao ag ON c.gestor_id = ag.id
)
SELECT 
    id,
    nome,
    cargo,
    nivel_hierarquia
FROM arvore_gestao
ORDER BY nivel_hierarquia ASC, nome ASC;`,
    expectedColumns: ["id", "nome", "cargo", "nivel_hierarquia"],
  },
  {
    id: 16,
    title: "Primeiro Pedido de Cada Cliente com DISTINCT ON",
    difficulty: "Médio",
    categories: ["Datas", "Distintos", "JOINs"],
    category: "Distintos",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `No PostgreSQL, a sintaxe \`DISTINCT ON (expressao)\` é altamente recomendada para deduplicação com base em ordenação específica.

Escreva uma consulta que retorne a primeira compra histórica realizada por cada cliente (menor data de compra).

**Regras:**
- Retorne as colunas: \`comprador_id\`, \`nome\`, \`primeira_data\` e \`primeiro_valor\`.
- Ordene obrigatoriamente por \`c.id ASC, p.data_compra ASC\`.`,
    schemaSql: `CREATE TABLE compradores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL
);

CREATE TABLE historico_pedidos (
    id SERIAL PRIMARY KEY,
    comprador_id INT NOT NULL REFERENCES compradores(id),
    data_compra TIMESTAMP NOT NULL,
    valor NUMERIC(10,2) NOT NULL
);`,
    sampleTables: [
      {
        name: "compradores",
        columns: ["id", "nome"],
        rows: [
          { id: 1, nome: "Lucas Azevedo" },
          { id: 2, nome: "Mariana Prado" },
        ],
      },
      {
        name: "historico_pedidos",
        columns: ["id", "comprador_id", "data_compra", "valor"],
        rows: [
          { id: 10, comprador_id: 1, data_compra: "2026-01-10 14:00", valor: "150.00" },
          { id: 11, comprador_id: 1, data_compra: "2026-02-15 09:30", valor: "320.00" },
          { id: 12, comprador_id: 2, data_compra: "2026-01-05 11:20", valor: "890.00" },
          { id: 13, comprador_id: 2, data_compra: "2026-01-20 18:00", valor: "45.00" },
        ],
      },
    ],
    starterSql: `SELECT DISTINCT ON (c.id)
    c.id AS comprador_id,
    c.nome,
    p.data_compra AS primeira_data,
    p.valor AS primeiro_valor
FROM compradores c
JOIN historico_pedidos p ON p.comprador_id = c.id
ORDER BY c.id ASC, p.data_compra ASC;`,
    expectedColumns: ["comprador_id", "nome", "primeira_data", "primeiro_valor"],
  },
  {
    id: 17,
    title: "Auditoria de Emails Não Corporativos e Extração de Domínios",
    difficulty: "Fácil",
    categories: ["Filtragem", "Funções", "Texto"],
    category: "Texto",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `A equipe de segurança da informação precisa auditar colaboradores ativos que estejam cadastrados com emails pessoais externos (que não terminam com \`@sqlarena.com\`).

Escreva uma consulta que extraia o nome limpo com \`TRIM()\`, o email em minúsculas com \`LOWER()\` e o domínio do provedor utilizando \`SUBSTRING\` e \`POSITION('@' IN email)\`.

**Regras:**
- Filtre apenas colaboradores com \`ativo = true\` e cujo email não pertença ao domínio \`@sqlarena.com\`.
- Ordene pelo identificador \`id\` em ordem ascendente.`,
    schemaSql: `CREATE TABLE usuarios_sistema (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL,
    ativo BOOLEAN DEFAULT true
);`,
    sampleTables: [
      {
        name: "usuarios_sistema",
        columns: ["id", "nome", "email", "ativo"],
        rows: [
          { id: 1, nome: "  Gabriel Ramos ", email: "gabriel@gmail.com", ativo: true },
          { id: 2, nome: "Luciana Alves", email: "luciana@sqlarena.com", ativo: true },
          { id: 3, nome: "Vanessa Costa", email: "vanessa@yahoo.com.br", ativo: true },
          { id: 4, nome: "Renato Silveira", email: "renato@hotmail.com", ativo: false },
        ],
      },
    ],
    starterSql: `SELECT 
    id,
    TRIM(nome) AS nome,
    LOWER(TRIM(email)) AS email_formatado,
    SUBSTRING(LOWER(TRIM(email)) FROM POSITION('@' IN email) + 1) AS dominio
FROM usuarios_sistema
WHERE email NOT LIKE '%@sqlarena.com' AND ativo = true
ORDER BY id ASC;`,
    expectedColumns: ["id", "nome", "email_formatado", "dominio"],
  },
  {
    id: 18,
    title: "Classificação de Risco de Crédito com Expressão CASE",
    difficulty: "Fácil",
    categories: ["Condicional", "Filtragem"],
    category: "Condicional",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `Uma fintech precisa categorizar os clientes para concessão de limite de cartão de crédito.

Escreva uma consulta com a instrução condicional \`CASE\` que classifique o risco do cliente:
- \`'ALTO'\`: Se o cliente estiver com restrição cadastral (\`negativado = true\`) ou possuir score inferior a 500.
- \`'MÉDIO'\`: Se o score estiver entre 500 e 749 (inclusive) e não for negativado.
- \`'BAIXO'\`: Para todos os demais clientes (score igual ou maior que 750 sem restrição).

**Regras:**
- Ordene a listagem pelo score em ordem decrescente; em caso de empate, pelo nome do titular alfabeticamente.`,
    schemaSql: `CREATE TABLE contas_credito (
    id SERIAL PRIMARY KEY,
    titular VARCHAR(100) NOT NULL,
    score_serasa INT NOT NULL,
    negativado BOOLEAN DEFAULT false
);`,
    sampleTables: [
      {
        name: "contas_credito",
        columns: ["id", "titular", "score_serasa", "negativado"],
        rows: [
          { id: 1, titular: "Roberta Mendes", score_serasa: 820, negativado: false },
          { id: 2, titular: "Danilo Cunha", score_serasa: 610, negativado: false },
          { id: 3, titular: "Sérgio Moraes", score_serasa: 430, negativado: false },
          { id: 4, titular: "Priscila Antunes", score_serasa: 790, negativado: true },
        ],
      },
    ],
    starterSql: `SELECT 
    id,
    titular,
    score_serasa,
    CASE 
        WHEN negativado = true OR score_serasa < 500 THEN 'ALTO'
        WHEN score_serasa BETWEEN 500 AND 749 THEN 'MÉDIO'
        ELSE 'BAIXO'
    END AS classificacao_risco
FROM contas_credito
ORDER BY score_serasa DESC, titular ASC;`,
    expectedColumns: ["id", "titular", "score_serasa", "classificacao_risco"],
  },
  {
    id: 19,
    title: "Produtos sem Saída no Trimestre usando EXCEPT",
    difficulty: "Médio",
    categories: ["Conjuntos", "Filtragem", "Subconsultas"],
    category: "Conjuntos",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `A gestão de suprimentos precisa identificar quais produtos ativos do catálogo NÃO tiveram nenhuma saída registrada no trimestre atual.

Utilize o operador relacional de conjuntos \`EXCEPT\` para subtrair os produtos vendidos do catálogo geral ativo.

**Regras:**
- Retorne apenas o código \`sku\` e o \`nome_produto\`.
- Ordene o resultado final alfabeticamente pelo código \`sku\` em ordem ascendente.`,
    schemaSql: `CREATE TABLE catalogo_geral (
    sku VARCHAR(20) PRIMARY KEY,
    nome_produto VARCHAR(100) NOT NULL,
    ativo BOOLEAN DEFAULT true
);

CREATE TABLE vendas_trimestre (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(20) NOT NULL REFERENCES catalogo_geral(sku),
    quantidade INT NOT NULL
);`,
    sampleTables: [
      {
        name: "catalogo_geral",
        columns: ["sku", "nome_produto", "ativo"],
        rows: [
          { sku: "PROD-001", nome_produto: "Mouse Óptico USB", ativo: true },
          { sku: "PROD-002", nome_produto: "Webcam Full HD", ativo: true },
          { sku: "PROD-003", nome_produto: "Suporte Ergonômico", ativo: true },
          { sku: "PROD-004", nome_produto: "Hub USB-C 7 portas", ativo: true },
        ],
      },
      {
        name: "vendas_trimestre",
        columns: ["id", "sku", "quantidade"],
        rows: [
          { id: 1, sku: "PROD-001", quantidade: 15 },
          { id: 2, sku: "PROD-003", quantidade: 8 },
        ],
      },
    ],
    starterSql: `SELECT sku, nome_produto
FROM catalogo_geral
WHERE ativo = true
EXCEPT
SELECT cg.sku, cg.nome_produto
FROM catalogo_geral cg
JOIN vendas_trimestre vt ON vt.sku = cg.sku
ORDER BY sku ASC;`,
    expectedColumns: ["sku", "nome_produto"],
  },
  {
    id: 20,
    title: "Tempo Médio de Resolução de Chamados em Horas",
    difficulty: "Médio",
    categories: ["Agrupamento", "Datas", "Filtragem", "Funções"],
    category: "Datas",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `Calcule a métrica de SLA da central de atendimento técnico ao cliente.

Escreva uma consulta SQL que calcule para cada categoria de suporte a **quantidade total de chamados resolvidos** e o **tempo médio de atendimento em horas** (diferença entre \`data_fechamento\` e \`data_abertura\`), arredondado para 2 casas decimais.

**Regras:**
- No PostgreSQL, use \`AVG(EXTRACT(EPOCH FROM (data_fechamento - data_abertura)) / 3600)\` para a média de horas.
- Considere apenas chamados com \`status = 'RESOLVIDO'\` e \`data_fechamento IS NOT NULL\`.
- Ordene do menor tempo médio para o maior; havendo empate, pelo nome da categoria alfabeticamente.`,
    schemaSql: `CREATE TABLE tickets_suporte (
    id SERIAL PRIMARY KEY,
    categoria VARCHAR(50) NOT NULL,
    data_abertura TIMESTAMP NOT NULL,
    data_fechamento TIMESTAMP,
    status VARCHAR(20) NOT NULL
);`,
    sampleTables: [
      {
        name: "tickets_suporte",
        columns: ["id", "categoria", "data_abertura", "data_fechamento", "status"],
        rows: [
          { id: 1, categoria: "Acesso e Senha", data_abertura: "2026-03-01 08:00:00", data_fechamento: "2026-03-01 10:30:00", status: "RESOLVIDO" },
          { id: 2, categoria: "Acesso e Senha", data_abertura: "2026-03-01 09:00:00", data_fechamento: "2026-03-01 10:00:00", status: "RESOLVIDO" },
          { id: 3, categoria: "Cobrança", data_abertura: "2026-03-01 10:00:00", data_fechamento: "2026-03-02 12:00:00", status: "RESOLVIDO" },
          { id: 4, categoria: "Cobrança", data_abertura: "2026-03-02 14:00:00", data_fechamento: null, status: "EM_ANDAMENTO" },
        ],
      },
    ],
    starterSql: `SELECT 
    categoria,
    COUNT(id) AS total_resolvidos,
    ROUND(AVG(EXTRACT(EPOCH FROM (data_fechamento - data_abertura)) / 3600)::NUMERIC, 2) AS tempo_medio_horas
FROM tickets_suporte
WHERE status = 'RESOLVIDO' AND data_fechamento IS NOT NULL
GROUP BY categoria
ORDER BY tempo_medio_horas ASC, categoria ASC;`,
    expectedColumns: ["categoria", "total_resolvidos", "tempo_medio_horas"],
  },
  {
    id: 21,
    title: "Desempenho Global de Cursos Online (5 Categorias)",
    difficulty: "Difícil",
    categories: ["Agrupamento", "Condicional", "Filtragem", "Funções", "JOINs"],
    category: "Agrupamento",
    status: "UNSOLVED",
    publishedStatus: "PUBLISHED",
    description: `A diretoria de uma plataforma de educação a distância quer um painel analítico abrangente de cada curso ofertado.

Escreva uma consulta que consolide para cada curso:
1. **total_matriculas**: Quantidade total de inscrições.
2. **receita_total**: Somatório dos pagamentos confirmados (\`m.pago = true\`), multiplicando pelo preço do curso.
3. **taxa_conclusao_pct**: Porcentagem de alunos que concluíram (\`m.concluido = true\`) sobre o total de matrículas, com 1 casa decimal.
4. **status_performance**: 
   - \`'Top Performer'\`: Mais de 2 matrículas e receita igual ou superior a R$ 1.000,00.
   - \`'Desempenho Regular'\`: Ao menos 1 matrícula.
   - \`'Sem Vendas'\`: Nenhuma matrícula.

**Regras:**
- Utilize \`LEFT JOIN\` para garantir que cursos sem matrícula também sejam exibidos no relatório com valores zerados.
- Ordene pela receita total decrescente, total de matrículas decrescente e pelo título do curso alfabeticamente.`,
    schemaSql: `CREATE TABLE cursos (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(100) NOT NULL,
    preco NUMERIC(10,2) NOT NULL
);

CREATE TABLE matriculas (
    id SERIAL PRIMARY KEY,
    curso_id INT NOT NULL REFERENCES cursos(id),
    aluno_id INT NOT NULL,
    pago BOOLEAN DEFAULT true,
    concluido BOOLEAN DEFAULT false
);`,
    sampleTables: [
      {
        name: "cursos",
        columns: ["id", "titulo", "preco"],
        rows: [
          { id: 1, titulo: "PostgreSQL do Básico ao Avançado", preco: "450.00" },
          { id: 2, titulo: "Modelagem Dimensional e Star Schema", preco: "550.00" },
          { id: 3, titulo: "Otimização de Queries e EXPLAIN ANALYZE", preco: "600.00" },
        ],
      },
      {
        name: "matriculas",
        columns: ["id", "curso_id", "aluno_id", "pago", "concluido"],
        rows: [
          { id: 1, curso_id: 1, aluno_id: 10, pago: true, concluido: true },
          { id: 2, curso_id: 1, aluno_id: 11, pago: true, concluido: true },
          { id: 3, curso_id: 1, aluno_id: 12, pago: true, concluido: false },
          { id: 4, curso_id: 2, aluno_id: 10, pago: true, concluido: false },
        ],
      },
    ],
    starterSql: `SELECT 
    c.id AS curso_id,
    c.titulo,
    COUNT(m.id) AS total_matriculas,
    COALESCE(SUM(CASE WHEN m.pago = true THEN c.preco ELSE 0 END), 0) AS receita_total,
    ROUND(
        (COUNT(CASE WHEN m.concluido = true THEN 1 END)::NUMERIC / NULLIF(COUNT(m.id), 0)) * 100, 
        1
    ) AS taxa_conclusao_pct,
    CASE 
        WHEN COUNT(m.id) >= 2 AND COALESCE(SUM(CASE WHEN m.pago = true THEN c.preco ELSE 0 END), 0) >= 1000.00 THEN 'Top Performer'
        WHEN COUNT(m.id) >= 1 THEN 'Desempenho Regular'
        ELSE 'Sem Vendas'
    END AS status_performance
FROM cursos c
LEFT JOIN matriculas m ON m.curso_id = c.id
GROUP BY c.id, c.titulo
ORDER BY receita_total DESC, total_matriculas DESC, c.titulo ASC;`,
    expectedColumns: ["curso_id", "titulo", "total_matriculas", "receita_total", "taxa_conclusao_pct", "status_performance"],
  },
];
