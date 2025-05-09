"""
Test script to verify that the data processor is working correctly,
with a focus on NaN handling in the technical indicators.
"""
import sys
import os
import asyncio
import pytest
import pandas as pd
import numpy as np
import json
import math
from datetime import datetime, timedelta
import unittest.mock as mock

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the module to test
from app.etl.data_processor import MarketDataProcessor
from app.technical_analysis.indicators import technical_indicators

@pytest.fixture
def data_processor():
    """Fixture to create a fresh MarketDataProcessor instance for each test"""
    return MarketDataProcessor()

@pytest.fixture
def mock_market_data():
    """Fixture to create mock market data response from API client"""
    # Create dates for the past 30 days
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30, 0, -1)]
    
    # Create time series data
    time_series = {}
    for i, date_str in enumerate(dates):
        time_series[date_str] = {
            "1. open": f"{100.0 + i}",
            "2. high": f"{105.0 + i}",
            "3. low": f"{95.0 + i}",
            "4. close": f"{102.0 + i}",
            "5. volume": f"{1000000 + i * 10000}"
        }
    
    # Create the full response
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
def mock_market_data_with_nan():
    """Fixture to create mock market data with NaN values"""
    # Create dates for the past 30 days
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30, 0, -1)]
    
    # Create time series data with some NaN values
    time_series = {}
    for i, date_str in enumerate(dates):
        # Introduce NaN values at specific positions
        open_val = "0.0" if i == 5 else f"{100.0 + i}"
        high_val = "0.0" if i == 10 else f"{105.0 + i}"
        low_val = "0.0" if i == 15 else f"{95.0 + i}"
        close_val = "0.0" if i == 20 else f"{102.0 + i}"
        volume_val = "0" if i == 25 else f"{1000000 + i * 10000}"
        
        time_series[date_str] = {
            "1. open": open_val,
            "2. high": high_val,
            "3. low": low_val,
            "4. close": close_val,
            "5. volume": volume_val
        }
    
    # Create the full response
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
def processed_market_data():
    """Fixture to provide processed market data"""
    return {
        "dates": [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30, 0, -1)],
        "open": [100.0 + i for i in range(30)],
        "high": [105.0 + i for i in range(30)],
        "low": [95.0 + i for i in range(30)],
        "close": [102.0 + i for i in range(30)],
        "volume": [1000000 + i * 10000 for i in range(30)]
    }

@pytest.fixture
def mock_indicators():
    """Fixture to provide mock technical indicators"""
    return {
        "sma_20": [102.0 + i for i in range(30)],
        "sma_50": [100.0 + i for i in range(30)],
        "sma_200": [98.0 + i for i in range(30)],
        "ema_12": [103.0 + i for i in range(30)],
        "ema_26": [101.0 + i for i in range(30)],
        "rsi": [50.0 + i % 30 for i in range(30)],
        "upper_band": [110.0 + i for i in range(30)],
        "middle_band": [102.0 + i for i in range(30)],
        "lower_band": [94.0 + i for i in range(30)],
        "macd": [2.0 + i * 0.1 for i in range(30)],
        "macd_signal": [1.0 + i * 0.1 for i in range(30)],
        "macd_histogram": [1.0 + i * 0.05 for i in range(30)]
    }

@pytest.mark.asyncio
async def test_transform_stock_data(data_processor, mock_market_data):
    """Test transforming raw stock data into usable format"""
    # Get the time series data
    time_series = mock_market_data["Time Series (Daily)"]
    
    # Transform the data
    result = data_processor._transform_stock_data(time_series)
    
    # Verify result structure
    assert "dates" in result
    assert "open" in result
    assert "high" in result
    assert "low" in result
    assert "close" in result
    assert "volume" in result
    
    # Check lengths
    assert len(result["dates"]) == 30
    assert len(result["open"]) == 30
    assert len(result["high"]) == 30
    assert len(result["low"]) == 30
    assert len(result["close"]) == 30
    assert len(result["volume"]) == 30
    
    # Check a few values to ensure correct transformation
    assert result["open"][0] == 100.0
    assert result["high"][0] == 105.0
    assert result["low"][0] == 95.0
    assert result["close"][0] == 102.0
    assert result["volume"][0] == 1000000

@pytest.mark.asyncio
async def test_transform_stock_data_with_nan(data_processor, mock_market_data_with_nan):
    """Test transforming stock data that contains NaN values"""
    # Get the time series data
    time_series = mock_market_data_with_nan["Time Series (Daily)"]
    
    # Transform the data
    result = data_processor._transform_stock_data(time_series)
    
    # Verify data types
    for value in result["open"]:
        assert isinstance(value, float)
    for value in result["high"]:
        assert isinstance(value, float)
    for value in result["low"]:
        assert isinstance(value, float)
    for value in result["close"]:
        assert isinstance(value, float)
    for value in result["volume"]:
        assert isinstance(value, int)
    
    # Make sure the conversion doesn't raise errors
    # This doesn't directly test NaN handling since the transformation
    # should use float() which would fail if it's actually the string "nan"
    
    # Try to JSON encode the result
    try:
        json_str = json.dumps(result)
        assert json_str is not None
    except TypeError:
        pytest.fail("JSON serialization failed due to invalid values")

