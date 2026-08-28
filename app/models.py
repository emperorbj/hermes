import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, func
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


class DocumentStatus(StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        default=DocumentStatus.PROCESSING,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
