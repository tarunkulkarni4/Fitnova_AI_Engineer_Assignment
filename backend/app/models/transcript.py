import uuid
from sqlalchemy import ForeignKey, String, Text, Float, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class Transcript(Base):
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
    speaker: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Relationships
    call: Mapped["Call"] = relationship(
        "Call",
        back_populates="transcript"
    )
