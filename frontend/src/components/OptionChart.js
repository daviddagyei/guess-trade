import React from 'react';
import { Line } from 'react-chartjs-2';

/**
 * Renders a mini chart for a continuation option
 */
const OptionChart = ({ mainData, optionData }) => {
  if (!mainData || !optionData) {
    return <div className="option-preview-loading">Loading...</div>;
  }
  
  // Take the last few points from main data to create a smooth continuation
  const transitionPoints = 10; // Number of points to use for transition
  const startIndex = Math.max(0, mainData.length - transitionPoints);
  
  // Extract the date and close price for chart
  const mainDates = mainData.slice(startIndex).map(point => point.date);
  const mainPrices = mainData.slice(startIndex).map(point => point.close);
  
  const optionDates = optionData.map(point => point.date);
  const optionPrices = optionData.map(point => point.close);
  
  // Combine data for a smooth transition
  const dates = [...mainDates, ...optionDates];
  const prices = [...mainPrices, ...optionPrices];
  
  const chartData = {
    labels: dates,
    datasets: [
      {
        data: prices,
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.1,
        pointRadius: 0,
      }
    ]
  };
  
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        enabled: false,
      },
    },
    scales: {
      x: {
        display: false,
      },
      y: {
        display: false,
      }
    },
    elements: {
      point: {
        radius: 0,
      },
    },
  };
  
  return (
    <div className="option-chart">
      <Line data={chartData} options={chartOptions} />
    </div>
  );
};

export default OptionChart;
