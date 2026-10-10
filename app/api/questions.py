import json
import logging
from typing import List, Optional, Any, Dict, Literal
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import Question, Category, User, UserSolvedQuestion
from app.api.deps import get_optional_current_user, require_instructor
from app.s3.s3_manager import S3Manager
from app.dynamodb.dynamo_manager import DynamoDBManager
from app.cache.redis_client import redis_client
from app.database.validator import QuestionValidator, QuestionValidationError

router = APIRouter(prefix="/questions", tags=["Questões"])
logger = logging.getLogger(__name__)

s3_manager = S3Manager()
dynamo_manager = DynamoDBManager()

class QuestionCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    difficulty: Literal["Fácil", "Médio", "Difícil"] = "Médio"
    categories: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    description: str = ""
    schemaSql: str = ""
    dataSql: str = ""
    answerSql: str = ""
    sampleTables: Optional[List[Dict[str, Any]]] = None
    expectedColumns: Optional[List[str]] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        if not value.strip():
            raise ValueError("O título não pode estar vazio.")
        return value.strip()

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

async def _read_sql_file_or_text(
    file: Optional[UploadFile],
    text: Optional[str],
    field_name: str
) -> str:
    """Extrai conteúdo SQL a partir de um arquivo .sql enviado ou de um campo de texto."""
    if file and file.filename:
        filename_lower = file.filename.lower()
        if not filename_lower.endswith(".sql"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Arquivo '{file.filename}' inválido para {field_name}. Apenas arquivos com extensão .sql são permitidos."
            )
        content_bytes = await file.read()
        if len(content_bytes) > 2 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Arquivo '{file.filename}' excede o tamanho máximo de 2 MB."
            )
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return content_bytes.decode("latin-1")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Não foi possível decodificar o arquivo '{file.filename}'. O arquivo deve ser um script SQL codificado em UTF-8."
                )
    return (text or "").strip()


