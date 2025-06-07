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
import OptionChart from './OptionChart'; // Import the OptionChart component
import './Game.css'; // Import the CSS file

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
    lives: 3,
    streak: 0,
    round: 0,
    gamePhase: 'INIT', // INIT, LOADING, QUESTION, REVEAL, GAME_OVER
    countdownTime: 20,
    sessionTimeRemaining: 300, // 5 minutes in seconds
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
  
  // Game timer state
  const [countdownInterval, setCountdownInterval] = useState(null);
  const [sessionInterval, setSessionInterval] = useState(null);
  const [spinnerVisible, setSpinnerVisible] = useState(false);

  // References for animation timers
  const spinnerTimerRef = useRef(null);
  const revealTimerRef = useRef(null);

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
      // Don't automatically start the game - wait for user to press Start
    });
    
    wsRef.current.onMessage((data) => {
      console.log('Received game data:', data);
      
      // Handle heartbeat ping from server
      if (data.type === 'ping') {
        // Respond with pong to maintain connection
        wsRef.current.send({ type: 'pong' });
        return;
      }
      
      if (data.message) {
        setGameState(prevState => ({
          ...prevState,
          message: data.message
        }));
      }
      
      // Handle different message types
      if (data.type === 'game_start') {
        handleGameSetup(data.game_data);
      } else if (data.type === 'game_setup') {
        // Handle next round setup - same as game start
        handleGameSetup(data.setup);
      } else if (data.type === 'game_result') {
        handleGameResult(data.result);
      } else if (data.type === 'error') {
        setError(data.message);
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
    
    // Clean up WebSocket connection and timers on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
      
      // Clear all timers
      if (countdownInterval) clearInterval(countdownInterval);
      if (sessionInterval) clearInterval(sessionInterval);
      if (spinnerTimerRef.current) clearTimeout(spinnerTimerRef.current);
      if (revealTimerRef.current) clearTimeout(revealTimerRef.current);
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
    // Only allow selection if we're in the QUESTION phase
    if (gameState.gamePhase !== 'QUESTION') return;
    
    setGameState(prevState => ({
      ...prevState,
      selectedOption: optionIndex
    }));
    
    // Clear the countdown timer since we've made a selection
    if (countdownInterval) clearInterval(countdownInterval);
    
    // Submit the answer immediately
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
    // If we're in game mode, use the game data
    if (gameState.setup?.data) {
      const setupData = gameState.setup.data;
      const dates = setupData.map(point => point.date);
      const prices = setupData.map(point => point.close);
      
      return {
        labels: dates,
        datasets: [
          {
            label: `${gameState.setup.instrument || 'Price'} Chart`,
            data: prices,
            borderColor: '#00ffff',
            backgroundColor: 'rgba(0, 255, 255, 0.1)',
            tension: 0.2,
            yAxisID: 'y',
            pointRadius: 0,
            borderWidth: 2,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: '#ff007f',
            pointHoverBorderColor: '#ffffff',
            pointHoverBorderWidth: 2,
          }
        ]
      };
    }
    
    // Fallback to market data for testing
    if (marketData) {
      const { dates, close } = marketData;
      
      return {
        labels: dates,
        datasets: [
          {
            label: `${selectedSymbol} Price`,
            data: close,
            borderColor: '#00ffff',
            backgroundColor: 'rgba(0, 255, 255, 0.1)',
            tension: 0.2,
            yAxisID: 'y',
            pointRadius: 0,
            borderWidth: 2,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: '#ff007f',
            pointHoverBorderColor: '#ffffff',
            pointHoverBorderWidth: 2,
          }
        ]
      };
    }
    
    // Empty data if nothing available
    return {
      labels: [],
      datasets: []
    };
  };
  
  const chartData = buildChartData();
  
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#ffffff',
          font: {
            family: 'Orbitron',
            size: 12,
            weight: 600
          },
          usePointStyle: true,
          pointStyle: 'circle'
        }
      },
      title: {
        display: true,
        text: gameState.setup?.instrument ? `${gameState.setup.instrument} Price Chart` : 'AlphaWave Chart',
        color: '#00ffff',
        font: {
          family: 'Orbitron',
          size: 16,
          weight: 700
        }
      },
      tooltip: {
        backgroundColor: 'rgba(15, 15, 25, 0.95)',
        titleColor: '#00ffff',
        bodyColor: '#ffffff',
        borderColor: '#00ffff',
        borderWidth: 1,
        cornerRadius: 8,
        titleFont: {
          family: 'Orbitron',
          size: 12,
          weight: 600
        },
        bodyFont: {
          family: 'Exo 2',
          size: 11
        },
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
          text: 'Time',
          color: '#b0b0b0',
          font: {
            family: 'Orbitron',
            size: 12,
            weight: 600
          }
        },
        ticks: {
          display: false,
          color: '#b0b0b0',
          font: {
            family: 'Exo 2',
            size: 10
          }
        },
        grid: {
          color: 'rgba(0, 255, 255, 0.1)',
          lineWidth: 1
        },
        border: {
          color: 'rgba(0, 255, 255, 0.3)'
        }
      },
      y: {
        display: true,
        position: 'left',
        title: {
          display: true,
          text: 'Price',
          color: '#b0b0b0',
          font: {
            family: 'Orbitron',
            size: 12,
            weight: 600
          }
        },
        ticks: {
          color: '#b0b0b0',
          font: {
            family: 'Exo 2',
            size: 10
          }
        },
        grid: {
          color: 'rgba(0, 255, 255, 0.1)',
          lineWidth: 1
        },
        border: {
          color: 'rgba(0, 255, 255, 0.3)'
        }
      }
    }
  };
  
  // Handler for game setup message
  const handleGameSetup = (setup) => {
    // Clear any existing timers
    if (countdownInterval) clearInterval(countdownInterval);
    if (sessionInterval) clearInterval(sessionInterval);
    if (spinnerTimerRef.current) clearTimeout(spinnerTimerRef.current);
    if (revealTimerRef.current) clearTimeout(revealTimerRef.current);
    
    // Start with loading phase - show spinner for 5 seconds
    setGameState(prevState => ({
      ...prevState,
      setup: setup.setup,
      options: setup.options,
      overlays: setup.overlays,
      selectedOption: null,
      gamePhase: 'LOADING',
      countdownTime: 20,
      message: 'Preparing chart data...'
    }));
    
    setSpinnerVisible(true);
    
    // After 5 seconds, transition to question phase
    spinnerTimerRef.current = setTimeout(() => {
      setSpinnerVisible(false);
      setGameState(prevState => ({
        ...prevState,
        gamePhase: 'QUESTION',
        message: 'Select the most likely continuation:'
      }));
      
      // Start the countdown timer
      startCountdownTimer();
      
      // If this is the first round, also start the session timer
      if (!sessionInterval) {
        startSessionTimer();
      }
    }, 5000);
  };
  
  // Handler for game result message
  const handleGameResult = (result) => {
    // Clear the countdown timer
    if (countdownInterval) clearInterval(countdownInterval);
    
    // Update game state with result
    setGameState(prevState => ({
      ...prevState,
      selectedOption: result.user_answer,
      score: result.score,
      lives: result.lives,
      streak: result.streak,
      round: result.round,
      gamePhase: 'REVEAL',
      message: result.is_correct ? 'Correct! Well done!' : 'Incorrect! Try again.',
    }));
    
    // Wait 3 seconds then either continue or end game
    revealTimerRef.current = setTimeout(() => {
      if (result.status === 'completed') {
        // Game over
        setGameState(prevState => ({
          ...prevState,
          gamePhase: 'GAME_OVER',
          message: 'Game Over! ' + (result.lives <= 0 ? 'You ran out of lives.' : 'Time is up.')
        }));
      } else {
        // Request next round
        if (wsRef.current) {
          wsRef.current.send({ action: 'next_round' });
        }
      }
    }, 3000);
  };
  
  // Start countdown timer for each question
  const startCountdownTimer = () => {
    // Clear any existing countdown
    if (countdownInterval) clearInterval(countdownInterval);
    
    // Set initial countdown time
    setGameState(prevState => ({
      ...prevState,
      countdownTime: 20
    }));
    
    // Create countdown interval
    const interval = setInterval(() => {
      setGameState(prevState => {
        const newTime = prevState.countdownTime - 1;
        
        // If time runs out, submit the current answer (or -1 if none selected)
        if (newTime <= 0) {
          clearInterval(interval);
          const answerToSubmit = prevState.selectedOption === null ? -1 : prevState.selectedOption;
          if (wsRef.current) {
            wsRef.current.send({
              action: 'submit_answer',
              answer: answerToSubmit
            });
          }
          return {
            ...prevState,
            countdownTime: 0
          };
        }
        
        return {
          ...prevState,
          countdownTime: newTime
        };
      });
    }, 1000);
    
    setCountdownInterval(interval);
  };
  
  // Start session timer (5 minutes)
  const startSessionTimer = () => {
    // Clear any existing session timer
    if (sessionInterval) clearInterval(sessionInterval);
    
    // Set initial session time (5 minutes = 300 seconds)
    setGameState(prevState => ({
      ...prevState,
      sessionTimeRemaining: 300
    }));
    
    // Create session timer interval
    const interval = setInterval(() => {
      setGameState(prevState => {
        const newTime = prevState.sessionTimeRemaining - 1;
        
        // If session time runs out, end the game
        if (newTime <= 0) {
          clearInterval(interval);
          // The game will end on the next result
          return {
            ...prevState,
            sessionTimeRemaining: 0
          };
        }
        
        return {
          ...prevState,
          sessionTimeRemaining: newTime
        };
      });
    }, 1000);
    
    setSessionInterval(interval);
  };

  // Handler for start game button
  const handleStartGame = () => {
    if (wsRef.current) {
      wsRef.current.send({ action: 'start_game' });
      setGameState(prevState => ({
        ...prevState,
        gamePhase: 'LOADING',
        message: 'Starting game...'
      }));
    }
  };
  
  // Format timer display
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  return (
    <div className="game-container">
      <div className="game-header">
        <h1>GuessTrade Game</h1>
        
        {/* Game HUD with lives, score, streak, and timers */}
        <div className="game-hud">
          <div className="score">Score: {gameState.score}</div>
          <div className="lives">Lives: {'♥'.repeat(gameState.lives)}</div>
          {gameState.streak > 0 && <div className="streak">Streak: {gameState.streak}</div>}
          {gameState.gamePhase !== 'INIT' && gameState.gamePhase !== 'GAME_OVER' && (
            <div className="timers">
              <div className="countdown">Time: {gameState.countdownTime}s</div>
              <div className="session-timer">Session: {formatTime(gameState.sessionTimeRemaining)}</div>
            </div>
          )}
        </div>
        
        <div className={`connection-status ${websocketConnected ? 'connected' : 'disconnected'}`}>
          {websocketConnected ? 'Connected' : 'Disconnected'}
        </div>
      </div>
      
      {/* Game content based on current phase */}
      <div className="game-content">
        {/* INIT phase - show start button */}
        {gameState.gamePhase === 'INIT' && (
          <div className="init-screen">
            <h2>Welcome to GuessTrade</h2>
            <p>Predict the price action continuation from the options below!</p>
            <button 
              className="start-button"
              onClick={handleStartGame}
              disabled={!websocketConnected}
            >
              Start Game
            </button>
          </div>
        )}
        
        {/* LOADING phase - show spinner */}
        {gameState.gamePhase === 'LOADING' && (
          <div className="loading-screen">
            <div className="spinner"></div>
            <div className="loading-message">{gameState.message}</div>
          </div>
        )}
        
        {/* QUESTION and REVEAL phases - show chart and options */}
        {(gameState.gamePhase === 'QUESTION' || gameState.gamePhase === 'REVEAL') && (
          <>
            {/* Display the frozen chart segment */}
            <div className="chart-container main-chart">
              {isLoading ? (
                <div className="loading-message">Loading data...</div>
              ) : error ? (
                <div className="error-message">{error}</div>
              ) : gameState.setup ? (
                <Line data={chartData} options={chartOptions} />
              ) : (
                <div className="loading-message">{gameState.message}</div>
              )}
            </div>
            
            {/* Show message */}
            <div className="game-message">{gameState.message}</div>
            
            {/* Display option charts */}
            <div className="options-container">
              {['A', 'B', 'C', 'D'].map((letter, index) => {
                const isSelected = gameState.selectedOption === index;
                const isCorrect = gameState.gamePhase === 'REVEAL' && 
                  index === gameState.options.findIndex(option => option.correct);
                
                let optionClass = 'option';
                if (gameState.gamePhase === 'REVEAL') {
                  if (isCorrect) optionClass += ' correct';
                  else if (isSelected) optionClass += ' incorrect';
                  else optionClass += ' faded';
                } else if (isSelected) {
                  optionClass += ' selected';
                }
                
                return (
                  <div 
                    key={index}
                    className={optionClass}
                    onClick={() => handleOptionSelect(index)}
                  >
                    <div className="option-label">{letter}</div>
                    {gameState.options[index] && gameState.setup?.data && (
                      <OptionChart 
                        mainData={gameState.setup.data}
                        optionData={gameState.options[index].data}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
        
        {/* GAME_OVER phase */}
        {gameState.gamePhase === 'GAME_OVER' && (
          <div className="game-over-screen">
            <h2>Game Over</h2>
            <p>{gameState.message}</p>
            <div className="final-score">Final Score: {gameState.score}</div>
            <button 
              className="restart-button"
              onClick={handleStartGame}
              disabled={!websocketConnected}
            >
              Play Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Game;