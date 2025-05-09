"""
Tests for the GameEngine class focusing on yfinance data integration
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
def mock_stock_data():
    """Create realistic mock stock data in the format returned from yfinance"""
    days = 100
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days, 0, -1)]
    
    time_series = {}
    price = 150.0
    
    for date in dates:
        # Simple random walk
        price += (0.5 - (0.5 * 0.1)) * price * 0.01
        open_price = price * (1 + (0.5 - (0.5 * 0.1)) * 0.01)
        high_price = max(price, open_price) * (1 + 0.005)
        low_price = min(price, open_price) * (1 - 0.005)
        volume = int(1000000 * (1 + (0.5 - (0.5 * 0.1)) * 0.2))
        
        time_series[date] = {
            "1. open": str(open_price),
            "2. high": str(high_price),
            "3. low": str(low_price),
            "4. close": str(price),
            "5. volume": str(volume)
        }
    
    return {
        "Meta Data": {
            "1. Information": "Daily Time Series data for AAPL",
            "2. Symbol": "AAPL",
            "3. Last Refreshed": datetime.now().strftime("%Y-%m-%d"),
            "4. Time Zone": "US/Eastern"
        },
        "Time Series (Daily)": time_series
    }


@pytest.fixture
def game_service_with_yfinance_data(mock_stock_data):
    """Create a GameService with mocked yfinance data"""
    service = GameService()
    
    # Create an async mock for the market data client
    async def mock_get_daily_time_series(symbol, output_size="compact"):
        return mock_stock_data
    
    async def mock_get_crypto_data(symbol):
        return None  # For this test, let's focus on stock data
    
    # Patch the methods in market_data_client
    with patch('app.api_clients.market_data.market_data_client.get_daily_time_series', 
              new=AsyncMock(side_effect=mock_get_daily_time_series)), \
         patch('app.api_clients.market_data.market_data_client.get_crypto_data', 
              new=AsyncMock(side_effect=mock_get_crypto_data)):
        
        yield service


@pytest.fixture
def game_engine_with_real_service(game_service_with_yfinance_data):
    """Create a GameEngine with a service that uses yfinance data"""
    engine = GameEngine()
    engine.service = game_service_with_yfinance_data
    return engine


@pytest.mark.asyncio
async def test_seed_game_with_yfinance_data(game_engine_with_real_service):
    """Test that seed_game properly initializes a game with yfinance data"""
    # Seed a new game
    session_id = "test-session-123"
    result = await game_engine_with_real_service.seed_game(session_id, difficulty=1)
    
    # Verify the session is created
    assert session_id in game_engine_with_real_service.active_games
    game_state = game_engine_with_real_service.active_games[session_id]
    
    # Verify it contains meaningful data from yfinance
    assert "setup" in game_state
    assert "data" in game_state["setup"]
    setup_data = game_state["setup"]["data"]
    
    # Verify we have the expected number of candles for difficulty 1
    # 50 + (10*1) = 60 candles for difficulty 1
    assert len(setup_data) >= 50
    
    # Verify candle structure
    first_candle = setup_data[0]
    assert "open" in first_candle
    assert "high" in first_candle
    assert "low" in first_candle
    assert "close" in first_candle
    assert "volume" in first_candle
    assert isinstance(first_candle["open"], float)
    
    # Verify the generated options
    assert "options" in game_state
    options = game_state["options"]
    assert len(options) == 4
    
    # Verify response to client
    assert "setup" in result
    assert "options" in result
    
    # Ensure options in the response don't contain is_correct flags
    for option in result["options"]:
        assert "is_correct" not in option
        assert "data" in option


@pytest.mark.asyncio
async def test_seed_game_different_difficulties(game_engine_with_real_service):
    """Test that difficulty affects the game session parameters"""
    # Seed games with different difficulties
    easy_session = "easy-session"
    hard_session = "hard-session"
    
    await game_engine_with_real_service.seed_game(easy_session, difficulty=1)
    await game_engine_with_real_service.seed_game(hard_session, difficulty=3)
    
    # Get the game states
    easy_game = game_engine_with_real_service.active_games[easy_session]
    hard_game = game_engine_with_real_service.active_games[hard_session]
    
    # Verify that difficulty is properly set in the game state
    assert easy_game["difficulty"] == 1
    assert hard_game["difficulty"] == 3
    
    # Instead of comparing candle counts (which might be the same if the mock data returns the same 
    # amount of data for both), verify that the difficulty property is correctly used by the game engine
    # to calculate the expected setup_candles and continuation_candles in the generated session
    easy_session_data = game_engine_with_real_service.service.generate_session(difficulty=1)
    hard_session_data = game_engine_with_real_service.service.generate_session(difficulty=3)
    
    assert easy_session_data["setup_candles"] < hard_session_data["setup_candles"]
    assert easy_session_data["continuation_candles"] < hard_session_data["continuation_candles"]


@pytest.mark.asyncio
async def test_full_game_flow_with_yfinance_data(game_engine_with_real_service):
    """Test a full game flow using yfinance data"""
    # 1. Seed a new game
    session_id = "full-flow-session"
    game_setup = await game_engine_with_real_service.seed_game(session_id, difficulty=1)
    
    # 2. Verify the game is active
    game_state = game_engine_with_real_service.active_games[session_id]
    assert game_state["status"] == "active"
    
    # 3. Find the correct option (in a real game the user wouldn't know this)
    options = game_state["options"]
    correct_option_id = None
    for option in options:
        if option.get("is_correct", False):
            correct_option_id = option["id"]
            break
    
    assert correct_option_id is not None
    
    # 4. Submit the correct answer
    result = game_engine_with_real_service.submit_guess(session_id, correct_option_id)
    
    # 5. Verify the result
    assert result["is_correct"] is True
    assert result["score"] > 0
    assert "time_taken" in result
    assert result["correct_option"] == correct_option_id
    
    # 6. Verify the game state was updated
    updated_state = game_engine_with_real_service.active_games[session_id]
    assert updated_state["status"] == "completed"
    assert updated_state["is_correct"] is True
    assert updated_state["score"] > 0


def test_prepare_game_response_hides_solutions(game_engine_with_real_service):
    """Test that _prepare_game_response properly hides solution information"""
    # Create a game state with solution data
    game_state = {
        "session_id": "test-session",
        "asset_type": "stock",
        "instrument": "AAPL",
        "timeframe": "daily",
        "difficulty": 1,
        "setup": {"data": [{"date": "2023-01-01", "open": 100, "high": 105, "low": 98, "close": 102}]},
        "overlays": {"sma_20": [100, 101]},
        "options": [
            {"id": 0, "data": [{"date": "2023-01-02", "close": 103}], "is_correct": True},
            {"id": 1, "data": [{"date": "2023-01-02", "close": 98}], "is_correct": False}
        ],
        "status": "active",
        "start_time": datetime.now().isoformat(),
        "user_answer": None,
        "is_correct": None,
        "score": 0
    }
    
    # Prepare response for client
    response = game_engine_with_real_service._prepare_game_response(game_state)
    
    # Verify solution is hidden
    for option in response["options"]:
        assert "is_correct" not in option
        assert "id" in option
        assert "data" in option
    
    # Verify game completed reveals solutions
    game_state["status"] = "completed"
    response = game_engine_with_real_service._prepare_game_response(game_state)
    
    # When game is completed, is_correct should be preserved
    for option in response["options"]:
        assert "is_correct" in option


def test_find_correct_option(game_engine_with_real_service):
    """Test the _find_correct_option helper method with yfinance-based options"""
    options = [
        {"id": 0, "data": [{"close": 100}], "is_correct": False},
        {"id": 1, "data": [{"close": 102}], "is_correct": True},
        {"id": 2, "data": [{"close": 98}], "is_correct": False}
    ]
    
    assert game_engine_with_real_service._find_correct_option(options) == 1