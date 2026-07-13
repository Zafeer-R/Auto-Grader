import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assignment_id: Mapped[str] = mapped_column(String(255), index=True)
    answers: Mapped[dict] = mapped_column(JSONB, default=dict)
    total_score: Mapped[float | None] = mapped_column(default=None)
    max_score: Mapped[float | None] = mapped_column(default=None)
    grade_result: Mapped[dict | None] = mapped_column(JSONB, default=None)
    submitted_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    graded_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class SubmissionAnswer(Base):
    """Individual answer within a submission, for per-question tracking."""

    __tablename__ = "submission_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    question_id: Mapped[str] = mapped_column(String(100))
    student_answer: Mapped[str] = mapped_column(String(1000))
    score: Mapped[float | None] = mapped_column(default=None)
    max_score: Mapped[float] = mapped_column()
    feedback: Mapped[str] = mapped_column(String(500), default="")
