"""CRUD contracts with a real SQLAlchemy session and isolated external services."""
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

# Construct cloud clients without credentials, metadata requests or network I/O.
with patch("boto3.client"), patch("boto3.resource"):
    from app.api import questions, submissions

from app.api.deps import get_current_user, get_optional_current_user
from app.database.models import Base, Category, Question, User, UserSolvedQuestion
from app.database.session import get_db
from app.database.validator import QuestionValidationError, QuestionValidator
from app.s3.s3_manager import S3Manager


@pytest.fixture
def context(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        teacher = User(id="teacher", name="Teacher", email="teacher@test", password_hash="x", role="INSTRUCTOR")
        student = User(id="student", name="Student", email="student@test", password_hash="x", role="STUDENT")
        db.add_all([teacher, student, Category(name="Filtragem", slug="filtragem")])
        db.commit()
        cache = Mock()
        cache.get_cached_questions.return_value = None
        cache.get_cached_question.return_value = None
        cache.check_rate_limit.return_value = (True, 0)
        storage, audit, validator = Mock(), Mock(), Mock()
        validator.validate_and_setup_question.return_value = {
            "expected_hash": "a" * 64, "expected_columns": ["id"], "sample_tables": []
        }
        monkeypatch.setattr(questions, "redis_client", cache)
        monkeypatch.setattr(questions, "s3_manager", storage)
        monkeypatch.setattr(questions, "dynamo_manager", audit)
        monkeypatch.setattr(questions, "QuestionValidator", validator)
        monkeypatch.setattr(submissions, "redis_client", cache)
        app = FastAPI()
        app.include_router(questions.router, prefix="/api")
        app.include_router(submissions.router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: teacher
        app.dependency_overrides[get_optional_current_user] = lambda: teacher
        with TestClient(app) as client:
            yield client, db, app, teacher, student, cache, storage, audit, validator
    engine.dispose()


def payload(**changes):
    return {"title": "Question", "schemaSql": "CREATE TABLE t(id int);",
            "dataSql": "INSERT INTO t VALUES (1);", "answerSql": "SELECT id FROM t ORDER BY id", **changes}


def test_create_publish_delete(context):
    client, db, app, teacher, student, cache, storage, audit, validator = context
    response = client.post("/api/questions", json=payload(categories=["Filtragem", "Filtragem"]))
    assert response.status_code == 201
    created = response.json()
    qid = created["id"]
    assert created["publishedStatus"] == "READY"
    assert created["categories"] == ["Filtragem"]
    storage.upload_question_sql_files.assert_called_once()
    assert [call[0] for call in cache.method_calls][-2:] == ["invalidate_questions_cache", "set_answer_hash"]
    app.dependency_overrides[get_optional_current_user] = lambda: student
    assert client.get("/api/questions").json() == []
    assert client.get(f"/api/questions/{qid}").status_code == 403
    app.dependency_overrides[get_optional_current_user] = lambda: teacher
    assert len(client.get("/api/questions").json()) == 1
    assert client.post(f"/api/questions/{qid}/publish").json()["publishedStatus"] == "PUBLISHED"
    assert client.post(f"/api/questions/{qid}/publish").status_code == 200
    db.add(UserSolvedQuestion(user_id=student.id, question_id=qid))
    db.commit()
    app.dependency_overrides[get_optional_current_user] = lambda: student
    assert client.get("/api/questions").json()[0]["status"] == "SOLVED"
    assert client.get(f"/api/questions/{qid}").json()["status"] == "SOLVED"
    assert client.delete(f"/api/questions/{qid}").status_code == 200
    assert db.query(Question).count() == 0
    assert db.query(UserSolvedQuestion).count() == 0
    assert db.query(Category).count() == 1
    storage.delete_question_files.assert_called_once_with(qid)
    validator.drop_question_schema.assert_called_once_with(qid)
    assert [c.kwargs["action_type"] for c in audit.log_crud_action.call_args_list] == [
        "CREATE_EXERCISE", "PUBLISH_EXERCISE", "DELETE_EXERCISE"]
    assert client.get(f"/api/questions/{qid}").status_code == 404


@pytest.mark.parametrize("method,path", [("post", "/api/questions"), ("post", "/api/questions/1/publish"), ("delete", "/api/questions/1")])
def test_student_cannot_mutate(context, method, path):
    client, _, app, _, student, *_ = context
    app.dependency_overrides[get_current_user] = lambda: student
    assert client.request(method, path, json=payload()).status_code == 403


@pytest.mark.parametrize("changes,code", [({"title": "  "}, 422), ({"title": "x" * 201}, 422),
                                         ({"difficulty": "unknown"}, 422), ({"categories": ["unknown"]}, 400)])
def test_invalid_metadata(context, changes, code):
    client, db, *rest = context
    assert client.post("/api/questions", json=payload(**changes)).status_code == code
    assert db.query(Question).count() == 0


def test_invalid_sql_rolls_back(context):
    client, db, _, _, _, _, storage, _, validator = context
    validator.validate_and_setup_question.side_effect = QuestionValidationError("ORDER BY obrigatório")
    assert client.post("/api/questions", json=payload(answerSql="SELECT 1")).status_code == 400
    assert db.query(Question).count() == 0
    storage.upload_question_sql_files.assert_not_called()


def test_validator_requires_order_by():
    with pytest.raises(QuestionValidationError, match="ORDER BY"):
        QuestionValidator.validate_and_setup_question(1, "", "", "SELECT 1")


def test_failed_upload_compensates(context):
    client, db, _, _, _, _, storage, audit, validator = context
    storage.upload_question_sql_files.side_effect = RuntimeError("offline")
    assert client.post("/api/questions", json=payload()).status_code == 503
    assert db.query(Question).count() == 0
    storage.delete_question_files.assert_called_once()
    validator.drop_question_schema.assert_called_once()
    audit.log_crud_action.assert_not_called()


@pytest.mark.parametrize("service", ["storage", "schema"])
def test_delete_can_resume(context, service):
    client, db, _, _, _, _, storage, _, validator = context
    qid = client.post("/api/questions", json=payload()).json()["id"]
    target = storage.delete_question_files if service == "storage" else validator.drop_question_schema
    target.side_effect = RuntimeError("offline")
    assert client.delete(f"/api/questions/{qid}").status_code == 503
    assert db.get(Question, qid).status == "DELETING"
    assert client.post(f"/api/questions/{qid}/publish").status_code == 409
    target.side_effect = None
    assert client.delete(f"/api/questions/{qid}").status_code == 200


def test_cached_details_enforce_visibility(context):
    client, _, app, _, student, cache, *_ = context
    app.dependency_overrides[get_optional_current_user] = lambda: student
    cache.get_cached_question.return_value = {"id": 1, "publishedStatus": "READY"}
    assert client.get("/api/questions/1").status_code == 403


def test_unpublished_question_rejects_submission(context):
    client, _, app, _, student, *_ = context
    qid = client.post("/api/questions", json=payload()).json()["id"]
    app.dependency_overrides[get_current_user] = lambda: student
    assert client.post("/api/submissions", json={"questionId": qid, "query": "SELECT 1"}).status_code == 403


@pytest.mark.parametrize("path,method", [("/api/questions/999", "get"), ("/api/questions/999", "delete"), ("/api/questions/999/publish", "post")])
def test_missing_question(context, path, method):
    assert context[0].request(method, path).status_code == 404


def test_s3_delete_uses_exact_directory():
    manager = object.__new__(S3Manager)
    manager.bucket_name = "test"
    manager.list_files = Mock(return_value=["questions/1/schema.sql"])
    manager.s3 = Mock()
    manager.s3.delete_objects.return_value = {"Deleted": [{"Key": "questions/1/schema.sql"}]}
    assert manager.delete_question_files(1) == 1
    manager.list_files.assert_called_once_with(prefix="questions/1/")
    manager.s3.delete_objects.return_value = {"Errors": [{"Key": "questions/1/schema.sql"}]}
    with pytest.raises(RuntimeError, match="parcial"):
        manager.delete_question_files(1)
