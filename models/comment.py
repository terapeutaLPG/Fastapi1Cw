from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base

class Comment(Base):
    __tablename__ = "comments"

    id         = Column(Integer, primary_key=True, index=True)
    content    = Column(Text, nullable=False)
    author_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id    = Column(Integer, ForeignKey("posts.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    author = relationship("User")
    post   = relationship("Post", back_populates="comments")