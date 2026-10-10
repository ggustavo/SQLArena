"""
SQLArena - Script de Teste de Carga e Estresse com Locust
==========================================================
Simula o tráfego real de alunos e instrutores para estressar:
1. Backend FastAPI e ALB (CPU e Auto Scaling Group `asg_web`)
2. Cache de Ranking no Redis (alta concorrência e invalidação)
3. Fila Amazon SQS e Workers desacoplados (Auto Scaling Group `worker_asg`)
4. Auditoria imutável no Amazon DynamoDB (ações de CRUD e submissões)
5. Sandbox PostgreSQL local nos Workers

Execução:
  - Local (com interface Web):
      app\\.venv\\Scripts\\locust.exe -f locustfile.py --host http://localhost:8000
      (Acesse http://localhost:8089 no navegador)

  - Na AWS (apontando para o Application Load Balancer):
      app\\.venv\\Scripts\\locust.exe -f locustfile.py --host http://<ALB_DNS_NAME>

  - Modo Headless (terminal sem interface gráfica, 30 segundos com 20 usuários):
      app\\.venv\\Scripts\\locust.exe -f locustfile.py --host http://localhost:8000 --users 20 --spawn-rate 5 --run-time 30s --headless
"""

import json
import logging
import os
import random
import time
import uuid
from pathlib import Path
from typing import Dict, List

from locust import HttpUser, between, task

logger = logging.getLogger("LocustTest")

# -----------------------------------------------------------------------------
# Carregamento do Banco de Soluções e Perguntas Oficiais
# -----------------------------------------------------------------------------
DATA_PATH = Path(__file__).resolve().parent / "app" / "database" / "initial_data.json"

CATALOG_QUESTIONS: List[Dict] = []
SOLUTIONS_MAP: Dict[int, str] = {}

if DATA_PATH.exists():
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            CATALOG_QUESTIONS = raw_data.get("questions", [])
            for q in CATALOG_QUESTIONS:
                qid = q.get("id")
                # Em initial_data.json, starterSql contém o gabarito oficial validado
                sql = q.get("starterSql", "").strip()
                if qid and sql:
                    SOLUTIONS_MAP[qid] = sql
    except Exception as e:
        logger.warning(f"Não foi possível carregar {DATA_PATH}: {e}")

# Fallback se não encontrar o JSON
if not SOLUTIONS_MAP:
    SOLUTIONS_MAP = {
        1: (
            "SELECT c.nome, SUM(p.valor_total) AS faturamento_total "
            "FROM clientes c JOIN pedidos p ON p.cliente_id = c.id "
            "WHERE p.status = 'FINALIZADO' GROUP BY c.id, c.nome "
            "ORDER BY faturamento_total DESC, c.nome ASC LIMIT 5;"
        ),
        2: (
            "SELECT c.nome, COUNT(p.id) AS total_pedidos "
            "FROM clientes c JOIN pedidos p ON p.cliente_id = c.id "
            "GROUP BY c.id, c.nome HAVING COUNT(p.id) > 2 "
            "ORDER BY total_pedidos DESC, c.nome ASC;"
        )
    }

# Amostras de consultas incorretas / sintaxe / segurança para o mix de teste
WRONG_QUERIES = [
    "SELECT nome FROM clientes LIMIT 5;",
    "SELECT c.nome, COUNT(*) FROM clientes c GROUP BY c.nome ORDER BY c.nome ASC;",
    "SELECT id, valor_total FROM pedidos WHERE valor_total > 500 ORDER BY id ASC;",
]

SYNTAX_ERROR_QUERIES = [
    "SELEC * FORM clientes WHERE id = 1;",
    "SELECT c.nome, SUM(p.valor) FROM clientes c JON pedidos p ON p.cliente_id = c.id;",
    "SELECT * FROM tabela_que_nao_existe_na_sandbox ORDER BY id DESC;",
]

