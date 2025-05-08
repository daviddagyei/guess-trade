from sqlalchemy import Column, String, Integer, Boolean
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
    
    def __repr__(self):
        return f"<User {self.username}>"