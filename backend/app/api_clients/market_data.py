"""
Market Data API Client for fetching financial data from Alpha Vantage API.
This can be replaced with your preferred financial data API provider.
"""
import os
import logging
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class MarketDataClient:
    """Client for fetching financial market data from Alpha Vantage"""
    
    def __init__(self):
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            logger.warning("ALPHA_VANTAGE_API_KEY not found in environment variables")
        self.base_url = "https://www.alphavantage.co/query"
    
    async def get_daily_time_series(self, symbol: str, output_size: str = "compact") -> Optional[Dict[str, Any]]:
        """
        Fetch daily time series data for a given symbol
        
        Args:
            symbol: Stock symbol e.g., AAPL, MSFT
            output_size: 'compact' (last 100 data points) or 'full' (all data points)
            
        Returns:
            Dictionary containing time series data or None if the request fails
        """
        try:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": output_size,
                "apikey": self.api_key,
            }
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching daily time series for {symbol}: {str(e)}")
            return None
    
    async def get_intraday_data(self, symbol: str, interval: str = "5min") -> Optional[Dict[str, Any]]:
        """
        Fetch intraday time series data
        
        Args:
            symbol: Stock symbol e.g., AAPL, MSFT
            interval: Time interval between data points (1min, 5min, 15min, 30min, 60min)
            
        Returns:
            Dictionary containing intraday data or None if the request fails
        """
        try:
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": symbol,
                "interval": interval,
                "apikey": self.api_key,
            }
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching intraday data for {symbol}: {str(e)}")
            return None
    
    async def get_crypto_data(self, symbol: str, market: str = "USD") -> Optional[Dict[str, Any]]:
        """
        Fetch cryptocurrency data
        
        Args:
            symbol: Cryptocurrency symbol e.g., BTC, ETH
            market: Market/Currency to convert to e.g., USD
            
        Returns:
            Dictionary containing cryptocurrency data or None if the request fails
        """
        try:
            params = {
                "function": "DIGITAL_CURRENCY_DAILY",
                "symbol": symbol,
                "market": market,
                "apikey": self.api_key,
            }
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching crypto data for {symbol}: {str(e)}")
            return None


# Singleton instance
market_data_client = MarketDataClient()