import json
import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.worker.main import SubmissionWorker
from app.sqs.queue_manager import SQSQueueManager
from app.cache.redis_client import redis_client
from app.dynamodb.dynamo_manager import DynamoDBManager

client = TestClient(app)

def test_full_student_frontend_flow():
    """
    Simula 100% do fluxo do aluno no frontend com USE_MOCK = false:
    1. Login do aluno
    2. Consulta de categorias (alfabética)
    3. Consulta de questões
    4. Envio de submissão via POST /api/submissions (Rate limit + SQS)
    5. Consumo pelo Worker (Sandbox Postgres 16)
    6. Polling do status via GET /api/submissions/{id}/status
    7. Verificação do histórico via GET /api/submissions/history
    """
    DynamoDBManager().ensure_tables_exist()
    # 1. Login
    login_resp = client.post("/api/auth/login", json={
        "email": "aluno@sqlarena.com",
        "password": "123" # ou 123456
    })
    if login_resp.status_code != 200:
        login_resp = client.post("/api/auth/login", json={
            "email": "aluno@sqlarena.com",
            "password": "123456"
        })
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Categorias
    cat_resp = client.get("/api/categories")
    assert cat_resp.status_code == 200
    categories = cat_resp.json()
    assert len(categories) == 12
    # Valida ordem alfabética case-insensitive
    cat_names = [c["name"] for c in categories]
    assert cat_names == sorted(cat_names, key=lambda x: x.lower())

    # 3. Questões
    q_resp = client.get("/api/questions", headers=headers)
    assert q_resp.status_code == 200
    questions = q_resp.json()
    assert len(questions) >= 21

    # 4. Envio de submissão
    # Limpa mensagens antigas da fila e rate limit para o teste
    sqs = SQSQueueManager()
    while True:
        old_msgs = sqs.receive_messages(max_messages=10, wait_time_seconds=1)
        if not old_msgs:
            break
        for m in old_msgs:
            if m.get("ReceiptHandle"):
                sqs.delete_message(m["ReceiptHandle"])

    redis_client.client.delete(f"ratelimit:{login_resp.json()['user']['id']}")

    submit_payload = {
        "question_id": 1,
        "sql_query": """
        SELECT c.nome, SUM(p.valor_total) AS faturamento_total
        FROM clientes c
        JOIN pedidos p ON p.cliente_id = c.id
        WHERE p.status = 'FINALIZADO'
        GROUP BY c.id, c.nome
        ORDER BY faturamento_total DESC, c.nome ASC
        LIMIT 5;
        """,
        "questionTitle": "Top 5 Clientes com Maior Faturamento",
        "difficulty": "Médio"
    }

    sub_resp = client.post("/api/submissions", json=submit_payload, headers=headers)
    assert sub_resp.status_code == 202
    sub_data = sub_resp.json()
    submission_id = sub_data["submissionId"]
    assert submission_id.startswith("sub_")

    # 5. Worker consome da fila SQS até concluir
    worker = SubmissionWorker()
    for _ in range(5):
        worker.process_one_message(wait_seconds=2)
        status_resp = client.get(f"/api/submissions/{submission_id}/status", headers=headers)
        if status_resp.status_code == 200 and status_resp.json().get("status") == "DONE":
            break

    # 6. Polling do status (como o frontend faz em setInterval a cada 700ms)
    status_resp = client.get(f"/api/submissions/{submission_id}/status", headers=headers)
    assert status_resp.status_code == 200
    status_result = status_resp.json()
    assert status_result["status"] == "DONE"
    assert status_result["outcome"] == "SUCCESS"
    assert status_result["strictModeHashMatched"] is True
    assert len(status_result["rows"]) == 3
    assert status_result["columns"] == ["nome", "faturamento_total"]

    # 7. Histórico do aluno
    hist_resp = client.get("/api/submissions/history", headers=headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert any(h["submissionId"] == submission_id for h in history)

    # Teardown: Remove a submissão de teste para nunca poluir o ambiente real do aluno
    dynamo = DynamoDBManager()
    try:
        dynamo.table.delete_item(Key={"submission_id": submission_id})
    except Exception:
        pass
    redis_client.delete_submission(submission_id)

def test_full_instructor_frontend_flow():
    """
    Simula o fluxo do instrutor:
    1. Login instrutor
    2. Tenta criar questão SEM ORDER BY -> deve falhar com HTTP 400
    3. Cria questão COM ORDER BY -> RDS + S3 + DynamoDB
    4. Publica a questão -> POST /api/questions/{id}/publish
    5. Exclui a questão -> DELETE /api/questions/{id}
    """
    login_resp = client.post("/api/auth/login", json={
        "email": "instrutor@sqlarena.com",
        "password": "123456"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Falha sem ORDER BY
    fail_create = client.post("/api/questions", json={
        "title": "Questão Teste Sem Order By",
        "difficulty": "Fácil",
        "answerSql": "SELECT id, nome FROM usuarios WHERE ativo = true;"
    }, headers=headers)
    assert fail_create.status_code == 400
    assert "ORDER BY" in fail_create.json()["detail"]

    # 3. Criação com sucesso
    success_create = client.post("/api/questions", json={
        "title": "Questão E2E Teste Com Order By",
        "difficulty": "Médio",
        "categories": ["Filtragem", "JOINs"],
        "description": "Exercício de teste automatizado ponta a ponta.",
        "schemaSql": "CREATE TABLE itens_teste (id SERIAL PRIMARY KEY, nome VARCHAR(100));",
        "dataSql": "INSERT INTO itens_teste (nome) VALUES ('Item A'), ('Item B');",
        "answerSql": "SELECT id, nome FROM itens_teste ORDER BY id ASC;"
    }, headers=headers)
    assert success_create.status_code == 201
    created_id = success_create.json()["id"]

    # 4. Publica questão
    pub_resp = client.post(f"/api/questions/{created_id}/publish", headers=headers)
    assert pub_resp.status_code == 200
    assert pub_resp.json()["publishedStatus"] == "PUBLISHED"

    # 5. Exclui questão
    del_resp = client.delete(f"/api/questions/{created_id}", headers=headers)
    assert del_resp.status_code == 200
