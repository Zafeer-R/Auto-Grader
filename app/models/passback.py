import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GradePassback(Base):
    """AGS passback state for a submission (one row per submission, upserted).

    status: pending (intent recorded), posted, dry_run, failed.
    Failed posts keep last_error for the TA dashboard — never silently dropped.
    """

    __tablename__ = "grade_passbacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), unique=True, index=True
    )
    lineitem_url: Mapped[str] = mapped_column(String(1000), default="")
    lti_user_id: Mapped[str] = mapped_column(String(255), default="")
    score_given: Mapped[float] = mapped_column(default=0.0)
    score_maximum: Mapped[float] = mapped_column(default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str] = mapped_column(String(500), default="")
    posted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
