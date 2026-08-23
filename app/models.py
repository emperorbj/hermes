import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Role(StrEnum):
    ADMIN = "admin"
    STAFF = "staff"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.STAFF)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