def _perform_create_question(
    title: str,
    difficulty: str,
    categories: List[str],
    category: Optional[str],
    description: str,
    schema_sql: str,
    data_sql: str,
    answer_sql: str,
    sample_tables: Optional[List[Dict[str, Any]]],
    expected_columns: Optional[List[str]],
    db: Session,
    user: User
) -> Dict[str, Any]:
    """Lógica centralizada de criação, validação em sandbox RDS, armazenamento em S3 e auditoria."""
    # 1. Cria registro preliminar no RDS
    new_q = Question(
        title=title,
        difficulty=difficulty or "Médio",
        status="READY",
        description=description or "",
        schema_sql=schema_sql or "",
        sample_tables=sample_tables or [],
        expected_columns=expected_columns or [],
        created_by=user.id
    )

    # Associa categorias
    cat_names = categories or ([category] if category else ["Filtragem"])
    for c_name in dict.fromkeys(cat_names):
        c = db.query(Category).filter(Category.name == c_name).first()
        if not c:
            raise HTTPException(status_code=400, detail=f"Categoria desconhecida: {c_name}")
        new_q.categories.append(c)

    db.add(new_q)
    db.flush()

    # 2. Executa Sandbox de Validação Real no RDS
    try:
        val_result = QuestionValidator.validate_and_setup_question(
            question_id=new_q.id,
            schema_sql=schema_sql or "",
            data_sql=data_sql or "",
            answer_sql=answer_sql or "",
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
    new_q.sample_tables = val_result["sample_tables"]

    # 4. Salva scripts no S3
    question_id = new_q.id
    try:
        s3_manager.upload_question_sql_files(
            question_id=question_id,
            schema_sql=schema_sql or "-- Sem schema\n",
            data_sql=data_sql or "-- Sem dados\n",
            answer_sql=answer_sql
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Falha ao persistir questão #%s", question_id)
        for cleanup in (s3_manager.delete_question_files, QuestionValidator.drop_question_schema):
            try:
                cleanup(question_id)
            except Exception:
                logger.exception("Falha na limpeza da questão #%s", question_id)
        raise HTTPException(status_code=503, detail="Não foi possível salvar a questão. Tente novamente.")

    # 5. Atualiza Caches do Redis
    db.refresh(new_q)
    redis_client.invalidate_questions_cache(new_q.id)
    redis_client.set_answer_hash(new_q.id, new_q.expected_hash)

    # 6. Auditoria no DynamoDB
    try:
        dynamo_manager.log_crud_action(
            action_type="CREATE_EXERCISE",
            entity_id=f"exercise_{new_q.id}",
            user_id=user.id,
            details={"title": new_q.title, "difficulty": new_q.difficulty, "expected_hash": new_q.expected_hash}
        )
    except Exception:
        logger.exception("Falha na auditoria CREATE_EXERCISE #%s", new_q.id)

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


@router.post("", status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor)
):
    """
    Cria e valida dinamicamente uma nova questão com dados em JSON (Instrutor).
    """
    return _perform_create_question(
        title=payload.title,
        difficulty=payload.difficulty or "Médio",
        categories=payload.categories,
        category=payload.category,
        description=payload.description or "",
        schema_sql=payload.schemaSql or "",
        data_sql=payload.dataSql or "",
        answer_sql=payload.answerSql or "",
        sample_tables=payload.sampleTables,
        expected_columns=payload.expectedColumns,
        db=db,
        user=user
    )


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def create_question_upload(
    title: str = Form(...),
    difficulty: str = Form("Médio"),
    categories: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    description: str = Form(""),
    schema_file: Optional[UploadFile] = File(None),
    schema_sql: Optional[str] = Form(None),
    data_file: Optional[UploadFile] = File(None),
    data_sql: Optional[str] = Form(None),
    answer_file: Optional[UploadFile] = File(None),
    answer_sql: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor)
):
    """
    Cria e valida uma nova questão permitindo envio direto de arquivos .sql ou texto digitado (multipart/form-data).
    """
    title_clean = title.strip()
    if not title_clean:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O título não pode estar vazio.")
    if len(title_clean) > 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O título deve ter no máximo 200 caracteres.")
    if difficulty not in ("Fácil", "Médio", "Difícil"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dificuldade inválida. Escolha entre Fácil, Médio ou Difícil.")

    # Resolve o conteúdo SQL a partir dos arquivos enviados ou campos de texto
    resolved_schema = await _read_sql_file_or_text(schema_file, schema_sql, "schema.sql")
    resolved_data = await _read_sql_file_or_text(data_file, data_sql, "data.sql")
    resolved_answer = await _read_sql_file_or_text(answer_file, answer_sql, "answer.sql")

    # Extrai lista de categorias
    parsed_cats: List[str] = []
    if categories:
        raw = categories.strip()
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed_cats = json.loads(raw)
            except Exception:
                parsed_cats = [c.strip().strip('"').strip("'") for c in raw[1:-1].split(",") if c.strip()]
        else:
            parsed_cats = [c.strip() for c in raw.split(",") if c.strip()]
    elif category:
        parsed_cats = [category.strip()]

    return _perform_create_question(
        title=title_clean,
        difficulty=difficulty,
        categories=parsed_cats,
        category=category,
        description=description or "",
        schema_sql=resolved_schema,
        data_sql=resolved_data,
        answer_sql=resolved_answer,
        sample_tables=None,
        expected_columns=None,
        db=db,
        user=user
    )

@router.delete("/{question_id}", status_code=status.HTTP_200_OK)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor)
):
    """Exclui recursos; DELETING permite retomar uma limpeza parcial."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Questão não encontrada.")

    q.status = "DELETING"
    db.commit()
    redis_client.invalidate_questions_cache(question_id)
    try:
        s3_manager.delete_question_files(question_id)
        QuestionValidator.drop_question_schema(question_id)
        db.query(UserSolvedQuestion).filter_by(question_id=question_id).delete(synchronize_session=False)
        db.delete(q)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Falha ao excluir questão #%s", question_id)
        raise HTTPException(status_code=503, detail="Exclusão pendente. Tente excluir novamente para concluir a limpeza.")
    redis_client.invalidate_questions_cache(question_id)

    # Log no DynamoDB
    try:
        dynamo_manager.log_crud_action(
            action_type="DELETE_EXERCISE",
            entity_id=f"exercise_{question_id}",
            user_id=user.id,
            details={"action": "deleted", "question_id": question_id}
        )
    except Exception:
        logger.exception("Falha na auditoria DELETE_EXERCISE #%s", question_id)

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
    if q.status == "PUBLISHED":
        return {"id": q.id, "publishedStatus": q.status, "status": q.status}
    if q.status != "READY" or not q.expected_hash:
        raise HTTPException(status_code=409, detail="Somente questões validadas e prontas podem ser publicadas.")
    q.status = "PUBLISHED"
    db.commit()
    db.refresh(q)

    # Invalida cache Redis
    redis_client.invalidate_questions_cache(question_id)
    redis_client.set_answer_hash(question_id, q.expected_hash)

    try:
        dynamo_manager.log_crud_action(
            action_type="PUBLISH_EXERCISE",
            entity_id=f"exercise_{question_id}",
            user_id=user.id,
            details={"title": q.title, "status": "PUBLISHED"}
        )
    except Exception:
        logger.exception("Falha na auditoria PUBLISH_EXERCISE #%s", question_id)

    return {
        "id": q.id,
        "title": q.title,
        "status": q.status,
        "publishedStatus": q.status,
        "message": f"Questão #{question_id} publicada com sucesso."
    }
