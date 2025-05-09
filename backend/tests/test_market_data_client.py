"""
Test script to verify that the market data API client is working correctly
with yfinance as the data source
"""
import sys
import os
import asyncio
import json
import pytest
import pandas as pd
from datetime import datetime, timedelta
import unittest.mock as mock

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the module to test
from app.api_clients.market_data import MarketDataClient

@pytest.fixture
def market_data_client():
    """Fixture to create a fresh MarketDataClient instance for each test"""
    return MarketDataClient()

@pytest.fixture
def mock_yf_ticker_data():
    """Fixture to create mock yfinance data"""
    # Create a mock DataFrame that mimics yfinance's history() return value
    dates = [datetime.now() - timedelta(days=i) for i in range(10, 0, -1)]
    
    data = {
        'Open': [100.0 + i for i in range(10)],
        'High': [105.0 + i for i in range(10)],
        'Low': [95.0 + i for i in range(10)],
        'Close': [102.0 + i for i in range(10)],
        'Volume': [1000000 + i*10000 for i in range(10)]
    }
    
    mock_df = pd.DataFrame(data, index=dates)
    return mock_df

@pytest.mark.asyncio
async def test_get_daily_time_series_success(market_data_client, mock_yf_ticker_data):
    """Test successful fetching of daily time series data"""
    with mock.patch('yfinance.Ticker') as mock_yf_ticker:
        # Set up the mock to return a suitable object
        mock_ticker = mock.MagicMock()
        mock_ticker.history.return_value = mock_yf_ticker_data
        mock_yf_ticker.return_value = mock_ticker
        
        # Test with a well-known stock symbol
        result = await market_data_client.get_daily_time_series("AAPL")
        
        # Assert the mock was called correctly
        mock_yf_ticker.assert_called_once_with("AAPL")
        mock_ticker.history.assert_called_once_with(period="3mo", interval="1d")
        
        # Verify the result structure
        assert result is not None
        assert "Meta Data" in result
        assert "Time Series (Daily)" in result
        
        # Check that we have data points in the response
        time_series = result["Time Series (Daily)"]
        assert len(time_series) == 10
        
        # Check the structure of a data point
        sample_date = next(iter(time_series))
        sample_data = time_series[sample_date]
        assert "1. open" in sample_data
        assert "2. high" in sample_data
        assert "3. low" in sample_data
        assert "4. close" in sample_data
        assert "5. volume" in sample_data

@pytest.mark.asyncio
async def test_get_daily_time_series_empty_data(market_data_client):
    """Test handling of empty data returned by yfinance"""
    with mock.patch('yfinance.Ticker') as mock_yf_ticker:
        # Set up the mock to return empty DataFrame
        mock_ticker = mock.MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()  # Empty DataFrame
        mock_yf_ticker.return_value = mock_ticker
        
        # Test with a stock symbol
        result = await market_data_client.get_daily_time_series("AAPL")
        
        # Assert the result is None when no data is returned
        assert result is None

@pytest.mark.asyncio
async def test_get_daily_time_series_error_handling(market_data_client):
    """Test error handling when yfinance raises an exception"""
    with mock.patch('yfinance.Ticker') as mock_yf_ticker:
        # Set up the mock to raise an exception
        mock_ticker = mock.MagicMock()
        mock_ticker.history.side_effect = Exception("API Error")
        mock_yf_ticker.return_value = mock_ticker
        
        # Test with a stock symbol
        result = await market_data_client.get_daily_time_series("AAPL")
        
        # Assert the result is None when an exception occurs
        assert result is None

