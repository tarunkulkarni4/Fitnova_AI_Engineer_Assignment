import uuid
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.mixins import TimestampMixin

class Team(Base, TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="teams"
    )
    advisors: Mapped[list["Advisor"]] = relationship(
        "Advisor",
        back_populates="team",
        cascade="all, delete-orphan"
    )
