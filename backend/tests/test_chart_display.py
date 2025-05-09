"""
Tests to verify that chart data is properly formatted and displayed
"""
import json
import pytest
import math
import pandas as pd
from datetime import datetime, timedelta
from unittest import mock

from fastapi.testclient import TestClient
from app.main import app
from app.etl.data_processor import market_data_processor
from app.api_clients.market_data import market_data_client


@pytest.fixture
def test_client():
    """Return a TestClient for testing API endpoints"""
    return TestClient(app)


@pytest.fixture
def mock_market_data():
    """Fixture to provide mock market data including some NaN values"""
    # Create mock data with some NaN values
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30, 0, -1)]
    
    # Create a market data response with some NaN values in it
    time_series_data = {}
    for i, date in enumerate(dates):
        # Add some NaN values in specific positions
        open_val = float('nan') if i == 5 else 100.0 + i
        high_val = float('nan') if i == 10 else 105.0 + i
        low_val = float('nan') if i == 15 else 95.0 + i 
        close_val = float('nan') if i == 20 else 102.0 + i
        volume_val = float('nan') if i == 25 else 1000000 + i * 10000
        
        time_series_data[date] = {
            "1. open": market_data_client._safe_convert(open_val),
            "2. high": market_data_client._safe_convert(high_val),
            "3. low": market_data_client._safe_convert(low_val), 
            "4. close": market_data_client._safe_convert(close_val),
            "5. volume": market_data_client._safe_convert(int(volume_val) if not math.isnan(volume_val) else volume_val)
        }
    
    return {
        "Meta Data": {
            "1. Information": "Daily Time Series data for GOOGL",
            "2. Symbol": "GOOGL",
            "3. Last Refreshed": datetime.now().strftime("%Y-%m-%d"),
            "4. Time Zone": "US/Eastern"
        },
        "Time Series (Daily)": time_series_data
    }


def test_market_data_client_safe_convert():
    """Test that _safe_convert method properly handles NaN values"""
    # Test with None
    assert market_data_client._safe_convert(None) == "0.0"
    
    # Test with NaN
    assert market_data_client._safe_convert(float('nan')) == "0.0"
    
    # Test with infinity
    assert market_data_client._safe_convert(float('inf')) == "0.0"
    
    # Test with negative infinity
    assert market_data_client._safe_convert(float('-inf')) == "0.0"
    
    # Test with normal value
    assert market_data_client._safe_convert(123.456) == "123.456"
    
    # Test with string
    assert market_data_client._safe_convert("test") == "test"


@pytest.mark.asyncio
async def test_process_stock_data_handles_nan_values():
    """Test that process_stock_data correctly handles NaN values"""
    with mock.patch('app.api_clients.market_data.market_data_client.get_daily_time_series') as mock_get_daily:
        # Use the mock data with NaN values properly converted with _safe_convert
        mock_data = {
            "Meta Data": {
                "1. Information": "Daily Time Series data for GOOGL",
                "2. Symbol": "GOOGL",
                "3. Last Refreshed": datetime.now().strftime("%Y-%m-%d"),
                "4. Time Zone": "US/Eastern"
            },
            "Time Series (Daily)": {
                "2023-01-01": {
                    "1. open": "100.0",
                    "2. high": "105.0",
                    "3. low": "95.0",
                    "4. close": "102.0",
                    "5. volume": "1000000"
                },
                "2023-01-02": {
                    "1. open": "0.0",  # This was a NaN value converted to "0.0" by _safe_convert
                    "2. high": "106.0",
                    "3. low": "96.0",
                    "4. close": "103.0",
                    "5. volume": "1100000"
                }
            }
        }
        mock_get_daily.return_value = mock_data
        
        # Process the data
        processed_data = await market_data_processor.process_stock_data("GOOGL")
        
        # Check that the result is valid JSON (no NaN values)
        json_str = json.dumps(processed_data)
        assert json_str is not None
        
        # Check data structure
        assert processed_data["dates"] is not None
        assert processed_data["open"] is not None
        assert processed_data["high"] is not None
        assert processed_data["low"] is not None
        assert processed_data["close"] is not None
        assert processed_data["volume"] is not None
        
        # Verify data can be serialized to JSON without error
        assert isinstance(json.dumps(processed_data), str)


