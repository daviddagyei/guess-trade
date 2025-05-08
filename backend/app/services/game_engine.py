from typing import Dict, Any, List
import time
from datetime import datetime

from .game_service import GameService

class GameEngine:
    """Engine to orchestrate the core game loop: seed → options → guess → score"""
    
    def __init__(self):
        self.service = GameService()
        self.active_games = {}  # Store active game sessions by session_id
    
    async def seed_game(self, session_id: str, difficulty: int = 1) -> Dict[str, Any]:
        """
        Start a new game session: generate session parameters and game options
        
        Args:
            session_id: Unique identifier for the game session
            difficulty: Game difficulty level (1-5)
            
        Returns:
            Dict containing the game setup data
        """
        # Generate basic session parameters
        session = self.service.generate_session(difficulty)
        
        # Generate game options with the selected parameters
        options_data = await self.service.generate_game_options(
            session["asset_type"],
            session["instrument"], 
            session["timeframe"],
            difficulty
        )
        
        # Create full game state
        game_state = {
            "session_id": session_id,
            "asset_type": session["asset_type"],
            "instrument": session["instrument"],
            "timeframe": session["timeframe"],
            "difficulty": session["difficulty"],
            "setup": options_data["setup"],
            "overlays": options_data.get("overlays", {}),
            "options": options_data["options"],
            "start_time": datetime.now().isoformat(),
            "status": "active",
            "user_answer": None,
            "is_correct": None,
            "score": 0,
            "time_taken": None
        }
        
        # Store the active game
        self.active_games[session_id] = game_state
        
        # Return game data to display to the user (without answers)
        return self._prepare_game_response(game_state)
    
    def submit_guess(self, session_id: str, user_answer: int) -> Dict[str, Any]:
        """
        Process a user's guess and calculate score
        
        Args:
            session_id: The game session identifier
            user_answer: The user's selected answer (option id)
            
        Returns:
            Dict with result information including correctness and score
        """
        if session_id not in self.active_games:
            return {"error": "Game session not found"}
        
        game_state = self.active_games[session_id]
        
        # Ensure this game is still active
        if game_state["status"] != "active":
            return {"error": "Game already completed"}
            
        # Record the user's answer
        game_state["user_answer"] = user_answer
        
        # Calculate time taken
        start_time = datetime.fromisoformat(game_state["start_time"])
        end_time = datetime.now()
        time_taken = (end_time - start_time).total_seconds()
        game_state["time_taken"] = time_taken
        
        # Check if the answer is correct
        options = game_state["options"]
        is_correct = self.service.check_answer(user_answer, {"options": options})
        game_state["is_correct"] = is_correct
        
        # Calculate score
        score = self.service.calculate_score(
            is_correct, 
            game_state["difficulty"], 
            time_taken
        )
        game_state["score"] = score
        
        # Update game status
        game_state["status"] = "completed"
        
        # Return result to the user
        result = {
            "session_id": session_id,
            "is_correct": is_correct,
            "score": score,
            "time_taken": time_taken,
            "correct_option": self._find_correct_option(options)
        }
        
        return result
    
    def get_game_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get the current state of a game session
        
        Args:
            session_id: The game session identifier
            
        Returns:
            Dict with the current game state (safe for client)
        """
        if session_id not in self.active_games:
            return {"error": "Game session not found"}
            
        game_state = self.active_games[session_id]
        return self._prepare_game_response(game_state)
    
    def _prepare_game_response(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare a game state response that's safe to send to the client
        (removes solution information)
        """
        # Make a copy of the game state to avoid modifying the original
        response = game_state.copy()
        
        # If game is active, hide which option is correct
        if response["status"] == "active":
            # Deep copy the options to prevent modifying the original
            safe_options = []
            for option in response["options"]:
                # Create a copy without the is_correct field
                safe_option = {
                    "id": option["id"],
                    "data": option["data"]
                }
                safe_options.append(safe_option)
            response["options"] = safe_options
            
        return response
    
    def _find_correct_option(self, options: List[Dict[str, Any]]) -> int:
        """Find the ID of the correct option"""
        for option in options:
            if option.get("is_correct", False):
                return option["id"]
        return None