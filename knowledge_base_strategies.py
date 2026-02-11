# 📚 KNOWLEDGE BASE - 30 ESTRATEGIAS DE TRADING

## CATEGORÍA 1: SCALPING (1m-5m)

### 1. VWAP Scalping
```python
{
  "name": "VWAP Scalping",
  "category": "Scalping",
  "timeframes": ["1m", "5m"],
  "indicators": ["VWAP"],
  "entry_rules": {
    "long": "Price crosses above VWAP with volume > 1.5x avg",
    "short": "Price crosses below VWAP with volume > 1.5x avg"
  },
  "exit_rules": {
    "take_profit": "2% or VWAP resistance",
    "stop_loss": "1% or opposite VWAP cross"
  },
  "risk_management": {
    "position_size": "10-20% of capital",
    "max_trades_day": 10,
    "max_loss_day": "3% of capital"
  }
}
```

### 2. Order Flow Scalping
```python
{
  "name": "Order Flow Scalping",
  "category": "Scalping", 
  "timeframes": ["1m"],
  "indicators": ["Order Book", "Volume"],
  "entry_rules": {
    "long": "Large bid orders absorption at support",
    "short": "Large ask orders absorption at resistance"
  },
  "exit_rules": {
    "take_profit": "1.5-2%",
    "stop_loss": "0.5-1%"
  }
}
```

### 3. Mean Reversion 1min
```python
{
  "name": "Mean Reversion 1min",
  "category": "Scalping",
  "timeframes": ["1m"],
  "indicators": ["Bollinger Bands", "RSI"],
  "entry_rules": {
    "long": "Price touches lower BB + RSI < 30",
    "short": "Price touches upper BB + RSI > 70"
  },
  "exit_rules": {
    "take_profit": "Middle BB or 1%",
    "stop_loss": "0.5% beyond BB"
  }
}
```

## CATEGORÍA 2: DAY TRADING (5m-1h)

### 4. Opening Range Breakout
```python
{
  "name": "ORB (Opening Range Breakout)",
  "category": "Day Trading",
  "timeframes": ["5m", "15m", "30m"],
  "entry_rules": {
    "long": "Breakout above first 15min high with volume",
    "short": "Breakout below first 15min low with volume"
  },
  "filters": {
    "trend": "Trade with daily trend",
    "volatility": "ATR > 2% daily"
  }
}
```

### 5. Gap & Go
```python
{
  "name": "Gap & Go",
  "category": "Day Trading",
  "timeframes": ["5m", "15m"],
  "entry_rules": {
    "long": "Gap up > 1% + volume > 2x avg + continuation",
    "short": "Gap down > 1% + volume > 2x avg + continuation"
  }
}
```

### 6. Bull/Bear Flags
```python
{
  "name": "Flag Patterns",
  "category": "Day Trading",
  "timeframes": ["15m", "1h"],
  "entry_rules": {
    "long": "Bull flag + volume spike + breakout",
    "short": "Bear flag + volume spike + breakdown"
  }
}
```

### 7. Breakout & Retest
```python
{
  "name": "Breakout & Retest",
  "category": "Day Trading",
  "timeframes": ["15m", "1h", "4h"],
  "entry_rules": {
    "long": "Break resistance + retest as support + confirmation",
    "short": "Break support + retest as resistance + confirmation"
  }
}
```

## CATEGORÍA 3: SMART MONEY CONCEPTS

### 8. Order Blocks
```python
{
  "name": "Order Blocks",
  "category": "SMC",
  "timeframes": ["15m", "1h", "4h"],
  "entry_rules": {
    "long": "Retrace to last bullish order block",
    "short": "Retrace to last bearish order block"
  },
  "confirmation": "FVG + Market Structure"
}
```

### 9. Fair Value Gaps
```python
{
  "name": "FVG (Fair Value Gaps)",
  "category": "SMC",
  "timeframes": ["5m", "15m", "1h"],
  "entry_rules": {
    "long": "FVG filled + bounce from gap lows",
    "short": "FVG filled + rejection from gap highs"
  }
}
```

### 10. Break of Structure
```python
{
  "name": "BOS (Break of Structure)",
  "category": "SMC", 
  "timeframes": ["15m", "1h", "4h"],
  "entry_rules": {
    "long": "Higher high + higher low + bullish FVG",
    "short": "Lower low + lower high + bearish FVG"
  }
}
```

### 11. Liquidity Sweeps
```python
{
  "name": "Liquidity Sweeps",
  "category": "SMC",
  "timeframes": ["5m", "15m", "1h"],
  "entry_rules": {
    "long": "Sweep lows + reversal candle + FVG",
    "short": "Sweep highs + reversal candle + FVG"
  }
}
```

## CATEGORÍA 4: TECHNICAL ANALYSIS

### 12. RSI Divergences
```python
{
  "name": "RSI Divergence",
  "category": "Technical",
  "timeframes": ["15m", "1h", "4h"],
  "entry_rules": {
    "long": "Price makes lower low + RSI makes higher low",
    "short": "Price makes higher high + RSI makes lower high"
  }
}
```

### 13. EMA Crossovers
```python
{
  "name": "EMA Crossover",
  "category": "Technical",
  "timeframes": ["5m", "15m", "1h", "4h"],
  "indicators": ["EMA 9", "EMA 21", "EMA 50", "EMA 200"],
  "entry_rules": {
    "long": "EMA 9 crosses above EMA 21 + price above EMA 200",
    "short": "EMA 9 crosses below EMA 21 + price below EMA 200"
  }
}
```

