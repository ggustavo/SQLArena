# ⚡ Testes de Carga e Estresse - SQLArena (Locust)

Esta pasta contém a suíte completa de testes de carga e simulação distribuída com **Locust** para avaliar a performance da Camada Web (FastAPI), filas SQS, Workers de execução em sandbox e cache Redis.

---

## 🎯 Cenário de Teste Simulado

O [`locustfile.py`](locustfile.py) simula dois perfis concorrentes realistas:

### 1. 🎓 Perfil `StudentUser` (Peso: 10 - Alta concorrência de alunos)
* **Cadastro e Login:** Gera contas únicas com JWT sob demanda.
* **Navegação:** Lista questões (`/api/questions`) e consulta detalhes com schema SQL.
* **Consultas ao Ranking:** Testa o cache do Redis sob leitura massiva (`/api/ranking`).
* **Submissão Assíncrona de Consultas SQL:**
  * **60% Gabarito Correto (`SUCCESS`):** Hash SHA-256 idêntico, pontua +10 XP no RDS e loga no DynamoDB.
  * **20% Resposta Incorreta (`WRONG_ANSWER`):** Executa query divergente e loga no DynamoDB.
  * **15% Erro de Sintaxe (`SYNTAX_ERROR`):** Dispara rollback na sandbox e grava auditoria.
  * **5% Tentativa Maliciosa (`BLOCKED_DML`):** Intercepta tentativa de `DROP`/`DELETE`.
* **Polling Assíncrono:** Consulta `/api/submissions/{id}/status` até a conclusão da sandbox.

### 2. 👨‍🏫 Perfil `InstructorUser` (Peso: 1 - Ações administrativas)
* Login administrativo (`admin@sqlarena.com`).
* Listagem de logs de auditoria administrativa no DynamoDB (`/api/audit`).

---

## 🚀 Como Executar

### 1. Teste Local (contra seu PC)
Com o Backend (`uvicorn`) e o Worker ativos:

```powershell
# Com interface web (http://localhost:8089):
app\.venv\Scripts\locust -f locust/locustfile.py --host http://localhost:8000

# Ou em modo Headless (terminal direto por 30 segundos com 10 usuários):
app\.venv\Scripts\locust -f locust/locustfile.py --host http://localhost:8000 --users 10 --spawn-rate 2 --run-time 30s --headless
```

---

### 2. Teste na Nuvem AWS (contra o Load Balancer)
Substitua pela URL pública do seu Application Load Balancer:

```powershell
# Com interface web:
app\.venv\Scripts\locust -f locust/locustfile.py --host http://<ALB_DNS_NAME>

# Exemplo real com o seu ALB:
app\.venv\Scripts\locust -f locust/locustfile.py --host http://sqlarena-alb-519551880.us-east-1.elb.amazonaws.com
```

Abra seu navegador em **[http://localhost:8089](http://localhost:8089)**, defina o número de usuários (ex: `20` ou `50`), clique em **Start swarming** e acompanhe os gráficos de RPS, latência e taxa de sucesso em tempo real!
