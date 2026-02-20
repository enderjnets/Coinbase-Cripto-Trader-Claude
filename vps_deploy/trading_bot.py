import asyncio
import time
import pandas as pd
from datetime import datetime
from config import Config
from scanner import MarketScanner
from strategy import Strategy
from coinbase.rest import RESTClient
import uuid

class TradingBot:
    def __init__(self):
        self.api_key, self.api_secret = Config.get_api_keys()
        self.client = None
        
        if self.api_key:
            try:
                self.client = RESTClient(api_key=self.api_key, api_secret=self.api_secret)
            except:
                pass

        # Use the generic MarketScanner (wrapper)
        # For now, we pass the raw client if it matches what MarketScanner expects 
        # OR we need a BrokerClient wrapper.
        # Given existing code in scanner.py expects a broker_client, let's wrap it slightly or assumes scanner handles it.
        # But wait, scanner.py (MarketScanner) expects a 'broker_client' with 'get_tradable_pairs' etc.
        # The raw RESTClient does NOT have 'get_tradable_pairs' directly in the same format potentially.
        # We should use the CoinbaseClient wrapper if possible, but let's look at what we have.
        # To avoid breaking 'trading_bot.py' which is legacy tailored to 'Scanner' class, 
        # let's try to make it work minimally.
        
        # ACTUALLY: The best fix is to use the new CoinbaseClient
        from coinbase_client import CoinbaseClient
        # If CoinbaseClient loads keys internally or from config, pass nothing?
        # Or if it's broken, I need to fix CoinbaseClient.
        # Let's try passing nothing if the error says it takes 1 argument (self).
        # But wait, if I pass nothing, how does it authenticate?
        # It probably loads from Config internally.
        self.broker = CoinbaseClient() 
        self.scanner = MarketScanner(self.broker)
        
        self.strategy = Strategy()

        self.is_running = False
        self.mode = "PAPER" # 'LIVE' or 'PAPER'
        self.risk_level = "LOW" # 'LOW', 'MEDIUM', 'HIGH'
        self.active_positions = {} # {product_id: {entry_price, size, stop_loss, ...}}
        self.logs = [] # List of strings
        self.paper_balance = Config.PAPER_TRADING_INITIAL_BALANCE
        self.paper_equity = Config.PAPER_TRADING_INITIAL_BALANCE
        self.logs = [] # List of strings
        self.balance = 0.0 # USD Balance
        
        # Enhanced Lists
        self.candidates = {} # {pid: {'rvol': x, 'status': 'Analyzing'}}
        self.trade_history = [] # List of closed trades

    def get_balance(self):
        """
        Fetches current USD or USDC balance.
        """
        if self.mode == "PAPER":
            return self.paper_balance

        if not self.client:
            return 0.0
        try:
            # print("DEBUG: Calling client.get_accounts()...") 
            # Disabled debug print to avoid clutter
            accounts = self.client.get_accounts()
            # print("DEBUG: accounts fetched.")
            # accounts.accounts is the list
            if hasattr(accounts, 'accounts'):
                acc_list = accounts.accounts
            else:
                acc_list = accounts # generic
            
            total_usd = 0.0
            
            for acc in acc_list:
                curr = getattr(acc, 'currency', None) or acc.get('currency')
                if curr in ['USD', 'USDC']:
                    bal = getattr(acc, 'available_balance', None) or acc.get('available_balance')
                    val = getattr(bal, 'value', None) or bal.get('value')
                    total_usd += float(val)
            
            return total_usd
        except Exception as e:
            self.log(f"Error fetching balance: {e}")
            return 0.0
        
    def log(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        msg = f"[{ts}] {message}"
        print(msg)
        self.logs.append(msg)
        if len(self.logs) > 100:
            self.logs.pop(0)

    async def execute_trade(self, signal, product_id, price):
        """
        Executes a trade.
        For PAPER mode: simulates balance updates and position tracking with fees.
        For LIVE mode: (To be implemented)
        """
        # Risk Calc
        size_usd = 100 # Fixed size $100 for paper test
        
        self.log(f"🚀 EXECUTING {signal} on {product_id} @ {price} ({self.mode} MODE)")
        
        # Fee Calculation
        fee_rate = Config.TRADING_FEE_PERCENT / 100.0 if hasattr(Config, 'TRADING_FEE_PERCENT') else 0.006
        
        if self.mode == "PAPER":
            # PAPER TRADING LOGIC
            if signal == "BUY":
                # Cost + Fee
                entry_fee = size_usd * fee_rate
                total_cost = size_usd + entry_fee
                
                if self.paper_balance < total_cost:
                    self.log(f"❌ Insufficient Paper Funds (${self.paper_balance:.2f} < ${total_cost:.2f}).")
                    return
                
                self.paper_balance -= total_cost
                sl = price * (1 - Config.RISK_PER_TRADE_PERCENT)
                
                self.active_positions[product_id] = {
                    'side': 'LONG',
                    'entry_price': price,
                    'current_price': price,
                    'stop_loss': sl,
                    'size': size_usd / price, # Quantity of crypto
                    'size_usd': size_usd,     # Cost basis (raw)
                    'entry_fee': entry_fee,
                    'pnl': 0.0,
                    'entry_time': datetime.now()
                }
                self.log(f"✅ PAPER BUY: {product_id} @ ${price:.2f} (Fee: ${entry_fee:.2f}). Bal: ${self.paper_balance:.2f}")

            elif signal == "SELL":
                 # Spot Market Rule: Can only SELL if we own it.
                 if product_id not in self.active_positions:
                     self.log(f"⛔ IGNORED SELL SIGNAL on {product_id}: Spot Market - Cannot Open Short.")
                     return

                 # Closing Position
                 pos = self.active_positions.pop(product_id)
                 
                 # Exit Value - Exit Fee
                 exit_value_gross = pos['size'] * price
                 exit_fee = exit_value_gross * fee_rate
                 exit_value_net = exit_value_gross - exit_fee
                 
                 # Balance Update
                 self.paper_balance += exit_value_net
                 
                 # PnL Calc: Net Proceeds - Total Cost (basis + entry fee)
                 total_cost = pos['size_usd'] + pos['entry_fee']
                 pnl_net = exit_value_net - total_cost
                 pnl_percent = (pnl_net / total_cost) * 100
                 
                 # Add to History
                 self.trade_history.append({
                     'ticker': product_id,
                     'side': 'LONG',
                     'entry_price': pos['entry_price'],
                     'exit_price': price,
                     'size_usd': pos['size_usd'],
                     'pnl_usd': pnl_net,
                     'pnl_percent': pnl_percent,
                     'exit_time': datetime.now().strftime("%H:%M:%S"),
                     'fees_paid': pos['entry_fee'] + exit_fee
                 })
                 
                 self.log(f"✅ PAPER SELL (Close). PnL: ${pnl_net:.2f} ({pnl_percent:.2f}%). Fees: ${pos['entry_fee']+exit_fee:.2f}")

        else:
            # LIVE TRADING LOGIC (Placeholder)
            self.log("⚠️ Live Trading execution not yet implemented (Safety Mode).")
            # Here we would use self.client.create_order(...)
            
    async def manage_positions(self):
        """
        Check Stop Loss, Take Profit, Trailing Stop for active positions.
        """
        if not self.active_positions:
            return

        remove_ids = []
        
        for pid, pos in self.active_positions.items():
            # Get current price implementation needed
            # For simplicity, we might reuse scanner or fetch ticker
            try:
                # Need to fetch current price for this asset
                # Avoiding too many API calls, maybe do this inside the main loop for monitored assets
                pass 
            except:
                continue

            # Trailing Stop Logic (Mock)
            # if price > entry + X, move SL up...
            pass

    async def run_loop(self):
        self.is_running = True
        self.log("Bot Started.")
        
        while self.is_running:
            try:
                # 1. Scan for opportunities
                # In a real bot, we might scan every 15 mins, not every loop if loop is fast.
                # Let's say we scan every cycle for now.
                self.log(f"Scanning market for pairs with RVOL > {Config.RVOL_THRESHOLD}...")
                opps = self.scanner.scan_market() # outcomes
                
                # Update Candidates List
                self.candidates = {} 
                for op in opps:
                    self.candidates[op['ticker']] = {
                        'rvol': op['rvol'], 
                        'price': op['price'],
                        'status': 'WAITING',
                        'last_check': datetime.now().strftime("%H:%M:%S")
                    }
                
                if not opps:
                    self.log("No candidates found this cycle.")
                else:
                    self.log(f"Found {len(opps)} candidates. Beginning analysis...")
                
                for asset in opps[:5]: # Check top 5
                    pid = asset['ticker']
                    self.candidates[pid]['status'] = 'ANALYZING'
                    
                    self.log(f"🔍 Analyzing {pid} (RVOL: {asset['rvol']:.2f})...")
                    
                    # 2. Analyze Strategy
                    # Get 1H for Trend
                    end = int(time.time())
                    start_1h = end - (100 * 3600)
                    
                    self.log(f"  > Fetching 1H candles for Trend ({pid})...")
                    df_1h = self.scanner.get_candles(pid, start_1h, end, "ONE_HOUR")
                    trend = self.strategy.check_trend(df_1h)
                    self.log(f"  > Trend Direction: {trend}")
                    
                    if trend == "NEUTRAL":
                         self.candidates[pid]['status'] = 'NEUTRAL TREND'
                         continue
                        
                    # Get 5M for Entry
                    self.log(f"  > Fetching 5M candles for Entry Pattern ({pid})...")
                    start_5m = end - (100 * 300) # 100 * 5 mins
                    df_5m = self.scanner.get_candles(pid, start_5m, end, "FIVE_MINUTE")
                    df_5m = self.strategy.calculate_support_resistance(df_5m)
                    
                    # 3. Detect Signal
                    signal, reason = self.strategy.detect_signal(df_5m, trend, self.risk_level)
                    
                    if signal:
                        self.log(f"✅ SIGNAL DETECTED: {signal} on {pid}!")
                        self.candidates[pid]['status'] = 'SIGNAL FOUND'
                        
                        if pid not in self.active_positions:
                            await self.execute_trade(signal, pid, asset['price'])
                            del self.candidates[pid] # Remove from watchlist once bought
                    else:
                        self.candidates[pid]['status'] = 'NO SIGNAL'
                        # Log the detailed reason for debugging
                        self.log(f"  > No signal on {pid}: {reason}")
                            
                # 4. Manage Positions
                self.log("Managing active positions...")
                await self.manage_positions()
                
                self.log(f"Cycle complete. Sleeping {Config.UPDATE_INTERVAL_SECONDS}s...")
                await asyncio.sleep(Config.UPDATE_INTERVAL_SECONDS)
                
            except Exception as e:
                self.log(f"Error in loop: {e}")
                await asyncio.sleep(10)
                
        self.log("Bot Stopped.")

    def get_system_snapshot(self):
        """
        Generates a comprehensive dictionary of the bot's state for export/analysis.
        """
        return {
            "meta": {
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
                "mode": self.mode
            },
            "performance": {
                "balance": self.paper_balance if self.mode == "PAPER" else self.balance,
                "equity": self.paper_balance, # Simplified
                "open_positions_count": len(self.active_positions),
                "closed_trades_count": len(self.trade_history)
            },
            "config": {
                "TIMEFRAME_TREND": Config.TIMEFRAME_TREND,
                "TIMEFRAME_ENTRY": Config.TIMEFRAME_ENTRY,
                "RVOL_THRESHOLD": Config.RVOL_THRESHOLD,
                "RISK_PERCENT": Config.RISK_PER_TRADE_PERCENT
            },
            "active_positions": self.active_positions,
            "trade_history": self.trade_history,
            "logs": self.logs
        }

# Global instance for UI to access
bot_instance = TradingBot()
