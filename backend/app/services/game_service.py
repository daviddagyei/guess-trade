from typing import Dict, List, Any, Tuple
import random
import json

class GameService:
    """Service class for handling game logic"""
    
    def __init__(self):
        """Initialize GameService with default settings"""
        self.instruments = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        self.timeframes = ["1min", "5min", "15min", "30min", "60min", "daily"]
        
    def generate_session(self, difficulty: int = 1) -> Dict[str, Any]:
        """Generate a new game session with the given difficulty"""
        instrument = random.choice(self.instruments)
        timeframe = random.choice(self.timeframes)
        
        return {
            "instrument": instrument,
            "timeframe": timeframe,
            "difficulty": difficulty,
            "setup_candles": 50,
            "continuation_candles": 20
        }
    
    def generate_game_options(self, instrument: str, timeframe: str) -> Dict[str, Any]:
        """
        Placeholder method for generating game options
        In the real implementation, this would fetch data from Alpha Vantage
        """
        # Mock data for milestone 1
        return {
            "setup": {
                "instrument": instrument,
                "timeframe": timeframe,
                "data": [{"mock": "data"}]  # This would be actual OHLC data
            },
            "overlays": {
                "ema20": [{"mock": "data"}],
                "ema50": [{"mock": "data"}],
                "bollinger": [{"mock": "data"}]
            },
            "options": [
                {"id": 0, "data": [{"mock": "option1"}], "is_correct": True},
                {"id": 1, "data": [{"mock": "option2"}], "is_correct": False},
                {"id": 2, "data": [{"mock": "option3"}], "is_correct": False},
                {"id": 3, "data": [{"mock": "option4"}], "is_correct": False}
            ]
        }
    
    def check_answer(self, user_answer: int, game_options: Dict[str, Any]) -> bool:
        """Check if the user's answer is correct"""
        for option in game_options["options"]:
            if option["id"] == user_answer:
                return option["is_correct"]
        return False
    
    def calculate_score(self, 
                        is_correct: bool, 
                        difficulty: int, 
                        time_taken: float) -> int:
        """Calculate score based on correctness, difficulty and time taken"""
        if not is_correct:
            return 0
            
        base_score = 100 * difficulty
        time_bonus = max(0, int(50 - (time_taken * 5)))  # Faster answers get more points
        
        return base_score + time_bonus