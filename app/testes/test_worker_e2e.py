"""
Teste E2E para simular o envio de submissoes na SQS e validar o consumo do Worker.
"""

import time
from sqs.queue_manager import SQSQueueManager

def main():
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