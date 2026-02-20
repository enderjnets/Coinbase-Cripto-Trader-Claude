import time
import pandas as pd
import threading
from datetime import datetime
from broker_client import BrokerClient

class PennyBasketStrategy:
    """
    Implements the "High-Frequency Penny Basket Scalping" strategy (v2 Advanced).
    
    Includes User-Requested Pillars:
    1. Automation: Smart Pegging (Bid + 0.01)
    2. Risk: Basket-level Panic Stop
    3. Scanning: (Hooks for Float/RVOL/VWAP)
    4. Tax: Wash Sale Guard (Optional)
    5. Scalability: Liquidity Checks
    """
    
    def __init__(self, broker: BrokerClient, max_basket_size=20):
        self.broker = broker
        self.max_basket_size = max_basket_size
        self.active_basket = [] # List of symbols
        self.open_orders = {}   # {symbol: {'id', 'price', 'time', 'type'}}
        self.positions = {}     # {symbol: {'qty', 'avg_price', 'start_time'}}
        self.closed_trades = {} # {symbol: last_close_time} for Wash Sale Logic
        
        self.running = False
        self.lock = threading.Lock()
        self.basket_pnl = 0.0
        
        # --- Strategy Parameters ---
        self.MIN_PRICE = 1.00
        self.MAX_PRICE = 5.00
        self.MIN_RVOL = 2.0  # User req: > 2.0
        
        # Execution Logic
        self.PEG_MODE = "PENNY_BID" # "PENNY_BID" (Bid + 0.01) or "PASSIVE_FISH" (Bid - Offset)
        self.BID_OFFSET = 0.01      # Cents to add to Bid (if Pennying)
        
        # Risk Management
        self.PROFIT_TARGET = 0.03   # Cents (Scalp)
        self.STOP_LOSS = 0.05       # Cents per trade (Hard Stop)
        self.BASKET_PANIC_THRESHOLD = -50.0 # If total basket PnL drops < -$50, Liquidate ALL
        
        # Scalability & Rules
        self.POSITION_SIZE_SHARES = 10 
        self.WASH_SALE_GUARD = False # Set True to avoid re-entry within 30 days (Not recommended for scalping)
        self.LIQUIDITY_MIN_VOLUME = 10000 # Min volume in last candle/minute to trade
        
    def start(self):
        """Starts the strategy loop in a background thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("Penny Basket Strategy v2 Started.")

    def stop(self):
        """Stops the strategy loop."""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()
        print("Penny Basket Strategy Stopped.")

    def emergency_liquidate(self):
        """Panic Button: Liquidate EVERYTHING."""
        print("🚨 EMERGENCY LIQUIDATION TRIGGERED 🚨")
        with self.lock:
            # Cancel all orders
            for sym, order in list(self.open_orders.items()):
                self.broker.cancel_order(order['id'])
                del self.open_orders[sym]
            
            # Close all positions (Market Sell)
            for sym, pos in list(self.positions.items()):
                print(f"Liquidating {sym}...")
                self.broker.place_order(sym, 'SELL', 'MARKET', pos['qty'], duration='GTC_EXT')
                del self.positions[sym]
            
            self.running = False # Stop strategy

    def _run_loop(self):
        """Main execution loop."""
        while self.running:
            try:
                self._update_basket_pnl()
                
                # Check Global Risk
                if self.basket_pnl < self.BASKET_PANIC_THRESHOLD:
                    self.emergency_liquidate()
                    break

                # 1. Update Basket (Scan)
                self._update_basket()
                
                # 2. Manage Portfolio (Fish & Shave)
                self._manage_positions()
                
                time.sleep(2) # Faster loop for HFT-lite
                
            except Exception as e:
                print(f"Error in strategy loop: {e}")
                time.sleep(5)

    def _update_basket_pnl(self):
        """Calculate Unrealized PnL of the entire basket."""
        # In a real app, fetch current prices and calc PnL
        # Here we mock it or track it roughly
        pass

    def _update_basket(self):
        """
        Scans for new opportunities.
        Filters: Price $1-$5, RVOL > 2, Above VWAP (Placeholder logic).
        """
        # TODO: Real integration with MarketScanner
        # Mimic "Finding" tokens
        if not self.active_basket:
            self.active_basket = ['XAIR', 'SEGG', 'JAGX', 'POLA', 'IVR'] # From user example

    def _manage_positions(self):
        """
        Iterates through the basket and manages orders/positions.
        """
        with self.lock:
            # Get real-time quotes for the entire basket
            if not self.active_basket:
                return

            quotes = self.broker.get_quotes(self.active_basket)
            
            for symbol in self.active_basket:
                quote = quotes.get(symbol)
                if not quote:
                    continue
                
                # Wash Sale Guard Check
                if self.WASH_SALE_GUARD and symbol in self.closed_trades:
                    # If closed recently with loss... (Simplified: just block for now)
                    last_time = self.closed_trades[symbol]
                    if time.time() - last_time < 300: # Block for 5 mins example
                        continue

                # Case 1: We have a Position -> Look to EXIT (Shaving)
                if symbol in self.positions:
                    self._manage_exit(symbol, quote)
                
                # Case 2: No Position, No Order -> Look to ENTER (Fishing)
                elif symbol not in self.open_orders:
                    self._place_fishing_order(symbol, quote)
                
                # Case 3: Open Order -> Check status / Adjust level
                elif symbol in self.open_orders:
                    self._adjust_fishing_order(symbol, quote)

    def _place_fishing_order(self, symbol, quote):
        """
        Places a Limit Buy order.
        Mode: "PENNY_BID" -> Bid + 0.01 (Aggressive Catch)
        """
        bid = quote['bid']
        
        if self.PEG_MODE == "PENNY_BID":
            limit_price = round(bid + self.BID_OFFSET, 2)
        else:
            limit_price = round(bid - 0.02, 2) # Deep fishing
        
        # Max Constraint
        if limit_price > self.MAX_PRICE: return

        order = self.broker.place_order(
            symbol=symbol,
            side='BUY',
            order_type='LIMIT',
            quantity=self.POSITION_SIZE_SHARES,
            price=limit_price,
            duration='GTC_EXT'
        )
        
        if order and 'id' in order:
            self.open_orders[symbol] = {
                'id': order['id'],
                'price': limit_price,
                'time': time.time()
            }

    def _adjust_fishing_order(self, symbol, quote):
        """
        Smarter Pegging:
        If logic is 'Penny the Bid', and Bid moves UP, we move UP.
        If Bid moves DOWN, does our Limit fill? (Ideally yes).
        """
        existing = self.open_orders[symbol]
        bid = quote['bid']
        
        target_price = round(bid + self.BID_OFFSET, 2) if self.PEG_MODE == "PENNY_BID" else round(bid - 0.02, 2)
        
        # Tolerance: Don't spam updates for < 1 cent noise unless precise
        if abs(target_price - existing['price']) >= 0.01:
            # print(f"⚡️ Adjusting {symbol}: {existing['price']} -> {target_price}")
            
            self.broker.cancel_order(existing['id'])
            
            new_order = self.broker.place_order(
                symbol=symbol,
                side='BUY',
                order_type='LIMIT',
                quantity=self.POSITION_SIZE_SHARES,
                price=target_price,
                duration='GTC_EXT'
            )
            
            if new_order and 'id' in new_order:
                self.open_orders[symbol] = {
                    'id': new_order['id'],
                    'price': target_price,
                    'time': time.time()
                }

    def _manage_exit(self, symbol, quote):
        """
        Logic to sell for a profit or stop loss.
        """
        pos = self.positions[symbol]
        entry_price = pos['avg_price']
        
        target = entry_price + self.PROFIT_TARGET
        stop = entry_price - self.STOP_LOSS
        
        current_bid = quote['bid']
        
        # Take Profit
        if current_bid >= target:
             print(f"💰 TAKING PROFIT {symbol} @ {current_bid}")
             self.broker.place_order(symbol, 'SELL', 'LIMIT', pos['qty'], price=current_bid)
             del self.positions[symbol]
             self.closed_trades[symbol] = time.time()
             
        # Stop Loss
        elif current_bid <= stop:
             print(f"🩸 STOP LOSS {symbol} @ {current_bid}")
             self.broker.place_order(symbol, 'SELL', 'MARKET', pos['qty'])
             del self.positions[symbol]
             self.closed_trades[symbol] = time.time()
