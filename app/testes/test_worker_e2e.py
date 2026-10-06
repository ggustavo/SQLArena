import json
import time
import pytest
from app.worker.executor import SandboxExecutor
from app.worker.main import SubmissionWorker
from app.sqs.queue_manager import SQSQueueManager
from app.cache.redis_client import redis_client

def test_executor_correct_query():
    executor = SandboxExecutor()
    correct_query = """
    SELECT 
        c.nome, 
        SUM(p.valor_total) AS faturamento_total
    FROM clientes c
    JOIN pedidos p ON p.cliente_id = c.id
    WHERE p.status = 'FINALIZADO'
    GROUP BY c.id, c.nome
    ORDER BY faturamento_total DESC, c.nome ASC
    LIMIT 5;
    """
    res = executor.execute_student_query(1, correct_query)
    assert res["outcome"] == "SUCCESS"
    assert res["strictModeHashMatched"] is True
    assert res["executionTimeMs"] > 0
    assert len(res["rows"]) > 0

def test_executor_wrong_answer():
    executor = SandboxExecutor()
    wrong_query = "SELECT nome, email FROM clientes ORDER BY nome ASC LIMIT 5;"
    res = executor.execute_student_query(1, wrong_query)
    assert res["outcome"] == "WRONG_ANSWER"
    assert res["strictModeHashMatched"] is False
    assert "Resultado divergente" in res["errorMessage"]

def test_executor_syntax_error():
    executor = SandboxExecutor()
    syntax_error_query = "SELECT nome FORM clientes WHERE;"
    res = executor.execute_student_query(1, syntax_error_query)
    assert res["outcome"] == "SYNTAX_ERROR"
    assert res["strictModeHashMatched"] is False
    assert "syntax error" in res["errorMessage"].lower()

def test_executor_security_block_dml():
    executor = SandboxExecutor()
    dangerous_query = "DELETE FROM clientes; SELECT 1;"
    res = executor.execute_student_query(1, dangerous_query)
    assert res["outcome"] == "SYNTAX_ERROR"
    assert "Comando não permitido" in res["errorMessage"]

def test_worker_process_message_end_to_end():
    worker = SubmissionWorker()
    sub_id = "test_sub_e2e_direct_456"
    msg = {
        "Body": json.dumps({
            "submission_id": sub_id,
            "user_id": "user_001",
            "question_id": 1,
            "query": """
            SELECT c.nome, SUM(p.valor_total) AS faturamento_total
            FROM clientes c
            JOIN pedidos p ON p.cliente_id = c.id
            WHERE p.status = 'FINALIZADO'
            GROUP BY c.id, c.nome
            ORDER BY faturamento_total DESC, c.nome ASC
            LIMIT 5;
            """
        }),
        "ReceiptHandle": None
    }
    success = worker.process_message(msg)
    assert success is True
    
    # Verifica status final persistido no Redis
    status_data = redis_client.get_submission_status(sub_id)
    assert status_data is not None
    assert status_data["status"] == "DONE"
    assert status_data["outcome"] == "SUCCESS"
    assert status_data["strictModeHashMatched"] is True
    assert status_data["executionTimeMs"] > 0
    assert len(status_data["rows"]) == 3

    # Limpeza pós-teste
    from app.dynamodb.dynamo_manager import DynamoDBManager
    dynamo = DynamoDBManager()
    try:
        dynamo.table.delete_item(Key={"submission_id": sub_id})
    except Exception:
        pass
    redis_client.delete_submission(sub_id)

def main():
    """Simulação manual de envio para validação ad-hoc."""
    manager = SQSQueueManager()

    # 1. Enviar submissao correta
    payload_ok = {
        "submission_id": "sub_test_001",
        "student_id": "aluno_felipe",
        "question_id": 1,
        "sql_query": "SELECT id, name FROM users ORDER BY id;"
    }
    print("[TESTE] Enviando submissao normal para a fila...")
    manager.send_message(payload_ok)

    # 2. Enviar submissao com erro de sintaxe (para validar diagnostico)
    payload_error = {
        "submission_id": "sub_test_002",
        "student_id": "aluno_felipe",
        "question_id": 1,
        "sql_query": "SELECT * FRROM nonexistent_table;"
    }
    print("[TESTE] Enviando submissao com erro sintatico...")
    manager.send_message(payload_error)

    # 3. Checar status da fila
    stats = manager.get_queue_stats()
    print(f"[STATUS FILA]: {stats}")

if __name__ == "__main__":
    main()
