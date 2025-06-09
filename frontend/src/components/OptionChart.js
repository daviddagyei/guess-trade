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
  
  const fontFamily = `'TT Fellows Uni Width', 'Space Mono', monospace`;

  const chartData = {
    labels: dates,
    datasets: [
      {
        data: prices,
        borderColor: 'rgb(75, 192, 192)', // Match main chart color
        backgroundColor: 'rgba(75, 192, 192, 0.2)', // Match main chart fill
        tension: 0.1, // Match main chart smoothness
        pointRadius: 0,
        borderWidth: 2,
        pointHoverRadius: 0,
        fill: true,
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
        labels: {
          font: {
            family: fontFamily,
            size: 14
          }
        }
      },
      tooltip: {
        enabled: false,
        titleFont: {
          family: fontFamily,
          size: 14
        },
        bodyFont: {
          family: fontFamily,
          size: 13
        }
      },
    },
    interaction: {
      intersect: false,
      mode: 'index',
    },
    elements: {
      point: {
        hoverRadius: 0,
      }
    },
    scales: {
      x: {
        display: false,
        grid: {
          display: false,
        },
        ticks: {
          font: {
            family: fontFamily,
            size: 12
          }
        }
      },
      y: {
        display: false,
        grid: {
          display: false,
        },
        ticks: {
          font: {
            family: fontFamily,
            size: 12
          }
        }
      },
    },
    animation: {
      duration: 0, // Disable animations for better performance
    },
  };
  
  return (
    <div className="option-chart">
      <Line data={chartData} options={chartOptions} />
    </div>
  );
};

export default OptionChart;
