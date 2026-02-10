import pandas as pd
import time
from config import Config
from coinbase.rest import RESTClient
from broker_client import BrokerClient

class CoinbaseClient(BrokerClient):
    """
    Concrete implementation/adapter for Coinbase Advanced Trade API.
    Replaces/Wraps previous logic from 'Scanner' class.
    """
    
    def __init__(self):
        self.api_key, self.api_secret = Config.get_api_keys()
        self.client = None
        
    def authenticate(self) -> bool:
        """
        Initializes the RESTClient. 
        Coinbase uses API Key/Secret, so 'auth' is just client instantiation.
        """
        if self.api_key and self.api_secret:
            try:
                self.client = RESTClient(api_key=self.api_key, api_secret=self.api_secret)
                return True
            except Exception as e:
                print(f"Coinbase Auth Failed: {e}")
                return False
        return False

    def get_historical_data(self, symbol: str, granularity: str, start_ts: int, end_ts: int) -> pd.DataFrame:
        if not self.client: 
            if not self.authenticate(): return None

        try:
            # Map simplified granularity names to Coinbase strings if needed
            # Assuming 'granularity' passed here is "ONE_HOUR" etc as used in backtester
            
            candles_response = self.client.get_candles(
                product_id=symbol,
                start=start_ts,
                end=end_ts,
                granularity=granularity
            )
            
            # SDK response handling (Object or Dict)
            if hasattr(candles_response, 'candles'):
                candles = candles_response.candles
            else:
                candles = candles_response

            data = []
            for c in candles:
                # Safe attribute access
                start = getattr(c, 'start', None) or c.get('start')
                o = getattr(c, 'open', None) or c.get('open')
                h = getattr(c, 'high', None) or c.get('high')
                l = getattr(c, 'low', None) or c.get('low')
                cl = getattr(c, 'close', None) or c.get('close')
                v = getattr(c, 'volume', None) or c.get('volume')
                
                data.append({
                    'timestamp': start,
                    'open': float(o),
                    'high': float(h),
                    'low': float(l),
                    'close': float(cl),
                    'volume': float(v)
                })
            
            df = pd.DataFrame(data)
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df = df.sort_values('timestamp')
            
            return df

        except Exception as e:
            print(f"Coinbase Get Candles Error: {e}")
            return None

    def get_current_price(self, symbol: str) -> float:
        if not self.client: self.authenticate()
        try:
            # Get latest trade or quote
            # get_product returns 'price' usually
            product = self.client.get_product(product_id=symbol)
            if hasattr(product, 'price'):
                 return float(product.price)
            return 0.0
        except Exception as e:
            print(f"Error getting price for {symbol}: {e}")
            return 0.0

    def get_account_balance(self) -> dict:
        if not self.client: self.authenticate()
        balances = {}
        try:
            accounts_response = self.client.get_accounts()
            # SDK structure
            if hasattr(accounts_response, 'accounts'):
                acc_list = accounts_response.accounts
            else:
                acc_list = accounts_response
                
            for acc in acc_list:
                currency = getattr(acc, 'currency', None) or acc.get('currency')
                avail = getattr(acc, 'available_balance', None) or acc.get('available_balance')
                # avail might be object {value, currency}
                val = getattr(avail, 'value', 0.0) if hasattr(avail, 'value') else avail.get('value', 0.0)
                balances[currency] = float(val)
                
            return balances
        except Exception as e:
            print(f"Error fetching balances: {e}")
            return {}

    def get_tradable_symbols(self) -> list:
        """Returns list of USD tradable pairs"""
        if not self.client: self.authenticate()
        tradable = []
        try:
            products = self.client.get_products()
            if hasattr(products, 'products'):
                p_list = products.products
            else:
                p_list = products
                
            for p in p_list:
                pid = getattr(p, 'product_id', None) or p.get('product_id')
                status = getattr(p, 'status', None) or p.get('status')
                quote = getattr(p, 'quote_currency_id', None) or p.get('quote_currency_id')
                
                if quote == "USD" and status == "online":
                    tradable.append(pid)
            return tradable
        except Exception:
            return []
