from broker_client import BrokerClient
import time

class SchwabClient(BrokerClient):
    def __init__(self, api_key, api_secret):
        super().__init__(api_key, api_secret)
        self.name = "Charles Schwab"
        print(f"[{self.name}] Client Initialized (MOCK MODE)")

    def authenticate(self):
        """
        Authenticate with Schwab API.
        """
        print(f"[{self.name}] Authenticated Successfully.")
        return True

    def get_account_balance(self):
        """
        Fetch account balance.
        """
        # Mock response: $1000 Account
        return {"cash": 1000.0, "buying_power": 4000.0} # 4:1 margin for Day Trading

    def get_historical_data(self, symbol, timeframe, start_date, end_date):
        """
        Fetch historical candle data.
        """
        # Mock response for now
        print(f"Mocking historical data for {symbol}")
        # Return a basic DataFrame structure
        import pandas as pd
        import numpy as np
        dates = pd.date_range(start=start_date, end=end_date, freq='1min') # Mock 1min data
        df = pd.DataFrame(index=dates)
        df['open'] = np.random.uniform(1, 5, size=len(dates))
        df['high'] = df['open'] * 1.01
        df['low'] = df['open'] * 0.99
        df['close'] = np.random.uniform(df['low'], df['high'])
        df['volume'] = np.random.randint(1000, 50000, size=len(dates))
        return df

    def get_current_price(self, symbol):
        """
        Get the current price (Last Trade or Mark).
        """
        # Mock
        import random
        return random.uniform(1.0, 5.0)

    def get_quotes(self, symbols):
        """
        Get Level 1 Data (Bid/Ask/Last) for a list of symbols.
        Crucial for 'Fishing' strategy to place orders relative to Bid.
        """
        quotes = {}
        for sym in symbols:
            # Mock data representing wide spreads common in pre-market
            mid = self.get_current_price(sym)
            spread = mid * 0.02 # 2% spread
            # Randomize movement slightly to test 'Pegging'
            import random
            noise = random.uniform(-0.02, 0.02)
            
            quotes[sym] = {
                'bid': mid - (spread/2) + noise,
                'ask': mid + (spread/2) + noise,
                'last': mid + noise,
                'volume': 50000
            }
        return quotes

    def place_order(self, symbol, side, order_type, quantity, price=None, duration="DAY"):
        """
        Place an order.
        side: 'BUY' or 'SELL'
        order_type: 'MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT'
        duration: 'DAY', 'GTC', 'GTC_EXT' (Extended Hours)
        """
        import uuid
        order_id = str(uuid.uuid4())
        print(f"[{self.name}] Placing Order: {side} {quantity} {symbol} @ {price if price else 'MKT'} ({order_type}, {duration})")
        return {"id": order_id, "status": "WORKING"}

    def cancel_order(self, order_id):
        """
        Cancel an existing order.
        """
        print(f"[{self.name}] Cancelling Order: {order_id}")
        return {"status": "CANCELLED"}
