from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, List, Dict

class BrokerClient(ABC):
    """
    Abstract base class for all broker clients (Coinbase, Schwab, etc.)
    Defines the standard interface for valid actions.
    """

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticates with the broker API.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def get_historical_data(self, symbol: str, granularity: str, start_ts: int, end_ts: int) -> Optional[pd.DataFrame]:
        """
        Fetches historical candle data.
        Returns DataFrame with columns: timestamp, open, high, low, close, volume
        timestamp should be proper datetime objects.
        """
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        """Gets the current market price of a symbol."""
        pass

    @abstractmethod
    def get_account_balance(self) -> Dict[str, float]:
        """
        Gets account balances.
        Returns dict like {'USD': 1000.0, 'BTC': 0.5}
        """
        pass

    @abstractmethod
    def get_tradable_symbols(self) -> List[str]:
        """Returns a list of tradable symbols (e.g. ['BTC-USD', 'ETH-USD'] or ['AAPL', 'TSLA'])"""
        pass
