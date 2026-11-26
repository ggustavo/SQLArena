import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app
from app.config import settings
from app.kafka.kafka_manager import KafkaQueueManager
from app.database.session import SessionLocal
from app.database.models import User, Question, UserSolvedQuestion
from app.database.seed import seed_database

client = TestClient(app)


# ==============================================================================
# 1. Testes de Segurança: Callback de Workers (x-internal-key)
# ==============================================================================

def test_callback_without_internal_key_forbidden():
    """Requisições ao callback sem o cabeçalho x-internal-key devem ser rejeitadas com HTTP 403."""
    with patch.object(settings, "INTERNAL_API_KEY", "secret-test-key-123"):
        response = client.post("/api/submissions/callback", json={
            "submission_id": "test_sub_no_key",
            "user_id": "1",
            "question_id": 1,
            "is_correct": True,
            "execution_time_ms": 12.5
        })
        assert response.status_code == 403
        assert "inválida ou ausente" in response.json()["detail"]


def test_callback_with_invalid_internal_key_forbidden():
    """Requisições ao callback com chave x-internal-key incorreta devem receber HTTP 403."""
    with patch.object(settings, "INTERNAL_API_KEY", "secret-test-key-123"):
        response = client.post(
            "/api/submissions/callback",
            headers={"x-internal-key": "wrong-key-xyz"},
            json={
                "submission_id": "test_sub_wrong_key",
                "user_id": "1",
                "question_id": 1,
                "is_correct": True,
                "execution_time_ms": 10.0
            }
        )
        assert response.status_code == 403
        assert "inválida ou ausente" in response.json()["detail"]


def test_callback_with_valid_internal_key_allowed():
    """Requisições ao callback com x-internal-key válida devem ser processadas com HTTP 200."""
    with patch.object(settings, "INTERNAL_API_KEY", "secret-test-key-123"):
        # Mock do DynamoDB para o teste de callback
        with patch("app.api.submissions.DynamoDBManager") as mock_dynamo_cls:
            mock_dynamo_inst = MagicMock()
            mock_dynamo_cls.return_value = mock_dynamo_inst

            response = client.post(
                "/api/submissions/callback",
                headers={"x-internal-key": "secret-test-key-123"},
                json={
                    "submission_id": "test_sub_valid_auth",
                    "user_id": "1",
                    "question_id": 1,
                    "is_correct": False,
                    "execution_time_ms": 25.0,
                    "error_message": "Consulta incorreta"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["submissionId"] == "test_sub_valid_auth"


# ==============================================================================
# 2. Testes de Health Check Real (Postgres, Redis, MinIO)
# ==============================================================================

def test_health_check_healthy():
    """Verifica se /api/health retorna HTTP 200 e detalha todos os serviços quando ativos."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "postgres" in data["checks"]
    assert "redis" in data["checks"]
    assert "minio" in data["checks"]


def test_health_check_unhealthy_when_postgres_fails():
    """Quando o PostgreSQL falhar, o health check deve retornar HTTP 503 e acusar o erro."""
    with patch("app.main.engine.connect", side_effect=OperationalError("connection refused", {}, None)):
        response = client.get("/api/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "unhealthy" in data["checks"]["postgres"]


def test_health_check_unhealthy_when_redis_fails():
    """Quando o Redis falhar, o health check deve retornar HTTP 503."""
    with patch("app.main.redis_client.ping", return_value=False):
        response = client.get("/api/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "unhealthy" in data["checks"]["redis"]


# ==============================================================================
# 3. Testes de Confiabilidade do Kafka (Offsets e DLQ)
# ==============================================================================

def test_kafka_delete_message_retains_offset_on_commit_failure():
    """Se o commit do offset falhar no Kafka, o handle NÃO pode ser removido de _uncommitted_offsets."""
    mgr = KafkaQueueManager(queue_name="test-queue", dlq_name="test-dlq")
    handle = "test-queue:0:42"
    mgr._uncommitted_offsets[handle] = ("test-queue", 0, 42, '{"sub": 1}')
    mgr._retry_counts[handle] = 1

    mock_consumer = MagicMock()
    mock_consumer.commit.side_effect = Exception("Kafka commit timeout")
    mgr._consumer = mock_consumer

    success = mgr.delete_message(handle)

    assert success is False
    # O offset deve ser PRESERVADO para recuperação/reprocessamento
    assert handle in mgr._uncommitted_offsets
    assert handle in mgr._retry_counts


def test_kafka_delete_message_removes_offset_on_success():
    """Ao concluir o commit com sucesso, o handle é devidamente removido do rastreamento."""
    mgr = KafkaQueueManager(queue_name="test-queue", dlq_name="test-dlq")
    handle = "test-queue:0:42"
    mgr._uncommitted_offsets[handle] = ("test-queue", 0, 42, '{"sub": 1}')
    mgr._retry_counts[handle] = 1

    mock_consumer = MagicMock()
    mock_consumer.commit.return_value = None
    mgr._consumer = mock_consumer

    success = mgr.delete_message(handle)

    assert success is True
    assert handle not in mgr._uncommitted_offsets
    assert handle not in mgr._retry_counts


def test_kafka_dlq_failure_preserves_offset():
    """Quando o envio para DLQ falhar, o offset deve ser preservado para novas tentativas."""
    mgr = KafkaQueueManager(queue_name="test-queue", dlq_name="test-dlq")
    handle = "test-queue:0:99"
    mgr._uncommitted_offsets[handle] = ("test-queue", 0, 99, '{"sub": 99}')
    mgr._retry_counts[handle] = 4  # A próxima tentativa será a 5ª (gatilho de DLQ)

    mock_consumer = MagicMock()
    mock_producer = MagicMock()
    mock_producer.send.side_effect = Exception("Broker DLQ indisponível")

    mgr._consumer = mock_consumer
    mgr._producer = mock_producer

    # Ao chamar receive_messages com erro no envio à DLQ:
    try:
        mgr.receive_messages(max_messages=1, wait_time_seconds=0.1)
    except Exception:
        pass

    # Como o envio à DLQ falhou, a mensagem NÃO foi descartada silenciosamente
    assert handle in mgr._uncommitted_offsets
    assert mgr._retry_counts[handle] == 5


# ==============================================================================
# 4. Testes de Proteção de Progresso e Idempotência do Seed
# ==============================================================================

def test_seed_preserves_user_scores_and_history():
    """O seed sem --reset-all não deve zerar a pontuação de usuários existentes."""
    db = SessionLocal()
    try:
        # Busca ou cria usuário de teste
        user = db.query(User).filter_by(email="gustavo@sqlarena.com").first()
        if user:
            original_score = 150
            user.score = original_score
            user.streak = 5
            db.commit()

            # Executa seed idempotente
            seed_database(only_if_empty=False, reset_all=False)

            # Recarrega usuário e valida que a pontuação não foi zerada
            db.refresh(user)
            assert user.score == original_score, f"O score foi alterado de {original_score} para {user.score}"
            assert user.streak == 5
    finally:
        db.close()


def test_seed_if_empty_skips_when_database_populated():
    """Com --if-empty, o seed deve pular imediatamente se já houver pelo menos 21 questões."""
    db = SessionLocal()
    try:
        q_count = db.query(Question).count()
        if q_count >= 21:
            with patch("app.database.seed.MinioManager") as mock_minio:
                seed_database(only_if_empty=True, reset_all=False)
                # MinIO não deve ser chamado para semear novamente se o banco já estiver preenchido
                mock_minio.return_value.upload_file_from_bytes.assert_not_called()
    finally:
        db.close()
