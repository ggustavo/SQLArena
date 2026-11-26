import argparse
import json
import logging
import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.database.session import Base, engine, SessionLocal
from app.database.models import User, Category, Question, question_categories, UserSolvedQuestion
from app.auth.security import get_password_hash
from app.minio.minio_manager import MinioManager
from app.dynamodb.dynamo_manager import DynamoDBManager
from app.kafka.kafka_manager import KafkaQueueManager
from app.cache.redis_client import redis_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DatabaseSeed")

from app.database.validator import QuestionValidator

PREDEFINED_CATEGORIES = [
    {"name": "Agrupamento", "slug": "agrupamento", "description": "GROUP BY, HAVING e funções de agregação (SUM, AVG, COUNT)"},
    {"name": "Condicional", "slug": "condicional", "description": "Expressões condicionais: CASE WHEN, COALESCE, NULLIF"},
    {"name": "Conjuntos", "slug": "conjuntos", "description": "Operações de conjunto: UNION, UNION ALL, INTERSECT, EXCEPT"},
    {"name": "CTEs", "slug": "ctes", "description": "Expressões de Tabela Comuns (WITH) e consultas recursivas (WITH RECURSIVE)"},
    {"name": "Datas", "slug": "datas", "description": "Manipulação de datas e tempos: DATE_TRUNC, EXTRACT, AGE, INTERVAL"},
    {"name": "Distintos", "slug": "distintos", "description": "Deduplicação de registros: DISTINCT e DISTINCT ON do PostgreSQL"},
    {"name": "Filtragem", "slug": "filtragem", "description": "Cláusulas WHERE, operadores IN, BETWEEN, LIKE, IS NULL"},
    {"name": "Funções", "slug": "funcoes", "description": "Funções escalares, matemáticas e utilitárias (ROUND, ABS, COALESCE)"},
    {"name": "Janelas", "slug": "janelas", "description": "Window Functions: OVER, PARTITION BY, ROW_NUMBER, RANK, LAG, LEAD"},
    {"name": "JOINs", "slug": "joins", "description": "Junções relacionais: INNER, LEFT, RIGHT, FULL OUTER e CROSS JOIN"},
    {"name": "Subconsultas", "slug": "subconsultas", "description": "Subqueries escalares, correlacionadas, EXISTS e NOT EXISTS"},
    {"name": "Texto", "slug": "texto", "description": "Manipulação de strings: UPPER, LOWER, TRIM, SPLIT_PART, CONCAT"},
]

def generate_data_sql(sample_tables: list) -> str:
    """Gera script DML (INSERT INTO) a partir da estrutura sampleTables."""
    if not sample_tables:
        return "-- Sem dados de carga inicial\n"
    
    statements = ["-- Carga de dados iniciais gerada automaticamente"]
    for table in sample_tables:
        table_name = table.get("name")
        cols = table.get("columns", [])
        rows = table.get("rows", [])
        if not table_name or not cols or not rows:
            continue
        
        cols_str = ", ".join(cols)
        values_list = []
        for row in rows:
            vals = []
            for col in cols:
                v = row.get(col)
                if v is None:
                    vals.append("NULL")
                elif isinstance(v, (int, float)):
                    vals.append(str(v))
                elif isinstance(v, bool):
                    vals.append("true" if v else "false")
                else:
                    escaped = str(v).replace("'", "''")
                    vals.append(f"'{escaped}'")
            values_list.append(f"({', '.join(vals)})")
        
        if values_list:
            stmt = f"INSERT INTO {table_name} ({cols_str}) VALUES\n  " + ",\n  ".join(values_list) + "\nON CONFLICT DO NOTHING;"
            statements.append(stmt)
            
    return "\n\n".join(statements) + "\n"

