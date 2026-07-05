import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, Text, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class AISummary(Base):
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
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    customer_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    objections: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    call: Mapped["Call"] = relationship(
        "Call",
        back_populates="summary"
    )
