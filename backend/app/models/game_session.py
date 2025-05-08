from sqlalchemy import Column, String, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class GameSession(BaseModel):
    """Game session model for storing session-related data"""
    __tablename__ = "game_sessions"
    
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="sessions")
    instrument = Column(String)  # e.g., "AAPL"
    timeframe = Column(String)   # e.g., "5min"
    difficulty = Column(Integer, default=1)
    current_score = Column(Integer, default=0)
    rounds_played = Column(Integer, default=0)
    rounds_correct = Column(Integer, default=0)
    session_data = Column(JSON, default={})
    
    def __repr__(self):
        return f"<GameSession {self.id} - User: {self.user_id}, Score: {self.current_score}>"
        
    def calculate_accuracy(self):
        """Calculate accuracy as a percentage"""
        if self.rounds_played == 0:
            return 0
        return (self.rounds_correct / self.rounds_played) * 100