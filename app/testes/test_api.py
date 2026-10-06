import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "sqlarena-web-api"

def test_auth_login_success():
    response = client.post("/api/auth/login", json={
        "email": "aluno@sqlarena.com",
        "password": "123456"
    })
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["email"] == "aluno@sqlarena.com"
    assert data["user"]["role"] == "STUDENT"
    assert data["user"]["name"] == "Gustavo Santos"

def test_auth_login_invalid():
    response = client.post("/api/auth/login", json={
        "email": "aluno@sqlarena.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_list_categories_alphabetical():
    response = client.get("/api/categories")
    assert response.status_code == 200
    cats = response.json()
    assert len(cats) >= 12
    # Verifica ordenação alfabética
    names = [c["name"] for c in cats]
    assert names == sorted(names, key=lambda x: x.lower())
    assert "Agrupamento" in names
    assert "JOINs" in names

def test_list_questions():
    response = client.get("/api/questions")
    assert response.status_code == 200
    questions = response.json()
    assert len(questions) >= 21
    q1 = next((q for q in questions if q["id"] == 1), None)
    assert q1 is not None
    assert "Top 5 Clientes com Maior Faturamento" in q1["title"]
    assert "Agrupamento" in q1["categories"]
    assert q1["categories"] == sorted(q1["categories"], key=lambda x: x.lower())

def test_get_question_details():
    response = client.get("/api/questions/1")
    assert response.status_code == 200
    q = response.json()
    assert q["id"] == 1
    assert len(q["sampleTables"]) > 0
    assert "schemaSql" in q

def test_submission_rate_limit():
    # Login aluno
    login_res = client.post("/api/auth/login", json={
        "email": "aluno@sqlarena.com",
        "password": "123456"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1ª submissão: deve ser aceita (202)
    sub_res_1 = client.post("/api/submissions", headers=headers, json={
        "questionId": 1,
        "query": "SELECT * FROM clientes;",
        "questionTitle": "Top 5 Clientes com Maior Faturamento"
    })
    assert sub_res_1.status_code == 202
    sub_data = sub_res_1.json()
    assert "submissionId" in sub_data
    assert sub_data["status"] == "PROCESSING"

    # 2ª submissão imediata: deve ser bloqueada por Rate Limit de 5 segundos (429)
    sub_res_2 = client.post("/api/submissions", headers=headers, json={
        "questionId": 1,
        "query": "SELECT * FROM clientes;",
        "questionTitle": "Top 5 Clientes com Maior Faturamento"
    })
    assert sub_res_2.status_code == 429
    assert "Rate limit" in sub_res_2.json()["detail"]
