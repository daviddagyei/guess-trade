import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import Game from './Game';
import MarketDataService from '../services/MarketDataService';
import WebSocketService from '../services/WebSocketService';

// Mock the dependencies
jest.mock('../services/MarketDataService');
jest.mock('../services/WebSocketService');
jest.mock('react-chartjs-2', () => ({
  Line: jest.fn(() => <canvas data-testid="chart-canvas"></canvas>),
}));

describe('Game Component Chart Rendering', () => {
  const mockStockSymbols = ['AAPL', 'GOOGL', 'MSFT'];
  const mockMarketData = {
    dates: ['2023-01-01', '2023-01-02', '2023-01-03'],
    open: [150.0, 152.0, 151.0],
    high: [155.0, 157.0, 154.0],
    low: [148.0, 149.0, 147.0],
    close: [153.0, 155.0, 152.0],
    volume: [1000000, 1100000, 900000],
  };
  
  // Technical indicators have been removed
  
  // Setup mocks
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Mock MarketDataService implementation
    MarketDataService.mockImplementation(() => ({
      getStockSymbols: jest.fn().mockResolvedValue(mockStockSymbols),
      getStockData: jest.fn().mockResolvedValue(mockMarketData)
    }));
    
    // Mock WebSocketService implementation
    WebSocketService.mockImplementation(() => ({
      connect: jest.fn(),
      disconnect: jest.fn(),
      send: jest.fn(),
      onConnect: jest.fn(cb => cb()),
      onMessage: jest.fn(),
      onDisconnect: jest.fn()
    }));
  });
  
  test('renders loading message initially', () => {
    render(<Game />);
    expect(screen.getByText(/loading data\.\.\./i)).toBeInTheDocument();
  });
  
  test('renders chart when market data is loaded', async () => {
    render(<Game />);
    
    // Wait for the component to load market data
    await waitFor(() => {
      expect(screen.getByTestId('chart-canvas')).toBeInTheDocument();
    });
  });
  
  test('toggles technical indicators when checkboxes are clicked', async () => {
    render(<Game />);
    
    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByTestId('chart-canvas')).toBeInTheDocument();
    });
    
    // Check SMA50 checkbox (SMA20 is checked by default)
    const sma50Checkbox = screen.getByText('SMA 50').previousSibling;
    fireEvent.click(sma50Checkbox);
    
    // Note: In a real test environment, we would verify the chart data has been updated
    // with the new indicator, but since we're mocking Chart.js, we can only verify
    // the checkbox state has changed.
    expect(sma50Checkbox).toBeChecked();
  });
  
  test('handles errors when fetching market data', async () => {
    // Override the mock to simulate an error
    const mockMarketDataServiceWithError = {
      getStockSymbols: jest.fn().mockResolvedValue(mockStockSymbols),
      getStockData: jest.fn().mockRejectedValue(new Error('Failed to fetch')),
      getTechnicalIndicators: jest.fn().mockRejectedValue(new Error('Failed to fetch'))
    };
    
    MarketDataService.mockImplementation(() => mockMarketDataServiceWithError);
    
    render(<Game />);
    
    // Wait for the error message to appear
    await waitFor(() => {
      expect(screen.getByText(/failed to fetch data for/i)).toBeInTheDocument();
    });
  });
  
  // Technical indicators test removed as that functionality has been removed
  
  test('changing selected stock fetches new data', async () => {
    render(<Game />);
    
    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByLabelText(/symbol:/i)).toBeInTheDocument();
    });
    
    // Find the select element 
    const symbolSelect = screen.getByLabelText(/symbol:/i);
    
    // Change the select value to a different symbol
    fireEvent.change(symbolSelect, { target: { value: 'MSFT' } });
    
    // Wait for the new data to be fetched
    await waitFor(() => {
      // Verify the getStockData was called with the new symbol
      const marketDataServiceInstance = MarketDataService.mock.instances[0];
      expect(marketDataServiceInstance.getStockData).toHaveBeenCalledWith('MSFT');
    });
  });
  
  test('chart is not displayed when there is an error', async () => {
    // Override the mock to simulate an error
    const mockMarketDataServiceWithError = {
      getStockSymbols: jest.fn().mockResolvedValue(mockStockSymbols),
      getStockData: jest.fn().mockRejectedValue(new Error('Failed to fetch'))
    };
    
    MarketDataService.mockImplementation(() => mockMarketDataServiceWithError);
    
    render(<Game />);
    
    // Wait for the error message to appear
    await waitFor(() => {
      expect(screen.getByText(/failed to fetch data for/i)).toBeInTheDocument();
      
      // The chart canvas should not be present
      expect(screen.queryByTestId('chart-canvas')).not.toBeInTheDocument();
    });
  });
});