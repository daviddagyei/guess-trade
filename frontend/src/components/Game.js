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
    stocks: [],
    crypto: []
  });
  const [selectedAssetType, setSelectedAssetType] = useState('stock');
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [marketData, setMarketData] = useState(null);
  const [technicalIndicators, setTechnicalIndicators] = useState(null);
  const [selectedIndicators, setSelectedIndicators] = useState({
    sma20: true,
    sma50: false,
    sma200: false,
    bollinger: false,
    rsi: false,
    macd: false
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Initialize services
  useEffect(() => {
    marketDataServiceRef.current = new MarketDataService();
    
    // Fetch available symbols
    const fetchSymbols = async () => {
      try {
        const stocks = await marketDataServiceRef.current.getStockSymbols();
        const crypto = await marketDataServiceRef.current.getCryptoSymbols();
        
        setAvailableSymbols({ stocks, crypto });
        
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

  // Fetch market data when symbol or asset type changes
  useEffect(() => {
    const fetchMarketData = async () => {
      if (!selectedSymbol) return;
      
      setIsLoading(true);
      setError(null);
      
      try {
        let data;
        if (selectedAssetType === 'stock') {
          data = await marketDataServiceRef.current.getStockData(selectedSymbol);
        } else {
          data = await marketDataServiceRef.current.getCryptoData(selectedSymbol);
        }
        
        setMarketData(data);
        
        // Also fetch technical indicators
        const indicators = await marketDataServiceRef.current.getTechnicalIndicators(
          selectedAssetType, 
          selectedSymbol
        );
        
        setTechnicalIndicators(indicators);
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
  }, [selectedSymbol, selectedAssetType]);
  
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

  const handleAssetTypeChange = (e) => {
    const newAssetType = e.target.value;
    setSelectedAssetType(newAssetType);
    
    // Update selected symbol to first of the new type
    if (newAssetType === 'stock' && availableSymbols.stocks.length > 0) {
      setSelectedSymbol(availableSymbols.stocks[0]);
    } else if (newAssetType === 'crypto' && availableSymbols.crypto.length > 0) {
      setSelectedSymbol(availableSymbols.crypto[0]);
    }
  };

  const handleSymbolChange = (e) => {
    setSelectedSymbol(e.target.value);
  };

  const toggleIndicator = (indicator) => {
    setSelectedIndicators(prev => ({
      ...prev,
      [indicator]: !prev[indicator]
    }));
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
    
    // Add selected technical indicators if available
    if (technicalIndicators) {
      // Add SMA 20
      if (selectedIndicators.sma20) {
        datasets.push({
          label: 'SMA 20',
          data: technicalIndicators.sma_20,
          borderColor: 'rgb(255, 99, 132)',
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 0,
          yAxisID: 'y',
        });
      }
      
      // Add SMA 50
      if (selectedIndicators.sma50) {
        datasets.push({
          label: 'SMA 50',
          data: technicalIndicators.sma_50,
          borderColor: 'rgb(54, 162, 235)',
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 0,
          yAxisID: 'y',
        });
      }
      
      // Add SMA 200
      if (selectedIndicators.sma200) {
        datasets.push({
          label: 'SMA 200',
          data: technicalIndicators.sma_200,
          borderColor: 'rgb(255, 159, 64)',
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 0,
          yAxisID: 'y',
        });
      }
      
      // Add Bollinger Bands
      if (selectedIndicators.bollinger) {
        datasets.push({
          label: 'Upper Band',
          data: technicalIndicators.upper_band,
          borderColor: 'rgba(153, 102, 255, 0.8)',
          backgroundColor: 'transparent',
          borderWidth: 1,
          borderDash: [5, 5],
          pointRadius: 0,
          yAxisID: 'y',
        });
        
        datasets.push({
          label: 'Lower Band',
          data: technicalIndicators.lower_band,
          borderColor: 'rgba(153, 102, 255, 0.8)',
          backgroundColor: 'transparent',
          borderWidth: 1,
          borderDash: [5, 5],
          pointRadius: 0,
          yAxisID: 'y',
          fill: {
            target: '-1',
            above: 'rgba(153, 102, 255, 0.1)',
          }
        });
      }
      
      // Add RSI
      if (selectedIndicators.rsi) {
        datasets.push({
          label: 'RSI',
          data: technicalIndicators.rsi,
          borderColor: 'rgb(201, 203, 207)',
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 0,
          yAxisID: 'y1',
        });
      }
      
      // Add MACD
      if (selectedIndicators.macd) {
        datasets.push({
          label: 'MACD',
          data: technicalIndicators.macd,
          borderColor: 'rgb(255, 99, 132)',
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 0,
          yAxisID: 'y2',
        });
        
        datasets.push({
          label: 'MACD Signal',
          data: technicalIndicators.macd_signal,
          borderColor: 'rgb(54, 162, 235)',
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 0,
          yAxisID: 'y2',
        });
      }
    }
    
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
        text: selectedSymbol ? `${selectedSymbol} Chart with Technical Indicators` : 'Loading...',
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
      },
      y1: {
        display: selectedIndicators.rsi,
        position: 'right',
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: 'RSI'
        },
        min: 0,
        max: 100
      },
      y2: {
        display: selectedIndicators.macd,
        position: 'right',
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: 'MACD'
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
          <label htmlFor="asset-type">Asset Type:</label>
          <select 
            id="asset-type" 
            value={selectedAssetType} 
            onChange={handleAssetTypeChange}
            disabled={isLoading}
          >
            <option value="stock">Stock</option>
            <option value="crypto">Cryptocurrency</option>
          </select>
        </div>
        
        <div className="control-group">
          <label htmlFor="symbol">Symbol:</label>
          <select 
            id="symbol" 
            value={selectedSymbol} 
            onChange={handleSymbolChange}
            disabled={isLoading}
          >
            {selectedAssetType === 'stock' && availableSymbols.stocks.map(symbol => (
              <option key={symbol} value={symbol}>{symbol}</option>
            ))}
            {selectedAssetType === 'crypto' && availableSymbols.crypto.map(symbol => (
              <option key={symbol} value={symbol}>{symbol}</option>
            ))}
          </select>
        </div>
      </div>
      
      <div className="indicator-toggles">
        <div className="toggle-group">
          <label>
            <input 
              type="checkbox" 
              checked={selectedIndicators.sma20} 
              onChange={() => toggleIndicator('sma20')} 
            />
            SMA 20
          </label>
          
          <label>
            <input 
              type="checkbox" 
              checked={selectedIndicators.sma50} 
              onChange={() => toggleIndicator('sma50')} 
            />
            SMA 50
          </label>
          
          <label>
            <input 
              type="checkbox" 
              checked={selectedIndicators.sma200} 
              onChange={() => toggleIndicator('sma200')} 
            />
            SMA 200
          </label>
        </div>
        
        <div className="toggle-group">
          <label>
            <input 
              type="checkbox" 
              checked={selectedIndicators.bollinger} 
              onChange={() => toggleIndicator('bollinger')} 
            />
            Bollinger Bands
          </label>
          
          <label>
            <input 
              type="checkbox" 
              checked={selectedIndicators.rsi} 
              onChange={() => toggleIndicator('rsi')} 
            />
            RSI
          </label>
          
          <label>
            <input 
              type="checkbox" 
              checked={selectedIndicators.macd} 
              onChange={() => toggleIndicator('macd')} 
            />
            MACD
          </label>
        </div>
      </div>
      
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