SECURITY_BLOCK_QUERIES = [
    "DROP TABLE IF EXISTS clientes CASCADE;",
    "DELETE FROM pedidos WHERE 1=1;",
    "INSERT INTO clientes (nome, email) VALUES ('Hacker', 'hacker@sqlarena.com');",
]


class SQLArenaStudent(HttpUser):
    """
    Simula um aluno navegando, resolvendo exercícios, consultando o ranking
    e submetendo consultas SQL para avaliação assíncrona via SQS + Worker.
    """
    weight = 10
    wait_time = between(1, 4)

    def on_start(self):
        """Inicializa a sessão: cadastra um aluno único e obtém o token JWT."""
        self.user_id = None
        self.token = None
        self.available_question_ids = list(SOLUTIONS_MAP.keys())
        self.name = f"Aluno Carga {uuid.uuid4().hex[:6]}"
        self.email = f"loadtest_{uuid.uuid4().hex[:8]}@sqlarena.com"
        self.password = "Teste12345!"

        # 1. Tenta cadastro
        reg_payload = {
            "name": self.name,
            "email": self.email,
            "password": self.password
        }
        with self.client.post("/api/auth/register", json=reg_payload, catch_response=True, name="/api/auth/register") as resp:
            if resp.status_code == 201:
                data = resp.json()
                self.token = data.get("token")
                self.user_id = data.get("user", {}).get("id")
                resp.success()
            elif resp.status_code == 409:
                # Se já existia, faz login
                login_payload = {"email": self.email, "password": self.password}
                with self.client.post("/api/auth/login", json=login_payload, catch_response=True, name="/api/auth/login") as log_resp:
                    if log_resp.status_code == 200:
                        data = log_resp.json()
                        self.token = data.get("token")
                        self.user_id = data.get("user", {}).get("id")
                        log_resp.success()
                    else:
                        log_resp.failure(f"Falha de login de fallback: {log_resp.status_code}")
            else:
                resp.failure(f"Falha ao registrar usuário: {resp.status_code}")

        # Injeta cabeçalho de autenticação para todas as próximas chamadas
        if self.token:
            self.client.headers["Authorization"] = f"Bearer {self.token}"

        # Carrega catálogo de IDs disponíveis
        try:
            with self.client.get("/api/questions", catch_response=True, name="/api/questions") as q_resp:
                if q_resp.status_code == 200:
                    q_list = q_resp.json()
                    if isinstance(q_list, list) and q_list:
                        self.available_question_ids = [q["id"] for q in q_list if "id" in q]
        except Exception:
            pass

    @task(6)
    def browse_questions_and_details(self):
        """Navega pelo catálogo e abre os detalhes de um exercício específico."""
        self.client.get("/api/questions", name="/api/questions")
        if self.available_question_ids:
            qid = random.choice(self.available_question_ids)
            self.client.get(f"/api/questions/{qid}", name="/api/questions/[id]")

    @task(5)
    def view_ranking(self):
        """Consulta o placar geral de líderes (estressa cache do Redis)."""
        self.client.get("/api/ranking", name="/api/ranking")

    @task(4)
    def submit_sql_solution(self):
        """
        Submete uma resposta SQL com mix probabilístico realista:
        - 60% Gabarito Correto (SUCCESS -> pontuação + invalidação de ranking)
        - 20% Resposta Incorreta (WRONG_ANSWER -> log no DynamoDB)
        - 15% Erro de Sintaxe (SYNTAX_ERROR -> rollback + log no DynamoDB)
        - 5%  Comando Proibido (SECURITY_BLOCK -> bloqueio defensivo)
        """
        if not self.available_question_ids:
            return

        qid = random.choice(self.available_question_ids)
        dice = random.random()

        if dice < 0.60 and qid in SOLUTIONS_MAP:
            query = SOLUTIONS_MAP[qid]
            tag = "CORRECT"
        elif dice < 0.80:
            query = random.choice(WRONG_QUERIES)
            tag = "WRONG"
        elif dice < 0.95:
            query = random.choice(SYNTAX_ERROR_QUERIES)
            tag = "SYNTAX_ERR"
        else:
            query = random.choice(SECURITY_BLOCK_QUERIES)
            tag = "BLOCKED_DML"

        payload = {
            "questionId": qid,
            "query": query,
            "difficulty": "Médio"
        }

        # Submete e trata Rate Limit (429) graciosamente
        sub_id = None
        with self.client.post("/api/submissions", json=payload, catch_response=True, name=f"/api/submissions [{tag}]") as resp:
            if resp.status_code == 202:
                resp.success()
                try:
                    data = resp.json()
                    sub_id = data.get("submissionId") or data.get("submission_id")
                except Exception:
                    sub_id = None
            elif resp.status_code == 429:
                # Rate limit de 5s é esperado pelo Requisito 8 sob alta concorrência
                resp.success()
            else:
                resp.failure(f"Erro inesperado no envio ({resp.status_code}): {resp.text}")

        # Se a submissão foi aceita, faz polling para acompanhar o processamento assíncrono do Worker
        if sub_id:
            for _ in range(3):
                time.sleep(1)
                with self.client.get(f"/api/submissions/{sub_id}/status", catch_response=True, name="/api/submissions/[id] [POLL]") as poll_resp:
                    if poll_resp.status_code == 200:
                        try:
                            data = poll_resp.json()
                            status = data.get("status") or data.get("outcome")
                            if status in ("COMPLETED", "ERROR", "DONE", "SUCCESS", "WRONG_ANSWER", "SYNTAX_ERROR"):
                                poll_resp.success()
                                break
                            else:
                                poll_resp.success()
                        except Exception:
                            # Resposta ainda não pronta ou payload vazio
                            pass
                    elif poll_resp.status_code in (404, 202):
                        # Em processamento assíncrono na fila SQS
                        poll_resp.success()


    @task(2)
    def view_my_submissions_history(self):
        """Visualiza o histórico de submissões do próprio aluno."""
        self.client.get("/api/submissions/history/me", name="/api/submissions/history/me")

    @task(1)
    def update_profile(self):
        """Atualiza nome do perfil (estressa log de auditoria no DynamoDB e invalidação de cache)."""
        new_name = f"Aluno {uuid.uuid4().hex[:6]}"
        payload = {"name": new_name}
        with self.client.put("/api/users/me", json=payload, catch_response=True, name="/api/users/me") as resp:
            if resp.status_code == 200:
                resp.success()


