from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel

class User(BaseModel):
    """User model for storing user-related data"""
    __tablename__ = "users"

    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    score = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
    
    # Add relationship to game sessions
    sessions = relationship("GameSession", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username}>"