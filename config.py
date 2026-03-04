class Config:
    # Spot fees (Coinbase Advanced Trade)
    SPOT_FEE_MAKER = 0.40    # 0.40%
    SPOT_FEE_TAKER = 0.60    # 0.60%

    # Futures fees (Coinbase Derivatives Exchange - CDE)
    FUTURES_FEE_MAKER = 0.02  # 0.02%
    FUTURES_FEE_TAKER = 0.06  # 0.06%

    # Funding rate (perpetual futures, cada 8h)
    FUTURES_FUNDING_RATE = 0.01  # 0.01% cada 8 horas (promedio)

    # Legacy compatibility
    TRADING_FEE_MAKER = 0.4
    TRADING_FEE_TAKER = 0.6

    # Legacy trading bot defaults (used by interface.py / trading_bot.py)
    PAPER_TRADING_INITIAL_BALANCE = 10000.0
    TRADING_FEE_PERCENT = 0.6
    RISK_PER_TRADE_PERCENT = 2.0
    RVOL_THRESHOLD = 1.5
    UPDATE_INTERVAL_SECONDS = 60
    TIMEFRAME_TREND = "1h"
    TIMEFRAME_ENTRY = "5m"

    @staticmethod
    def get_api_keys():
        """Legacy stub - returns empty keys for dashboard compatibility."""
        return ("", "")