def seed_database(only_if_empty: bool = False, reset_all: bool = False):
    logger.info("Iniciando verificação e seed do banco PostgreSQL, MinIO, Kafka e DynamoDB...")
    
    # 1. Cria tabelas no PostgreSQL
    Base.metadata.create_all(bind=engine)
    logger.info("[✓] Tabelas do PostgreSQL verificadas/criadas.")

    # 2. Inicializa gerenciador MinIO
    minio_manager = MinioManager()
    minio_manager.ensure_bucket_exists()
    logger.info("[✓] Bucket MinIO verificado.")

    db: Session = SessionLocal()
    try:
        # Se only_if_empty=True (ex: boot de Pod no Kubernetes ou restart de container),
        # verifica se as questões já estão no Postgres para preservar 100% dos dados existentes
        if only_if_empty:
            existing_q_count = db.query(Question).count()
            if existing_q_count >= 21:
                logger.info(
                    f"[✓] Ambiente já inicializado ({existing_q_count} questões no Postgres). "
                    "Preservando dados e progresso existentes."
                )
                try:
                    DynamoDBManager().ensure_tables_exist()
                except Exception as e:
                    logger.warning(f"Aviso ao verificar tabelas DynamoDB: {e}")
                try:
                    KafkaQueueManager().ensure_queues_exist()
                except Exception as e:
                    logger.warning(f"Aviso ao verificar tópicos Kafka: {e}")
                return

        # Garante coluna expected_hash caso a tabela já existisse
        try:
            db.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS expected_hash VARCHAR(64);"))
            db.commit()
        except Exception:
            db.rollback()

        # 3. Categorias pré-definidas
        cat_map = {}
        for cat_data in PREDEFINED_CATEGORIES:
            existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
            if not existing:
                existing = Category(
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    description=cat_data["description"]
                )
                db.add(existing)
                db.flush()
            cat_map[existing.name] = existing
        db.commit()
        logger.info(f"[✓] {len(cat_map)} categorias cadastradas/verificadas.")

        # 4. Usuários Iniciais: cadastrados se não existirem; se já existirem, pontuações NUNCA são zeradas (a menos que reset_all=True)
        users_to_seed = [
            {
                "id": "user_101",
                "name": "Gustavo Moraes",
                "email": "gustavo@sqlarena.com",
                "password": "123456",
                "role": "STUDENT",
                "score": 0,
                "streak_days": 0,
                "solved_count": 0
            },
            {
                "id": "user_001",
                "name": "Admin",
                "email": "admin@sqlarena.com",
                "password": "123456",
                "role": "INSTRUCTOR",
                "score": 0,
                "streak_days": 0,
                "solved_count": 0
            }
        ]
        # Limpa possíveis usuários obsoletos com emails antigos
        db.query(User).filter(User.email.in_(["instrutor@sqlarena.com", "aluno@sqlarena.com"])).delete(synchronize_session=False)
        db.commit()

        for u_data in users_to_seed:
            user = db.query(User).filter((User.id == u_data["id"]) | (User.email == u_data["email"])).first()
            if not user:
                user = User(
                    id=u_data["id"],
                    name=u_data["name"],
                    email=u_data["email"],
                    password_hash=get_password_hash(u_data["password"]),
                    role=u_data["role"],
                    score=u_data["score"],
                    streak_days=u_data["streak_days"],
                    solved_count=u_data["solved_count"]
                )
                db.add(user)
            elif reset_all:
                user.id = u_data["id"]
                user.name = u_data["name"]
                user.email = u_data["email"]
                user.password_hash = get_password_hash(u_data["password"])
                user.role = u_data["role"]
                user.score = 0
                user.streak_days = 0
                user.solved_count = 0
        db.commit()
        logger.info("[✓] Usuários iniciais cadastrados/verificados com sucesso.")

        # Remove questões resolvidas APENAS se explicitamente solicitado via reset_all
        if reset_all:
            deleted_solved = db.query(UserSolvedQuestion).delete()
            db.commit()
            if deleted_solved:
                logger.info(f"[✓] Removidas {deleted_solved} resoluções mockadas de usuários (--reset-all).")

        # 5. Validação dinâmica e povoamento das 21 questões de initial_data.json
        json_path = Path(__file__).resolve().parent / "initial_data.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            questions_data = data.get("questions", [])

            for q_data in questions_data:
                q_id = q_data["id"]
                schema_sql = q_data.get("schemaSql", "-- Sem schema\n")
                data_sql = generate_data_sql(q_data.get("sampleTables", []))
                answer_sql = q_data.get("starterSql", "SELECT 1;")

                logger.info(f"Validando dinamicamente questão #{q_id}: '{q_data['title']}'...")
                val_res = QuestionValidator.validate_and_setup_question(
                    question_id=q_id,
                    schema_sql=schema_sql,
                    data_sql=data_sql,
                    answer_sql=answer_sql
                )

                q = db.query(Question).filter(Question.id == q_id).first()
                if not q:
                    q = Question(
                        id=q_id,
                        title=q_data["title"],
                        difficulty=q_data["difficulty"],
                        status=q_data.get("publishedStatus", "PUBLISHED"),
                        description=q_data.get("description", ""),
                        schema_sql=schema_sql,
                        sample_tables=q_data.get("sampleTables") or val_res["sample_tables"],
                        expected_columns=val_res["expected_columns"],
                        expected_hash=val_res["expected_hash"],
                        created_by="user_001"
                    )
                    cats = q_data.get("categories", [q_data.get("category", "Filtragem")])
                    for c_name in cats:
                        if c_name in cat_map:
                            q.categories.append(cat_map[c_name])
                    db.add(q)
                else:
                    q.title = q_data["title"]
                    q.difficulty = q_data["difficulty"]
                    q.description = q_data.get("description", "")
                    q.schema_sql = schema_sql
                    q.expected_columns = val_res["expected_columns"]
                    q.expected_hash = val_res["expected_hash"]
                    if not q.sample_tables:
                        q.sample_tables = q_data.get("sampleTables") or val_res["sample_tables"]

                db.commit()

                # Salva o Hash no Redis
                redis_client.set_answer_hash(q_id, val_res["expected_hash"])

                # Upload dos scripts SQL para o MinIO
                minio_manager.upload_question_sql_files(
                    question_id=q_id,
                    schema_sql=schema_sql,
                    data_sql=data_sql,
                    answer_sql=answer_sql
                )

            logger.info(f"[✓] Todas as {len(questions_data)} questões foram validadas, geraram hash no Postgres/Redis e subiram para o MinIO.")

        # 6. Invalida caches do Redis para garantir frescor
        redis_client.invalidate_questions_cache()
        logger.info("[✓] Cache Redis de questões invalidado.")

        # 7. Sincroniza a sequence questions_id_seq com o maior id
        try:
            db.execute(text("SELECT setval('questions_id_seq', COALESCE((SELECT MAX(id) FROM questions), 1));"))
            db.commit()
            logger.info("[✓] Sequência questions_id_seq sincronizada com sucesso.")
        except Exception as e:
            logger.warning(f"Não foi possível sincronizar sequence questions_id_seq: {e}")

        # 8. Garante tabelas do DynamoDB prontas (expurgo de dados APENAS se reset_all=True)
        try:
            dynamo = DynamoDBManager()
            dynamo.ensure_tables_exist()
            if reset_all:
                with dynamo.table.batch_writer() as batch:
                    scan = dynamo.table.scan(ProjectionExpression="submission_id")
                    for item in scan.get("Items", []):
                        batch.delete_item(Key={"submission_id": item["submission_id"]})
                with dynamo.crud_table.batch_writer() as batch:
                    scan = dynamo.crud_table.scan(ProjectionExpression="action_id")
                    for item in scan.get("Items", []):
                        batch.delete_item(Key={"action_id": item["action_id"]})
                logger.info("[✓] Tabelas DynamoDB expurgadas com sucesso (--reset-all ativo).")
            else:
                logger.info("[✓] Tabelas DynamoDB verificadas com sucesso.")
        except Exception as e:
            logger.warning(f"Aviso ao inicializar/limpar DynamoDB no seed: {e}")

        # 9. Garante tópicos Kafka prontos
        try:
            kafka = KafkaQueueManager()
            kafka.ensure_queues_exist()
            logger.info("[✓] Tópicos Kafka verificados/criados com sucesso.")
        except Exception as e:
            logger.warning(f"Aviso ao inicializar Kafka no seed: {e}")

    except Exception as e:
        db.rollback()
        logger.error(f"Erro durante o seed: {e}")
        raise
    finally:
        db.close()

    logger.info("============================================================")
    logger.info("SEED DO POSTGRESQL, MINIO, KAFKA E DYNAMODB CONCLUÍDO!")
    logger.info("============================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed do banco de dados SQLArena")
    parser.add_argument(
        "--if-empty",
        action="store_true",
        help="Executa o seed completo apenas se o banco ainda estiver vazio"
    )
    parser.add_argument(
        "--reset-all",
        action="store_true",
        help="Limpa e zera pontuações de usuários e tabelas do DynamoDB (somente para testes locais)"
    )
    args = parser.parse_args()
    seed_database(only_if_empty=args.if_empty, reset_all=args.reset_all)
