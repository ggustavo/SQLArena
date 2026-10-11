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

    # Mock S3 storage for avatars
    s3_storage = {}
    class FakeS3:
        def __init__(self, *args, **kwargs):
            pass
        def upload_file(self, key, content, content_type="text/plain"):
            s3_storage[key] = content
            return True
        def read_file_bytes(self, key):
            if key not in s3_storage:
                raise Exception("NotFound")
            return s3_storage[key]
        def file_exists(self, key):
            return key in s3_storage
        def delete_file(self, key):
            s3_storage.pop(key, None)
            return True
    monkeypatch.setattr("app.api.users.S3Manager", FakeS3)

    cache = {"value": None}
    monkeypatch.setattr("app.api.ranking.redis_client.get_ranking", lambda: cache["value"])
    monkeypatch.setattr("app.api.ranking.redis_client.set_ranking", lambda data: cache.update(value=data))
    monkeypatch.setattr("app.api.auth.redis_client.invalidate_ranking", lambda: cache.update(value=None))
    monkeypatch.setattr("app.api.users.redis_client.invalidate_ranking", lambda: cache.update(value=None))

    # Bypassa tentativas de conexão de rede externa no lifespan do FastAPI durante testes
    monkeypatch.setattr("app.main.S3Manager.ensure_bucket_exists", lambda self: True)
    monkeypatch.setattr("app.main.DynamoDBManager.ensure_tables_exist", lambda self: True)
    monkeypatch.setattr("app.main.SQSQueueManager.ensure_queues_exist", lambda self: True)

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
        yield test_client, audit, session_factory, cache, s3_storage
    app.dependency_overrides.clear()
    engine.dispose()


def token(client, email):
    response = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_register_and_duplicate_email(client):
    http, audit, session_factory, *_ = client
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
    http, audit, *_ = client
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
    http, audit, *_ = client
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
    http, _, session_factory, cache, *_ = client
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
    http, _, session_factory, cache, *_ = client
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


def test_profile_update_extended_fields(client):
    http, audit, session_factory, *_ = client
    headers = token(http, "s@example.com")
    resp = http.put("/api/users/me", headers=headers, json={
        "university": "Universidade de São Paulo",
        "city": "São Paulo",
        "state": "SP",
        "country": "Brasil"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["university"] == "Universidade de São Paulo"
    assert data["city"] == "São Paulo"
    assert data["state"] == "SP"
    assert data["country"] == "Brasil"

    with session_factory() as db:
        user = db.query(User).filter_by(id="student").one()
        assert user.university == "Universidade de São Paulo"
        assert user.city == "São Paulo"

    assert audit.log_crud_action.call_args.kwargs["action_type"] == "USER_UPDATE"
    assert "university" in audit.log_crud_action.call_args.kwargs["changed_data"]


def test_avatar_upload_resize_get_and_delete(client):
    import io
    from PIL import Image

    http, audit, session_factory, cache, s3_storage = client
    headers = token(http, "s@example.com")

    # 1. Cria imagem sintética 500x500
    img = Image.new("RGB", (500, 500), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # 2. Upload do arquivo binário
    files = {"file": ("avatar.png", buf.getvalue(), "image/png")}
    upload_resp = http.post("/api/users/me/avatar", headers=headers, files=files)
    assert upload_resp.status_code == 200
    user_data = upload_resp.json()
    assert user_data["avatarUrl"] == "/api/users/student/avatar"

    # 3. Verifica armazenamento e rescaling no FakeS3 (deve ter virado 256x256)
    assert "avatars/student.png" in s3_storage
    stored_bytes = s3_storage["avatars/student.png"]
    processed_img = Image.open(io.BytesIO(stored_bytes))
    assert processed_img.size == (256, 256)

    # 4. Verifica auditoria DynamoDB
    assert audit.log_crud_action.call_args.kwargs["action_type"] == "USER_AVATAR_UPLOAD"

    # 5. Download do avatar via GET /api/users/{user_id}/avatar
    get_resp = http.get("/api/users/student/avatar")
    assert get_resp.status_code == 200
    assert get_resp.headers["content-type"] == "image/png"
    assert get_resp.content == stored_bytes

    # 6. Remoção do avatar via DELETE /api/users/me/avatar
    del_resp = http.delete("/api/users/me/avatar", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["avatarUrl"] is None
    assert "avatars/student.png" not in s3_storage
    assert audit.log_crud_action.call_args.kwargs["action_type"] == "USER_AVATAR_DELETE"


def test_user_delete_crud(client):
    http, audit, session_factory, cache, s3_storage = client
    student_headers = token(http, "s@example.com")
    instructor_headers = token(http, "i@example.com")

    # 1. Instrutor tenta deletar a si próprio (proibido)
    del_self = http.delete("/api/users/instructor", headers=instructor_headers)
    assert del_self.status_code == 400

    # 2. Aluno deleta a própria conta via DELETE /api/users/me
    del_resp = http.delete("/api/users/me", headers=student_headers)
    assert del_resp.status_code == 200
    assert "detail" in del_resp.json()

    with session_factory() as db:
        assert db.query(User).filter_by(id="student").first() is None

    assert audit.log_crud_action.call_args.kwargs["action_type"] == "USER_DELETE"
