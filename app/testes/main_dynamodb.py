"""
Script de testes e validação das operações do Amazon DynamoDB no SQLArena.
Demonstra:
1. Conexão com o DynamoDB (Ministack local ou AWS real)
2. Verificação / Criação automática da tabela de logs imutáveis
3. Registro inicial de submissão (simulando FastAPI recebendo requisição do aluno)
4. Consulta por ID (simulando Polling do Frontend)
5. Atualização da submissão com resultado do processamento do Worker (acerto e erro com log do PostgreSQL)
6. Consulta de histórico de tentativas de um aluno via Global Secondary Index (StudentIndex)
"""

import json
from pathlib import Path
import sys
import time

# Garante a resolução correta de módulos executando de qualquer diretório
_testes_dir = Path(__file__).resolve().parent
_app_dir = _testes_dir.parent
_project_root = _app_dir.parent

for _p in [str(_project_root), str(_app_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from app.dynamodb.dynamo_manager import DynamoDBManager
except ImportError:
    from dynamodb.dynamo_manager import DynamoDBManager


def print_separator(title: str):
    print("\n" + "=" * 60)
    print(f"  {title.upper()}")
    print("=" * 60)


def run_tests():
    print_separator("1. Inicializando Gerenciador DynamoDB")
    manager = DynamoDBManager()

    print(f"[*] Tabela Alvo : {manager.table_name}")
    print(f"[*] Endpoint AWS: {manager.endpoint_url or 'AWS Real'}")
    print(f"[*] Região      : {manager.region_name}")

    # ------------------------------------------------------------------
    # 2. Assegurar Existência da Tabela
    # ------------------------------------------------------------------
    print_separator("2. Verificando / Criando Tabela DynamoDB")
    try:
        manager.ensure_table_exists()
        print(f"[✓] Tabela '{manager.table_name}' pronta para gravação de logs.")
    except Exception as e:
        print(f"[!] Falha ao verificar/criar tabela DynamoDB: {e}")
        print("[!] Verifique se o Ministack está rodando.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3. Simulação Transacional: Registro Inicial (FastAPI - HTTP 202)
    # ------------------------------------------------------------------
    submission_id = f"sub-{int(time.time())}"
    student_id = "aluno-42"
    question_id = "10"
    student_query = "SELECT customer_id, SUM(total) FROM orders WHERE status = 'completed' GROUP BY customer_id ORDER BY SUM(total) DESC;"

    print_separator(f"3. Registrando Submissão Inicial (ID: {submission_id})")
    initial_log = manager.save_execution_log(
        submission_id=submission_id,
        student_id=student_id,
        question_id=question_id,
        query=student_query,
        status="PENDING",
        is_correct=False,
    )
    print(f"[✓] Submissão registrada com status: {initial_log.get('status')}")

    # ------------------------------------------------------------------
    # 4. Simulação: Frontend fazendo Polling do status
    # ------------------------------------------------------------------
    print_separator("4. Simulação de Polling pelo Frontend")
    fetched = manager.get_submission_log(submission_id)
    assert fetched is not None, "Submissão deveria existir na tabela"
    print(f"[✓] Polling retornou status atual: '{fetched.get('status')}'")

    # ------------------------------------------------------------------
    # 5. Simulação: Worker finaliza a execução com Sucesso (+1 ponto)
    # ------------------------------------------------------------------
    print_separator("5. Worker atualizando resultado da execução (Acerto)")
    simulated_hash = "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e"
    updated = manager.update_submission_status(
        submission_id=submission_id,
        status="SUCCESS",
        is_correct=True,
        execution_time_ms=34.82,
        hash_result=simulated_hash,
    )
    print(f"[✓] Status final pós-Worker: {updated.get('status')}")
    print(f"[✓] Resposta correta: {updated.get('is_correct')}")
    print(f"[✓] Tempo de execução: {updated.get('execution_time_ms')} ms")
    print(f"[✓] Hash gerado: {updated.get('hash_result')[:16]}...")

    # ------------------------------------------------------------------
    # 6. Registro de Tentativa com Erro do PostgreSQL (Requisito 8)
    # ------------------------------------------------------------------
    print_separator("6. Registrando Submissão com Erro Técnico do PostgreSQL")
    error_sub_id = f"sub-err-{int(time.time())}"
    bad_query = "SELECT customer_id FORM orders;"
    pg_error_msg = 'syntax error at or near "orders"\nLINE 1: SELECT customer_id FORM orders;\n                                ^'

    manager.save_execution_log(
        submission_id=error_sub_id,
        student_id=student_id,
        question_id=question_id,
        query=bad_query,
        status="ERROR",
        is_correct=False,
        execution_time_ms=12.10,
        pg_error=pg_error_msg,
    )
    error_log = manager.get_submission_log(error_sub_id)
    print(f"[✓] Submissão #{error_sub_id} gravada com status '{error_log.get('status')}'")
    print(f"[✓] Log nativo do Postgres preservado:\n---\n{error_log.get('pg_error')}\n---")

    # ------------------------------------------------------------------
    # 7. Consulta de Histórico do Aluno via GSI (StudentIndex)
    # ------------------------------------------------------------------
    print_separator(f"7. Consultando Histórico do Aluno '{student_id}' (via GSI)")
    history = manager.list_student_submissions(student_id)
    print(f"[*] Total de tentativas encontradas para o aluno: {len(history)}")
    for item in history:
        print(f" - Submissão: {item.get('submission_id')} | Status: {item.get('status')} | Correto: {item.get('is_correct')} | Data: {item.get('created_at')}")

    print_separator("8. Resumo Final")
    print("[✓] Todos os testes das operações com DynamoDB foram concluídos com sucesso!\n")


if __name__ == "__main__":
    run_tests()
