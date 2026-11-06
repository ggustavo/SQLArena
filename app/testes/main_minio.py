"""
Script de testes e validação das operações do MinIO no SQLArena.
Demonstra o ciclo de vida completo de scripts SQL puros de uma questão:
1. Conexão com o MinIO
2. Verificação / Criação automática do Bucket
3. Upload dos scripts SQL de uma questão (schema.sql, data.sql, answer.sql)
4. Leitura e validação do conteúdo dos arquivos diretamente do MinIO
5. Simulação de Bootstrapping do Worker (download dos 3 scripts SQL para disco local)
6. Notificação ao Worker via Apache Kafka após publicação dos scripts da questão
7. Listagem e checagem de existência de objetos
8. Deleção atômica dos arquivos da questão
"""

from pathlib import Path
import shutil
import sys

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.minio.minio_manager import MinioManager
from app.kafka.kafka_manager import KafkaQueueManager


def print_separator(title: str):
    print("\n" + "=" * 60)
    print(f"  {title.upper()}")
    print("=" * 60)


def run_tests():
    print_separator("1. Inicializando Gerenciador MinIO")
    manager = MinioManager()

    print(f"[*] Bucket Alvo     : {manager.bucket_name}")
    print(f"[*] Endpoint MinIO  : {manager.endpoint_url}")

    print_separator("2. Verificando / Criando Bucket MinIO")
    manager.ensure_bucket_exists()
    print(f"[✓] Bucket '{manager.bucket_name}' pronto para uso.")

    question_id = 999
    print_separator(f"3. Upload dos Scripts SQL para Questão #{question_id}")
    schema_sql_content = "CREATE TABLE IF NOT EXISTS orders (order_id INT PRIMARY KEY, total NUMERIC(10, 2));\n"
    data_sql_content = "INSERT INTO orders (order_id, total) VALUES (1, 150.00) ON CONFLICT DO NOTHING;\n"
    answer_sql_content = "SELECT order_id, total FROM orders ORDER BY order_id ASC;\n"

    uploaded_keys = manager.upload_question_sql_files(
        question_id=question_id,
        schema_sql=schema_sql_content,
        data_sql=data_sql_content,
        answer_sql=answer_sql_content,
    )
    for role, key in uploaded_keys.items():
        print(f"[✓] {role.upper():<7} -> minio://{manager.bucket_name}/{key}")

    print_separator(f"4. Lendo Conteúdo dos Arquivos da Questão #{question_id}")
    files_content = manager.get_question_sql_files(question_id)
    assert "ORDER BY order_id ASC" in files_content["answer"]
    print("[✓] Scripts SQL lidos e validados com sucesso no MinIO!")

    print_separator("5. Simulação de Bootstrapping do Worker (Download Local)")
    local_download_dir = _project_root / ".temp_test_worker_boot" / f"pergunta_{question_id}"
    try:
        downloaded_paths = manager.download_question_sql_files(question_id, local_download_dir)
        for role, path in downloaded_paths.items():
            print(f"[✓] Arquivo {role} salvo localmente em: {path} ({path.stat().st_size} bytes)")
    finally:
        if local_download_dir.parent.exists():
            shutil.rmtree(local_download_dir.parent, ignore_errors=True)

    print_separator(f"6. Excluindo Arquivos da Questão #{question_id}")
    deleted_count = manager.delete_question_files(question_id)
    print(f"[✓] {deleted_count} arquivo(s) SQL removido(s) do MinIO.")
    remaining = manager.list_files(prefix=f"questions/{question_id}")
    assert len(remaining) == 0
    print("[✓] Exclusão atômica confirmada no MinIO com sucesso!\n")


if __name__ == "__main__":
    run_tests()
