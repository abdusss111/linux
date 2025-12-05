from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Table, UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from dapmeet.db.db import Base

# Таблица для списка участников каждой сессии
meeting_participants = Table(
    "meeting_participants",
    Base.metadata,
    Column("session_id", String, ForeignKey("meetings.unique_session_id", ondelete="CASCADE"), primary_key=True),
    Column("user_id",    String, ForeignKey("users.id",    ondelete="CASCADE"), primary_key=True),
    Column("joined_at",  DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("left_at",    DateTime(timezone=True), nullable=True),
)

class Meeting(Base):
    __tablename__ = "meetings"

    unique_session_id = Column(String, primary_key=True, index=True)
    meeting_id      = Column(String, nullable=False, index=True)
    user_id         = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title           = Column(String(255), nullable=True)
    subscription_plan = Column(String(20), nullable=True)  # Store subscription plan of user who started the meeting
    created_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user        = relationship("User", back_populates="meetings")
    participants = relationship(
        "User",
        secondary=meeting_participants,
        viewonly=True
    )
    chat_history = relationship(
        "ChatMessage", back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )
    segments     = relationship(
        "TranscriptSegment", back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="TranscriptSegment.timestamp, TranscriptSegment.version"
    )