@pytest.mark.asyncio
async def test_get_intraday_data_success(market_data_client, mock_yf_ticker_data):
    """Test successful fetching of intraday data"""
    with mock.patch('yfinance.Ticker') as mock_yf_ticker:
        # Set up the mock to return a suitable object
        mock_ticker = mock.MagicMock()
        mock_ticker.history.return_value = mock_yf_ticker_data
        mock_yf_ticker.return_value = mock_ticker
        
        # Test with different intervals
        intervals = ["1m", "5m", "15m", "30m", "60m"]
        expected_periods = ["5d", "60d", "60d", "60d", "60d"]
        
        for idx, interval in enumerate(intervals):
            # Reset the mock
            mock_ticker.reset_mock()
            
            # Call the method
            result = await market_data_client.get_intraday_data("MSFT", interval)
            
            # Assert the mock was called correctly
            mock_ticker.history.assert_called_once_with(period=expected_periods[idx], interval=interval)
            
            # Verify the result structure
            assert result is not None
            assert "Meta Data" in result
            assert f"Time Series ({interval})" in result
            
            # Check that we have data points in the response
            time_series = result[f"Time Series ({interval})"]
            assert len(time_series) == 10
            
            # Verify structure of a data point and proper NaN handling
            sample_date = next(iter(time_series))
            sample_data = time_series[sample_date]
            assert "1. open" in sample_data
            assert "2. high" in sample_data
            assert "3. low" in sample_data
            assert "4. close" in sample_data
            assert "5. volume" in sample_data

@pytest.mark.asyncio
async def test_nan_handling(market_data_client):
    """Test that NaN values are handled properly"""
    # Create a DataFrame with NaN values
    dates = [datetime.now() - timedelta(days=i) for i in range(5, 0, -1)]
    
    data = {
        'Open': [100.0, float('nan'), 102.0, 103.0, 104.0],
        'High': [105.0, 106.0, float('nan'), 108.0, 109.0],
        'Low': [95.0, 96.0, 97.0, float('nan'), 99.0],
        'Close': [102.0, 103.0, 104.0, 105.0, float('nan')],
        'Volume': [1000000, float('nan'), 1200000, 1300000, 1400000]
    }
    
    mock_df = pd.DataFrame(data, index=dates)
    
    with mock.patch('yfinance.Ticker') as mock_yf_ticker:
        # Set up the mock to return our DataFrame with NaN values
        mock_ticker = mock.MagicMock()
        mock_ticker.history.return_value = mock_df
        mock_yf_ticker.return_value = mock_ticker
        
        # Test daily data with NaN values
        result = await market_data_client.get_daily_time_series("TEST")
        
        # Verify the result
        assert result is not None
        time_series = result["Time Series (Daily)"]
        
        # Check all values are properly converted to strings (no NaN)
        for day_data in time_series.values():
            for value in day_data.values():
                # All values should be valid strings, not "nan"
                assert value != "nan"
                # Test that we've replaced NaN with "0.0"
                if value == "0.0":
                    # This is expected for NaN values
                    pass
                else:
                    # Other values should be valid numbers
                    float(value)  # This should not raise an exception

@pytest.mark.asyncio
async def test_safe_convert_function_standalone(market_data_client):
    """Test the _safe_convert method directly for various input types"""
    # Test with None
    assert market_data_client._safe_convert(None) == "0.0"
    
    # Test with NaN
    assert market_data_client._safe_convert(float('nan')) == "0.0"
    
    # Test with infinity
    assert market_data_client._safe_convert(float('inf')) == "0.0"
    assert market_data_client._safe_convert(float('-inf')) == "0.0"
    
    # Test with regular values
    assert market_data_client._safe_convert(123.45) == "123.45"
    assert market_data_client._safe_convert(0) == "0"
    
    # Test with strings
    assert market_data_client._safe_convert("test") == "test"

