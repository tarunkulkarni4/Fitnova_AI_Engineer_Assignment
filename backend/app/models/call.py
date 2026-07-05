import uuid
import enum
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, Integer, DateTime, Enum, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.mixins import TimestampMixin

class ProcessingStatus(str, enum.Enum):
    UPLOADED = "Uploaded"
    QUEUED = "Queued"
    PROCESSING = "Processing"
    READY_FOR_TRANSCRIPTION = "Ready For Transcription"
    READY_FOR_DIARIZATION = "Ready For Diarization"
    READY_FOR_TRANSCRIPT_MERGE = "Ready For Transcript Merge"
    READY_FOR_PII_REDACTION = "Ready For PII Redaction"
    READY_FOR_AI_ANALYSIS = "Ready For AI Analysis"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"

class Call(Base, TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    advisor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("advisor.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audio_file: Mapped[str] = mapped_column(Text, nullable=False)
    processed_audio_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    upload_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(
            ProcessingStatus,
            native_enum=False,
            length=50,
            values_callable=lambda obj: [item.value for item in obj]
        ),
        default=ProcessingStatus.UPLOADED,
        nullable=False,
        index=True
    )
    call_type: Mapped[str] = mapped_column(String(50), default="SALES_CALL", server_default="SALES_CALL", nullable=False)
    is_sales_call: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)
    non_sales_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    advisor: Mapped["Advisor"] = relationship(
        "Advisor",
        back_populates="calls"
    )
    transcript: Mapped[list["Transcript"]] = relationship(
        "Transcript",
        back_populates="call",
        cascade="all, delete-orphan"
    )
    score: Mapped["CallScore | None"] = relationship(
        "CallScore",
        back_populates="call",
        uselist=False,
        cascade="all, delete-orphan"
    )
    summary: Mapped["AISummary | None"] = relationship(
        "AISummary",
        back_populates="call",
        uselist=False,
        cascade="all, delete-orphan"
    )
    issue_tags: Mapped[list["IssueTag"]] = relationship(
        "IssueTag",
        back_populates="call",
        cascade="all, delete-orphan"
    )
    feedback: Mapped[list["Feedback"]] = relationship(
        "Feedback",
        back_populates="call",
        cascade="all, delete-orphan"
    )
    processing_job: Mapped["ProcessingJob | None"] = relationship(
        "ProcessingJob",
        back_populates="call",
        uselist=False,
        cascade="all, delete-orphan"
    )
