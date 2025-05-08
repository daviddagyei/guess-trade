class WebSocketService {
  constructor(url) {
    this.url = url;
    this.socket = null;
    this.onMessageCallback = null;
    this.onConnectCallback = null;
    this.onDisconnectCallback = null;
  }

  connect() {
    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      console.log('WebSocket connected');
      if (this.onConnectCallback) {
        this.onConnectCallback();
      }
    };

    this.socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket message received:', data);
      if (this.onMessageCallback) {
        this.onMessageCallback(data);
      }
    };

    this.socket.onclose = () => {
      console.log('WebSocket disconnected');
      if (this.onDisconnectCallback) {
        this.onDisconnectCallback();
      }
      // Attempt to reconnect after a delay
      setTimeout(() => this.connect(), 2000);
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  send(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  onMessage(callback) {
    this.onMessageCallback = callback;
  }

  onConnect(callback) {
    this.onConnectCallback = callback;
  }

  onDisconnect(callback) {
    this.onDisconnectCallback = callback;
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
    }
  }
}

export default WebSocketService;