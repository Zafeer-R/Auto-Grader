import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AnswerKey(Base):
    __tablename__ = "answer_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    questions: Mapped[dict] = mapped_column(JSONB)  # full answer key JSON
    total_points: Mapped[float] = mapped_column()
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