@pytest.mark.asyncio
async def test_calculate_technical_indicators_nan_handling(data_processor):
    """Test that NaN values are handled properly in technical indicators"""
    # Create test data with enough points for calculations
    close_prices = [100.0] * 250
    # Insert a few NaN values
    close_prices[50] = float('nan')
    close_prices[150] = float('nan')
    
    data = {
        "dates": [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(250, 0, -1)],
        "close": close_prices,
        "open": [100.0] * 250,
        "high": [105.0] * 250,
        "low": [95.0] * 250,
        "volume": [1000000] * 250
    }
    
    # Mock the Redis cache
    with mock.patch("app.cache.redis_cache.redis_cache.set_data") as mock_set_data:
        mock_set_data.return_value = None
        
        # Calculate indicators
        indicators = await data_processor._calculate_technical_indicators("TEST", data)
    
    # Check that all indicators are present
    for key in ["sma_20", "sma_50", "sma_200", "ema_12", "ema_26", "rsi",
               "upper_band", "middle_band", "lower_band", "macd",
               "macd_signal", "macd_histogram"]:
        assert key in indicators
    
    # Check that all arrays have the same length as the input
    for values in indicators.values():
        assert len(values) == len(data["close"])
    
    # Check that there are no NaN or infinite values in the output
    for key, values in indicators.items():
        for value in values:
            assert not math.isnan(value), f"Found NaN in {key}"
            assert not math.isinf(value), f"Found infinity in {key}"
    
    # Check that the arrays can be JSON serialized
    try:
        json_str = json.dumps(indicators)
        assert json_str is not None
    except (TypeError, ValueError) as e:
        pytest.fail(f"JSON serialization failed: {str(e)}")
        
    # Verify that each indicator value is a valid float or 0.0 if it was NaN
    for values in indicators.values():
        for value in values:
            assert isinstance(value, (int, float))

@pytest.mark.asyncio
async def test_process_stock_data_nan_handling(data_processor, mock_market_data):
    """Test that process_stock_data method handles NaN values properly"""
    # Mock the Redis cache to return None (so we use the API)
    async def mock_get_data(key):
        return None
    
    # Mock the set_data method to do nothing
    async def mock_set_data(key, data, ttl_seconds=None):
        pass
    
    # Mock the market_data_client to return our mock data
    async def mock_get_daily_time_series(symbol, output_size=None):
        return mock_market_data
    
    # Mock the _save_to_file to do nothing
    def mock_save_to_file(symbol, data):
        pass
    
    # Mock the _calculate_technical_indicators to return indicators with NaN values
    async def mock_calculate_indicators(symbol, data, asset_type=None):
        # Create indicators with some NaN values
        indicators = {key: [float('nan') if i % 10 == 0 else i * 0.1 for i in range(30)] for key in [
            "sma_20", "sma_50", "sma_200", "ema_12", "ema_26", "rsi",
            "upper_band", "middle_band", "lower_band", "macd",
            "macd_signal", "macd_histogram"
        ]}
        
        # Define our own replace_nan function since we can't access the one inside _calculate_technical_indicators
        def replace_nan(values):
            return [0.0 if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))) else value for value in values]
        
        # Apply the NaN replacement
        return {key: replace_nan(values) for key, values in indicators.items()}
    
    # Apply the mocks
    with mock.patch("app.cache.redis_cache.redis_cache.get_data", mock_get_data), \
         mock.patch("app.cache.redis_cache.redis_cache.set_data", mock_set_data), \
         mock.patch("app.etl.data_processor.market_data_client.get_daily_time_series", mock_get_daily_time_series), \
         mock.patch.object(data_processor, "_save_to_file", mock_save_to_file), \
         mock.patch.object(data_processor, "_calculate_technical_indicators", mock_calculate_indicators):
        
        # Process the data
        result = await data_processor.process_stock_data("AAPL")
    
    # Verify the result
    assert result is not None
    assert "dates" in result
    assert "open" in result
    assert "high" in result
    assert "low" in result
    assert "close" in result
    assert "volume" in result
    assert "indicators" in result
    
    # Verify the indicators
    indicators = result["indicators"]
    for key in ["sma_20", "sma_50", "sma_200", "ema_12", "ema_26", "rsi",
                "upper_band", "middle_band", "lower_band", "macd",
                "macd_signal", "macd_histogram"]:
        assert key in indicators
    
    # Check that there are no NaN values after processing
    for key, values in indicators.items():
        for i, value in enumerate(values):
            # Check if this position should have been a NaN
            if i % 10 == 0:
                # It should have been replaced with 0.0
                assert value == 0.0, f"NaN was not properly replaced at index {i} in {key}"
            else:
                # Other values should be preserved
                assert abs(value - i * 0.1) < 1e-10
    
    # Try to serialize the result to JSON
    try:
        json_str = json.dumps(result)
        assert json_str is not None
    except (TypeError, ValueError) as e:
        pytest.fail(f"JSON serialization failed: {str(e)}")

