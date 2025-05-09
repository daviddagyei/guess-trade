"""
Data Processor for ETL operations - handles extracting, transforming, and loading market data.
This module performs scheduled data processing to ensure the game has fresh market data.
"""
import os
import json
import asyncio
import logging
import numpy as np
import math
from typing import Dict, Any, Optional, List

from ..api_clients.market_data import market_data_client
from ..cache.redis_cache import redis_cache

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
        
        # Default stock symbols to process
        self.stock_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    
    async def process_all_data(self):
        """Process all defined stock data"""
        logger.info("Starting full data processing")
        
        # Process stocks
        for symbol in self.stock_symbols:
            try:
                await self.process_stock_data(symbol)
            except Exception as e:
                logger.error(f"Error processing stock data for {symbol}: {str(e)}")
        
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
            self._save_to_file(symbol, processed_data)
            
            logger.info(f"Processed and cached data for {symbol}")
        else:
            logger.info(f"Using cached data for {symbol}")
            processed_data = cached_data
        
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
    

    
    def _save_to_file(self, symbol: str, data: Dict[str, Any]):
        """Save processed data to file for persistence"""
        file_path = os.path.join(self.data_dir, f"stock_{symbol}.json")
        
        with open(file_path, 'w') as f:
            json.dump(data, f)
            
        logger.info(f"Saved stock data for {symbol} to {file_path}")


# Singleton instance
market_data_processor = MarketDataProcessor()