from sqlalchemy import Column, String, Integer, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid
import enum

class GameDifficulty(str, enum.Enum):
    EASY = "easy"         # Obvious patterns, longer timeframe
    MEDIUM = "medium"     # Moderate patterns, standard timeframe
    HARD = "hard"         # Subtle patterns, shorter timeframe

class MarketDirection(str, enum.Enum):
    UP = "up"             # Price will go up
    DOWN = "down"         # Price will go down
    SIDEWAYS = "sideways" # Price will move sideways

class GameStatus(str, enum.Enum):
    CREATED = "created"   # Game session created
    ACTIVE = "active"     # Game in progress
    COMPLETED = "completed" # Game finished
    EXPIRED = "expired"   # Game time expired without submission

class GameSession(BaseModel):
    """Game session model representing a single game instance"""
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
    
    def __init__(
        self,
        user_id: str,
        symbol: str,
        asset_type: str,
        timeframe: int = 30,  # Data points to show
        prediction_window: int = 5,  # Future bars to predict
        difficulty: GameDifficulty = GameDifficulty.MEDIUM,
        session_id: Optional[str] = None
    ):
        super().__init__()
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id
        self.symbol = symbol
        self.asset_type = asset_type  # 'stock' or 'crypto'
        self.timeframe = timeframe
        self.prediction_window = prediction_window
        self.difficulty = difficulty
        self.status = GameStatus.CREATED
        
        # Initialize game session data
        self.instrument = symbol
        self.current_score = 0
        self.rounds_played = 0
        self.rounds_correct = 0
        
        # These are stored in session_data JSON column
        self.session_data = {
            "market_data_id": None,
            "market_data_snapshot": {},
            "hidden_data": {},
            "options": [],
            "selected_option": None,
            "correct_option": None,
            "result": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "asset_type": asset_type,
            "prediction_window": prediction_window,
            "difficulty_level": difficulty
        }
    
    @property
    def market_data_id(self) -> Optional[str]:
        return self.session_data.get("market_data_id")
    
    @property
    def market_data_snapshot(self) -> Dict[str, Any]:
        return self.session_data.get("market_data_snapshot", {})
    
    @property
    def hidden_data(self) -> Dict[str, Any]:
        return self.session_data.get("hidden_data", {})
    
    @property
    def options(self) -> List[Dict[str, Any]]:
        return self.session_data.get("options", [])
    
    @property
    def selected_option(self) -> Optional[int]:
        return self.session_data.get("selected_option")
    
    @property
    def correct_option(self) -> Optional[int]:
        return self.session_data.get("correct_option")
    
    @property
    def result(self) -> Optional[Dict[str, Any]]:
        return self.session_data.get("result")
    
    @property
    def score(self) -> int:
        return self.current_score
    
    @property
    def completed_at(self) -> Optional[datetime]:
        completed_str = self.session_data.get("completed_at")
        return datetime.fromisoformat(completed_str) if completed_str else None
    
    @property
    def created_at(self) -> datetime:
        created_str = self.session_data.get("created_at")
        return datetime.fromisoformat(created_str)
    
    @property
    def updated_at(self) -> datetime:
        updated_str = self.session_data.get("updated_at")
        return datetime.fromisoformat(updated_str)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for API responses"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "asset_type": self.asset_type,
            "timeframe": self.timeframe,
            "prediction_window": self.session_data.get("prediction_window", 5),
            "difficulty": self.session_data.get("difficulty_level", "medium"),
            "status": self.status,
            "options": self.options,
            "selected_option": self.selected_option,
            "score": self.score,
            "rounds_played": self.rounds_played,
            "rounds_correct": self.rounds_correct,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    def set_market_data(self, market_data_id: str, market_data: Dict[str, Any], hidden_data: Dict[str, Any]):
        """Set market data for the game session"""
        self.session_data["market_data_id"] = market_data_id
        self.session_data["market_data_snapshot"] = market_data
        self.session_data["hidden_data"] = hidden_data
        self.session_data["updated_at"] = datetime.utcnow().isoformat()
        self.status = GameStatus.ACTIVE
    
    def set_options(self, options: List[Dict[str, Any]], correct_option: int):
        """Set prediction options and correct answer"""
        self.session_data["options"] = options
        self.session_data["correct_option"] = correct_option
        self.session_data["updated_at"] = datetime.utcnow().isoformat()
    
    def submit_guess(self, selected_option: int) -> bool:
        """Submit player's guess and calculate score"""
        if self.status != GameStatus.ACTIVE:
            return False
        
        self.session_data["selected_option"] = selected_option
        self.status = GameStatus.COMPLETED
        now = datetime.utcnow()
        self.session_data["completed_at"] = now.isoformat()
        self.session_data["updated_at"] = now.isoformat()
        
        # Check if correct
        is_correct = selected_option == self.correct_option
        
        # Calculate score
        base_score = 100
        
        # Apply difficulty multiplier
        if self.session_data.get("difficulty_level") == GameDifficulty.EASY:
            difficulty_multiplier = 1.0
        elif self.session_data.get("difficulty_level") == GameDifficulty.MEDIUM:
            difficulty_multiplier = 1.5
        else:  # HARD
            difficulty_multiplier = 2.0
        
        round_score = int(base_score * difficulty_multiplier) if is_correct else 0
        
        # Update session stats
        self.current_score += round_score
        self.rounds_played += 1
        if is_correct:
            self.rounds_correct += 1
        
        # Set result
        self.session_data["result"] = {
            "correct": is_correct,
            "correct_option": self.correct_option,
            "selected_option": selected_option,
            "score": round_score,
            "hidden_data": self.hidden_data
        }
        
        return is_correct
    
    def calculate_accuracy(self):
        """Calculate accuracy as a percentage"""
        if self.rounds_played == 0:
            return 0
        return (self.rounds_correct / self.rounds_played) * 100
    
    def __repr__(self):
        return f"<GameSession {self.id} - User: {self.user_id}, Score: {self.current_score}>"