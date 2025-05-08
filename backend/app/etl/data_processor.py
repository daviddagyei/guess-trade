"""
Data Processor for ETL operations - handles extracting, transforming, and loading market data.
This module performs scheduled data processing to ensure the game has fresh market data.
"""
import os
import csv
import json
import asyncio
import logging
import datetime
from typing import List, Dict, Any, Optional

from ..api_clients.market_data import market_data_client
from ..cache.redis_cache import redis_cache
from ..technical_analysis.indicators import technical_indicators

logger = logging.getLogger(__name__)

class MarketDataProcessor:
    """
    Handles ETL operations for market data processing
    """
    
    def __init__(self):
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data"
        )
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Default symbols to process
        self.stock_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
        self.crypto_symbols = ["BTC", "ETH", "SOL", "ADA", "DOT"]
    
    async def process_all_data(self):
        """Process all defined stock and crypto data"""
        logger.info("Starting full data processing")
        
        # Process stocks
        for symbol in self.stock_symbols:
            try:
                await self.process_stock_data(symbol)
            except Exception as e:
                logger.error(f"Error processing stock data for {symbol}: {str(e)}")
        
        # Process crypto
        for symbol in self.crypto_symbols:
            try:
                await self.process_crypto_data(symbol)
            except Exception as e:
                logger.error(f"Error processing crypto data for {symbol}: {str(e)}")
        
        logger.info("Completed full data processing")
    
    async def process_stock_data(self, symbol: str):
        """Process stock data for a symbol"""
        logger.info(f"Processing stock data for {symbol}")
        
        # Check cache first
        cache_key = redis_cache.build_market_data_key(symbol, "stock")
        cached_data = await redis_cache.get_data(cache_key)
        
        if not cached_data:
            # Fetch from API
            raw_data = await market_data_client.get_daily_time_series(symbol)
            if not raw_data or "Time Series (Daily)" not in raw_data:
                logger.error(f"Failed to fetch stock data for {symbol}")
                return
            
            # Transform data
            time_series = raw_data["Time Series (Daily)"]
            processed_data = self._transform_stock_data(time_series)
            
            # Cache processed data
            await redis_cache.set_data(cache_key, processed_data, ttl_seconds=86400)  # 24 hours
            
            # Write to file for persistence
            self._save_to_file(symbol, "stock", processed_data)
            
            logger.info(f"Processed and cached data for {symbol}")
        else:
            logger.info(f"Using cached data for {symbol}")
            processed_data = cached_data
        
        # Calculate technical indicators
        indicators = await self._calculate_technical_indicators(symbol, processed_data, asset_type="stock")
        
        return processed_data
    
    async def process_crypto_data(self, symbol: str):
        """Process crypto data for a symbol"""
        logger.info(f"Processing crypto data for {symbol}")
        
        # Check cache first
        cache_key = redis_cache.build_market_data_key(symbol, "crypto")
        cached_data = await redis_cache.get_data(cache_key)
        
        if not cached_data:
            # Fetch from API
            raw_data = await market_data_client.get_crypto_data(symbol)
            if not raw_data or "Time Series (Digital Currency Daily)" not in raw_data:
                logger.error(f"Failed to fetch crypto data for {symbol}")
                return
            
            # Transform data
            time_series = raw_data["Time Series (Digital Currency Daily)"]
            processed_data = self._transform_crypto_data(time_series)
            
            # Cache processed data
            await redis_cache.set_data(cache_key, processed_data, ttl_seconds=86400)  # 24 hours
            
            # Write to file for persistence
            self._save_to_file(symbol, "crypto", processed_data)
            
            logger.info(f"Processed and cached data for {symbol}")
        else:
            logger.info(f"Using cached data for {symbol}")
            processed_data = cached_data
        
        # Calculate technical indicators
        indicators = await self._calculate_technical_indicators(symbol, processed_data, asset_type="crypto")
        
        return processed_data
    
    def _transform_stock_data(self, time_series: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw stock data into usable format"""
        result = {
            "dates": [],
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": []
        }
        
        # Sort dates in ascending order
        sorted_dates = sorted(time_series.keys())
        
        for date in sorted_dates:
            daily_data = time_series[date]
            
            result["dates"].append(date)
            result["open"].append(float(daily_data["1. open"]))
            result["high"].append(float(daily_data["2. high"]))
            result["low"].append(float(daily_data["3. low"]))
            result["close"].append(float(daily_data["4. close"]))
            result["volume"].append(int(daily_data["5. volume"]))
        
        return result
    
    def _transform_crypto_data(self, time_series: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw cryptocurrency data into usable format"""
        result = {
            "dates": [],
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": []
        }
        
        # Sort dates in ascending order
        sorted_dates = sorted(time_series.keys())
        
        for date in sorted_dates:
            daily_data = time_series[date]
            
            result["dates"].append(date)
            result["open"].append(float(daily_data["1a. open (USD)"]))
            result["high"].append(float(daily_data["2a. high (USD)"]))
            result["low"].append(float(daily_data["3a. low (USD)"]))
            result["close"].append(float(daily_data["4a. close (USD)"]))
            result["volume"].append(float(daily_data["5. volume"]))
        
        return result
    
    async def _calculate_technical_indicators(self, symbol: str, data: Dict[str, Any], asset_type: str = "stock"):
        """Calculate and cache technical indicators for the data"""
        logger.info(f"Calculating technical indicators for {symbol}")
        
        close_prices = data["close"]
        
        # Calculate SMA with different periods
        sma_20 = technical_indicators.moving_average(close_prices, period=20)
        sma_50 = technical_indicators.moving_average(close_prices, period=50)
        sma_200 = technical_indicators.moving_average(close_prices, period=200)
        
        # Calculate EMA with different periods
        ema_12 = technical_indicators.exponential_moving_average(close_prices, period=12)
        ema_26 = technical_indicators.exponential_moving_average(close_prices, period=26)
        
        # Calculate RSI
        rsi = technical_indicators.relative_strength_index(close_prices)
        
        # Calculate Bollinger Bands
        bbands = technical_indicators.bollinger_bands(close_prices)
        
        # Calculate MACD
        macd_data = technical_indicators.macd(close_prices)
        
        # Combine all indicators
        indicators = {
            "sma_20": sma_20,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "ema_12": ema_12,
            "ema_26": ema_26,
            "rsi": rsi,
            "upper_band": bbands["upper"],
            "middle_band": bbands["middle"],
            "lower_band": bbands["lower"],
            "macd": macd_data["macd"],
            "macd_signal": macd_data["signal"],
            "macd_histogram": macd_data["histogram"]
        }
        
        # Cache indicators
        cache_key = f"indicators:{asset_type}:{symbol}"
        await redis_cache.set_data(cache_key, indicators, ttl_seconds=86400)
        
        logger.info(f"Cached technical indicators for {symbol}")
        
        return indicators
    
    def _save_to_file(self, symbol: str, data_type: str, data: Dict[str, Any]):
        """Save processed data to file for persistence"""
        file_path = os.path.join(self.data_dir, f"{data_type}_{symbol}.json")
        
        with open(file_path, 'w') as f:
            json.dump(data, f)
            
        logger.info(f"Saved {data_type} data for {symbol} to {file_path}")


# Singleton instance
market_data_processor = MarketDataProcessor()