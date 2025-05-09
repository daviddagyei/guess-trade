"""
Tests for the GameService class focusing on yfinance data integration
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
import json
import random
from datetime import datetime, timedelta

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the modules to test
from app.services.game_service import GameService
from app.api_clients.market_data import MarketDataClient


@pytest.fixture
def game_service():
    """Create a GameService instance for testing"""
    # Use a fixed seed for reproducible tests
    random.seed(42)
    return GameService()


@pytest.fixture
def mock_stock_data():
    """Create mock stock data that mimics what would be returned by the MarketDataClient"""
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(100, 0, -1)]
    
    time_series = {}
    current_price = 150.0
    
    for date in dates:
        # Random walk
        change = random.uniform(-3.0, 3.0)
        current_price += change
        
        open_price = current_price - random.uniform(-2.0, 2.0)
        high_price = max(open_price, current_price) + random.uniform(0.1, 1.0)
        low_price = min(open_price, current_price) - random.uniform(0.1, 1.0)
        volume = int(random.uniform(1000000, 10000000))
        
        time_series[date] = {
            "1. open": str(open_price),
            "2. high": str(high_price),
            "3. low": str(low_price),
            "4. close": str(current_price),
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
def mock_crypto_data():
    """Create mock cryptocurrency data that mimics what would be returned by the MarketDataClient"""
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(100, 0, -1)]
    
    time_series = {}
    current_price = 45000.0
    
    for date in dates:
        # Random walk
        change = random.uniform(-1000.0, 1000.0)
        current_price += change
        
        open_price = current_price - random.uniform(-500.0, 500.0)
        high_price = max(open_price, current_price) + random.uniform(10.0, 200.0)
        low_price = min(open_price, current_price) - random.uniform(10.0, 200.0)
        volume = int(random.uniform(10000, 100000))
        
        time_series[date] = {
            "1a. open (USD)": str(open_price),
            "2a. high (USD)": str(high_price),
            "3a. low (USD)": str(low_price),
            "4a. close (USD)": str(current_price),
            "5. volume": str(volume),
            "6. market cap (USD)": str(int(current_price * volume))
        }
    
    return {
        "Meta Data": {
            "1. Information": "Daily Time Series for Digital Currency BTC",
            "2. Digital Currency Code": "BTC",
            "3. Last Refreshed": datetime.now().strftime("%Y-%m-%d"),
            "4. Time Zone": "UTC"
        },
        "Time Series (Digital Currency Daily)": time_series
    }


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
async def test_generate_game_options_with_stock_data(game_service, mock_stock_data):
    """Test generate_game_options with mocked stock data from yfinance"""
    # Mock the market_data_client's get_daily_time_series method
    with patch('app.api_clients.market_data.market_data_client.get_daily_time_series', 
               new=AsyncMock(return_value=mock_stock_data)):
        
        # Generate game options for a stock
        options = await game_service.generate_game_options(
            asset_type="stock",
            instrument="AAPL",
            timeframe="daily",
            difficulty=1
        )
        
        # Verify structure of returned data
        assert "setup" in options
        assert options["setup"]["asset_type"] == "stock"
        assert options["setup"]["instrument"] == "AAPL"
        assert "data" in options["setup"]
        
        # Verify data is correctly processed from the mock yfinance data
        setup_data = options["setup"]["data"]
        assert len(setup_data) == 60  # 50 + (10*1) for difficulty 1
        
        # Verify first candle structure
        first_candle = setup_data[0]
        assert "date" in first_candle
        assert "open" in first_candle
        assert "high" in first_candle
        assert "low" in first_candle
        assert "close" in first_candle
        assert "volume" in first_candle
        
        # Check that values were converted from strings to numbers
        assert isinstance(first_candle["open"], float)
        assert isinstance(first_candle["high"], float)
        assert isinstance(first_candle["low"], float)
        assert isinstance(first_candle["close"], float)
        assert isinstance(first_candle["volume"], int)
        
        # Check options
        assert "options" in options
        assert len(options["options"]) == 4  # Should have 4 options
        
        # Check that exactly one option is marked as correct
        correct_options = [opt for opt in options["options"] if opt.get("is_correct", False)]
        assert len(correct_options) == 1


@pytest.mark.asyncio
async def test_generate_game_options_with_crypto_data(game_service, mock_crypto_data):
    """Test generate_game_options with mocked cryptocurrency data from yfinance"""
    # Mock the market_data_client's get_crypto_data method
    with patch('app.api_clients.market_data.market_data_client.get_crypto_data', 
               new=AsyncMock(return_value=mock_crypto_data)):
        
        # Generate game options for a cryptocurrency
        options = await game_service.generate_game_options(
            asset_type="crypto",
            instrument="BTC",
            timeframe="daily",
            difficulty=2
        )
        
        # Verify structure of returned data
        assert "setup" in options
        assert options["setup"]["asset_type"] == "crypto"
        assert options["setup"]["instrument"] == "BTC"
        assert "data" in options["setup"]
        
        # Verify data is correctly processed from the mock yfinance data
        setup_data = options["setup"]["data"]
        assert len(setup_data) == 70  # 50 + (10*2) for difficulty 2
        
        # Verify first candle structure
        first_candle = setup_data[0]
        assert "date" in first_candle
        assert "open" in first_candle
        assert "high" in first_candle
        assert "low" in first_candle
        assert "close" in first_candle
        assert "volume" in first_candle
        
        # Check that values were converted from strings to numbers
        assert isinstance(first_candle["open"], float)
        assert isinstance(first_candle["high"], float)
        assert isinstance(first_candle["low"], float)
        assert isinstance(first_candle["close"], float)
        assert isinstance(first_candle["volume"], float)
        
        # Check options
        assert "options" in options
        assert len(options["options"]) == 4  # Should have 4 options
        
        # Each option should have continuation data
        for option in options["options"]:
            assert "data" in option
            assert len(option["data"]) == 15  # 15 continuation candles


@pytest.mark.asyncio
async def test_fallback_to_mock_on_empty_data(game_service):
    """Test that the service falls back to mock data when yfinance returns empty data"""
    # Mock the market_data_client's methods to return None (simulating API failure)
    with patch('app.api_clients.market_data.market_data_client.get_daily_time_series', 
               new=AsyncMock(return_value=None)), \
         patch('app.api_clients.market_data.market_data_client.get_crypto_data', 
               new=AsyncMock(return_value=None)):
        
        # Generate game options for a stock
        options = await game_service.generate_game_options(
            asset_type="stock",
            instrument="AAPL",
            timeframe="daily",
            difficulty=1
        )
        
        # Verify we get mock data instead
        assert "setup" in options
        assert "data" in options["setup"]
        assert len(options["setup"]["data"]) > 0
        
        # Verify options exist
        assert "options" in options
        assert len(options["options"]) == 4


@pytest.mark.asyncio
async def test_yfinance_exception_handling(game_service):
    """Test that the service handles exceptions from yfinance gracefully"""
    # Mock the market_data_client to raise an exception
    with patch('app.api_clients.market_data.market_data_client.get_daily_time_series', 
               new=AsyncMock(side_effect=Exception("API Error"))):
        
        # Generate game options should still work by falling back to mock data
        options = await game_service.generate_game_options(
            asset_type="stock",
            instrument="AAPL",
            timeframe="daily",
            difficulty=1
        )
        
        # Verify we get mock data instead
        assert "setup" in options
        assert "data" in options["setup"]
        assert len(options["setup"]["data"]) > 0


def test_generate_continuation_options(game_service):
    """Test the generation of continuation options based on market data"""
    # Create sample setup and continuation data similar to what would be processed from yfinance
    setup_data = [
        {"date": "2023-01-01", "open": 100, "high": 105, "low": 98, "close": 100, "volume": 1000000},
        {"date": "2023-01-02", "open": 101, "high": 106, "low": 99, "close": 102, "volume": 1100000},
        {"date": "2023-01-03", "open": 102, "high": 107, "low": 100, "close": 103, "volume": 1200000}
    ]
    
    real_continuation = [
        {"date": "2023-01-04", "open": 103, "high": 108, "low": 101, "close": 105, "volume": 1200000},
        {"date": "2023-01-05", "open": 106, "high": 110, "low": 104, "close": 108, "volume": 1300000}
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
    
    # Verify other options have different data
    for option in options:
        if not option["is_correct"]:
            assert option["data"] != real_continuation


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
    
    # Test correct answers with various difficulties and times
    
    # Difficulty 1, fast answer (maximum time bonus)
    assert game_service.calculate_score(is_correct=True, difficulty=1, time_taken=5) == 150  # 100 + 50 time bonus
    
    # Difficulty 2, medium time (partial time bonus)
    score = game_service.calculate_score(is_correct=True, difficulty=2, time_taken=20)
    assert score == 250  # 200 + (25*2) time bonus
    
    # Difficulty 3, slow answer (no time bonus)
    assert game_service.calculate_score(is_correct=True, difficulty=3, time_taken=35) == 300  # 300 + 0 time bonus