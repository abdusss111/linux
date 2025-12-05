# src/dapmeet/models/meeting_participants.py

from sqlalchemy import Table, Column, String, DateTime, ForeignKey
from sqlalchemy.orm import registry
from sqlalchemy.sql import func
from dapmeet.db.db import Base

meeting_participants = Table(
    "meeting_participants",
    Base.metadata,
    Column("meeting_id", String, ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id",    String, ForeignKey("users.id",    ondelete="CASCADE"), primary_key=True),
    Column("joined_at",  DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("left_at",    DateTime(timezone=True), nullable=True),
)
