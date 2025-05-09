from typing import Dict, List, Any, Tuple
import random
import json
import numpy as np
from datetime import datetime, timedelta

from ..api_clients.market_data import market_data_client
from ..cache.redis_cache import redis_cache

class GameService:
    """Service class for handling game logic"""
    
    def __init__(self):
        """Initialize GameService with default settings"""
        # Available instruments for the game
        self.stock_instruments = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        self.timeframes = ["5min", "15min", "30min", "60min", "daily"]
        
    def generate_session(self, difficulty: int = 1) -> Dict[str, Any]:
        """Generate a new game session with the given difficulty"""
        # Choose instrument
        asset_type = "stock"
        instrument = random.choice(self.stock_instruments)
            
        timeframe = random.choice(self.timeframes)
        
        # Adjust setup based on difficulty
        setup_candles = 50 + (10 * difficulty)  # More history for higher difficulty
        continuation_candles = 10 + (5 * difficulty)  # Longer prediction for higher difficulty
        
        return {
            "asset_type": asset_type,
            "instrument": instrument,
            "timeframe": timeframe,
            "difficulty": difficulty,
            "setup_candles": setup_candles,
            "continuation_candles": continuation_candles,
            "timestamp": datetime.now().isoformat()
        }
    
    async def generate_game_options(self, asset_type: str, instrument: str, timeframe: str, difficulty: int) -> Dict[str, Any]:
        """
        Generate game options with real market data
        Returns setup data, overlays, and multiple-choice continuation options
        """
        try:
            # Fetch market data using our API client
            data = await market_data_client.get_daily_time_series(instrument)
            if not data or "Time Series (Daily)" not in data:
                # Fallback to mock data if API fails
                return self._generate_mock_options(instrument, timeframe, difficulty)
            
            # Extract time series data
            time_series = data["Time Series (Daily)"]
            dates = sorted(time_series.keys())
            
            # Get enough candles for setup + continuation
            total_candles_needed = 100  # Enough for setup and all options
            if len(dates) < total_candles_needed:
                # Not enough data, use mock
                return self._generate_mock_options(instrument, timeframe, difficulty)
            
            # Process the data
            prices = []
            for date in dates[-total_candles_needed:]:
                candle = time_series[date]
                prices.append({
                    "date": date,
                    "open": float(candle["1. open"]),
                    "high": float(candle["2. high"]),
                    "low": float(candle["3. low"]),
                    "close": float(candle["4. close"]),
                    "volume": int(candle["5. volume"])
                })
            
            # Split data into setup and options sections
            setup_candles = 50 + (10 * difficulty)
            continuation_candles = 15
            
            setup_data = prices[:setup_candles]
            real_continuation = prices[setup_candles:setup_candles + continuation_candles]
            
            # Get indicators for overlays
            indicators = await self._get_technical_indicators(asset_type, instrument)
            
            # Generate 3 fake continuations and 1 real one
            options = self._generate_continuation_options(setup_data, real_continuation)
            
            return {
                "setup": {
                    "asset_type": asset_type,
                    "instrument": instrument,
                    "timeframe": timeframe,
                    "data": setup_data
                },
                "overlays": indicators,
                "options": options
            }
            
        except Exception as e:
            # If anything fails, fall back to mock data
            print(f"Error generating game options: {e}")
            return self._generate_mock_options(instrument, timeframe, difficulty)
    
    async def _get_technical_indicators(self, asset_type: str, symbol: str) -> Dict[str, Any]:
        """Get technical indicators for the specified asset"""
        try:
            # Try to get indicators from cache
            cache_key = f"indicators:{asset_type}:{symbol}"
            cached_indicators = redis_cache.get_data(cache_key)
            
            if cached_indicators:
                return cached_indicators
            
            # For now, return empty indicators if not cached
            return {}
        except Exception as e:
            print(f"Error fetching indicators: {e}")
            return {}
    
    def _generate_continuation_options(self, setup_data: List[Dict], real_continuation: List[Dict]) -> List[Dict]:
        """Generate multiple choice options including the real continuation and three fake ones"""
        options = []
        
        # Option 0: Real continuation (correct answer)
        options.append({
            "id": 0,
            "data": real_continuation,
            "is_correct": True
        })
        
        # Generate 3 fake continuations
        # These should look plausible but have different patterns
        
        # Get the last close price from setup
        last_close = setup_data[-1]["close"]
        
        # Option 1: Bullish trend (upward movement)
        bullish_trend = []
        current_close = last_close
        for i in range(len(real_continuation)):
            # Generate an upward trend with some randomness
            change = random.uniform(0.005, 0.015) * current_close
            current_close += change
            
            # Copy structure from real data but modify prices
            fake_candle = real_continuation[i].copy()
            fake_candle["close"] = current_close
            fake_candle["open"] = current_close - random.uniform(-0.002, 0.008) * current_close
            fake_candle["high"] = max(fake_candle["open"], fake_candle["close"]) + random.uniform(0.001, 0.01) * current_close
            fake_candle["low"] = min(fake_candle["open"], fake_candle["close"]) - random.uniform(0.001, 0.01) * current_close
            
            bullish_trend.append(fake_candle)
        
        options.append({
            "id": 1,
            "data": bullish_trend,
            "is_correct": False
        })
        
        # Option 2: Bearish trend (downward movement)
        bearish_trend = []
        current_close = last_close
        for i in range(len(real_continuation)):
            # Generate a downward trend with some randomness
            change = -random.uniform(0.005, 0.015) * current_close
            current_close += change
            
            # Copy structure from real data but modify prices
            fake_candle = real_continuation[i].copy()
            fake_candle["close"] = current_close
            fake_candle["open"] = current_close - random.uniform(-0.008, 0.002) * current_close
            fake_candle["high"] = max(fake_candle["open"], fake_candle["close"]) + random.uniform(0.001, 0.01) * current_close
            fake_candle["low"] = min(fake_candle["open"], fake_candle["close"]) - random.uniform(0.001, 0.01) * current_close
            
            bearish_trend.append(fake_candle)
        
        options.append({
            "id": 2,
            "data": bearish_trend,
            "is_correct": False
        })
        
        # Option 3: Sideways/choppy movement
        sideways_trend = []
        current_close = last_close
        for i in range(len(real_continuation)):
            # Generate sideways movement with some randomness
            change = random.uniform(-0.008, 0.008) * current_close
            current_close += change
            
            # Copy structure from real data but modify prices
            fake_candle = real_continuation[i].copy()
            fake_candle["close"] = current_close
            fake_candle["open"] = current_close - random.uniform(-0.005, 0.005) * current_close
            fake_candle["high"] = max(fake_candle["open"], fake_candle["close"]) + random.uniform(0.001, 0.008) * current_close
            fake_candle["low"] = min(fake_candle["open"], fake_candle["close"]) - random.uniform(0.001, 0.008) * current_close
            
            sideways_trend.append(fake_candle)
        
        options.append({
            "id": 3,
            "data": sideways_trend,
            "is_correct": False
        })
        
        # Shuffle the options
        random.shuffle(options)
        
        # Reassign IDs after shuffling
        for i, option in enumerate(options):
            option["id"] = i
            # Find and remember which option is correct
            if option.get("is_correct", False):
                correct_option_id = i
        
        return options
    
    def _generate_mock_options(self, instrument: str, timeframe: str, difficulty: int) -> Dict[str, Any]:
        """Generate mock data when real market data is not available"""
        # Set asset type to stock only
        asset_type = "stock"
        
        # Generate some basic mock price data
        base_price = random.uniform(50, 500)
        
        # Generate setup data (historical prices)
        setup_data = []
        current_price = base_price
        for i in range(60):  # 60 candles of setup data
            # Add some randomness to price
            current_price = current_price * (1 + random.uniform(-0.015, 0.015))
            
            # Generate a candle
            open_price = current_price * (1 + random.uniform(-0.01, 0.01))
            close_price = current_price * (1 + random.uniform(-0.01, 0.01))
            high_price = max(open_price, close_price) * (1 + random.uniform(0.001, 0.01))
            low_price = min(open_price, close_price) * (1 - random.uniform(0.001, 0.01))
            
            # Mock date, going backward from today
            date = (datetime.now() - timedelta(days=60-i)).strftime("%Y-%m-%d")
            
            setup_data.append({
                "date": date,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": int(random.uniform(100000, 1000000))
            })
        
        # Generate real continuation
        real_continuation = []
        current_price = setup_data[-1]["close"]
        for i in range(15):  # 15 candles continuation
            # Continue the trend with some randomness
            current_price = current_price * (1 + random.uniform(-0.02, 0.02))
            
            # Generate a candle
            open_price = current_price * (1 + random.uniform(-0.01, 0.01))
            close_price = current_price * (1 + random.uniform(-0.01, 0.01))
            high_price = max(open_price, close_price) * (1 + random.uniform(0.001, 0.01))
            low_price = min(open_price, close_price) * (1 - random.uniform(0.001, 0.01))
            
            # Mock future date
            date = (datetime.now() + timedelta(days=i+1)).strftime("%Y-%m-%d")
            
            real_continuation.append({
                "date": date,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": int(random.uniform(100000, 1000000))
            })
        
        # Generate mock options using the helper method
        options = self._generate_continuation_options(setup_data, real_continuation)
        
        # Generate mock indicators for overlays
        mock_indicators = {
            "sma_20": [random.uniform(base_price * 0.9, base_price * 1.1) for _ in range(60)],
            "sma_50": [random.uniform(base_price * 0.85, base_price * 1.15) for _ in range(60)],
            "rsi": [random.uniform(30, 70) for _ in range(60)]
        }
        
        return {
            "setup": {
                "asset_type": asset_type,
                "instrument": instrument,
                "timeframe": timeframe,
                "data": setup_data
            },
            "overlays": mock_indicators,
            "options": options
        }
    
    def check_answer(self, user_answer: int, game_options: Dict[str, Any]) -> bool:
        """Check if the user's answer is correct"""
        options = game_options.get("options", [])
        for option in options:
            if option["id"] == user_answer and option.get("is_correct", False):
                return True
        return False
    
    def calculate_score(self, 
                        is_correct: bool, 
                        difficulty: int, 
                        time_taken: float) -> int:
        """Calculate score based on correctness, difficulty and time taken"""
        if not is_correct:
            return 0
            
        # Base score depends on difficulty
        base_score = 100 * difficulty
        
        # Time bonus: faster answers get higher scores
        # Max time bonus at 10 seconds or less
        # No time bonus after 30 seconds
        if time_taken <= 10:
            time_bonus = 50  # Maximum time bonus
        elif time_taken >= 30:
            time_bonus = 0   # No time bonus
        else:
            # Linear decrease from 50 to 0 between 10 and 30 seconds
            time_bonus = int(50 * (30 - time_taken) / 20)
        
        # Scale time bonus with difficulty level for consistent scaling
        time_bonus *= difficulty
        
        return base_score + time_bonus