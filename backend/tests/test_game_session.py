"""
Tests for the GameSession model
"""
import sys
import os
import unittest
from datetime import datetime, timedelta
import pytest
from typing import Dict, Any

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the model to test
from app.models.game_session import GameSession, GameDifficulty, GameStatus, MarketDirection

class TestGameSession:
    """Test cases for the GameSession model"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create a test game session
        self.session = GameSession(
            user_id="test_user",
            symbol="AAPL",
            asset_type="stock",
            timeframe=30,
            prediction_window=5,
            difficulty=GameDifficulty.MEDIUM
        )
        
        # Create test market data
        self.market_data = {
            "dates": ["2023-01-01", "2023-01-02", "2023-01-03"],
            "open": [100.0, 102.0, 103.0],
            "high": [105.0, 107.0, 108.0],
            "low": [98.0, 100.0, 101.0],
            "close": [103.0, 105.0, 106.0],
            "volume": [1000, 1200, 1100]
        }
        
        # Create test hidden data
        self.hidden_data = {
            "dates": ["2023-01-04", "2023-01-05"],
            "open": [106.0, 108.0],
            "high": [110.0, 112.0],
            "low": [104.0, 105.0],
            "close": [109.0, 110.0],
            "volume": [1300, 1400]
        }
        
        # Create test options
        self.options = [
            {
                "direction": MarketDirection.UP,
                "description": "Price will increase by approximately 3.00%",
                "predicted_price": 109.18
            },
            {
                "direction": MarketDirection.DOWN,
                "description": "Price will decrease by approximately 2.50%",
                "predicted_price": 103.35
            },
            {
                "direction": MarketDirection.SIDEWAYS,
                "description": "Price will remain relatively stable (within ±0.75%)",
                "predicted_price": 106.5
            }
        ]
        
    def test_initialization(self):
        """Test that the session is initialized properly"""
        assert self.session.user_id == "test_user"
        assert self.session.symbol == "AAPL"
        assert self.session.asset_type == "stock"
        assert self.session.status == GameStatus.CREATED
        assert self.session.score == 0
        assert self.session.timeframe == 30
        assert self.session.prediction_window == 5
        assert self.session.difficulty == GameDifficulty.MEDIUM
        assert self.session.market_data_snapshot == {}
        assert self.session.hidden_data == {}
        assert self.session.options == []
        assert self.session.selected_option is None
        assert self.session.correct_option is None
        
    def test_set_market_data(self):
        """Test setting market data"""
        self.session.set_market_data("test_data_id", self.market_data, self.hidden_data)
        
        assert self.session.market_data_id == "test_data_id"
        assert self.session.market_data_snapshot == self.market_data
        assert self.session.hidden_data == self.hidden_data
        assert self.session.status == GameStatus.ACTIVE
        
    def test_set_options(self):
        """Test setting options"""
        self.session.set_options(self.options, 0)  # 0 = UP is correct
        
        assert self.session.options == self.options
        assert self.session.correct_option == 0
        
    def test_submit_guess_correct(self):
        """Test submitting a correct guess"""
        # Setup
        self.session.set_market_data("test_data_id", self.market_data, self.hidden_data)
        self.session.set_options(self.options, 0)  # 0 = UP is correct
        
        # Submit the correct guess
        result = self.session.submit_guess(0)
        
        assert result is True
        assert self.session.status == GameStatus.COMPLETED
        assert self.session.selected_option == 0
        assert self.session.score > 0  # Should have earned points
        assert self.session.rounds_played == 1
        assert self.session.rounds_correct == 1
        assert self.session.result is not None
        assert self.session.result["correct"] is True
        assert self.session.completed_at is not None
        
    def test_submit_guess_incorrect(self):
        """Test submitting an incorrect guess"""
        # Setup
        self.session.set_market_data("test_data_id", self.market_data, self.hidden_data)
        self.session.set_options(self.options, 0)  # 0 = UP is correct
        
        # Submit an incorrect guess
        result = self.session.submit_guess(1)  # 1 = DOWN, which is wrong
        
        assert result is False
        assert self.session.status == GameStatus.COMPLETED
        assert self.session.selected_option == 1
        assert self.session.score == 0  # Should not have earned points
        assert self.session.rounds_played == 1
        assert self.session.rounds_correct == 0
        assert self.session.result is not None
        assert self.session.result["correct"] is False
        assert self.session.completed_at is not None
        
    def test_submit_guess_inactive_session(self):
        """Test submitting a guess on an inactive session"""
        # Session starts in CREATED state (not ACTIVE)
        # Try to submit a guess without setting market data first
        result = self.session.submit_guess(0)
        
        assert result is False
        assert self.session.status == GameStatus.CREATED  # Unchanged
        assert self.session.selected_option is None
        assert self.session.score == 0
        
    def test_calculate_accuracy(self):
        """Test accuracy calculation"""
        # Setup a session with some history
        self.session.set_market_data("test_data_id", self.market_data, self.hidden_data)
        self.session.set_options(self.options, 0)
        self.session.submit_guess(0)  # Correct
        
        # First round: 1 correct out of 1 = 100%
        assert self.session.calculate_accuracy() == 100.0
        
        # Setup for another round
        self.session.status = GameStatus.ACTIVE  # Reset status for testing
        self.session.set_options(self.options, 0)
        self.session.submit_guess(1)  # Incorrect
        
        # Second round: 1 correct out of 2 = 50%
        assert self.session.calculate_accuracy() == 50.0
        
    def test_to_dict(self):
        """Test converting session to dictionary"""
        # Setup
        self.session.set_market_data("test_data_id", self.market_data, self.hidden_data)
        self.session.set_options(self.options, 0)
        self.session.submit_guess(0)
        
        # Convert to dict
        session_dict = self.session.to_dict()
        
        # Assert all expected keys exist
        expected_keys = {
            "session_id", "user_id", "symbol", "asset_type", 
            "timeframe", "prediction_window", "difficulty", 
            "status", "options", "selected_option", "score",
            "rounds_played", "rounds_correct", "created_at", 
            "updated_at", "completed_at"
        }
        
        assert all(key in session_dict for key in expected_keys)
        
        # Check some specific values
        assert session_dict["symbol"] == "AAPL"
        assert session_dict["asset_type"] == "stock"
        assert session_dict["status"] == GameStatus.COMPLETED
        assert session_dict["selected_option"] == 0
        assert session_dict["score"] > 0
        assert session_dict["rounds_played"] == 1
        assert session_dict["rounds_correct"] == 1