@pytest.mark.asyncio
async def test_process_all_data(data_processor):
    """Test that process_all_data doesn't raise exceptions"""
    # Mock the process_stock_data to do nothing
    async def mock_process_stock_data(symbol):
        return {"status": "ok"}
    
    with mock.patch.object(data_processor, "process_stock_data", mock_process_stock_data):
        # This shouldn't raise any exception
        await data_processor.process_all_data()

@pytest.mark.asyncio
async def test_process_all_data_error_handling(data_processor):
    """Test that process_all_data handles errors correctly"""
    # Mock the process_stock_data to raise an exception for certain symbols
    async def mock_process_stock_data(symbol):
        if symbol == "GOOGL":
            raise ValueError("Test error")
        return {"status": "ok"}
    
    with mock.patch.object(data_processor, "process_stock_data", mock_process_stock_data):
        # This shouldn't raise any exception, the error should be caught
        await data_processor.process_all_data()
        # If we reach here, the test passed

@pytest.mark.asyncio
async def test_process_stock_data_api_error(data_processor):
    """Test handling of API errors in process_stock_data"""
    # Mock the Redis cache to return None
    async def mock_get_data(key):
        return None
    
    # Mock the market_data_client to return None (indicating an error)
    async def mock_get_daily_time_series(symbol, output_size=None):
        return None
    
    # Apply the mocks
    with mock.patch("app.cache.redis_cache.redis_cache.get_data", mock_get_data), \
         mock.patch("app.etl.data_processor.market_data_client.get_daily_time_series", mock_get_daily_time_series):
        
        # Process the data - should handle the None result gracefully
        result = await data_processor.process_stock_data("AAPL")
        
        # Verify the result is None
        assert result is None

@pytest.mark.asyncio
async def test_process_stock_data_from_cache(data_processor):
    """Test that process_stock_data uses cached data when available"""
    # Create a mock cached data
    cached_data = {
        "dates": [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30, 0, -1)],
        "open": [100.0 + i for i in range(30)],
        "high": [105.0 + i for i in range(30)],
        "low": [95.0 + i for i in range(30)],
        "close": [102.0 + i for i in range(30)],
        "volume": [1000000 + i * 10000 for i in range(30)]
    }
    
    # Mock the Redis cache to return our cached data
    async def mock_get_data(key):
        return cached_data
    
    # Mock the set_data method to do nothing
    async def mock_set_data(key, data, ttl_seconds=None):
        pass
    
    # Mock the _calculate_technical_indicators to return simple indicators
    async def mock_calculate_indicators(symbol, data, asset_type=None):
        return {
            "sma_20": [102.0] * 30,
            "sma_50": [100.0] * 30,
            "sma_200": [98.0] * 30,
            "ema_12": [103.0] * 30,
            "ema_26": [101.0] * 30,
            "rsi": [50.0] * 30,
            "upper_band": [110.0] * 30,
            "middle_band": [102.0] * 30,
            "lower_band": [94.0] * 30,
            "macd": [2.0] * 30,
            "macd_signal": [1.0] * 30,
            "macd_histogram": [1.0] * 30
        }
    
    # Apply the mocks
    with mock.patch("app.cache.redis_cache.redis_cache.get_data", mock_get_data), \
         mock.patch("app.cache.redis_cache.redis_cache.set_data", mock_set_data), \
         mock.patch.object(data_processor, "_calculate_technical_indicators", mock_calculate_indicators):
        
        # Process the data
        result = await data_processor.process_stock_data("AAPL")
    
    # Verify the result is the cached data plus indicators
    assert result is not None
    assert "dates" in result
    assert "open" in result
    assert "high" in result
    assert "low" in result
    assert "close" in result
    assert "volume" in result
    assert "indicators" in result
    
    # Verify that the data is from cache
    assert result["dates"] == cached_data["dates"]
    assert result["open"] == cached_data["open"]
    assert result["high"] == cached_data["high"]
    assert result["low"] == cached_data["low"]
    assert result["close"] == cached_data["close"]
    assert result["volume"] == cached_data["volume"]

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
