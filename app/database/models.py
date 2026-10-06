from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Table, UniqueConstraint, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .session import Base

# Tabela Associativa N:N entre Question e Category
question_categories = Table(
    "question_categories",
    Base.metadata,
    Column("question_id", Integer, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="STUDENT")  # STUDENT, INSTRUCTOR
    score = Column(Integer, default=0)
    solved_count = Column(Integer, default=0)
    streak_days = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    solved_questions = relationship("UserSolvedQuestion", back_populates="user", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(60), unique=True, nullable=False, index=True)
    slug = Column(String(60), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    questions = relationship("Question", secondary=question_categories, back_populates="categories")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    difficulty = Column(String(20), nullable=False, default="Médio")  # Fácil, Médio, Difícil
    status = Column(String(20), nullable=False, default="PUBLISHED")  # DRAFT, READY, PUBLISHED
    description = Column(Text, nullable=True)
    schema_sql = Column(Text, nullable=True)
    sample_tables = Column(JSON, nullable=True)
    expected_columns = Column(JSON, nullable=True)
    created_by = Column(String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    categories = relationship("Category", secondary=question_categories, back_populates="questions")


class UserSolvedQuestion(Base):
    __tablename__ = "user_solved_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    solved_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_user_question_solved"),
    )

    user = relationship("User", back_populates="solved_questions")
    question = relationship("Question")
