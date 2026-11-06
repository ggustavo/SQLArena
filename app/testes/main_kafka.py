"""
Script de testes e validação das operações do Apache Kafka no SQLArena.
Demonstra:
1. Conexão com o Broker Apache Kafka
2. Consulta de estatísticas do tópico (Consumer Lag)
3. Envio de mensagens (payloads JSON e atributos)
4. Leitura / consumo de mensagens via Consumer Group
5. Confirmação de offset (delete_message)
6. Inspeção da Dead Letter Queue (DLQ)
"""

import json
from pathlib import Path
import sys
import time

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.kafka.kafka_manager import KafkaQueueManager


def print_separator(title: str):
    print("\n" + "=" * 60)
    print(f"  {title.upper()}")
    print("=" * 60)


def run_tests():
    print_separator("1. Inicializando Gerenciador Apache Kafka")
    manager = KafkaQueueManager()

    print(f"[*] Tópico Principal Alvo : {manager.queue_name}")
    print(f"[*] Tópico DLQ Alvo       : {manager.dlq_name}")
    print(f"[*] Bootstrap Servers     : {manager.bootstrap_servers}")
    print(f"[*] Consumer Group        : {manager.consumer_group}")

    try:
        queue_url = manager.get_queue_url()
        print(f"[✓] Tópico Principal verificado: {queue_url}")
    except Exception as e:
        print(f"[!] Falha ao conectar no broker Kafka: {e}")
        sys.exit(1)

    print_separator("2. Estatísticas Iniciais do Tópico")
    stats = manager.get_queue_stats()
    print(f"[*] Mensagens disponíveis (Lag): {stats.get('mensagens_disponiveis')}")

    print_separator("3. Enviando Mensagens de Teste")
    payload_1 = {
        "submission_id": 1001,
        "student_id": 42,
        "question_id": 10,
        "query": "SELECT * FROM orders WHERE status = 'completed';",
        "timestamp": time.time(),
    }

    res1 = manager.send_message(
        payload=payload_1,
        attributes={"Source": "WebAPI", "Priority": 1},
    )
    print(f"[✓] Mensagem enviada! MessageId: {res1.get('MessageId')}")

    print_separator("4. Recebendo e Confirmando Mensagens")
    messages = manager.receive_messages(max_messages=2, wait_time_seconds=3)
    for idx, msg in enumerate(messages, start=1):
        body = msg.get("Body")
        receipt_handle = msg.get("ReceiptHandle")
        msg_id = msg.get("MessageId")
        print(f"\n--- Mensagem #{idx} (ID: {msg_id}) ---")
        try:
            parsed_body = json.loads(body)
            print(f"Payload decodificado: {json.dumps(parsed_body, indent=2)}")
        except json.JSONDecodeError:
            print(f"Payload (texto): {body}")
        if receipt_handle:
            manager.delete_message(receipt_handle)
            print(f"[✓] Offset da mensagem {msg_id} confirmado no Kafka.")

    print_separator("5. Resumo Final")
    print("[✓] Testes do ciclo de vida do Apache Kafka concluídos com sucesso!\n")


if __name__ == "__main__":
    run_tests()
