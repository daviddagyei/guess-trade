"""
Market Data API Client for fetching financial data from Yahoo Finance using yfinance.
"""
import logging
import asyncio
from typing import Dict, Any, Optional
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MarketDataClient:
    """Client for fetching financial market data from Yahoo Finance using yfinance"""
    
    def __init__(self):
        """Initialize the market data client"""
        logger.info("Initializing Yahoo Finance market data client")
    
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
            # Define period based on output_size
            period = "3mo" if output_size == "compact" else "1y"
            
            # Run the yfinance API call in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            ticker_data = await loop.run_in_executor(
                None, lambda: yf.Ticker(symbol).history(period=period, interval="1d")
            )
            
            if ticker_data.empty:
                logger.warning(f"No data returned for symbol {symbol}")
                return None
            
            # Format the data to match our expected structure
            result = {
                "Meta Data": {
                    "1. Information": f"Daily Time Series data for {symbol}",
                    "2. Symbol": symbol,
                    "3. Last Refreshed": datetime.now().strftime("%Y-%m-%d"),
                    "4. Time Zone": "US/Eastern"
                },
                "Time Series (Daily)": {}
            }
            
            # Convert the DataFrame to our expected dictionary format
            for date, row in ticker_data.iterrows():
                date_str = date.strftime("%Y-%m-%d")
                result["Time Series (Daily)"][date_str] = {
                    "1. open": str(row["Open"]),
                    "2. high": str(row["High"]),
                    "3. low": str(row["Low"]),
                    "4. close": str(row["Close"]),
                    "5. volume": str(int(row["Volume"]))
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching daily time series for {symbol}: {str(e)}")
            return None
    
    async def get_intraday_data(self, symbol: str, interval: str = "5m") -> Optional[Dict[str, Any]]:
        """
        Fetch intraday time series data
        
        Args:
            symbol: Stock symbol e.g., AAPL, MSFT
            interval: Time interval between data points (1m, 5m, 15m, 30m, 60m)
            
        Returns:
            Dictionary containing intraday data or None if the request fails
        """
        try:
            # Map interval to yfinance format if needed
            yf_interval = interval.replace("min", "m")
            
            # Define appropriate period based on interval
            if yf_interval == "1m":
                period = "5d"  # For 1m data, Yahoo only provides 5 days max
            elif yf_interval in ["5m", "15m"]:
                period = "60d"
            else:
                period = "60d"
            
            # Run the yfinance API call in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            ticker_data = await loop.run_in_executor(
                None, lambda: yf.Ticker(symbol).history(period=period, interval=yf_interval)
            )
            
            if ticker_data.empty:
                logger.warning(f"No intraday data returned for symbol {symbol}")
                return None
            
            # Format the data to match our expected structure
            result = {
                "Meta Data": {
                    "1. Information": f"Intraday Time Series ({interval}) for {symbol}",
                    "2. Symbol": symbol,
                    "3. Last Refreshed": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "4. Interval": interval,
                    "5. Time Zone": "US/Eastern"
                },
                f"Time Series ({interval})": {}
            }
            
            # Convert the DataFrame to our expected dictionary format
            for date, row in ticker_data.iterrows():
                date_str = date.strftime("%Y-%m-%d %H:%M:%S")
                result[f"Time Series ({interval})"][date_str] = {
                    "1. open": str(row["Open"]),
                    "2. high": str(row["High"]),
                    "3. low": str(row["Low"]),
                    "4. close": str(row["Close"]),
                    "5. volume": str(int(row["Volume"]))
                }
            
            return result
            
        except Exception as e:
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
            # Format the ticker symbol for crypto
            crypto_symbol = f"{symbol}-{market}"
            
            # Run the yfinance API call in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            ticker_data = await loop.run_in_executor(
                None, lambda: yf.Ticker(crypto_symbol).history(period="1y")
            )
            
            if ticker_data.empty:
                logger.warning(f"No data returned for crypto {symbol}-{market}")
                return None
            
            # Format the data to match our expected structure
            result = {
                "Meta Data": {
                    "1. Information": f"Daily Time Series for Digital Currency ({symbol})",
                    "2. Digital Currency Code": symbol,
                    "3. Digital Currency Name": symbol,  # We don't have the name from yfinance
                    "4. Market Code": market,
                    "5. Market Name": f"{market} Market",
                    "6. Last Refreshed": datetime.now().strftime("%Y-%m-%d"),
                    "7. Time Zone": "UTC"
                },
                "Time Series (Digital Currency Daily)": {}
            }
            
            # Convert the DataFrame to our expected dictionary format
            for date, row in ticker_data.iterrows():
                date_str = date.strftime("%Y-%m-%d")
                result["Time Series (Digital Currency Daily)"][date_str] = {
                    "1a. open (USD)": str(row["Open"]),
                    "2a. high (USD)": str(row["High"]),
                    "3a. low (USD)": str(row["Low"]),
                    "4a. close (USD)": str(row["Close"]),
                    "5. volume": str(int(row["Volume"]) if not pd.isna(row["Volume"]) else 0),
                    "6. market cap (USD)": "0"  # Not available from yfinance
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching crypto data for {symbol}: {str(e)}")
            return None


# Singleton instance
market_data_client = MarketDataClient()