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
  
  // Initialize WebSocket connection
  useEffect(() => {
    // Use the window location to determine the WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
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
  
  // This is a placeholder for chart data, in a real implementation
  // we would format the data from the backend properly
  const chartData = {
    labels: ['Label 1', 'Label 2', 'Label 3', 'Label 4', 'Label 5'],
    datasets: [
      {
        label: 'Setup Chart',
        data: [12, 19, 3, 5, 2],
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1
      }
    ]
  };
  
  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Chart Pattern Game',
      },
    },
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
      
      <div className="chart-container">
        {gameState.setup ? (
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
      
      {/* For milestone 1, let's add a test button to send messages to the server */}
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