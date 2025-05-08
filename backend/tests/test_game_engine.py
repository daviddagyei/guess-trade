"""
Tests for the GameEngine class that implements the core game loop
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime, timedelta

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the modules to test
from app.services.game_engine import GameEngine
from app.services.game_service import GameService


@pytest.fixture
def mock_game_service():
    """Create a mocked GameService for testing"""
    mock_service = MagicMock(spec=GameService)
    
    # Mock the generate_session method
    mock_service.generate_session.return_value = {
        "asset_type": "stock",
        "instrument": "AAPL",
        "timeframe": "daily",
        "difficulty": 1,
        "setup_candles": 60,
        "continuation_candles": 15,
        "timestamp": datetime.now().isoformat()
    }
    
    # Create a mock for the async generate_game_options method
    async_mock = AsyncMock()
    async_mock.return_value = {
        "setup": {
            "asset_type": "stock",
            "instrument": "AAPL",
            "timeframe": "daily",
            "data": [{"date": "2023-01-01", "open": 100, "high": 105, "low": 98, "close": 102, "volume": 1000000}]
        },
        "overlays": {
            "sma_20": [100, 101, 102],
            "rsi": [50, 55, 60]
        },
        "options": [
            {"id": 0, "data": [{"date": "2023-01-02", "open": 102, "high": 106, "low": 100, "close": 105}], "is_correct": True},
            {"id": 1, "data": [{"date": "2023-01-02", "open": 102, "high": 104, "low": 98, "close": 99}], "is_correct": False},
            {"id": 2, "data": [{"date": "2023-01-02", "open": 102, "high": 110, "low": 102, "close": 108}], "is_correct": False},
            {"id": 3, "data": [{"date": "2023-01-02", "open": 102, "high": 103, "low": 96, "close": 97}], "is_correct": False}
        ]
    }
    mock_service.generate_game_options = async_mock
    
    # Mock check_answer method
    mock_service.check_answer.side_effect = lambda user_answer, options: user_answer == 0
    
    # Mock the calculate_score method
    mock_service.calculate_score.side_effect = lambda is_correct, difficulty, time_taken: 150 if is_correct else 0
    
    return mock_service


@pytest.fixture
def game_engine(mock_game_service):
    """Create a GameEngine with mocked dependencies for testing"""
    engine = GameEngine()
    engine.service = mock_game_service
    return engine


@pytest.mark.asyncio
async def test_seed_game(game_engine):
    """Test that seed_game creates a new game session properly"""
    # Seed a new game
    session_id = "test-session-123"
    result = await game_engine.seed_game(session_id, difficulty=1)
    
    # Verify the session is created and stored
    assert session_id in game_engine.active_games
    
    # Verify the game data is returned properly
    assert "session_id" in result
    assert result["session_id"] == session_id
    assert "instrument" in result
    assert result["instrument"] == "AAPL"
    assert "setup" in result
    assert "options" in result
    
    # Verify that options don't contain is_correct flag (solution hidden from client)
    for option in result["options"]:
        assert "is_correct" not in option


def test_submit_guess_correct(game_engine):
    """Test submitting a correct guess"""
    # First we need to set up a mock active game
    session_id = "test-session-123"
    game_engine.active_games[session_id] = {
        "session_id": session_id,
        "asset_type": "stock",
        "instrument": "AAPL",
        "timeframe": "daily",
        "difficulty": 1,
        "setup": {"data": []},
        "overlays": {},
        "options": [
            {"id": 0, "data": [], "is_correct": True},
            {"id": 1, "data": [], "is_correct": False}
        ],
        "start_time": datetime.now().isoformat(),
        "status": "active",
        "user_answer": None,
        "is_correct": None,
        "score": 0,
        "time_taken": None
    }
    
    # Submit the guess
    result = game_engine.submit_guess(session_id, 0)  # 0 is the correct answer in our mock
    
    # Verify the result
    assert result["is_correct"] is True
    assert result["score"] == 150  # Based on our mocked calculate_score
    assert "time_taken" in result
    assert result["correct_option"] == 0
    
    # Verify the game state was updated
    assert game_engine.active_games[session_id]["status"] == "completed"
    assert game_engine.active_games[session_id]["is_correct"] is True
    assert game_engine.active_games[session_id]["score"] == 150


def test_submit_guess_incorrect(game_engine):
    """Test submitting an incorrect guess"""
    # First we need to set up a mock active game
    session_id = "test-session-123"
    game_engine.active_games[session_id] = {
        "session_id": session_id,
        "asset_type": "stock",
        "instrument": "AAPL",
        "timeframe": "daily",
        "difficulty": 1,
        "setup": {"data": []},
        "overlays": {},
        "options": [
            {"id": 0, "data": [], "is_correct": True},
            {"id": 1, "data": [], "is_correct": False}
        ],
        "start_time": datetime.now().isoformat(),
        "status": "active",
        "user_answer": None,
        "is_correct": None,
        "score": 0,
        "time_taken": None
    }
    
    # Submit the incorrect guess
    result = game_engine.submit_guess(session_id, 1)  # 1 is incorrect in our mock
    
    # Verify the result
    assert result["is_correct"] is False
    assert result["score"] == 0
    assert "time_taken" in result
    assert result["correct_option"] == 0
    
    # Verify the game state was updated
    assert game_engine.active_games[session_id]["status"] == "completed"
    assert game_engine.active_games[session_id]["is_correct"] is False
    assert game_engine.active_games[session_id]["score"] == 0


def test_submit_guess_invalid_session(game_engine):
    """Test submitting a guess for a nonexistent session"""
    result = game_engine.submit_guess("nonexistent-session", 0)
    assert "error" in result


def test_submit_guess_completed_game(game_engine):
    """Test submitting a guess for an already completed game"""
    # Set up a completed game
    session_id = "completed-session"
    game_engine.active_games[session_id] = {
        "session_id": session_id,
        "status": "completed",
        "options": []
    }
    
    result = game_engine.submit_guess(session_id, 0)
    assert "error" in result


def test_get_game_state(game_engine):
    """Test retrieving a game state"""
    # Set up a mock game
    session_id = "test-session-123"
    game_engine.active_games[session_id] = {
        "session_id": session_id,
        "asset_type": "stock",
        "instrument": "AAPL",
        "timeframe": "daily",
        "difficulty": 1,
        "setup": {"data": []},
        "overlays": {},
        "options": [
            {"id": 0, "data": [], "is_correct": True},
            {"id": 1, "data": [], "is_correct": False}
        ],
        "start_time": datetime.now().isoformat(),
        "status": "active",
        "user_answer": None,
        "is_correct": None,
        "score": 0,
        "time_taken": None
    }
    
    # Get the state
    result = game_engine.get_game_state(session_id)
    
    # Verify the response
    assert result["session_id"] == session_id
    assert result["instrument"] == "AAPL"
    assert "status" in result
    
    # Ensure is_correct is removed from options for active games
    assert "is_correct" not in result["options"][0]
    assert "is_correct" not in result["options"][1]


def test_get_game_state_invalid_session(game_engine):
    """Test retrieving a nonexistent game state"""
    result = game_engine.get_game_state("nonexistent-session")
    assert "error" in result


def test_find_correct_option(game_engine):
    """Test the _find_correct_option helper method"""
    options = [
        {"id": 0, "data": [], "is_correct": False},
        {"id": 1, "data": [], "is_correct": True},
        {"id": 2, "data": [], "is_correct": False}
    ]
    
    assert game_engine._find_correct_option(options) == 1
    
    # Test with no correct option
    options = [
        {"id": 0, "data": [], "is_correct": False},
        {"id": 1, "data": [], "is_correct": False}
    ]
    
    assert game_engine._find_correct_option(options) is None