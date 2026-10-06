from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import Question, Category, User, UserSolvedQuestion
from app.api.deps import get_optional_current_user, require_instructor
from app.s3.s3_manager import S3Manager
from app.dynamodb.dynamo_manager import DynamoDBManager
from app.cache.redis_client import redis_client
from app.database.validator import QuestionValidator, QuestionValidationError

router = APIRouter(prefix="/questions", tags=["Questões"])

s3_manager = S3Manager()
dynamo_manager = DynamoDBManager()

class QuestionCreateRequest(BaseModel):
    title: str
    difficulty: str = "Médio"
    categories: List[str] = []
    category: Optional[str] = None
    description: str = ""
    schemaSql: str = ""
    dataSql: str = ""
    answerSql: str = ""
    sampleTables: Optional[List[Dict[str, Any]]] = None
    expectedColumns: Optional[List[str]] = None

@router.get("")
def list_questions(
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Retorna as questões. Alunos só veem PUBLISHED; instrutores veem tudo.
    Enriquece com status (SOLVED, UNSOLVED) baseado nas resoluções do usuário.
    Utiliza cache Redis para evitar leituras repetidas ao PostgreSQL RDS.
    """
    role = "INSTRUCTOR" if (user and user.role == "INSTRUCTOR") else "STUDENT"
    cached_base = redis_client.get_cached_questions(role)

    if cached_base is None:
        query = db.query(Question)
        if role == "STUDENT":
            query = query.filter(Question.status == "PUBLISHED")
        
        questions = query.order_by(Question.id.asc()).all()
        cached_base = []
        for q in questions:
            cats = sorted([c.name for c in q.categories], key=lambda x: x.lower())
            if not cats:
                cats = ["Filtragem"]

            cached_base.append({
                "id": q.id,
                "title": q.title,
                "difficulty": q.difficulty,
                "categories": cats,
                "category": cats[0] if cats else "Filtragem",
                "publishedStatus": q.status,
                "description": q.description or "",
                "schemaSql": q.schema_sql or "",
                "sampleTables": q.sample_tables or [],
                "expectedColumns": q.expected_columns or [],
                "expectedHash": q.expected_hash or "",
            })
        redis_client.set_cached_questions(role, cached_base, ttl=300)

    # Mapeamento dinâmico de resoluções do usuário autenticado
    solved_set = set()
    if user:
        solved_ids = db.query(UserSolvedQuestion.question_id).filter_by(user_id=user.id).all()
        solved_set = {sid[0] for sid in solved_ids}

    result = []
    for q in cached_base:
        item = dict(q)
        item["status"] = "SOLVED" if q["id"] in solved_set else "UNSOLVED"
        result.append(item)
    return result

@router.get("/{question_id}")
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retorna detalhes de uma questão pelo ID com cache Redis."""
    cached_q = redis_client.get_cached_question(question_id)
    if not cached_q:
        q = db.query(Question).filter(Question.id == question_id).first()
        if not q:
            raise HTTPException(status_code=404, detail="Questão não encontrada.")
        
        cats = sorted([c.name for c in q.categories], key=lambda x: x.lower())
        if not cats:
            cats = ["Filtragem"]

        cached_q = {
            "id": q.id,
            "title": q.title,
            "difficulty": q.difficulty,
            "categories": cats,
            "category": cats[0] if cats else "Filtragem",
            "publishedStatus": q.status,
            "description": q.description or "",
            "schemaSql": q.schema_sql or "",
            "sampleTables": q.sample_tables or [],
            "expectedColumns": q.expected_columns or [],
            "expectedHash": q.expected_hash or "",
        }
        redis_client.set_cached_question(question_id, cached_q, ttl=300)

    is_instructor = user and user.role == "INSTRUCTOR"
    if cached_q["publishedStatus"] != "PUBLISHED" and not is_instructor:
        raise HTTPException(status_code=403, detail="Questão ainda não publicada.")

    is_solved = False
    if user:
        is_solved = db.query(UserSolvedQuestion).filter_by(user_id=user.id, question_id=question_id).first() is not None

    res = dict(cached_q)
    res["status"] = "SOLVED" if is_solved else "UNSOLVED"
    return res

@router.post("", status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor)
):
    """
    Cria e valida dinamicamente uma nova questão (Instrutor):
    1. Registra no RDS para obter ID.
    2. Executa a sandbox de validação no PostgreSQL RDS (schema pergunta_{id}).
    3. Executa schema.sql, data.sql e answer.sql (exigindo ORDER BY).
    4. Extrai colunas esperadas e gera o hash canônico SHA-256.
    5. Persiste expected_hash no RDS e no Redis.
    6. Salva scripts no S3 e grava log de auditoria no DynamoDB.
    7. Invalida caches do Redis.
    """
    # 1. Cria registro preliminar no RDS
    new_q = Question(
        title=payload.title,
        difficulty=payload.difficulty or "Médio",
        status="PUBLISHED",
        description=payload.description or "",
        schema_sql=payload.schemaSql or "",
        sample_tables=payload.sampleTables or [],
        expected_columns=payload.expectedColumns or [],
        created_by=user.id
    )

    # Associa categorias
    cat_names = payload.categories or ([payload.category] if payload.category else ["Filtragem"])
    for c_name in cat_names:
        c = db.query(Category).filter(Category.name == c_name).first()
        if c:
            new_q.categories.append(c)

    db.add(new_q)
    db.flush()

    # 2. Executa Sandbox de Validação Real no RDS
    try:
        val_result = QuestionValidator.validate_and_setup_question(
            question_id=new_q.id,
            schema_sql=payload.schemaSql or "",
            data_sql=payload.dataSql or "",
            answer_sql=payload.answerSql or "",
        )
    except QuestionValidationError as qe:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(qe)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha na validação do ambiente SQL da questão: {e}"
        )

    # 3. Enriquece os dados com os resultados validados
    new_q.expected_hash = val_result["expected_hash"]
    new_q.expected_columns = val_result["expected_columns"]
    if not new_q.sample_tables:
        new_q.sample_tables = val_result["sample_tables"]

    db.commit()
    db.refresh(new_q)

    # 4. Atualiza o Hash no Redis e invalida caches de lista
    redis_client.set_answer_hash(new_q.id, new_q.expected_hash)
    redis_client.invalidate_questions_cache(new_q.id)

    # 5. Upload dos scripts no S3
    try:
        s3_manager.upload_question_sql_files(
            question_id=new_q.id,
            schema_sql=payload.schemaSql or "-- Sem schema\n",
            data_sql=payload.dataSql or "-- Sem dados\n",
            answer_sql=payload.answerSql
        )
    except Exception as e:
        logger.warning(f"Aviso ao salvar scripts no S3 para questão #{new_q.id}: {e}")

    # 6. Auditoria no DynamoDB
    try:
        dynamo_manager.log_crud_action(
            action_type="CREATE_EXERCISE",
            entity_id=f"exercise_{new_q.id}",
            user_id=user.id,
            details={"title": new_q.title, "difficulty": new_q.difficulty, "expected_hash": new_q.expected_hash}
        )
    except Exception:
        pass

    cats = sorted([c.name for c in new_q.categories], key=lambda x: x.lower())
    return {
        "id": new_q.id,
        "title": new_q.title,
        "difficulty": new_q.difficulty,
        "categories": cats,
        "category": cats[0] if cats else "Filtragem",
        "status": "UNSOLVED",
        "publishedStatus": new_q.status,
        "description": new_q.description,
        "schemaSql": new_q.schema_sql,
        "sampleTables": new_q.sample_tables,
        "expectedColumns": new_q.expected_columns,
        "expectedHash": new_q.expected_hash
    }

