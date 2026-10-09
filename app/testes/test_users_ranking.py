from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.security import get_password_hash
from app.database.models import User
from app.database.session import Base, get_db
from app.main import app


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    audit = Mock()
    monkeypatch.setattr("app.api.auth.DynamoDBManager", lambda: audit)
    monkeypatch.setattr("app.api.users.DynamoDBManager", lambda: audit)

    cache = {"value": None}
    monkeypatch.setattr("app.api.ranking.redis_client.get_ranking", lambda: cache["value"])
    monkeypatch.setattr("app.api.ranking.redis_client.set_ranking", lambda data: cache.update(value=data))
    monkeypatch.setattr("app.api.auth.redis_client.invalidate_ranking", lambda: cache.update(value=None))
    monkeypatch.setattr("app.api.users.redis_client.invalidate_ranking", lambda: cache.update(value=None))

    db = session_factory()
    db.add_all([
        User(id="instructor", name="Instrutor", email="i@example.com",
             password_hash=get_password_hash("password123"), role="INSTRUCTOR",
             score=20, solved_count=2),
        User(id="student", name="Aluno", email="s@example.com",
             password_hash=get_password_hash("password123"), role="STUDENT",
             score=20, solved_count=1),
    ])
    db.commit()
    db.close()

    with TestClient(app) as test_client:
        yield test_client, audit, session_factory, cache
    app.dependency_overrides.clear()
    engine.dispose()


def token(client, email):
    response = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_register_and_duplicate_email(client):
    http, audit, session_factory, _ = client
    response = http.post("/api/auth/register", json={
        "name": "  Maria  ", "email": "MARIA@example.com", "password": "newpassword123"
    })
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "STUDENT"
    assert response.json()["user"]["score"] == 0
    assert response.json()["user"]["solvedCount"] == 0
    with session_factory() as db:
        user = db.query(User).filter_by(email="maria@example.com").one()
        assert user.name == "Maria"
        assert user.password_hash != "newpassword123"
    assert audit.log_crud_action.call_args.kwargs["action_type"] == "USER_REGISTER"
    assert "password" not in str(audit.log_crud_action.call_args.kwargs)

    duplicate = http.post("/api/auth/register", json={
        "name": "Outra", "email": "maria@EXAMPLE.com", "password": "newpassword123"
    })
    assert duplicate.status_code == 409
    forbidden = http.post("/api/auth/register", json={
        "name": "Outra", "email": "another@example.com", "password": "newpassword123",
        "role": "INSTRUCTOR",
    })
    assert forbidden.status_code == 422


def test_profile_only_updates_allowed_fields(client):
    http, audit, _, _ = client
    headers = token(http, "s@example.com")
    denied = http.put("/api/users/me", headers=headers, json={"role": "INSTRUCTOR"})
    assert denied.status_code == 422
    wrong = http.put("/api/users/me", headers=headers, json={
        "password": "changedpassword", "currentPassword": "wrong"
    })
    assert wrong.status_code == 400
    updated = http.put("/api/users/me", headers=headers, json={
        "name": "Novo Aluno", "password": "changedpassword", "currentPassword": "password123"
    })
    assert updated.status_code == 200
    assert updated.json()["name"] == "Novo Aluno"
    assert audit.log_crud_action.call_args.kwargs["action_type"] == "USER_UPDATE"
    assert "changedpassword" not in str(audit.log_crud_action.call_args.kwargs)


def test_only_instructor_changes_roles(client):
    http, audit, _, _ = client
    student = token(http, "s@example.com")
    instructor = token(http, "i@example.com")
    assert http.get("/api/users", headers=student).status_code == 403
    assert http.patch("/api/users/student/role", headers=student, json={"role": "INSTRUCTOR"}).status_code == 403
    assert http.patch("/api/users/instructor/role", headers=instructor, json={"role": "STUDENT"}).status_code == 400
    assert len(http.get("/api/users", headers=instructor, params={"search": "alu"}).json()) == 1
    promoted = http.patch("/api/users/student/role", headers=instructor, json={"role": "INSTRUCTOR"})
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "INSTRUCTOR"
    assert audit.log_crud_action.call_args.kwargs["action_type"] == "PROMOTE_USER"


def test_ranking_order_and_cache(client):
    http, _, session_factory, cache = client
    result = http.get("/api/ranking")
    assert result.status_code == 200
    assert [row["id"] for row in result.json()] == ["instructor", "student"]
    assert [row["position"] for row in result.json()] == [1, 2]
    with session_factory() as db:
        student = db.query(User).filter_by(id="student").one()
        student.score = 100
        db.commit()
    assert http.get("/api/ranking").json()[0]["id"] == "instructor"
    cache["value"] = None
    assert http.get("/api/ranking").json()[0]["id"] == "student"


def test_ranking_is_limited_to_top_50(client):
    http, _, session_factory, cache = client
    with session_factory() as db:
        db.add_all([
            User(id=f"extra_{index}", name=f"Pessoa {index}",
                 email=f"extra{index}@example.com", password_hash="unused",
                 role="STUDENT", score=index, solved_count=0)
            for index in range(55)
        ])
        db.commit()
    cache["value"] = None
    result = http.get("/api/ranking")
    assert result.status_code == 200
    assert len(result.json()) == 50
    assert result.json()[0]["score"] == 54
