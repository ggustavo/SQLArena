
## 1. Visão Geral

A API do SQLArena é construída em **FastAPI**, em `app/backend/`. Ela expõe as rotas que o
frontend (`frontend/src/services/*`) já espera consumir em `http://localhost:8000/api/*`,
e conecta com o S3 (`S3Manager`) e o DynamoDB (`DynamoDBManager`).

### Estrutura de Arquivos

```text
app/backend/
├── main.py              # Ponto de entrada: cria o FastAPI app, CORS, inclui as rotas
├── dependencies.py       # Injeção de dependência: instancia S3Manager e DynamoDBManager
├── store.py              # Armazenamento EM MEMÓRIA dos metadados de questão (placeholder)
└── routers/
    ├── questions.py       # CRUD de exercícios
    └── audit.py           # Log de auditoria (CRUD actions)
```

---

## 2. Como Rodar

```bash
# com o venv ativado, Ministack no ar e terraform já aplicado
uvicorn app.backend.main:app --reload --port 8000
```

Teste rápido:
```bash
curl http://localhost:8000/api/health
# -> {"status":"ok"}
```

O CORS já libera o frontend Vite (`http://localhost:5173`) e `http://localhost:3000` por
padrão, então basta rodar o `npm run dev` do frontend em paralelo e desligar o `USE_MOCK`
em `frontend/src/services/api.js` para conversar com a API real.

---

## 3. Rotas Disponíveis

### `GET /api/health`
Checagem simples de que a API está no ar. Sem dependência de AWS.

### `GET /api/questions`
Lista todas as questões cadastradas (em memória — ver seção 5).

### `GET /api/questions/{id}`
Detalhe de uma questão. `404` se não existir.

### `POST /api/questions`
Cria uma questão nova. **Corpo em `multipart/form-data`** (não JSON — ver seção 6), campos:

| Campo | Obrigatório | Descrição |
|---|---|---|
| `title` | sim | Título do exercício |
| `schema_sql` | sim | DDL (`CREATE TABLE`, etc.) |
| `data_sql` | sim | DML de carga inicial |
| `answer_sql` | sim | Gabarito — **precisa conter `ORDER BY`**, senão retorna `422` |
| `difficulty` | não (padrão `"Médio"`) | |
| `category` | não (padrão `"Geral"`) | |
| `user_id` | não (padrão `"sistema"`) | Quem está criando — ver TODO(AUTH) na seção 7 |

O que acontece por baixo, em ordem:
1. `S3Manager.ensure_bucket_exists()` + `upload_question_sql_files(...)` — sobe os 3 `.sql`.
2. `DynamoDBManager.log_crud_action("CREATE_EXERCISE", ...)` — registra a ação no log de
   auditoria, com `changed_data` contendo título/dificuldade/categoria.
3. Retorna a questão criada (com `id` gerado).

### `POST /api/questions/{id}/publish`
Marca a questão como `PUBLISHED`. Loga `PUBLISH_EXERCISE` no DynamoDB. **Não espera corpo**
na requisição (o frontend hoje chama sem `data`) — `user_id` é opcional via query string.

### `DELETE /api/questions/{id}`
Remove a questão. Também **sem corpo esperado**. Por baixo:
1. `S3Manager.delete_question_files(id)` — remove os `.sql` do S3 de uma vez.
2. Publica `DELETE_QUESTION` no SQS (mesmo padrão descrito em `docs/s3.md`, seção 5 — avisa
   os workers pra rodarem `DROP SCHEMA IF EXISTS pergunta_{id} CASCADE;`).
3. Loga `DELETE_EXERCISE` no DynamoDB.

### `GET /api/audit/logs?limit=N`
Lista as ações de CRUD mais recentes. Chama direto `DynamoDBManager.list_crud_actions(limit)`.

### `POST /api/audit/logs`
Registra uma ação de auditoria manualmente. Corpo em **JSON**:

```json
{
  "action_type": "PUBLISH_EXERCISE",
  "entity": "exercise",
  "entity_id": "2",
  "user_id": "professor-7",
  "details": "Questão publicada para os alunos."
}
```

Essa rota existe principalmente pra resolver uma divergência de contrato: o frontend
(`auditService.js`) manda um campo `details` (texto livre), enquanto o
`DynamoDBManager.log_crud_action` usa `changed_data` (dicionário estruturado). O endpoint
faz esse mapeamento automaticamente — internamente vira
`changed_data={"details": "..."}` — então nenhum dos dois lados precisou mudar.

> Os campos `action_id` e `created_at`, se vierem no corpo, são **ignorados de propósito**:
> o backend é a fonte da verdade e gera os dois no servidor, pra evitar IDs duplicados ou
> timestamps de clientes diferentes fora de sincronia.

---

## 4. Testes

Não existe (ainda) um test runner formal pra esse módulo — a validação foi feita com
`fastapi.testclient.TestClient` + a lib `moto` (mock real de S3/DynamoDB/SQS), simulando
exatamente as chamadas que o frontend faz hoje, incluindo os casos sem corpo
(`publish`/`delete`). Todos os 6 endpoints foram exercitados nesse teste antes do código
ser entregue.

Pra testar manualmente contra o Ministack:
```bash
curl -X POST http://localhost:8000/api/questions \
  -F "title=Top clientes" \
  -F "schema_sql=CREATE TABLE orders (id INT);" \
  -F "data_sql=INSERT INTO orders VALUES (1);" \
  -F "answer_sql=SELECT * FROM orders ORDER BY id;"

curl http://localhost:8000/api/questions
curl http://localhost:8000/api/audit/logs
```

---

## 5. Limitação Conhecida: Metadados em Memória (TODO RDS)

