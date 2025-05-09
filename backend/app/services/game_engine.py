from typing import Dict, Any, List
import time
from datetime import datetime, timedelta

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
            "time_taken": None,
            "lives": 3,                         # New: Player has 3 lives
            "streak": 0,                        # New: Track consecutive correct answers
            "session_end_time": (datetime.now() + timedelta(minutes=5)).isoformat(),  # New: 5-minute session
            "countdown": 20,                    # New: 20-second countdown per round
            "round": 1                          # New: Track the current round number
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
        
        # Update streak and calculate score with bonus
        if is_correct:
            game_state["streak"] += 1
            # Apply streak bonus (25 points per correct answer + streak bonus)
            streak_bonus = min(game_state["streak"] - 1, 5) * 5  # Cap bonus at +25 for streak of 6+
            score = self.service.calculate_score(
                is_correct, 
                game_state["difficulty"], 
                time_taken
            ) + streak_bonus
        else:
            game_state["streak"] = 0
            game_state["lives"] -= 1
            score = 0
        
        game_state["score"] += score  # Add to cumulative score
        
        # Check if game should end (out of lives or session time expired)
        current_time = datetime.now()
        session_end_time = datetime.fromisoformat(game_state["session_end_time"])
        
        if game_state["lives"] <= 0 or current_time > session_end_time:
            game_state["status"] = "completed"
        else:
            # Continue to next round if still active
            game_state["round"] += 1
            game_state["status"] = "next_round"
        
        # Return result to the user
        result = {
            "session_id": session_id,
            "is_correct": is_correct,
            "score": game_state["score"],
            "round_score": score,
            "time_taken": time_taken,
            "correct_option": self._find_correct_option(options),
            "lives": game_state["lives"],
            "streak": game_state["streak"],
            "status": game_state["status"],
            "round": game_state["round"]
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
    
    async def next_round(self, session_id: str) -> Dict[str, Any]:
        """
        Generate the next round of the game
        
        Args:
            session_id: Unique identifier for the game session
            
        Returns:
            Dict containing the next game round setup data
        """
        if session_id not in self.active_games:
            return {"error": "Game session not found"}
            
        game_state = self.active_games[session_id]
        
        if game_state["status"] == "completed":
            return {"error": "Game already completed"}
            
        # Generate new game options with possibly different instrument
        session = self.service.generate_session(game_state["difficulty"])
        
        # Generate game options with the selected parameters
        options_data = await self.service.generate_game_options(
            session["asset_type"],
            session["instrument"], 
            session["timeframe"],
            game_state["difficulty"]
        )
        
        # Update game state for the new round
        game_state["asset_type"] = session["asset_type"]
        game_state["instrument"] = session["instrument"]
        game_state["timeframe"] = session["timeframe"]
        game_state["setup"] = options_data["setup"]
        game_state["overlays"] = options_data.get("overlays", {})
        game_state["options"] = options_data["options"]
        game_state["start_time"] = datetime.now().isoformat()
        game_state["status"] = "active"
        game_state["user_answer"] = None
        game_state["is_correct"] = None
        game_state["time_taken"] = None
        
        # Store the updated game state
        self.active_games[session_id] = game_state
        
        # Return game data for the new round
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
    
    def _find_correct_option(self, options: List[Dict]) -> int:
        """Find the ID of the correct option in the options list"""
        for option in options:
            if option.get("is_correct", False):
                return option["id"]
        return -1  # No correct option found (should never happen)