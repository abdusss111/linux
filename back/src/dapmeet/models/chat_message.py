from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from dapmeet.db.db import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("meetings.unique_session_id", ondelete="CASCADE"), nullable=False, index=True)
    sender     = Column(String(50), nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    meeting    = relationship("Meeting", back_populates="chat_history")
