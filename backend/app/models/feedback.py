import uuid
import enum
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class FeedbackType(str, enum.Enum):
    SCORE = "Score"
    TAG = "Tag"
    SUMMARY = "Summary"
    TRANSCRIPT = "Transcript"

class Feedback(Base):
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    call_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("call.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    reviewer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    feedback_type: Mapped[FeedbackType] = mapped_column(
        Enum(
            FeedbackType,
            native_enum=False,
            length=50,
            values_callable=lambda obj: [item.value for item in obj]
        ),
        nullable=False
    )
    original_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    call: Mapped["Call"] = relationship(
        "Call",
        back_populates="feedback"
    )