### 14. Supertrend
```python
{
  "name": "Supertrend",
  "category": "Technical",
  "timeframes": ["5m", "15m", "1h"],
  "entry_rules": {
    "long": "Supertrend turns green + price above",
    "short": "Supertrend turns red + price below"
  }
}
```

## CATEGORÍA 5: VOLUME-BASED

### 15. Volume Profile
```python
{
  "name": "Volume Profile",
  "category": "Volume",
  "timeframes": ["15m", "1h", "4h"],
  "entry_rules": {
    "long": "Price returns to POC + bullish confirmation",
    "short": "Price returns to POC + bearish confirmation"
  }
}
```

### 16. Volume Spikes
```python
{
  "name": "Volume Spike Reversal",
  "category": "Volume",
  "timeframes": ["1m", "5m", "15m"],
  "entry_rules": {
    "long": "Volume spike > 3x avg + rejection candle",
    "short": "Volume spike > 3x avg + rejection candle"
  }
}
```

## CATEGORÍA 6: TREND FOLLOWING

### 17. Moving Average Ribbon
```python
{
  "name": "MA Ribbon Trend",
  "category": "Trend Following",
  "timeframes": ["1h", "4h", "1d"],
  "indicators": ["EMA 8", "EMA 13", "EMA 21", "EMA 34", "EMA 55"],
  "entry_rules": {
    "long": "All EMAs aligned bullish + price above all",
    "short": "All EMAs aligned bearish + price below all"
  }
}
```

### 18. Parabolic SAR Trailing
```python
{
  "name": "Parabolic SAR",
  "category": "Trend Following",
  "timeframes": ["15m", "1h", "4h"],
  "entry_rules": {
    "long": "SAR below price + trend change signal",
    "short": "SAR above price + trend change signal"
  }
}
```

## CATEGORÍA 7: PATTERNS

### 19. Head & Shoulders
```python
{
  "name": "Head & Shoulders",
  "category": "Patterns",
  "timeframes": ["1h", "4h", "1d"],
  "entry_rules": {
    "short": "Right shoulder forms + neckline break"
  }
}
```

### 20. Double Top/Bottom
```python
{
  "name": "Double Top/Bottom",
  "category": "Patterns", 
  "timeframes": ["1h", "4h", "1d"],
  "entry_rules": {
    "long": "Double bottom + neckline break",
    "short": "Double top + neckline break"
  }
}
```

## CATEGORÍA 8: COMBINACIONES AVANZADAS

### 21. VWAP + RSI Confluence
```python
{
  "name": "VWAP + RSI Confluence",
  "category": "Advanced",
  "timeframes": ["5m", "15m"],
  "entry_rules": {
    "long": "Price above VWAP + RSI > 50 + bullish momentum",
    "short": "Price below VWAP + RSI < 50 + bearish momentum"
  }
}
```

### 22. SMC + Volume
```python
{
  "name": "SMC + Volume Confluence",
  "category": "Advanced",
  "timeframes": ["15m", "1h"],
  "entry_rules": {
    "long": "Order block + FVG + Volume spike",
    "short": "Order block + FVG + Volume spike"
  }
}
```

### 23. Multi-Timeframe Trend
```python
{
  "name": "Multi-Timeframe Trend",
  "category": "Advanced",
  "timeframes": ["1h", "4h", "1d"],
  "entry_rules": {
    "long": "Daily trend UP + 4h trend UP + 1h pullback to support",
    "short": "Daily trend DOWN + 4h trend DOWN + 1h pullback to resistance"
  }
}
```

### 24. ICT Concepts (Inner Circle Trader)
```python
{
  "name": "ICT Premium/Discount Zones",
  "category": "ICT",
  "timeframes": ["15m", "1h", "4h"],
  "entry_rules": {
    "long": "Price enters premium zone + market structure bullish",
    "short": "Price enters discount zone + market structure bearish"
  }
}
```

### 25. Market Structure + Momentum
```python
{
  "name": "Structure + Momentum",
  "category": "Advanced",
  "timeframes": ["15m", "1h"],
  "entry_rules": {
    "long": "BOS bullish + RSI > 50 + bullish candle",
    "short": "BOS bearish + RSI < 50 + bearish candle"
  }
}
```

## 📊 MÉTRICAS POR ESTRATEGIA

| Estrategia | Win Rate Esperado | Risk/Reward | Frecuencia |
|------------|-------------------|-------------|------------|
| VWAP Scalping | 55-60% | 1:1.5 | Alta |
| Order Flow | 50-55% | 1:2 | Muy Alta |
| Mean Reversion | 60-65% | 1:1 | Alta |
| ORB | 55-60% | 1:2 | Media |
| Gap & Go | 50-55% | 1:2 | Baja |
| Bull Flags | 55-60% | 1:1.5 | Media |
| Order Blocks | 55-60% | 1:2 | Media |
| FVG | 50-55% | 1:1.5 | Alta |
| RSI Div | 60-65% | 1:1.5 | Baja |
| EMA Cross | 55-60% | 1:2 | Media |
| Supertrend | 50-55% | 1:1.5 | Media |
| Volume Profile | 55-60% | 1:2 | Baja |
| Structure + Momentum | 60-65% | 1:1.5 | Alta |

## 🎯 CÓMO USAR ESTA KNOWLEDGE BASE

1. **Cada estrategia se pasará al Algoritmo Genético**
2. **El GA optimizará los parámetros**
3. **Se crearán Work Units por estrategia**
4. **Los workers procesarán en paralelo**
5. **Los mejores resultados entrenarán la IA**
