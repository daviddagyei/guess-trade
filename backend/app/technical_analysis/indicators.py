"""
Technical Analysis module for calculating various market indicators.
These indicators can be used for overlays in the game prediction UI.
"""
import numpy as np
from typing import Dict, List, Tuple, Any, Union
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """
    Technical analysis indicators for market data
    """
    
    @staticmethod
    def moving_average(data: List[float], period: int = 20) -> List[float]:
        """
        Calculate Simple Moving Average (SMA)
        
        Args:
            data: List of price data points
            period: Number of periods for moving average
            
        Returns:
            List of moving average values
        """
        if len(data) < period:
            logger.warning(f"Data length ({len(data)}) is less than period ({period})")
            # Return list of NaNs with same length as data
            return [np.nan] * len(data)
        
        result = []
        # First periods-1 points will be NaN
        result.extend([np.nan] * (period - 1))
        
        # Calculate SMA for the rest
        for i in range(period - 1, len(data)):
            window = data[i - period + 1 : i + 1]
            ma = sum(window) / period
            result.append(ma)
        
        return result
    
    @staticmethod
    def exponential_moving_average(data: List[float], period: int = 20) -> List[float]:
        """
        Calculate Exponential Moving Average (EMA)
        
        Args:
            data: List of price data points
            period: Number of periods for EMA
            
        Returns:
            List of EMA values
        """
        if len(data) < period:
            logger.warning(f"Data length ({len(data)}) is less than period ({period})")
            return [np.nan] * len(data)
        
        result = [np.nan] * (period - 1)
        
        # First EMA is SMA
        multiplier = 2 / (period + 1)
        sma = sum(data[:period]) / period
        ema = sma
        result.append(ema)
        
        # Calculate EMA for the rest
        for i in range(period, len(data)):
            ema = (data[i] - ema) * multiplier + ema
            result.append(ema)
        
        return result
    
    @staticmethod
    def relative_strength_index(data: List[float], period: int = 14) -> List[float]:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            data: List of price data points
            period: Number of periods for RSI
            
        Returns:
            List of RSI values
        """
        if len(data) < period + 1:
            logger.warning(f"Data length ({len(data)}) is less than period+1 ({period+1})")
            return [np.nan] * len(data)
        
        # Calculate price changes
        deltas = [data[i] - data[i-1] for i in range(1, len(data))]
        
        # Prepend a NaN to make length match original data
        result = [np.nan]
        
        # Not enough data points for the first (period) values
        result.extend([np.nan] * period)
        
        # Calculate RSI
        for i in range(period, len(deltas)):
            window = deltas[i - period + 1 : i + 1]
            
            gains = [x for x in window if x > 0]
            losses = [-x for x in window if x < 0]
            
            avg_gain = sum(gains) / period if gains else 0
            avg_loss = sum(losses) / period if losses else 0
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                
            result.append(rsi)
            
        return result
    
    @staticmethod
    def bollinger_bands(data: List[float], period: int = 20, num_std: float = 2.0) -> Dict[str, List[float]]:
        """
        Calculate Bollinger Bands
        
        Args:
            data: List of price data points
            period: Number of periods for moving average
            num_std: Number of standard deviations for band width
            
        Returns:
            Dictionary with lists for 'upper', 'middle' (SMA), and 'lower' bands
        """
        if len(data) < period:
            logger.warning(f"Data length ({len(data)}) is less than period ({period})")
            nan_list = [np.nan] * len(data)
            return {"upper": nan_list, "middle": nan_list, "lower": nan_list}
        
        # Calculate SMA
        middle_band = TechnicalIndicators.moving_average(data, period)
        
        upper_band = []
        lower_band = []
        
        # First (period-1) values will be NaN
        for i in range(len(data)):
            if i < period - 1:
                upper_band.append(np.nan)
                lower_band.append(np.nan)
            else:
                window = data[i - period + 1 : i + 1]
                std = np.std(window)
                upper_band.append(middle_band[i] + num_std * std)
                lower_band.append(middle_band[i] - num_std * std)
        
        return {
            "upper": upper_band,
            "middle": middle_band,
            "lower": lower_band
        }
    
    @staticmethod
    def macd(data: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, List[float]]:
        """
        Calculate Moving Average Convergence Divergence (MACD)
        
        Args:
            data: List of price data points
            fast_period: Number of periods for fast EMA
            slow_period: Number of periods for slow EMA
            signal_period: Number of periods for signal EMA
            
        Returns:
            Dictionary with lists for 'macd', 'signal', and 'histogram'
        """
        # Calculate EMAs
        fast_ema = TechnicalIndicators.exponential_moving_average(data, fast_period)
        slow_ema = TechnicalIndicators.exponential_moving_average(data, slow_period)
        
        # Calculate MACD line
        macd_line = []
        for i in range(len(data)):
            if np.isnan(fast_ema[i]) or np.isnan(slow_ema[i]):
                macd_line.append(np.nan)
            else:
                macd_line.append(fast_ema[i] - slow_ema[i])
        
        # Calculate signal line (EMA of MACD)
        signal_line = TechnicalIndicators.exponential_moving_average(macd_line, signal_period)
        
        # Calculate histogram (MACD - Signal)
        histogram = []
        for i in range(len(data)):
            if np.isnan(macd_line[i]) or np.isnan(signal_line[i]):
                histogram.append(np.nan)
            else:
                histogram.append(macd_line[i] - signal_line[i])
        
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }


# Singleton instance
technical_indicators = TechnicalIndicators()