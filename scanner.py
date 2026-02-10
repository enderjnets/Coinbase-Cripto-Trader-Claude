import pandas as pd
import time
import asyncio
from datetime import datetime, timedelta
from config import Config
import pandas as pd
import time
from config import Config

class MarketScanner:
    """
    Generic Market Scanner.
    Works with any implementation of BrokerClient.
    """
    def __init__(self, broker_client):
        self.broker = broker_client

    def get_tradable_pairs(self):
        """
        Delegates to broker to get list of tradable assets.
        For Coinbase: USD pairs.
        For Schwab: Penny Stock watchlist or screener results.
        """
        if not self.broker:
            return []
        return self.broker.get_tradable_symbols()

    def get_candles(self, symbol, start, end, granularity):
        """
        Delegates to broker.
        """
        if not self.broker:
            return None
        return self.broker.get_historical_data(symbol, granularity, start, end)

    def calculate_rvol(self, df):
        """
        Calculates Relative Volume.
        RVOL = Current Volume (last closed candle) / Average Volume (last N candles)
        """
        if df is None or df.empty or len(df) < 20:
            return 0.0
            
        # Calculate Average Volume (e.g. SMA 20 or 24h equivalent)
        avg_vol = df['volume'].rolling(window=20).mean().iloc[-1]
        current_vol = df['volume'].iloc[-1]
        
        if avg_vol == 0:
            return 0.0
            
        rvol = current_vol / avg_vol
        return rvol

    def scan_market(self):
        """
        Scans the market for opportunities based on RVOL and Volume.
        """
        print("Starting Market Scan...")
        symbols = self.get_tradable_pairs()
        print(f"Scanning {len(symbols)} symbols...")
        
        results = []
        count = 0
        
        for pid in symbols:
            # Rate limit throttle mechanism could be moved to BrokerClient if needed
            time.sleep(0.1) 
            
            end_dt = int(time.time())
            start_dt = end_dt - (25 * 3600) # Last 25 hours
            
            # Using generic ONE_HOUR granularity
            # BrokerClient implementation must map this to specific API values
            df = self.get_candles(pid, start_dt, end_dt, "ONE_HOUR")
            
            if df is None or df.empty:
                continue
                
            # Filter by 24h volume USD/Value (approx)
            total_vol_24h = (df['volume'] * df['close']).sum() 
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
            if count >= 30: # Limit scan for testing/performance
                break
                
        # Sort by RVOL desc
        results.sort(key=lambda x: x['rvol'], reverse=True)
        return results

if __name__ == "__main__":
    scanner = Scanner()
    opps = scanner.scan_market()
    print("Scan Results:", opps)
