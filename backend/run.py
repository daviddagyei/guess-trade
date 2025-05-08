import uvicorn
import argparse
from app.main import app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the GuessTradeAPI server')
    parser.add_argument('--port', type=int, default=8000, help='Port to run the server on')
    args = parser.parse_args()
    
    uvicorn.run("app.main:app", host="0.0.0.0", port=args.port, reload=True)