@router.delete("/{question_id}", status_code=status.HTTP_200_OK)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor)
):
    """Exclui atomicamente uma questão do RDS, do S3, limpa schema e invalida cache."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Questão não encontrada.")

    # Remove o schema sandbox no PostgreSQL
    QuestionValidator.drop_question_schema(question_id)

    # Invalida cache no Redis
    redis_client.invalidate_questions_cache(question_id)

    # Remove do S3
    try:
        s3_manager.delete_question_files(question_id)
    except Exception:
        pass

    # Remove do RDS
    db.delete(q)
    db.commit()

    # Log no DynamoDB
    try:
        dynamo_manager.log_crud_action(
            action_type="DELETE_EXERCISE",
            entity_id=f"exercise_{question_id}",
            user_id=user.id,
            details={"action": "deleted", "question_id": question_id}
        )
    except Exception:
        pass

    return {"message": f"Questão #{question_id} removida com sucesso."}

@router.post("/{question_id}/publish", status_code=status.HTTP_200_OK)
def publish_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor)
):
    """Publica uma questão mudando o status para PUBLISHED e invalidando o cache."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Questão não encontrada.")
    q.status = "PUBLISHED"
    db.commit()
    db.refresh(q)

    # Invalida cache Redis
    redis_client.invalidate_questions_cache(question_id)

    try:
        dynamo_manager.log_crud_action(
            action_type="PUBLISH_EXERCISE",
            entity_id=f"exercise_{question_id}",
            user_id=user.id,
            details={"title": q.title, "status": "PUBLISHED"}
        )
    except Exception:
        pass

    return {
        "id": q.id,
        "title": q.title,
        "status": q.status,
        "publishedStatus": q.status,
        "message": f"Questão #{question_id} publicada com sucesso."
    }
