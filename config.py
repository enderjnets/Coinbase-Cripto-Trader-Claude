import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    # API Key Configuration
    # Prioritize Environment Variables, then JSON file
    API_KEY_FILE = "cdp_api_key.json"
    
    @staticmethod
    def get_api_keys():
        """
        Retrieves API Key and Secret.
        Tries to load from 'cdp_api_key.json' first (standard CDP download format),
        then falls back to environment variables.
        """
        api_key_name = os.getenv("COINBASE_API_KEY_NAME")
        api_key_private_key = os.getenv("COINBASE_API_KEY_PRIVATE_KEY")

        if api_key_name and api_key_private_key:
            # Handle private key formatting if loaded from env var (newlines)
            return api_key_name, api_key_private_key.replace('\\n', '\n')

        # Try loading from JSON file
        if os.path.exists(Config.API_KEY_FILE):
            try:
                with open(Config.API_KEY_FILE, 'r') as f:
                    data = json.load(f)
                    # CDP JSON format usually has 'name' and 'privateKey'
                    return data.get('name'), data.get('privateKey')
            except Exception as e:
                print(f"Error loading {Config.API_KEY_FILE}: {e}")
        
        return None, None

    # Trading Strategy Settings
    TIMEFRAME_TREND = "1h"       # 1 Hour for trend direction
    TIMEFRAME_ENTRY = "5m"       # 5 or 15 min for entry
    
    # Scanner Settings
    RVOL_THRESHOLD = 2.0         # Minimum Relative Volume to consider
    MIN_VOLUME_USD = 1000000     # Minimum 24h Volume to filter low cap trash

    # Risk Management
    RISK_PER_TRADE_PERCENT = 0.01  # 1% of equity
    TRAILING_STOP_PERCENT = 0.015  # 1.5% trailing stop
    
    # Bot Settings
    UPDATE_INTERVAL_SECONDS = 60 # Main loop interval
    
    # Paper Trading
    PAPER_TRADING_INITIAL_BALANCE = 10000.0 # USD
    TRADING_FEE_PERCENT = 0.6 # Coinbase Advanced Taker Fee (approx)

    # Backtester Settings
    TRADING_FEE_MAKER = 0.4    # Maker fee % (used by numba_backtester)
    INITIAL_BALANCE = 10000.0  # Starting balance for backtests
