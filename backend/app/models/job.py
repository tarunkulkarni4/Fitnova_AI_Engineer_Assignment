import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, Integer, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.call import ProcessingStatus

class ProcessingJob(Base):
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    call_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("call.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(
            ProcessingStatus,
            native_enum=False,
            length=50,
            values_callable=lambda obj: [item.value for item in obj]
        ),
        default=ProcessingStatus.QUEUED,
        nullable=False
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    call: Mapped["Call"] = relationship(
        "Call",
        back_populates="processing_job"
    )
