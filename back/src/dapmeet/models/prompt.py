from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from dapmeet.db.db import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True, unique=True)
    content = Column(Text, nullable=False)
    prompt_type = Column(String(50), nullable=False, default="user", index=True)  # "admin" or "user"
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # NULL for admin prompts
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="prompts")

    def __repr__(self):
        return f"<Prompt(id={self.id}, name='{self.name}', type='{self.prompt_type}')>"
