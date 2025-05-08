"""
Tests for the technical indicators module
"""
import sys
import os
import unittest
import numpy as np

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import our modules
from app.technical_analysis.indicators import TechnicalIndicators

class TestTechnicalIndicators(unittest.TestCase):
    """Test cases for technical indicators"""
    
    def setUp(self):
        # Set up some test data
        # This represents 20 days of closing prices
        self.test_data = [
            100.0, 102.0, 104.0, 103.0, 105.0,
            107.0, 108.0, 107.0, 106.0, 105.0,
            104.0, 103.0, 102.0, 103.0, 101.0,
            99.0, 98.0, 96.0, 95.0, 97.0
        ]
    
    def test_moving_average(self):
        """Test Simple Moving Average calculation"""
        # Calculate a 5-day SMA
        sma = TechnicalIndicators.moving_average(self.test_data, period=5)
        
        # First 4 values should be NaN
        for i in range(4):
            self.assertTrue(np.isnan(sma[i]))
        
        # Check a few specific values
        # SMA of first 5 days: (100+102+104+103+105)/5 = 102.8
        self.assertAlmostEqual(sma[4], 102.8)
        
        # SMA of days 6-10: (102+104+103+105+107)/5 = 104.2
        self.assertAlmostEqual(sma[5], 104.2)
        
        # SMA of last 5 days: (99+98+96+95+97)/5 = 97
        self.assertAlmostEqual(sma[19], 97.0)
    
    def test_exponential_moving_average(self):
        """Test Exponential Moving Average calculation"""
        # Calculate a 5-day EMA
        ema = TechnicalIndicators.exponential_moving_average(self.test_data, period=5)
        
        # First 4 values should be NaN
        for i in range(4):
            self.assertTrue(np.isnan(ema[i]))
        
        # Check the first calculated value (which is just the SMA of the first period)
        # EMA of first 5 days: (100+102+104+103+105)/5 = 102.8
        self.assertAlmostEqual(ema[4], 102.8)
        
        # Spot check that EMA values are different from SMA (due to weighting)
        sma = TechnicalIndicators.moving_average(self.test_data, period=5)
        self.assertNotEqual(ema[10], sma[10])
    
    def test_relative_strength_index(self):
        """Test RSI calculation"""
        # Calculate a 14-day RSI
        rsi = TechnicalIndicators.relative_strength_index(self.test_data, period=14)
        
        # First 15 values should be NaN (14 for period, 1 for initial delta)
        for i in range(15):
            self.assertTrue(np.isnan(rsi[i]))
        
        # Check that RSI is within the valid range (0-100)
        for i in range(15, len(rsi)):
            self.assertTrue(0 <= rsi[i] <= 100)
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        # Calculate Bollinger Bands with 20-day period
        # Since we only have 20 days of data, we'll use a shorter period (5)
        bbands = TechnicalIndicators.bollinger_bands(self.test_data, period=5, num_std=2.0)
        
        # Test structure
        self.assertIn('upper', bbands)
        self.assertIn('middle', bbands)
        self.assertIn('lower', bbands)
        
        # First 4 values should be NaN
        for i in range(4):
            self.assertTrue(np.isnan(bbands['upper'][i]))
            self.assertTrue(np.isnan(bbands['middle'][i]))
            self.assertTrue(np.isnan(bbands['lower'][i]))
        
        # Check some values
        # Middle band is the same as SMA
        sma = TechnicalIndicators.moving_average(self.test_data, period=5)
        self.assertEqual(bbands['middle'][10], sma[10])
        
        # Upper band is always higher than middle band
        for i in range(5, len(self.test_data)):
            self.assertGreater(bbands['upper'][i], bbands['middle'][i])
        
        # Lower band is always lower than middle band
        for i in range(5, len(self.test_data)):
            self.assertLess(bbands['lower'][i], bbands['middle'][i])
    
    def test_macd(self):
        """Test MACD calculation"""
        # Calculate MACD with default settings
        # Note: For proper testing we would need more data points
        # but we'll still do some basic checks with what we have
        macd_data = TechnicalIndicators.macd(self.test_data)
        
        # Test structure
        self.assertIn('macd', macd_data)
        self.assertIn('signal', macd_data)
        self.assertIn('histogram', macd_data)
        
        # Check lengths match the input data
        self.assertEqual(len(macd_data['macd']), len(self.test_data))
        self.assertEqual(len(macd_data['signal']), len(self.test_data))
        self.assertEqual(len(macd_data['histogram']), len(self.test_data))

if __name__ == '__main__':
    unittest.main()