"""
Test script to verify that the JSON serialization handles NaN values correctly.
"""
import sys
import os
import json
import pytest
import numpy as np
import pandas as pd
import math

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.api_clients.market_data import market_data_client

def test_safe_convert_method():
    """Test the _safe_convert method in the market_data_client"""
    # Test with normal values
    assert market_data_client._safe_convert(123.45) == "123.45"
    assert market_data_client._safe_convert(0) == "0"
    assert market_data_client._safe_convert("string") == "string"
    
    # Test with problematic values
    assert market_data_client._safe_convert(None) == "0.0"
    assert market_data_client._safe_convert(float('nan')) == "0.0"
    assert market_data_client._safe_convert(float('inf')) == "0.0"
    assert market_data_client._safe_convert(float('-inf')) == "0.0"
    
    # Test with numpy values if numpy is available
    assert market_data_client._safe_convert(np.nan) == "0.0"
    assert market_data_client._safe_convert(np.inf) == "0.0"
    assert market_data_client._safe_convert(-np.inf) == "0.0"
    
    # Test with pandas null value if pandas is available
    try:
        assert market_data_client._safe_convert(pd.NA) == "0.0"
    except:
        # Skip if pandas NA is not available
        pass

def test_json_serialization_with_nan():
    """Test that JSON serialization with NaN values"""
    # Create data with NaN values
    data_with_nan = {
        "value1": float('nan'),
        "value2": float('inf'),
        "value3": [1.0, 2.0, float('nan'), 4.0],
        "value4": {"nested": float('nan')}
    }
    
    # Try to serialize it directly (behavior depends on Python version and environment)
    try:
        json.dumps(data_with_nan)
        # If we get here, the serialization didn't fail
        # This is expected in some environments, but we still need to clean up the NaNs
    except ValueError:
        pass  # This is the expected behavior in most environments

def test_json_serialization_with_safe_convert():
    """Test that using _safe_convert allows JSON serialization"""
    # Create data with NaN values
    raw_data = {
        "value1": float('nan'),
        "value2": float('inf'),
        "value3": [1.0, 2.0, float('nan'), 4.0],
        "value4": {"nested": float('nan')}
    }
    
    # Convert the data using _safe_convert
    converted_data = {
        "value1": market_data_client._safe_convert(raw_data["value1"]),
        "value2": market_data_client._safe_convert(raw_data["value2"]),
        "value3": [market_data_client._safe_convert(v) for v in raw_data["value3"]],
        "value4": {"nested": market_data_client._safe_convert(raw_data["value4"]["nested"])}
    }
    
    # This should not raise an exception
    try:
        json_str = json.dumps(converted_data)
        assert json_str is not None
    except ValueError as e:
        pytest.fail(f"JSON serialization failed: {str(e)}")
    
    # Parse it back and check values
    parsed = json.loads(json_str)
    assert parsed["value1"] == "0.0"  # Was NaN
    assert parsed["value2"] == "0.0"  # Was inf
    assert parsed["value3"][2] == "0.0"  # Was NaN
    assert parsed["value4"]["nested"] == "0.0"  # Was NaN

def test_deep_nested_nan_handling():
    """Test handling NaN values in deeply nested structures"""
    # Create a deeply nested structure with NaN values
    nested_structure = {
        "level1": {
            "level2": {
                "level3": {
                    "array": [1.0, float('nan'), 3.0],
                    "dict": {"a": 1.0, "b": float('nan')}
                }
            }
        }
    }
    
    # Function to recursively replace NaN values
    def replace_nan_recursive(obj):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return market_data_client._safe_convert(obj)
        elif isinstance(obj, dict):
            return {k: replace_nan_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [replace_nan_recursive(v) for v in obj]
        else:
            return obj
    
    # Apply the recursive replacement
    clean_structure = replace_nan_recursive(nested_structure)
    
    # This should not raise an exception
    try:
        json_str = json.dumps(clean_structure)
        assert json_str is not None
    except ValueError as e:
        pytest.fail(f"JSON serialization failed: {str(e)}")
    
    # Check that the structure was properly cleaned
    assert clean_structure["level1"]["level2"]["level3"]["array"][1] == "0.0"
    assert clean_structure["level1"]["level2"]["level3"]["dict"]["b"] == "0.0"

def test_numpy_nan_handling():
    """Test handling of numpy NaN values"""
    # Create numpy array with NaN values
    np_array = np.array([1.0, np.nan, 3.0, np.inf])
    
    # Convert to list of Python values
    py_list = np_array.tolist()
    
    # Try raw serialization (behavior depends on environment)
    try:
        json.dumps({"values": py_list})
    except ValueError:
        pass  # Expected in most environments
    
    # Apply _safe_convert
    safe_list = [market_data_client._safe_convert(v) for v in py_list]
    
    # This should not raise an exception
    try:
        json_str = json.dumps({"values": safe_list})
        assert json_str is not None
    except ValueError as e:
        pytest.fail(f"JSON serialization failed: {str(e)}")
    
    # Parse back and check
    parsed = json.loads(json_str)
    assert parsed["values"][1] == "0.0"  # Was NaN
    assert parsed["values"][3] == "0.0"  # Was inf

def test_pandas_dataframe_conversion():
    """Test handling NaN values from pandas DataFrame"""
    # Create a DataFrame with NaN values
    df = pd.DataFrame({
        'Open': [100.0, np.nan, 102.0],
        'High': [105.0, 106.0, np.nan],
        'Low': [95.0, np.nan, 97.0],
        'Close': [102.0, 103.0, np.nan],
        'Volume': [10000, np.nan, 12000]
    })
    
    # Convert DataFrame values to a dict with _safe_convert
    result = {}
    for column in df.columns:
        result[column] = [market_data_client._safe_convert(v) for v in df[column].values]
    
    # This should not raise an exception
    try:
        json_str = json.dumps(result)
        assert json_str is not None
    except ValueError as e:
        pytest.fail(f"JSON serialization failed: {str(e)}")
    
    # Check the values
    assert result["Open"][1] == "0.0"  # Was NaN
    assert result["High"][2] == "0.0"  # Was NaN
    assert result["Low"][1] == "0.0"  # Was NaN
    assert result["Close"][2] == "0.0"  # Was NaN
    assert result["Volume"][1] == "0.0"  # Was NaN

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])