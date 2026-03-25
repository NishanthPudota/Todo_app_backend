import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Boolean, ForeignKey, Index, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

Base = declarative_base()

# IST = UTC + 5:30
IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    """Return the current datetime in Indian Standard Time (UTC+5:30)."""
    return datetime.now(IST)


class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(225), unique=True, nullable=False, index=True)
    passwordhash = Column(String(255), nullable=False)

    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(225), nullable=False)
    description = Column(String(500))
    priority = Column(String(10), nullable=False, default='P3')

    # Stored in IST at creation time
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=now_ist,
    )

    # Only the originally estimated duration is stored.
    # remaining_minutes is NOT stored — it is computed dynamically from:
    #   remaining = estimated_minutes - minutes_elapsed_since_creation
    estimated_minutes = Column(Integer, nullable=True)

    # Status flags
    is_done = Column(Boolean, nullable=False, default=False)
    is_deleted = Column(Boolean, nullable=False, default=False)

    # Ownership
    created_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    owner = relationship('User', back_populates='tasks')


Index('idx_users_name', User.name)
Index('idx_tasks_created_by', Task.created_by_id)
