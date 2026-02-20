import asyncio
import time
import pandas as pd
from datetime import datetime
from config import Config

# Wrapper para Coinbase que maneja errores
try:
    from coinbase.rest import RESTClient
    HAS_COINBASE = True
except ImportError:
    HAS_COINBASE = False
    RESTClient = None

try:
    from scanner import MarketScanner
except ImportError:
    MarketScanner = None

try:
    from strategy import Strategy
except ImportError:
    Strategy = None

try:
    from coinbase_client import CoinbaseClient
    HAS_COINBASE_CLIENT = True
except ImportError:
    HAS_COINBASE_CLIENT = False
    CoinbaseClient = None

try:
    from schwab_client import SchwabClient
    HAS_SCHWAB = True
except ImportError:
    SchwabClient = None
    HAS_SCHWAB = False

class TradingBot:
    def __init__(self, broker_type="PAPER"):
        self.broker_type = broker_type.upper()
        self.client = None
        self.broker = None
        
        # Initialize Broker (simplificado)
        if self.broker_type == "SCHWAB" and HAS_SCHWAB:
            try:
                self.broker = SchwabClient()
            except:
                self.broker = None
        elif HAS_COINBASE_CLIENT:
            try:
                self.broker = CoinbaseClient()
            except:
                self.broker = None
        
        # Client legacy (opcional)
        if HAS_COINBASE and Config.get_api_keys()[0]:
            try:
                api_key, api_secret = Config.get_api_keys()
                if api_key:
                    self.client = RESTClient(api_key=api_key, api_secret=api_secret)
            except:
                pass
        
        # Scanner y Strategy
        if MarketScanner:
            self.scanner = MarketScanner(self.broker)
        else:
            self.scanner = None
        
        if Strategy:
            self.strategy = Strategy()
        else:
            self.strategy = None
        
        # State
        self.last_trend = "WAITING"
        self.last_analysis_time = "-"
        self.last_price = 0.0
        self.is_running = False
        self.mode = "PAPER"
        self.risk_level = "LOW"
        self.active_positions = {}
        self.logs = []
        self.paper_balance = Config.PAPER_TRADING_INITIAL_BALANCE
        self.paper_equity = Config.PAPER_TRADING_INITIAL_BALANCE
        self.balance = 0.0
        self.candidates = {}
        self.trade_history = []
    
    def get_balance(self):
        if self.mode == "PAPER":
            return self.paper_balance
        
        if not self.client:
            return 0.0
        
        try:
            accounts = self.client.get_accounts()
            acc_list = getattr(accounts, 'accounts', accounts)
            total_usd = 0.0
            for acc in acc_list:
                curr = getattr(acc, 'currency', None) or acc.get('currency')
                if curr in ['USD', 'USDC']:
                    bal = getattr(acc, 'available_balance', None) or acc.get('available_balance')
                    val = getattr(bal, 'value', None) or bal.get('value')
                    total_usd += float(val)
            return total_usd
        except:
            return 0.0
    
    def log(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        msg = f"[{ts}] {message}"
        print(msg)
        self.logs.append(msg)
        if len(self.logs) > 100:
            self.logs.pop(0)
    
    async def execute_trade(self, signal, product_id, price):
        size_usd = 100
        fee_rate = Config.TRADING_FEE_PERCENT / 100.0 if hasattr(Config, 'TRADING_FEE_PERCENT') else 0.006
        
        self.log(f"🚀 {signal} on {product_id} @ {price} ({self.mode})")
        
        if self.mode == "PAPER":
            if signal == "BUY":
                entry_fee = size_usd * fee_rate
                total_cost = size_usd + entry_fee
                
                if self.paper_balance < total_cost:
                    self.log(f"❌ Insufficient Funds")
                    return
                
                self.paper_balance -= total_cost
                sl = price * (1 - Config.RISK_PER_TRADE_PERCENT)
                
                self.active_positions[product_id] = {
                    'side': 'LONG',
                    'entry_price': price,
                    'current_price': price,
                    'stop_loss': sl,
                    'size_usd': size_usd,
                    'entry_fee': entry_fee,
                    'pnl': 0,
                    'entry_time': datetime.now()
                }
                self.log(f"✅ BUY: {product_id} @ ${price:.2f}")
            
            elif signal == "SELL":
                if product_id not in self.active_positions:
                    return
                
                pos = self.active_positions.pop(product_id)
                exit_value_gross = pos['size_usd'] / pos['entry_price'] * price
                exit_fee = exit_value_gross * fee_rate
                self.paper_balance += exit_value_gross - exit_fee
                
                total_cost = pos['size_usd'] + pos['entry_fee']
                pnl_net = (exit_value_gross - exit_fee) - total_cost
                
                self.trade_history.append({
                    'ticker': product_id,
                    'pnl_usd': pnl_net,
                    'exit_time': datetime.now().strftime("%H:%M:%S")
                })
                self.log(f"SELL: {product_id} - PnL: ${pnl_net:.2f}")
    
    async def run_loop(self):
        self.is_running = True
        self.log("Bot Iniciado (Paper Mode)")
        
        while self.is_running:
            try:
                if self.scanner and self.strategy:
                    self.log("Scanning...")
                    # Simplified - no implement for now
                self.log(f"Cycle complete. Sleeping...")
                await asyncio.sleep(Config.UPDATE_INTERVAL_SECONDS)
            except Exception as e:
                self.log(f"Error: {e}")
                await asyncio.sleep(10)
        
        self.log("Bot Stopped")
    
    def get_system_snapshot(self):
        return {
            "mode": self.mode,
            "balance": self.paper_balance,
            "positions": len(self.active_positions),
            "trades": len(self.trade_history),
            "logs": self.logs[-20:]
        }

# Global instance
bot_instance = TradingBot()
