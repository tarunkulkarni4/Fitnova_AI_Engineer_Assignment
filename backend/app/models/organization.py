import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.mixins import TimestampMixin

class Organization(Base, TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    teams: Mapped[list["Team"]] = relationship(
        "Team",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
