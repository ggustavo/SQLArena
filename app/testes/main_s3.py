"""
Script de testes e validação das operações do Amazon S3 no SQLArena.
Demonstra:
1. Conexão com o S3 (Ministack local ou AWS real)
2. Verificação / Criação automática do Bucket
3. Upload dos scripts SQL de uma questão (schema.sql, data.sql, answer.sql)
4. Leitura e validação do conteúdo dos arquivos diretamente do S3
5. Simulação de Bootstrapping do Worker (download dos arquivos para disco local)
6. Listagem e checagem de existência de objetos
7. Deleção dos arquivos da questão (ciclo de vida de exclusão)
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
except ImportError:
    from s3.s3_manager import S3Manager



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
    # 6. Listagem de Arquivos no Bucket
    # ------------------------------------------------------------------
    print_separator("6. Listando Todos os Arquivos no Bucket")
    all_files = manager.list_files()
    print(f"[*] Total de arquivos encontrados: {len(all_files)}")
    for key in all_files:
        print(f" - {key}")

    # ------------------------------------------------------------------
    # 7. Ciclo de Vida: Deleção de Questão
    # ------------------------------------------------------------------
    print_separator(f"7. Excluindo Arquivos da Questão #{question_id} (Deleção de Questão)")
    deleted_count = manager.delete_question_files(question_id)
    print(f"[✓] {deleted_count} arquivo(s) removido(s) do S3.")

    # Confirmação
    remaining = manager.list_files(prefix=f"questions/{question_id}")
    print(f"[*] Arquivos restantes para a questão #{question_id}: {len(remaining)}")
    assert len(remaining) == 0, "Deveriam existir 0 arquivos após a deleção."
    print("[✓] Exclusão confirmada no S3 com sucesso!")

    print_separator("8. Resumo Final")
    print("[✓] Todos os testes das operações com S3 foram concluídos com sucesso!\n")


if __name__ == "__main__":
    run_tests()
