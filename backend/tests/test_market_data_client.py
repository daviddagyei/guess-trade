"""
Test script to verify that the market data API client is working correctly
"""
import sys
import os
import asyncio
import pytest

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the module to test
from app.api_clients.market_data import market_data_client

@pytest.mark.asyncio
async def test_get_daily_time_series():
    """Test fetching daily time series data"""
    # Test with a well-known stock symbol
    result = await market_data_client.get_daily_time_series("AAPL")
    
    # Yahoo Finance should always return data for AAPL
    assert result is not None
    assert "Meta Data" in result
    assert "Time Series (Daily)" in result
    
    # Check that we have data points in the response
    time_series = result["Time Series (Daily)"]
    assert len(time_series) > 0
    
    # Check the structure of a data point
    sample_date = next(iter(time_series))
    sample_data = time_series[sample_date]
    assert "1. open" in sample_data
    assert "2. high" in sample_data
    assert "3. low" in sample_data
    assert "4. close" in sample_data
    assert "5. volume" in sample_data

@pytest.mark.asyncio
async def test_get_intraday_data():
    """Test fetching intraday data"""
    # Test with a popular stock
    result = await market_data_client.get_intraday_data("MSFT", "5m")
    
    # Yahoo Finance should return data for MSFT
    assert result is not None
    assert "Meta Data" in result
    assert "Time Series (5m)" in result
    
    # Check that we have data points in the response
    time_series = result["Time Series (5m)"]
    assert len(time_series) > 0

@pytest.mark.asyncio
async def test_get_crypto_data():
    """Test fetching cryptocurrency data"""
    # Test with a popular cryptocurrency
    result = await market_data_client.get_crypto_data("BTC")
    
    # Yahoo Finance should return data for BTC-USD
    assert result is not None
    assert "Meta Data" in result
    assert "Time Series (Digital Currency Daily)" in result
    
    # Check that we have data points in the response
    time_series = result["Time Series (Digital Currency Daily)"]
    assert len(time_series) > 0
    
    # Check the structure of a data point
    sample_date = next(iter(time_series))
    sample_data = time_series[sample_date]
    assert "1a. open (USD)" in sample_data
    assert "2a. high (USD)" in sample_data
    assert "3a. low (USD)" in sample_data
    assert "4a. close (USD)" in sample_data
    assert "5. volume" in sample_data

# Run the tests if executed directly
if __name__ == "__main__":
    asyncio.run(test_get_daily_time_series())
    asyncio.run(test_get_intraday_data())
    asyncio.run(test_get_crypto_data())
    print("All tests passed!")