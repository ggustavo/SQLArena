from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import Category

router = APIRouter(prefix="/categories", tags=["Categorias"])

class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)

@router.get("", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """Retorna todas as categorias pré-definidas em ordem alfabética estrita."""
    categories = db.query(Category).order_by(func.lower(Category.name).asc()).all()
    return categories
