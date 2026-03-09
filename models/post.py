from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base
from models.tag import post_tags

class Post(Base):
    __tablename__ = "posts"

    id        = Column(Integer, primary_key=True, index=True)
    title     = Column(String(200), nullable=False)
    content   = Column(Text, nullable=False)
    published = Column(Boolean, default=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    author   = relationship("User", back_populates="posts")
    tags     = relationship("Tag", secondary=post_tags, back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")