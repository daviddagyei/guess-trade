import React, { useState, useEffect, useRef } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import WebSocketService from '../services/WebSocketService';
import MarketDataService from '../services/MarketDataService';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const Game = () => {
  const [gameState, setGameState] = useState({
    setup: null,
    options: [],
    overlays: null,
    selectedOption: null,
    score: 0,
    message: 'Waiting for game data...',
  });
  
  const [websocketConnected, setWebsocketConnected] = useState(false);
  const wsRef = useRef(null);
  const marketDataServiceRef = useRef(null);

  // Market data state
  const [availableSymbols, setAvailableSymbols] = useState({
    stocks: []
  });
  const [selectedAssetType, setSelectedAssetType] = useState('stock');
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [marketData, setMarketData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Initialize services
  useEffect(() => {
    marketDataServiceRef.current = new MarketDataService();
    
    // Fetch available symbols
    const fetchSymbols = async () => {
      try {
        const stocks = await marketDataServiceRef.current.getStockSymbols();
        setAvailableSymbols({ stocks });
        
        // Set default selected symbol if available
        if (stocks.length > 0) {
          setSelectedSymbol(stocks[0]);
        }
      } catch (error) {
        console.error('Error fetching symbols:', error);
        setError('Failed to fetch available symbols');
      }
    };
    
    fetchSymbols();
  }, []);

  // Initialize WebSocket connection
  useEffect(() => {
    // Use the window location to determine the WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname === 'localhost' ? 'localhost:8001' : window.location.host;
    const wsUrl = `${protocol}//${host}/game/ws/client-${Date.now()}`;
    
    wsRef.current = new WebSocketService(wsUrl);
    
    wsRef.current.onConnect(() => {
      setWebsocketConnected(true);
      wsRef.current.send({ action: 'start_game' });
    });
    
    wsRef.current.onMessage((data) => {
      console.log('Received game data:', data);
      if (data.message) {
        setGameState(prevState => ({
          ...prevState,
          message: data.message
        }));
      }
    });
    
    wsRef.current.onDisconnect(() => {
      setWebsocketConnected(false);
      setGameState(prevState => ({
        ...prevState,
        message: 'Connection lost. Reconnecting...'
      }));
    });
    
    wsRef.current.connect();
    
    // Clean up WebSocket connection on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
    };
  }, []);

  // Fetch market data when symbol changes
  useEffect(() => {
    const fetchMarketData = async () => {
      if (!selectedSymbol) return;
      
      setIsLoading(true);
      setError(null);
      
      try {
        const data = await marketDataServiceRef.current.getStockData(selectedSymbol);
        setMarketData(data);
      } catch (error) {
        console.error('Error fetching market data:', error);
        setError(`Failed to fetch data for ${selectedSymbol}`);
      } finally {
        setIsLoading(false);
      }
    };
    
    if (selectedSymbol && marketDataServiceRef.current) {
      fetchMarketData();
    }
  }, [selectedSymbol]);
  
  const handleOptionSelect = (optionIndex) => {
    setGameState(prevState => ({
      ...prevState,
      selectedOption: optionIndex
    }));
    
    if (wsRef.current) {
      wsRef.current.send({
        action: 'submit_answer',
        answer: optionIndex
      });
    }
  };

  const handleSymbolChange = (e) => {
    setSelectedSymbol(e.target.value);
  };

  // Prepare chart data
  const buildChartData = () => {
    if (!marketData) {
      return {
        labels: [],
        datasets: []
      };
    }
    
    const { dates, close } = marketData;
    
    // Base dataset for price data
    const datasets = [
      {
        label: `${selectedSymbol} Price`,
        data: close,
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.1,
        yAxisID: 'y',
      }
    ];
    
    return {
      labels: dates,
      datasets: datasets
    };
  };
  
  const chartData = buildChartData();
  
  const chartOptions = {
    responsive: true,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: selectedSymbol ? `${selectedSymbol} Price Chart` : 'Loading...',
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += new Intl.NumberFormat('en-US', {
                style: 'decimal',
                minimumFractionDigits: 2,
                maximumFractionDigits: 4
              }).format(context.parsed.y);
            }
            return label;
          }
        }
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Date'
        }
      },
      y: {
        display: true,
        position: 'left',
        title: {
          display: true,
          text: 'Price'
        }
      }
    }
  };
  
  return (
    <div className="game-container">
      <div className="game-header">
        <h1>GuessTrade Game</h1>
        <div className="score">Score: {gameState.score}</div>
        <div className={`connection-status ${websocketConnected ? 'connected' : 'disconnected'}`}>
          {websocketConnected ? 'Connected' : 'Disconnected'}
        </div>
      </div>
      
      <div className="market-data-controls">
        <div className="control-group">
          <label htmlFor="symbol">Symbol:</label>
          <select 
            id="symbol" 
            value={selectedSymbol} 
            onChange={handleSymbolChange}
            disabled={isLoading}
          >
            {availableSymbols.stocks.map(symbol => (
              <option key={symbol} value={symbol}>{symbol}</option>
            ))}
          </select>
        </div>
      </div>
      
      {/* Technical indicator toggles have been removed */}
      
      <div className="chart-container">
        {isLoading ? (
          <div className="loading-message">Loading data...</div>
        ) : error ? (
          <div className="error-message">{error}</div>
        ) : marketData ? (
          <Line data={chartData} options={chartOptions} />
        ) : (
          <div className="loading-message">{gameState.message}</div>
        )}
      </div>
      
      <div className="options-container">
        {gameState.options.map((option, index) => (
          <div 
            key={index} 
            className={`option ${gameState.selectedOption === index ? 'selected' : ''}`}
            onClick={() => handleOptionSelect(index)}
          >
            Option {index + 1}
          </div>
        ))}
      </div>
      
      {/* For testing purposes, we'll keep the test button */}
      <button 
        className="test-button"
        onClick={() => {
          if (wsRef.current) {
            wsRef.current.send({ action: 'ping', message: 'Hello from client!' });
          }
        }}
        disabled={!websocketConnected}
      >
        Send Test Message
      </button>
    </div>
  );
};

export default Game;