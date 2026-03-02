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
