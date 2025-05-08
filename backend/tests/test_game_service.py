"""
Tests for the GameService class that handles game logic
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import random
from datetime import datetime

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the module to test
from app.services.game_service import GameService


@pytest.fixture
def game_service():
    """Create a GameService instance for testing"""
    # Use a fixed seed for reproducible tests
    random.seed(42)
    return GameService()


def test_generate_session(game_service):
    """Test that generate_session returns valid session parameters"""
    # Test with default difficulty
    session = game_service.generate_session()
    
    assert "asset_type" in session
    assert session["asset_type"] in ["stock", "crypto"]
    assert "instrument" in session
    assert "timeframe" in session
    assert "difficulty" in session
    assert "setup_candles" in session
    assert "continuation_candles" in session
    assert "timestamp" in session
    
    # Validate instrument based on asset type
    if session["asset_type"] == "stock":
        assert session["instrument"] in game_service.stock_instruments
    else:
        assert session["instrument"] in game_service.crypto_instruments
    
    # Test with specific difficulty
    session2 = game_service.generate_session(difficulty=3)
    assert session2["difficulty"] == 3
    assert session2["setup_candles"] > session["setup_candles"]  # Higher difficulty has more setup candles


@pytest.mark.asyncio
async def test_generate_game_options_mock(game_service, monkeypatch):
    """Test generate_game_options with mocked API calls"""
    # This test uses the fallback mock options generator for testing
    
    # Mock the API client to always fail (forcing the mock generator to run)
    async def mock_get_daily_time_series(*args, **kwargs):
        return None
    
    async def mock_get_crypto_data(*args, **kwargs):
        return None
    
    # Apply the monkeypatch
    from app.api_clients.market_data import market_data_client
    monkeypatch.setattr(market_data_client, "get_daily_time_series", mock_get_daily_time_series)
    monkeypatch.setattr(market_data_client, "get_crypto_data", mock_get_crypto_data)
    
    # Generate game options
    options = await game_service.generate_game_options(
        asset_type="stock",
        instrument="AAPL",
        timeframe="daily",
        difficulty=1
    )
    
    # Verify structure of returned data
    assert "setup" in options
    assert "instrument" in options["setup"]
    assert "data" in options["setup"]
    assert len(options["setup"]["data"]) > 0
    
    assert "overlays" in options
    assert len(options["overlays"]) > 0
    
    assert "options" in options
    assert len(options["options"]) == 4  # Should have 4 options
    
    # Check that exactly one option is marked as correct
    correct_options = [opt for opt in options["options"] if opt.get("is_correct", False)]
    assert len(correct_options) == 1


def test_generate_continuation_options(game_service):
    """Test the generation of continuation options"""
    # Create sample setup and continuation data
    setup_data = [
        {"date": "2023-01-01", "open": 100, "high": 105, "low": 98, "close": 100, "volume": 1000000},
        {"date": "2023-01-02", "open": 101, "high": 106, "low": 99, "close": 102, "volume": 1100000}
    ]
    
    real_continuation = [
        {"date": "2023-01-03", "open": 103, "high": 108, "low": 101, "close": 105, "volume": 1200000},
        {"date": "2023-01-04", "open": 106, "high": 110, "low": 104, "close": 108, "volume": 1300000}
    ]
    
    options = game_service._generate_continuation_options(setup_data, real_continuation)
    
    # Verify we get 4 options
    assert len(options) == 4
    
    # Verify each option has the required fields
    for option in options:
        assert "id" in option
        assert "data" in option
        assert "is_correct" in option
        assert len(option["data"]) == len(real_continuation)
    
    # Verify exactly one option is marked correct
    correct_options = [opt for opt in options if opt["is_correct"]]
    assert len(correct_options) == 1
    
    # Verify the correct option has the real continuation data
    correct_option = correct_options[0]
    assert correct_option["data"] == real_continuation


def test_generate_mock_options(game_service):
    """Test generation of mock options when real data is unavailable"""
    mock_options = game_service._generate_mock_options("AAPL", "daily", 1)
    
    # Check structure
    assert "setup" in mock_options
    assert "asset_type" in mock_options["setup"]
    assert "instrument" in mock_options["setup"]
    assert "timeframe" in mock_options["setup"]
    assert "data" in mock_options["setup"]
    
    assert "overlays" in mock_options
    assert "sma_20" in mock_options["overlays"]
    assert "sma_50" in mock_options["overlays"]
    assert "rsi" in mock_options["overlays"]
    
    assert "options" in mock_options
    assert len(mock_options["options"]) == 4
    
    # Verify price data looks realistic
    setup_data = mock_options["setup"]["data"]
    assert len(setup_data) > 0
    
    # Check that each candle has the required fields
    for candle in setup_data:
        assert "date" in candle
        assert "open" in candle
        assert "high" in candle
        assert "low" in candle
        assert "close" in candle
        assert "volume" in candle
        # Verify high is highest price in candle
        assert candle["high"] >= candle["open"]
        assert candle["high"] >= candle["close"]
        # Verify low is lowest price in candle
        assert candle["low"] <= candle["open"]
        assert candle["low"] <= candle["close"]


def test_check_answer(game_service):
    """Test that check_answer correctly validates user answers"""
    options = {
        "options": [
            {"id": 0, "data": [], "is_correct": False},
            {"id": 1, "data": [], "is_correct": True},
            {"id": 2, "data": [], "is_correct": False},
            {"id": 3, "data": [], "is_correct": False}
        ]
    }
    
    # Check correct answer
    assert game_service.check_answer(1, options) is True
    
    # Check incorrect answers
    assert game_service.check_answer(0, options) is False
    assert game_service.check_answer(2, options) is False
    assert game_service.check_answer(3, options) is False
    
    # Check invalid answer
    assert game_service.check_answer(4, options) is False


def test_calculate_score(game_service):
    """Test that calculate_score correctly computes scores"""
    # Test incorrect answer (always 0)
    assert game_service.calculate_score(is_correct=False, difficulty=1, time_taken=10) == 0
    assert game_service.calculate_score(is_correct=False, difficulty=3, time_taken=5) == 0
    
    # Test correct answers with various difficulties and times
    
    # Difficulty 1, fast answer (maximum time bonus)
    assert game_service.calculate_score(is_correct=True, difficulty=1, time_taken=5) == 150  # 100 + 50 time bonus
    
    # Difficulty 2, medium time (partial time bonus)
    score = game_service.calculate_score(is_correct=True, difficulty=2, time_taken=20)
    assert score == 250  # 200 + (25*2) time bonus
    
    # Difficulty 3, slow answer (no time bonus)
    assert game_service.calculate_score(is_correct=True, difficulty=3, time_taken=35) == 300  # 300 + 0 time bonus
    
    # Verify difficulty scaling
    score1 = game_service.calculate_score(is_correct=True, difficulty=1, time_taken=15)
    score2 = game_service.calculate_score(is_correct=True, difficulty=2, time_taken=15)
    
    # Base score scales with difficulty, and time bonus also scales with difficulty
    # For time_taken=15, the time bonus is 37.5 (rounded to 37) per difficulty level
    assert score1 == 100 + 37  # 100 base + 37 time bonus
    assert score2 == 200 + 74  # 200 base + 74 time bonus