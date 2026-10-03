"""
Script de testes e validação das operações do Amazon S3 no SQLArena.
Demonstra:
1. Conexão com o S3 (Ministack local ou AWS real)
2. Verificação / Criação automática do Bucket
3. Upload dos scripts SQL de uma questão (schema.sql, data.sql, answer.sql)
4. Leitura e validação do conteúdo dos arquivos diretamente do S3
5. Simulação de Bootstrapping do Worker (download dos arquivos para disco local)
6. Upload do dataset CSV da questão (arquivo binário obrigatório — Requisito 3)
7. Notificação ao Worker via SQS após o upload do binário (desacoplamento — Requisito 6)
8. Listagem e checagem de existência de objetos
9. Deleção dos arquivos da questão, incluindo o CSV (ciclo de vida de exclusão)
"""

import os
from pathlib import Path
import shutil
import sys

# Garante a resolução correta de módulos executando de qualquer diretório
_testes_dir = Path(__file__).resolve().parent
_app_dir = _testes_dir.parent
_project_root = _app_dir.parent

for _p in [str(_project_root), str(_app_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from app.s3.s3_manager import S3Manager
    from app.sqs.queue_manager import SQSQueueManager
except ImportError:
    from s3.s3_manager import S3Manager
    from sqs.queue_manager import SQSQueueManager



def print_separator(title: str):
    print("\n" + "=" * 60)
    print(f"  {title.upper()}")
    print("=" * 60)


def run_tests():
    print_separator("1. Inicializando Gerenciador S3")
    manager = S3Manager()

    print(f"[*] Bucket Alvo   : {manager.bucket_name}")
    print(f"[*] Endpoint AWS  : {manager.endpoint_url or 'AWS Real'}")
    print(f"[*] Região        : {manager.region_name}")

    # ------------------------------------------------------------------
    # 2. Assegurar Existência do Bucket
    # ------------------------------------------------------------------
    print_separator("2. Verificando / Criando Bucket S3")
    try:
        manager.ensure_bucket_exists()
        print(f"[✓] Bucket '{manager.bucket_name}' pronto para uso.")
    except Exception as e:
        print(f"[!] Falha ao verificar/criar bucket S3: {e}")
        print("[!] Verifique se o Ministack está rodando (docker compose up -d).")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3. Upload dos Scripts SQL da Questão (schema, data, answer)
    # ------------------------------------------------------------------
    question_id = 10
    print_separator(f"3. Upload dos Scripts SQL para Questão #{question_id}")

    schema_sql_content = """-- Estrutura da Questao 10
CREATE TABLE IF NOT EXISTS orders (
    order_id INT PRIMARY KEY,
    customer_id INT NOT NULL,
    total NUMERIC(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

    data_sql_content = """-- Carga de dados iniciais da Questao 10
INSERT INTO orders (order_id, customer_id, total, status) VALUES
(1, 101, 150.00, 'completed'),
(2, 102, 89.90, 'pending'),
(3, 101, 230.50, 'completed'),
(4, 103, 45.00, 'completed')
ON CONFLICT (order_id) DO NOTHING;
"""

    answer_sql_content = """-- Gabarito do Professor (com ORDER BY obrigatorio)
SELECT customer_id, SUM(total) AS total_gasto
FROM orders
WHERE status = 'completed'
GROUP BY customer_id
ORDER BY total_gasto DESC;
"""

    uploaded_keys = manager.upload_question_sql_files(
        question_id=question_id,
        schema_sql=schema_sql_content,
        data_sql=data_sql_content,
        answer_sql=answer_sql_content,
    )

    for role, key in uploaded_keys.items():
        print(f"[✓] {role.upper():<7} -> s3://{manager.bucket_name}/{key}")

    # ------------------------------------------------------------------
    # 4. Leitura e Validação dos Conteúdos no S3
    # ------------------------------------------------------------------
    print_separator(f"4. Lendo Conteúdo dos Arquivos da Questão #{question_id}")
    files_content = manager.get_question_sql_files(question_id)

    print("[*] Conteúdo do answer.sql recuperado do S3:")
    print("-" * 40)
    print(files_content["answer"].strip())
    print("-" * 40)

    assert "ORDER BY total_gasto DESC" in files_content["answer"]
    print("[✓] Conteúdo validado com sucesso!")

    # ------------------------------------------------------------------
    # 5. Simulação de Bootstrapping do Worker (Download local)
    # ------------------------------------------------------------------
    print_separator("5. Simulação de Bootstrapping do Worker (Download Local)")
    local_download_dir = _project_root / ".temp_test_worker_boot" / f"pergunta_{question_id}"
    try:
        downloaded_paths = manager.download_question_sql_files(question_id, local_download_dir)
        for role, path in downloaded_paths.items():
            print(f"[✓] Arquivo {role} salvo localmente em: {path} ({path.stat().st_size} bytes)")
    finally:
        # Limpeza do diretório temporário após validação
        if local_download_dir.parent.exists():
            shutil.rmtree(local_download_dir.parent, ignore_errors=True)
            print("[*] Diretório temporário de bootstrapping limpo.")

    # ------------------------------------------------------------------
    # 6. Upload do Dataset CSV (Arquivo Binário Obrigatório — Requisito 3)
    # ------------------------------------------------------------------
    print_separator(f"6. Upload do Dataset CSV para Questão #{question_id}")
    csv_content = (
        "order_id,customer_id,total,status\n"
        "1,101,150.00,completed\n"
        "2,102,89.90,pending\n"
        "3,101,230.50,completed\n"
        "4,103,45.00,completed\n"
    ).encode("utf-8")

    dataset_key = manager.upload_question_dataset_csv(question_id, csv_content)
    print(f"[✓] DATASET -> s3://{manager.bucket_name}/{dataset_key}")

    assert manager.has_question_dataset(question_id), "O dataset deveria existir após o upload."
    downloaded_bytes = manager.get_question_dataset_csv_bytes(question_id)
    assert downloaded_bytes == csv_content, "Conteúdo do CSV baixado não bate com o original."
    print(f"[✓] Dataset lido de volta do S3 ({len(downloaded_bytes)} bytes) e validado.")

    # ------------------------------------------------------------------
    # 7. Notificando o Worker via SQS (Desacoplamento — Requisito 6)
    # ------------------------------------------------------------------
    print_separator("7. Notificando o Worker via SQS")
    try:
        sqs = SQSQueueManager()
        before = sqs.get_queue_stats()
        sqs.send_message(
            payload={
                "event_type": "DATASET_UPLOADED",
                "question_id": question_id,
                "s3_key": dataset_key,
                "file_type": "csv",
            },
            attributes={"event_type": "DATASET_UPLOADED"},
        )
        after = sqs.get_queue_stats()
        print(f"[✓] Mensagem enviada para a fila '{sqs.queue_name}'.")
        print(f"[*] Mensagens disponíveis antes: {before.get('mensagens_disponiveis')} | depois: {after.get('mensagens_disponiveis')}")
    except Exception as e:
        print(f"[!] Não foi possível notificar o SQS (Ministack rodando?): {e}")
        print("[*] Seguindo mesmo assim — essa etapa depende da fila configurada pela")

    # ------------------------------------------------------------------
    # 8. Listagem de Arquivos no Bucket
    # ------------------------------------------------------------------
    print_separator("8. Listando Todos os Arquivos no Bucket")
    all_files = manager.list_files()
    print(f"[*] Total de arquivos encontrados: {len(all_files)}")
    for key in all_files:
        print(f" - {key}")

    # ------------------------------------------------------------------
    # 9. Ciclo de Vida: Deleção de Questão (remove SQL + CSV juntos)
    # ------------------------------------------------------------------
    print_separator(f"9. Excluindo Arquivos da Questão #{question_id} (Deleção de Questão)")
    deleted_count = manager.delete_question_files(question_id)
    print(f"[✓] {deleted_count} arquivo(s) removido(s) do S3 (SQL + CSV juntos).")

    # Confirmação
    remaining = manager.list_files(prefix=f"questions/{question_id}")
    print(f"[*] Arquivos restantes para a questão #{question_id}: {len(remaining)}")
    assert len(remaining) == 0, "Deveriam existir 0 arquivos após a deleção."
    print("[✓] Exclusão confirmada no S3 com sucesso!")

    print_separator("10. Resumo Final")
    print("[✓] Todos os testes das operações com S3 (incluindo dataset CSV) foram concluídos com sucesso!\n")


if __name__ == "__main__":
    run_tests()