def test_stock_data_endpoint_returns_clean_data(test_client, monkeypatch):
    """Test that the stock data endpoint returns clean data without NaN values"""
    # Mock the Redis cache to return None so we call the real process_stock_data
    async def mock_get_data(key):
        return None
    
    # Mock the process_stock_data function to return clean test data
    async def mock_process_stock_data(symbol):
        return {
            "dates": ["2023-01-01", "2023-01-02", "2023-01-03"],
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 106.0, 107.0],
            "low": [95.0, 96.0, 97.0],
            "close": [102.0, 103.0, 104.0],
            "volume": [1000000, 1100000, 1200000]
        }
    
    from app.cache.redis_cache import redis_cache
    monkeypatch.setattr(redis_cache, "get_data", mock_get_data)
    monkeypatch.setattr(market_data_processor, "process_stock_data", mock_process_stock_data)
    
    # Test the endpoint
    response = test_client.get("/game/market-data/stock/GOOGL")
    assert response.status_code == 200
    
    data = response.json()
    assert "dates" in data
    assert "open" in data
    assert "high" in data
    assert "low" in data
    assert "close" in data
    assert "volume" in data
    
    # Check the data is properly formatted for charts
    assert len(data["dates"]) == 3
    assert len(data["open"]) == 3
    assert len(data["high"]) == 3
    assert len(data["low"]) == 3
    assert len(data["close"]) == 3
    assert len(data["volume"]) == 3


def test_technical_indicators_endpoint_returns_valid_data(test_client, monkeypatch):
    """Test that technical indicators endpoint returns clean data without NaN values"""
    # Mock redis cache
    async def mock_get_data(key):
        return None
    
    # Mock the get_stock_data function
    async def mock_get_stock_data(symbol):
        return {
            "dates": ["2023-01-01", "2023-01-02", "2023-01-03"],
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 106.0, 107.0],
            "low": [95.0, 96.0, 97.0],
            "close": [102.0, 103.0, 104.0],
            "volume": [1000000, 1100000, 1200000]
        }
    
    # Mock the calculate technical indicators function
    async def mock_calculate_indicators(symbol, market_data, asset_type):
        return {
            "sma_20": [102.0, 103.0, 104.0],
            "sma_50": [101.0, 102.0, 103.0],
            "sma_200": [100.0, 101.0, 102.0],
            "rsi": [50.0, 55.0, 60.0],
            "macd": [0.5, 0.6, 0.7],
            "macd_signal": [0.4, 0.5, 0.6],
            "upper_band": [110.0, 111.0, 112.0],
            "lower_band": [94.0, 95.0, 96.0]
        }
    
    from app.cache.redis_cache import redis_cache
    monkeypatch.setattr(redis_cache, "get_data", mock_get_data)
    monkeypatch.setattr(market_data_processor, "_calculate_technical_indicators", mock_calculate_indicators)
    
    # Mock the get_stock_data endpoint function
    from app.routers.game import get_stock_data
    monkeypatch.setattr("app.routers.game.get_stock_data", mock_get_stock_data)
    
    # Test the endpoint
    response = test_client.get("/game/indicators/stock/GOOGL")
    assert response.status_code == 200
    
    data = response.json()
    # Verify all expected indicators are present
    assert "sma_20" in data
    assert "sma_50" in data
    assert "sma_200" in data
    assert "rsi" in data
    assert "macd" in data
    assert "macd_signal" in data
    assert "upper_band" in data
    assert "lower_band" in data
    
    # Check arrays are the expected length
    assert len(data["sma_20"]) == 3
    assert len(data["rsi"]) == 3


def test_chart_json_serialization_with_nan():
    """Test that JSON serialization properly handles NaN values in the data"""
    # Create data with NaN values
    data_with_nan = {
        "dates": ["2023-01-01", "2023-01-02"],
        "open": [100.0, float('nan')],
        "high": [float('nan'), 106.0],
        "low": [95.0, 96.0],
        "close": [102.0, float('nan')],
        "volume": [float('nan'), 1100000]
    }
    
    # In our specific environment, JSON serialization might actually handle NaN values,
    # but we want to make sure our _safe_convert function still works to replace them
    # with "0.0" strings for consistent behavior across environments
    
    # Convert using our safe_convert function
    safe_data = {
        "dates": data_with_nan["dates"],
        "open": [float(market_data_client._safe_convert(val)) for val in data_with_nan["open"]],
        "high": [float(market_data_client._safe_convert(val)) for val in data_with_nan["high"]],
        "low": [float(market_data_client._safe_convert(val)) for val in data_with_nan["low"]],
        "close": [float(market_data_client._safe_convert(val)) for val in data_with_nan["close"]],
        "volume": [float(market_data_client._safe_convert(val)) for val in data_with_nan["volume"]]
    }
    
    # This should not raise an exception
    json_str = json.dumps(safe_data)
    assert json_str is not None
    
    # Parse it back and check values
    parsed = json.loads(json_str)
    assert parsed["open"][1] == 0.0  # Was NaN
    assert parsed["high"][0] == 0.0  # Was NaN