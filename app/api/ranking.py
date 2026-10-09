from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.cache.redis_client import redis_client
from app.database.models import User
from app.database.session import get_db

router = APIRouter(prefix="/ranking", tags=["Ranking"])


class RankingEntry(BaseModel):
    position: int
    id: str
    name: str
    score: int
    solvedCount: int


@router.get("", response_model=list[RankingEntry])
def get_ranking(db: Session = Depends(get_db)):
    cached = redis_client.get_ranking()
    if cached is not None:
        return cached

    users = (
        db.query(User)
        .order_by(func.coalesce(User.score, 0).desc(), func.coalesce(User.solved_count, 0).desc(), User.name.asc(), User.id.asc())
        .limit(50)
        .all()
    )
    result = [
        {"position": position, "id": user.id, "name": user.name,
         "score": user.score or 0, "solvedCount": user.solved_count or 0}
        for position, user in enumerate(users, start=1)
    ]
    redis_client.set_ranking(result)
    return result