class SQLArenaInstructor(HttpUser):
    """
    Simula ações administrativas do Instrutor (Auditoria, listagem geral de usuários).
    Proporção menor (1 instrutor para cada ~10 alunos).
    """
    weight = 1
    wait_time = between(3, 8)

    def on_start(self):
        """Faz login como Admin / Instrutor padrão do sistema."""
        self.token = None
        login_payload = {
            "email": "admin@sqlarena.com",
            "password": "123456"
        }
        with self.client.post("/api/auth/login", json=login_payload, catch_response=True, name="/api/auth/login [ADMIN]") as resp:
            if resp.status_code == 200:
                try:
                    self.token = resp.json().get("token")
                    self.client.headers["Authorization"] = f"Bearer {self.token}"
                    resp.success()
                except Exception:
                    resp.failure("Erro ao decodificar token do Admin")
            else:
                resp.failure("Instrutor Admin não encontrado. Verifique se o seed foi executado.")

    @task(4)
    def inspect_audit_logs(self):
        """Consulta registros de auditoria no DynamoDB."""
        if not self.token:
            return
        self.client.get("/api/audit/logs?limit=50", name="/api/audit/logs")

    @task(3)
    def list_users(self):
        """Consulta listagem de alunos cadastrados."""
        if not self.token:
            return
        self.client.get("/api/users", name="/api/users")

    @task(2)
    def check_ranking(self):
        """Acompanha o ranking de alunos."""
        self.client.get("/api/ranking", name="/api/ranking")
