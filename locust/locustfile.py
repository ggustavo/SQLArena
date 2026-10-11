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
DATA_PATH = Path(__file__).resolve().parent.parent / "app" / "database" / "initial_data.json"
if not DATA_PATH.exists():
    DATA_PATH = Path(__file__).resolve().parent / "app" / "database" / "initial_data.json"
if not DATA_PATH.exists():
    DATA_PATH = Path("app/database/initial_data.json")

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
                    SOLUTIONS_MAP[str(qid)] = sql
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
    Simula um aluno ativo navegando, consultando ranking, histórico
    e submetendo consultas SQL para avaliação assíncrona.
    Otimizado para gerar carga constante de CPU na camada Web sem bloqueios desnecessários.
    """
    weight = 10
    wait_time = between(0.1, 0.4)

    def on_start(self):
        """Inicializa a sessão: cadastra um aluno único e obtém o token JWT com resiliência."""
        if hasattr(self.client, "base_url") and self.client.base_url:
            self.client.base_url = self.client.base_url.rstrip("/")

        # Distribui conexões no tempo para evitar thundering herd no primeiro segundo
        time.sleep(random.uniform(0.05, 0.4))

        self.user_id = None
        self.token = None
        self.available_question_ids = list(SOLUTIONS_MAP.keys())
        self.last_sub_time = 0
        self.name = f"Aluno Carga {uuid.uuid4().hex[:6]}"
        self.email = f"loadtest_{uuid.uuid4().hex[:8]}@sqlarena.com"
        self.password = "Teste12345!"

        # 1. Tenta cadastro rápido
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
            elif resp.status_code in (409, 503):
                # Se já existia ou houve contenção momentânea, tenta login
                login_payload = {"email": self.email, "password": self.password}
                with self.client.post("/api/auth/login", json=login_payload, catch_response=True, name="/api/auth/login") as log_resp:
                    if log_resp.status_code == 200:
                        data = log_resp.json()
                        self.token = data.get("token")
                        self.user_id = data.get("user", {}).get("id")
                        log_resp.success()
                        resp.success()
                    else:
                        # Fallback no aluno semente padrão
                        fb_payload = {"email": "gustavo@sqlarena.com", "password": "123456"}
                        with self.client.post("/api/auth/login", json=fb_payload, catch_response=True, name="/api/auth/login [FALLBACK]") as fb_resp:
                            if fb_resp.status_code == 200:
                                data = fb_resp.json()
                                self.token = data.get("token")
                                self.user_id = data.get("user", {}).get("id")
                                fb_resp.success()
                                resp.success()
                            else:
                                resp.failure(f"Falha de autenticação: {resp.status_code}")
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
                        valid_ids = [q["id"] for q in q_list if ("id" in q and (q["id"] in SOLUTIONS_MAP or str(q["id"]) in SOLUTIONS_MAP))]
                        self.available_question_ids = valid_ids if valid_ids else [q["id"] for q in q_list if "id" in q]
        except Exception:
            pass

    @task(30)
    def browse_questions_and_details(self):
        """Navega pelo catálogo e estuda os detalhes de um exercício específico."""
        self.client.get("/api/questions", name="/api/questions")
        if self.available_question_ids:
            qid = random.choice(self.available_question_ids)
            self.client.get(f"/api/questions/{qid}", name="/api/questions/[id]")

    @task(25)
    def view_ranking(self):
        """Consulta o placar geral de líderes (estressa serialização e cache)."""
        self.client.get("/api/ranking", name="/api/ranking")

    @task(15)
    def view_my_submissions_history(self):
        """Visualiza o histórico de submissões do próprio aluno."""
        self.client.get("/api/submissions/history/me", name="/api/submissions/history/me")

    @task(5)
    def update_profile(self):
        """Atualiza nome do perfil (estressa log de auditoria no DynamoDB e invalidação de cache)."""
        new_name = f"Aluno {uuid.uuid4().hex[:6]}"
        payload = {"name": new_name}
        with self.client.put("/api/users/me", json=payload, catch_response=True, name="/api/users/me") as resp:
            if resp.status_code == 200:
                resp.success()

    @task(25)
    def submit_sql_solution(self):
        """
        Submete uma resposta SQL respeitando o Rate Limit de 5s sem bloquear o fluxo.
        Se ainda estiver em cooldown de 5s, redireciona o ciclo para consulta do catálogo.
        """
        now = time.time()
        if now - getattr(self, "last_sub_time", 0) < 5.2:
            self.browse_questions_and_details()
            return

        if not self.available_question_ids:
            return

        valid_qids = [q for q in self.available_question_ids if (q in SOLUTIONS_MAP or str(q) in SOLUTIONS_MAP)]
        qid = random.choice(valid_qids) if valid_qids else random.choice(self.available_question_ids)
        dice = random.random()

        base_solution = SOLUTIONS_MAP.get(qid) or SOLUTIONS_MAP.get(str(qid))
        if not base_solution and SOLUTIONS_MAP:
            base_solution = next(iter(SOLUTIONS_MAP.values()))

        if dice < 0.95 and base_solution:
            query = base_solution
            tag = "CORRECT"
        elif dice < 0.98 and base_solution:
            query = f"{base_solution} OFFSET 1"
            tag = "WRONG"
        else:
            query = "SELEC * FORM clientes WHERE id = 1;"
            tag = "SYNTAX_ERR"

        payload = {
            "questionId": qid,
            "query": query,
            "difficulty": "Médio"
        }

        self.last_sub_time = now
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
                resp.success()
                return
            else:
                resp.failure(f"Erro inesperado no envio ({resp.status_code}): {resp.text}")
                return

        # Polling leve e não-bloqueante
        if sub_id:
            for _ in range(2):
                with self.client.get(f"/api/submissions/{sub_id}/status", catch_response=True, name="/api/submissions/[id] [POLL]") as poll_resp:
                    if poll_resp.status_code in (200, 202, 404):
                        poll_resp.success()
                        if poll_resp.status_code == 200:
                            data = poll_resp.json()
                            if data.get("status") == "DONE":
                                break


class SQLArenaInstructor(HttpUser):
    """
    Simula ações administrativas do Instrutor (Auditoria, listagem geral de usuários).
    Proporção menor (1 instrutor para cada ~10 alunos).
    """
    weight = 1
    wait_time = between(0.1, 0.4)

    def on_start(self):
        """Faz login como Admin / Instrutor padrão do sistema."""
        if hasattr(self.client, "base_url") and self.client.base_url:
            self.client.base_url = self.client.base_url.rstrip("/")

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

    @task(3)
    def check_ranking(self):
        """Acompanha o ranking de alunos."""
        self.client.get("/api/ranking", name="/api/ranking")
