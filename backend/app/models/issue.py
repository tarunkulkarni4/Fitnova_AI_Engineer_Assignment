import uuid
import enum
from sqlalchemy import ForeignKey, String, Text, Float, Numeric, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class IssueSeverity(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class IssueTag(Base):
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
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[IssueSeverity] = mapped_column(
        Enum(
            IssueSeverity,
            native_enum=False,
            length=20,
            values_callable=lambda obj: [item.value for item in obj]
        ),
        nullable=False,
        index=True
    )
    timestamp: Mapped[float | None] = mapped_column(Float, nullable=True)
    speaker: Mapped[str | None] = mapped_column(String(30), nullable=True)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Relationships
    call: Mapped["Call"] = relationship(
        "Call",
        back_populates="issue_tags"
    )