`app/backend/store.py` guarda `title`, `difficulty`, `category` e `status` num dicionário
Python em memória — **não é o RDS** . Duas consequências práticas:

- Reiniciar o `uvicorn` apaga todas as questões cadastradas.
- Os IDs são sequenciais e só existem nessa instância do processo.

O `store.py` foi escrito como uma camada isolada de propósito: as rotas em
`questions.py` só chamam `store.create()`, `store.get()`, `store.list_all()`,
`store.update()`, `store.delete()` — quando o RDS existir, essas 5 funções podem ser
reescritas para fazer queries reais no Postgres **sem precisar tocar nos routers**.
Procure por `TODO(RDS)` no código.

---

## 6. Detalhe de Implementação: `multipart/form-data` vs JSON

O `POST /api/questions` espera `multipart/form-data`, não JSON. Isso é proposital — é o
formato padrão pra upload de arquivo, e é o que vai ser necessário se/quando o dataset CSV
voltar (ver seção 7). O `api.js` do frontend, porém, usa
`headers: {"Content-Type": "application/json"}` por padrão.

**Atenção pra quem for ligar esse endpoint no frontend de verdade:** essa chamada
específica (`createQuestion`) vai precisar montar um `FormData` e deixar o Axios definir o
`Content-Type` automaticamente (não usar o header JSON herdado da instância padrão), ou a
requisição vai falhar.

Já os outros endpoints (`publish`, `delete`, `audit/logs`) foram ajustados pra bater com o
jeito que o frontend já chama hoje (sem corpo, ou com JSON simples).

---

## 7. TODOs Pendentes

**`TODO(RDS)`** — metadados de questão em memória, ver seção 5.

**`TODO(CSV)`** — o upload de `dataset.csv` (arquivo binário do Requisito 3) foi retirado
do `POST /api/questions` por decisão do time (ficar só com os `.sql` por enquanto),
pendente de confirmação com o professor sobre se isso atende ao requisito do enunciado
("Dentre as informações manipuladas pela aplicação, uma obrigatoriamente deve ser um
arquivo binário"). O suporte já existe pronto e testado — se a resposta for "precisa de
binário", é restaurar `S3Manager.upload_question_dataset_csv` (código já escrito antes,
só não está na `main` no momento) e o parâmetro `dataset_csv` no router. Ver comentário no
topo de `app/backend/routers/questions.py`.

**`TODO(AUTH)`** — `user_id` hoje é só um campo de formulário/query com valor padrão
`"sistema"`, sem nenhuma verificação. O frontend já manda um JWT no header
`Authorization: Bearer <token>` (interceptor em `api.js`), mas o backend ainda não decodifica
esse token pra extrair o usuário real — quem fizer a autenticação vai precisar trocar esse
valor padrão por algo extraído do token.

---

## 8. Perguntas que o time pode receber

**"O backend já está rodando de verdade, ou é só mock?"**
É real — conecta no S3 e DynamoDB de verdade (via Ministack localmente). O único dado que
ainda não é real é o metadado da questão (título, status etc.), que fica em memória até o
RDS ser integrado.

**"Por que criar/editar questão precisa ser multipart e não JSON?"**
Porque é upload de arquivo (os `.sql`, e potencialmente o CSV no futuro) — multipart é o
formato padrão da web pra isso. Ver seção 6.

---

## 9. Onde Está o Código

| O quê | Arquivo |
|---|---|
| App FastAPI (CORS, rotas) | `app/backend/main.py` |
| Injeção de dependência (S3/DynamoDB) | `app/backend/dependencies.py` |
| Metadados de questão (placeholder RDS) | `app/backend/store.py` |
| Rotas de questão | `app/backend/routers/questions.py` |
| Rotas de auditoria | `app/backend/routers/audit.py` |
| Dependências Python (fastapi, uvicorn, python-multipart, sqlalchemy, etc.) | `app/requirements.txt` |

---

## 10. Integração Concluída: RDS PostgreSQL, Autenticação JWT e Worker Sandbox

Os itens marcados como `TODO(RDS)` e `TODO(AUTH)` foram **100% implementados e integrados**:

1. **RDS PostgreSQL Relacional (`app/database/`):**
   - Modelos SQLAlchemy 2.0 reais (`User`, `Category`, `Question`, `question_categories`, `UserSolvedQuestion`).
   - Seed automático populando 12 categorias em ordem alfabética e 21 questões reais com upload para o S3.
   - IDs agora são gerados e persistidos no banco de dados relacional.

2. **Autenticação JWT Real (`app/auth/` e `app/api/auth.py`):**
   - Senhas criptografadas com `bcrypt`.
   - Emissão de tokens JWT com validação de claims (`sub`, `role`, `email`, `name`).
   - Dependência `get_current_user` e `require_instructor` protegendo endpoints administrativos.

3. **Submissões Assíncronas e Worker Sandbox (`app/worker/` e `app/api/submissions.py`):**
   - Rate limit atômico de 5 segundos via Redis por aluno (`ratelimit:{user_id}`).
   - Publicação na fila Amazon SQS `sqlarena-submissions-queue`.
   - Sandbox de execução em PostgreSQL 16 com schema isolado por questão (`pergunta_{id}`), modo Read-Only estrito e timeout de 3000ms.
   - Comparação determinística O(1) com Hash SHA-256 e pontuação de +10 XP no RDS para resoluções inéditas.
   - Registro imutável de todas as tentativas no DynamoDB (`sqlarena-submissions-log`).

4. **Compatibilidade dos Pontos de Entrada:**
   A aplicação pode ser iniciada indistintamente com qualquer um dos comandos:
   ```bash
   uvicorn app.main:app --reload --port 8000
   # ou
   uvicorn app.backend.main:app --reload --port 8000
   ```
