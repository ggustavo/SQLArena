"""
Script de testes e validação das operações do Amazon SQS.
Demonstra:
1. Conexão com o SQS (local ou AWS)
2. Consulta de estatísticas da fila
3. Envio de mensagens (payloads JSON e atributos)
4. Leitura / consumo de mensagens
5. Remoção de mensagem com ReceiptHandle
6. Inspeção da Dead Letter Queue (DLQ)
7. Limpeza (Purge) da fila
"""

import json
import sys
import time
from queue_manager import SQSQueueManager


def print_separator(title: str):
    print("\n" + "=" * 60)
    print(f"  {title.upper()}")
    print("=" * 60)


def run_tests():
    print_separator("1. Inicializando Gerenciador SQS")
    manager = SQSQueueManager()

    print(f"[*] Fila Principal Alvo : {manager.queue_name}")
    print(f"[*] Fila DLQ Alvo       : {manager.dlq_name}")
    print(f"[*] Endpoint AWS        : {manager.endpoint_url or 'AWS Real'}")
    print(f"[*] Região              : {manager.region_name}")

    try:
        queue_url = manager.get_queue_url()
        print(f"[✓] URL da Fila Principal obtida: {queue_url}")
    except Exception as e:
        print(f"[!] Falha ao conectar na fila principal: {e}")
        print("[!] Verifique se o Ministack está rodando e se o Terraform aplicou o sqs.tf.")
        sys.exit(1)

    dlq_url = manager.get_dlq_url()
    if dlq_url:
        print(f"[✓] URL da DLQ obtida: {dlq_url}")
    else:
        print("[i] Fila DLQ não encontrada (ou ainda não criada).")

    # ------------------------------------------------------------------
    # 2. Estatísticas Iniciais
    # ------------------------------------------------------------------
    print_separator("2. Estatísticas Iniciais da Fila")
    stats = manager.get_queue_stats()
    print(f"[*] Mensagens disponíveis para consumo: {stats.get('mensagens_disponiveis')}")
    print(f"[*] Mensagens em processamento (invisíveis): {stats.get('mensagens_em_processamento')}")

    # ------------------------------------------------------------------
    # 3. Enviar Mensagens de Teste
    # ------------------------------------------------------------------
    print_separator("3. Enviando Mensagens de Teste")

    payload_1 = {
        "submission_id": 1001,
        "student_id": 42,
        "question_id": 10,
        "query": "SELECT * FROM orders WHERE status = 'completed';",
        "timestamp": time.time(),
    }

    payload_2 = {
        "submission_id": 1002,
        "student_id": 43,
        "question_id": 10,
        "query": "SELECT customer_id, COUNT(*) FROM orders GROUP BY customer_id;",
        "timestamp": time.time(),
    }

    res1 = manager.send_message(
        payload=payload_1,
        attributes={"Source": "WebAPI", "Priority": 1},
    )
    print(f"[✓] Mensagem 1 enviada! MessageId: {res1.get('MessageId')}")

    res2 = manager.send_message(
        payload=payload_2,
        attributes={"Source": "WebAPI", "Priority": 2},
    )
    print(f"[✓] Mensagem 2 enviada! MessageId: {res2.get('MessageId')}")

    # ------------------------------------------------------------------
    # 4. Verificar Estatísticas Atualizadas
    # ------------------------------------------------------------------
    print_separator("4. Verificando Fila Pós-Envio")
    time.sleep(1)
    stats = manager.get_queue_stats()
    print(f"[*] Mensagens disponíveis agora: {stats.get('mensagens_disponiveis')}")

    # ------------------------------------------------------------------
    # 5. Receber e Consumir Mensagem
    # ------------------------------------------------------------------
    print_separator("5. Recebendo e Processando Mensagens")
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

        # Simula o processamento do backend e deleta da fila
        print("[*] Processamento concluído com sucesso. Removendo da fila...")
        success = manager.delete_message(receipt_handle)
        if success:
            print(f"[✓] Mensagem {msg_id} removida definitivamente da fila.")
        else:
            print(f"[!] Falha ao remover mensagem {msg_id}.")

    # ------------------------------------------------------------------
    # 6. Checar a Dead Letter Queue (DLQ)
    # ------------------------------------------------------------------
    print_separator("6. Verificando Dead Letter Queue (DLQ)")
    dlq_messages = manager.receive_dlq_messages(max_messages=5, wait_time_seconds=1)
    if dlq_messages:
        print(f"[!] Existem {len(dlq_messages)} mensagens na DLQ precisando de atenção!")
        for dlq_msg in dlq_messages:
            print(f" - DLQ MessageId: {dlq_msg.get('MessageId')} | Body: {dlq_msg.get('Body')}")
    else:
        print("[✓] DLQ está limpa (nenhuma mensagem falhou).")

    # ------------------------------------------------------------------
    # 7. Resumo Final
    # ------------------------------------------------------------------
    print_separator("7. Resumo Final da Fila")
    final_stats = manager.get_queue_stats()
    print(f"[*] Mensagens restantes disponíveis: {final_stats.get('mensagens_disponiveis')}")
    print("[✓] Testes do ciclo de vida do SQS concluídos com sucesso!\n")


if __name__ == "__main__":
    run_tests()
