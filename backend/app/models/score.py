import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class CallScore(Base):
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
    rapport_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    needs_discovery_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    objection_handling_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_knowledge_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compliance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closing_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trial_booking_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    call: Mapped["Call"] = relationship(
        "Call",
        back_populates="score"
    )
