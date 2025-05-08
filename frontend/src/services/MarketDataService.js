/**
 * Service for fetching market data and technical indicators from the API
 */
class MarketDataService {
  constructor(baseUrl = 'http://localhost:8001') {
    this.baseUrl = baseUrl;
    this.apiBase = `${this.baseUrl}/game`;
  }

  /**
   * Get a list of available stock symbols
   * @returns {Promise<Array<string>>} List of stock symbols
   */
  async getStockSymbols() {
    try {
      const response = await fetch(`${this.apiBase}/market-data/stocks`);
      const data = await response.json();
      return data.symbols;
    } catch (error) {
      console.error('Error fetching stock symbols:', error);
      return [];
    }
  }

  /**
   * Get a list of available cryptocurrency symbols
   * @returns {Promise<Array<string>>} List of cryptocurrency symbols
   */
  async getCryptoSymbols() {
    try {
      const response = await fetch(`${this.apiBase}/market-data/crypto`);
      const data = await response.json();
      return data.symbols;
    } catch (error) {
      console.error('Error fetching crypto symbols:', error);
      return [];
    }
  }

  /**
   * Get market data for a specific stock
   * @param {string} symbol - Stock symbol (e.g., AAPL)
   * @returns {Promise<Object>} Market data for the stock
   */
  async getStockData(symbol) {
    try {
      const response = await fetch(`${this.apiBase}/market-data/stock/${symbol}`);
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching stock data for ${symbol}:`, error);
      throw error;
    }
  }

  /**
   * Get market data for a specific cryptocurrency
   * @param {string} symbol - Cryptocurrency symbol (e.g., BTC)
   * @returns {Promise<Object>} Market data for the cryptocurrency
   */
  async getCryptoData(symbol) {
    try {
      const response = await fetch(`${this.apiBase}/market-data/crypto/${symbol}`);
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching crypto data for ${symbol}:`, error);
      throw error;
    }
  }

  /**
   * Get technical indicators for a specific asset
   * @param {string} assetType - "stock" or "crypto"
   * @param {string} symbol - Asset symbol (e.g., AAPL, BTC)
   * @returns {Promise<Object>} Technical indicators
   */
  async getTechnicalIndicators(assetType, symbol) {
    try {
      const response = await fetch(`${this.apiBase}/indicators/${assetType}/${symbol}`);
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching technical indicators for ${assetType}:${symbol}:`, error);
      throw error;
    }
  }
}

export default MarketDataService;