@pytest.mark.asyncio
async def test_intraday_nan_handling(market_data_client):
    """Test that intraday data function handles NaN values properly"""
    # Create test data with NaN values for different intervals
    dates = [datetime.now() - timedelta(hours=i) for i in range(10, 0, -1)]
    
    data = {
        'Open': [100.0, float('nan'), 102.0, 103.0, 104.0, 105.0, float('nan'), 107.0, 108.0, 109.0],
        'High': [105.0, 106.0, float('nan'), 108.0, 109.0, 110.0, 111.0, float('nan'), 113.0, 114.0],
        'Low': [95.0, 96.0, 97.0, float('nan'), 99.0, 100.0, 101.0, 102.0, float('nan'), 104.0],
        'Close': [102.0, 103.0, 104.0, 105.0, float('nan'), 107.0, 108.0, 109.0, 110.0, float('nan')],
        'Volume': [1000000, float('nan'), 1200000, 1300000, 1400000, 1500000, float('nan'), 1700000, 1800000, 1900000]
    }
    
    mock_df = pd.DataFrame(data, index=dates)
    
    with mock.patch('yfinance.Ticker') as mock_yf_ticker:
        # Set up the mock to return our DataFrame with NaN values
        mock_ticker = mock.MagicMock()
        mock_ticker.history.return_value = mock_df
        mock_yf_ticker.return_value = mock_ticker
        
        # Test intraday data with different intervals
        intervals = ["1m", "5m", "15m", "30m", "60m"]
        
        for interval in intervals:
            # Reset mock
            mock_ticker.reset_mock()
            
            # Test the method
            result = await market_data_client.get_intraday_data("TEST", interval)
            
            # Verify the result
            assert result is not None
            time_series = result[f"Time Series ({interval})"]
            assert len(time_series) == 10
            
            # Check all values are properly converted to strings (no NaN)
            for entry_data in time_series.values():
                for value in entry_data.values():
                    # All values should be valid strings, not "nan"
                    assert value != "nan"
                    
                    # Either it's "0.0" (for NaN values) or a valid number
                    if value != "0.0":
                        float(value)  # Should not raise an exception

@pytest.mark.asyncio
async def test_edge_cases_with_nan(market_data_client):
    """Test edge cases with NaN and mixed data types"""
    # Create a DataFrame with edge cases
    dates = [datetime.now() - timedelta(days=i) for i in range(5, 0, -1)]
    
    data = {
        'Open': [float('nan'), 101.0, float('inf'), 103.0, float('-inf')],
        'High': [105.0, float('nan'), 107.0, float('inf'), 109.0],
        'Low': [float('-inf'), 96.0, float('nan'), 98.0, 99.0],
        'Close': [102.0, float('inf'), 104.0, float('nan'), 106.0],
        'Volume': [None, 1100000, None, 1300000, None]  # Mix in some None values
    }
    
    mock_df = pd.DataFrame(data, index=dates)
    
    with mock.patch('yfinance.Ticker') as mock_yf_ticker:
        # Set up the mock to return our DataFrame with edge cases
        mock_ticker = mock.MagicMock()
        mock_ticker.history.return_value = mock_df
        mock_yf_ticker.return_value = mock_ticker
        
        # Test daily data with edge cases
        result = await market_data_client.get_daily_time_series("TEST")
        
        # Verify the result
        assert result is not None
        time_series = result["Time Series (Daily)"]
        
        # Check that all problematic values are converted to "0.0"
        for day_data in time_series.values():
            for value in day_data.values():
                assert value != "nan"
                assert value != "inf"
                assert value != "-inf"
                assert value is not None
                
                # Try to parse as a number
                try:
                    float(value)
                except ValueError:
                    pytest.fail(f"Value '{value}' could not be parsed as a float")

@pytest.mark.asyncio
async def test_json_serialization_after_processing(market_data_client):
    """Test that the result from the client can be safely JSON serialized"""
    # Create a DataFrame with NaN values
    dates = [datetime.now() - timedelta(days=i) for i in range(5, 0, -1)]
    
    data = {
        'Open': [100.0, float('nan'), 102.0, 103.0, 104.0],
        'High': [105.0, 106.0, float('nan'), 108.0, 109.0],
        'Low': [95.0, 96.0, 97.0, float('nan'), 99.0],
        'Close': [102.0, 103.0, 104.0, 105.0, float('nan')],
        'Volume': [1000000, float('nan'), 1200000, 1300000, 1400000]
    }
    
    mock_df = pd.DataFrame(data, index=dates)
    
    with mock.patch('yfinance.Ticker') as mock_yf_ticker:
        # Set up the mock
        mock_ticker = mock.MagicMock()
        mock_ticker.history.return_value = mock_df
        mock_yf_ticker.return_value = mock_ticker
        
        # Get the result
        result = await market_data_client.get_daily_time_series("TEST")
        
        # Try to JSON serialize it
        try:
            json_str = json.dumps(result)
            assert json_str is not None
        except TypeError as e:
            pytest.fail(f"JSON serialization failed: {str(e)}")

# Run the tests if executed directly
if __name__ == "__main__":
    pytest.main(["-xvs", __file__])