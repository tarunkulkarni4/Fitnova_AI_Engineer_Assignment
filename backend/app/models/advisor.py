import uuid
import enum
from sqlalchemy import ForeignKey, String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.mixins import TimestampMixin

class AdvisorStatus(str, enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"

class Advisor(Base, TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("team.id", ondelete="CASCADE"),
        nullable=False
    )
    employee_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[AdvisorStatus] = mapped_column(
        Enum(AdvisorStatus, values_callable=lambda obj: [item.value for item in obj]),
        default=AdvisorStatus.ACTIVE,
        nullable=False
    )

    # Relationships
    team: Mapped["Team"] = relationship(
        "Team",
        back_populates="advisors"
    )
    calls: Mapped[list["Call"]] = relationship(
        "Call",
        back_populates="advisor",
        cascade="all, delete-orphan"
    )
