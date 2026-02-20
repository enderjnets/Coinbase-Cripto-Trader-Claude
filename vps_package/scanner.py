import pandas as pd
import time
import asyncio
from datetime import datetime, timedelta
from config import Config
from coinbase.rest import RESTClient

class Scanner:
    def __init__(self):
        self.api_key, self.api_secret = Config.get_api_keys()
        self.client = None
        if self.api_key and self.api_secret:
            try:
                self.client = RESTClient(api_key=self.api_key, api_secret=self.api_secret)
            except Exception as e:
                print(f"Failed to initialize RESTClient in Scanner: {e}")

    def get_tradable_pairs(self):
        """
        Fetches all pairs ending in USD that are online and not auction mode.
        """
        if not self.client:
            print("Scanner: No API Connection.")
            return []

        try:
            # fetch_products returns a generator or list
            products = self.client.get_products()
            tradable = []
            
            # The SDK response structure might vary, adapting to common object structure
            # usually products['products'] or iterating if it's a generator
            # Inspecting structure via simple iteration if object is iterable
            
            # Note: The official SDK usually returns an object with a 'products' attribute list
            # or simply a list of objects.
            
            # For coinbase-advanced-py or similar, we need to be careful.
            # We'll assume standard object access.
            if hasattr(products, 'products'):
                product_list = products.products
            else:
                product_list = products

            for p in product_list:
                # Check for USD pair, Status Online
                # p might be a dictionary or object. Safe access via getattr or dict get
                pid = getattr(p, 'product_id', None) or p.get('product_id')
                status = getattr(p, 'status', None) or p.get('status')
                quote = getattr(p, 'quote_currency_id', None) or p.get('quote_currency_id')
                
                if quote == "USD" and status == "online":
                    tradable.append(pid)
            
            return tradable

        except Exception as e:
            print(f"Error fetching products: {e}")
            return []

    def get_candles(self, product_id, start, end, granularity):
        """
        Fetches candles for calculation.
        Granularity: ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE, ONE_HOUR, SIX_HOUR, ONE_DAY
        """
        if not self.client:
            return None
        
        try:
            # granularity needs to be a specific string or enum for the API
            candles_response = self.client.get_candles(
                product_id=product_id,
                start=start,
                end=end,
                granularity=granularity
            )
            
            if hasattr(candles_response, 'candles'):
                 candles = candles_response.candles
            else:
                 candles = candles_response

            # Convert to DataFrame
            # Candle format: [start, low, high, open, close, volume]
            # Verify the object structure.
            # Assuming objects with attributes
            
            data = []
            for c in candles:
                # Safe attribute access
                start_ts = getattr(c, 'start', None) or c.get('start')
                open_p = getattr(c, 'open', None) or c.get('open')
                high_p = getattr(c, 'high', None) or c.get('high')
                low_p = getattr(c, 'low', None) or c.get('low')
                close_p = getattr(c, 'close', None) or c.get('close')
                vol = getattr(c, 'volume', None) or c.get('volume')
                
                data.append({
                    'timestamp': start_ts,
                    'open': float(open_p),
                    'high': float(high_p),
                    'low': float(low_p),
                    'close': float(close_p),
                    'volume': float(vol)
                })
            
            df = pd.DataFrame(data)
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df = df.sort_values('timestamp')
            
            return df

        except Exception as e:
            print(f"Error fetching candles for {product_id}: {e}")
            return None

    def calculate_rvol(self, df):
        """
        Calculates Relative Volume.
        RVOL = Current Volume (last closed candle) / Average Volume (last N candles)
        """
        if df is None or df.empty or len(df) < 20:
            return 0.0
            
        # Calculate Average Volume (e.g. SMA 20 or 24h equivalent)
        # Using 24 periods as proxy if hourly
        avg_vol = df['volume'].rolling(window=20).mean().iloc[-1]
        current_vol = df['volume'].iloc[-1]
        
        if avg_vol == 0:
            return 0.0
            
        rvol = current_vol / avg_vol
        return rvol

    def scan_market(self):
        """
        Main function to scan top assets.
        WARNING: Making too many requests might hit rate limits.
        We will limit to top assets or filter by volume first if possible.
        """
        print("Starting Scan...")
        pairs = self.get_tradable_pairs()
        print(f"Found {len(pairs)} USD pairs.")
        
        # Optimization: To avoid rate limits, maybe only check major ones or batch?
        # For this demo, let's take a subset or just traverse carefully.
        # Coinbase Advanced has rate limits (e.g. 10 req/s typically, varies).
        
        results = []
        
        # Limit to first 20 for testing speed and rate limits in this prototype
        # User wants "Scan actively", but we must be careful.
        # Ideally, we get 24h stats first to filter low volume coins.
        
        # Get 24h volume stats via get_product or market_trades?
        # get_best_bid_ask doesn't give volume.
        # get_products typically contains 24h volume? No, it's metadata.
        # We might need to iterate.
        
        count = 0
        for pid in pairs:
            # Rate limit throttle
            time.sleep(0.1) 
            
            # SKIP illiquid pairs? 
            # We can't easily check 24h volume without fetching it.
            # Let's try to fetch 1h candles (last 24) to estimate volume + RVOL.
            
            end_dt = int(time.time())
            start_dt = end_dt - (25 * 3600) # Last 25 hours
            
            df = self.get_candles(pid, start_dt, end_dt, "ONE_HOUR")
            
            if df is None or df.empty:
                continue
                
            # Filter by 24h volume USD
            total_vol_24h = (df['volume'] * df['close']).sum() # Approx
            if total_vol_24h < Config.MIN_VOLUME_USD:
                continue
                
            rvol = self.calculate_rvol(df)
            
            if rvol > Config.RVOL_THRESHOLD:
                print(f"Found Opportunity: {pid} | RVOL: {rvol:.2f}")
                results.append({
                    'ticker': pid,
                    'rvol': rvol,
                    'price': df['close'].iloc[-1],
                    'volume_24h': total_vol_24h
                })
            
            count += 1
            if count >= 30: # limit scan for now
                break
                
        # Sort by RVOL desc
        results.sort(key=lambda x: x['rvol'], reverse=True)
        return results

if __name__ == "__main__":
    scanner = Scanner()
    opps = scanner.scan_market()
    print("Scan Results:", opps)
