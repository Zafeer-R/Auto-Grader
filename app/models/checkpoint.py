import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

CHECKPOINT_STATE_UNIQUE_CONSTRAINT = "uq_checkpoint_states_submission_checkpoint"


class CheckpointState(Base):
    __tablename__ = "checkpoint_states"
    __table_args__ = (
        UniqueConstraint(
            "submission_id",
            "checkpoint_id",
            name=CHECKPOINT_STATE_UNIQUE_CONSTRAINT,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    checkpoint_id: Mapped[str] = mapped_column(String(100))
    verified: Mapped[bool] = mapped_column(default=False)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    verified_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    points: Mapped[float] = mapped_column(default=0.0)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
