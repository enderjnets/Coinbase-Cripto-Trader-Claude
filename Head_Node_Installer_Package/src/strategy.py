"""
Hybrid Strategy Orchestrator
Detecta condiciones del mercado y selecciona la estrategia óptima:
- RANGING (Lateral): Grid Trading
- TRENDING (Tendencial): Momentum Scalping
"""

import pandas as pd
import numpy as np
from market_regime_detector import MarketRegimeDetector
from strategy_grid import GridTradingStrategy
from strategy_momentum import MomentumScalpingStrategy


class Strategy:
    """
    Orquestador de estrategias híbrido.

    Analiza el mercado en tiempo real y selecciona la estrategia óptima:
    - Mercados laterales → Grid Trading (captura spread)
    - Mercados tendenciales → Momentum Scalping (sigue tendencia)
    """

    def __init__(self, strategy_params=None):
        """
        Args:
            strategy_params: Dict con parámetros para ambas estrategias
        """
        # Default parameters - OPTIMIZED for 0.8% commission break-even
        self.default_params = {
            # Market Regime Detection
            'adx_period': 14,
            'adx_threshold': 25,
            'volatility_window': 20,

            # Grid Trading - INCREASED spacing to exceed commissions
            'grid_spacing_pct': 2.0,  # Increased from 1.2% to ensure profitability
            'num_grids': 8,           # Reduced to focus on quality levels
            'grid_range_pct': 12.0,   # Wider range
            'rebalance_threshold': 6.0,

            # Momentum Scalping - HIGHER targets
            'sma_fast': 5,
            'sma_slow': 12,
            'rsi_period': 4,  # RSI corto para scalping
            'rsi_overbought': 80,
            'rsi_oversold': 20,
            'bb_period': 20,
            'bb_std': 2.0,
            'min_move_pct': 2.5,  # Increased from 1.5% to ensure profitability after fees

            # Risk Management - WIDER SL/TP
            'risk_per_trade_pct': 2.0,  # % del capital arriesgado por trade
            'max_position_size_pct': 20.0,  # % máximo del capital en una posición
            'sl_multiplier': 2.5,  # Increased from 1.5 - wider SL to avoid false stops
            'tp_multiplier': 6.0   # Increased from 3.0 - target >2% moves
        }

        # Merge con parámetros customizados
        if strategy_params:
            self.params = {**self.default_params, **strategy_params}
        else:
            self.params = self.default_params

        # Inicializar componentes
        self.regime_detector = MarketRegimeDetector(
            adx_period=self.params['adx_period'],
            adx_threshold=self.params['adx_threshold'],
            volatility_window=self.params['volatility_window']
        )

        self.grid_strategy = GridTradingStrategy(
            grid_spacing_pct=self.params['grid_spacing_pct'],
            num_grids=self.params['num_grids'],
            grid_range_pct=self.params['grid_range_pct'],
            rebalance_threshold=self.params['rebalance_threshold']
        )

        self.momentum_strategy = MomentumScalpingStrategy(
            sma_fast=self.params['sma_fast'],
            sma_slow=self.params['sma_slow'],
            rsi_period=self.params['rsi_period'],
            rsi_overbought=self.params['rsi_overbought'],
            rsi_oversold=self.params['rsi_oversold'],
            bb_period=self.params['bb_period'],
            bb_std=self.params['bb_std'],
            min_move_pct=self.params['min_move_pct']
        )

        # Estado interno
        self.current_regime = None
        self.active_strategy = None
        self.cash_mode = False  # True cuando estamos en USD esperando mercado alcista

    def check_trend(self, df):
        """
        Compatibility method for TradingBot.
        Returns 'UP', 'DOWN', or 'NEUTRAL'.
        """
        if df is None or len(df) < 50: return "NEUTRAL"
        
        # We can use the internal regime detector if we want
        # But for 'UP/DOWN' specifically, let's look at SMA slope or ADX
        
        current_close = df['close'].iloc[-1]
        sma50 = df['close'].rolling(window=50).mean().iloc[-1]
        
        if current_close > sma50:
            return "UP"
        elif current_close < sma50:
            return "DOWN"
        return "NEUTRAL"


    def prepare_data(self, df):
        """
        Pre-calculates all indicators and regime data for the entire DataFrame (Vectorized).
        Drastically speeds up backtesting by avoiding re-calculation per candle.
        """
        if df is None or df.empty: return df
        
        # 1. Market Regime Indicators (Vectorized)
        # We can implement this logic here or reuse detector if optimized
        # Reusing logic for consistency:
        
        # Calculate Regime Indicators
        df['adx'] = self.regime_detector.calculate_adx(df)
        df['volatility_ratio'] = self.regime_detector.calculate_volatility_ratio(df)
        df['price_range_pct'] = self.regime_detector.calculate_price_range_pct(df)
        
        # Vectorized Regime Detection
        vol_median = df['volatility_ratio'].median()
        range_median = df['price_range_pct'].median()
        
        trending_mask = (
            (df['adx'] > self.regime_detector.adx_threshold) &
            (df['volatility_ratio'] > vol_median) &
            (df['price_range_pct'] > range_median)
        )
        
        df['regime'] = 'RANGING'
        df.loc[trending_mask, 'regime'] = 'TRENDING'
        
        # 2. Strategy Indicators - Momentum (Vectorized)
        close = df['close']
        
        # SMA
        df['sma_fast'] = close.rolling(window=self.params['sma_fast']).mean()
        df['sma_slow'] = close.rolling(window=self.params['sma_slow']).mean()
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.params['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.params['rsi_period']).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        sma_bb = close.rolling(window=self.params['bb_period']).mean()
        std_bb = close.rolling(window=self.params['bb_period']).std()
        df['bb_upper'] = sma_bb + (std_bb * self.params['bb_std'])
        df['bb_lower'] = sma_bb - (std_bb * self.params['bb_std'])
        
        # 3. Strategy Indicators - Grid (Vectorized/Logic)
        # Grid doesn't need much pre-calc other than maybe support/resistance if dynamic
        # But we'll leave it simple for now.
        
        return df

    def get_signal(self, df, index, risk_level="LOW"):
        """
        Genera señal de trading adaptativa (Optimized).
        """
        if len(df) < 50 or index < 50:
            return {
                'signal': None,
                'regime': None,
                'strategy': None,
                'reason': 'Insufficient data for analysis'
            }

        current_row = df.iloc[index]
        
        # 1. Detectar régimen (Read pre-calc or calc on fly)
        if 'regime' in df.columns:
            self.current_regime = current_row['regime']
        else:
            # Fallback for live trading single candle updates
            df_slice = df.loc[:index].copy()
            self.current_regime = self.regime_detector.get_current_regime(df_slice)

        # 2. Seleccionar estrategia según régimen
        if self.current_regime == 'RANGING':
            self.active_strategy = 'GRID'
            # Grid strategy currently doesn't use heavy indicators, so fast enough
            signal_result = self.grid_strategy.get_signal(df, index)

        else:  # TRENDING
            self.active_strategy = 'MOMENTUM'
            # Check if we have pre-calc indicators to pass to momentum strategy?
            # The momentum strategy likely recalculates if we just pass df/index.
            # We should optimize MomentumScalpingStrategy too or handle it here.
            
            # For now, let's inject pre-calculated values into the row for logic check *if* we refactor Momentum
            # BUT, let's just do the logic inline here if it's simple or trust Momentum isn't too slow?
            # Actually Momentum creates huge overhead if it does rolling means on slices too.
            # Let's see if we can use the pre-calculated columns.
            
            if 'rsi' in df.columns:
                # Optimized Inline Momentum Logic using pre-calc data
                rsi = current_row['rsi']
                close = current_row['close']
                bb_lower = current_row['bb_lower']
                bb_upper = current_row['bb_upper']
                sma_fast = current_row['sma_fast']
                sma_slow = current_row['sma_slow']
                
                signal = None
                reason = ""
                
                # BUY: RSI Oversold + Price < BB Lower + Trend Up (Fast > Slow)
                if (rsi < self.params['rsi_oversold']) and (close < bb_lower) and (sma_fast > sma_slow):
                    signal = "BUY"
                    reason = f"Momentum Buy (RSI {rsi:.1f} < {self.params['rsi_oversold']})"
                    
                # SELL: RSI Overbought + Price > BB Upper
                elif (rsi > self.params['rsi_overbought']) and (close > bb_upper):
                    signal = "SELL"
                    reason = f"Momentum Sell (RSI {rsi:.1f} > {self.params['rsi_overbought']})"
                    
                signal_result = {'signal': signal, 'reason': reason}
            else:
                # Fallback to class logic
                signal_result = self.momentum_strategy.get_signal(df, index)

        # Si no hay señal, retornar temprano
        if signal_result['signal'] is None:
            # Si estamos en cash_mode, verificar si deberíamos buscar reentrada
            if self.cash_mode:
                return {
                    'signal': None,
                    'regime': self.current_regime,
                    'strategy': self.active_strategy,
                    'reason': 'CASH MODE - Waiting for bullish conditions',
                    'cash_mode': True
                }

            return {
                'signal': None,
                'regime': self.current_regime,
                'strategy': self.active_strategy,
                'reason': signal_result.get('reason', 'No signal')
            }

        # 3. Manejar señales SELL de tipo "exit to cash"
        current_price = df.loc[index, 'close']
        signal_type = signal_result['signal']

        # Si es SELL de tipo FULL (exit to cash)
        if signal_type == 'SELL' and signal_result.get('exit_type') == 'FULL':
            self.cash_mode = True
            return {
                'signal': 'SELL',
                'regime': self.current_regime,
                'strategy': self.active_strategy,
                'reason': signal_result.get('reason', 'Exit to cash'),
                'exit_type': 'FULL',
                'cash_mode': True,
                'price': current_price
            }

        # Si estamos en cash_mode y recibimos señal BUY, salir de cash_mode
        if signal_type == 'BUY' and self.cash_mode:
            self.cash_mode = False
            # Continuar con el flujo normal para generar señal BUY

        # Si estamos en cash_mode pero la señal no es BUY fuerte, ignorar
        if self.cash_mode and signal_type != 'BUY':
            return {
                'signal': None,
                'regime': self.current_regime,
                'strategy': self.active_strategy,
                'reason': 'CASH MODE - Only accepting strong BUY signals',
                'cash_mode': True
            }

        # 4. Calcular parámetros de riesgo

        # Calcular ATR para SL/TP dinámicos
        atr = self.calculate_atr(df, index, period=14)

        # Stop Loss y Take Profit basados en ATR
        if signal_type == 'BUY':
            sl = current_price - (atr * self.params['sl_multiplier'])
            tp = current_price + (atr * self.params['tp_multiplier'])

        else:  # SELL
            sl = current_price + (atr * self.params['sl_multiplier'])
            tp = current_price - (atr * self.params['tp_multiplier'])

        # 4. Ajustar según risk_level
        sl, tp = self.adjust_for_risk_level(current_price, sl, tp, risk_level)

        # 5. Calcular confianza de la señal
        confidence = self.calculate_signal_confidence(signal_result, df, index)

        return {
            'signal': signal_type,
            'regime': self.current_regime,
            'strategy': self.active_strategy,
            'sl': sl,
            'tp': tp,
            'reason': signal_result.get('reason', ''),
            'confidence': confidence,
            'price': current_price
        }

    def calculate_atr(self, df, index, period=14):
        """Calcula Average True Range"""
        if index < period:
            return df.loc[index, 'close'] * 0.01  # 1% default

        df_slice = df.loc[max(0, index - period):index].copy()

        high = df_slice['high']
        low = df_slice['low']
        close = df_slice['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.mean()
        return atr

    def adjust_for_risk_level(self, price, sl, tp, risk_level):
        """
        Ajusta SL/TP según el nivel de riesgo seleccionado.

        LOW: SL más cercano, TP más conservador
        MEDIUM: Balance
        HIGH: SL más lejano, TP más agresivo
        """
        if risk_level == "LOW":
            # SL más cercano (1.2x), TP conservador (2.5x)
            sl_distance = abs(price - sl)
            tp_distance = abs(price - tp)

            if sl > price:  # Short
                sl = price + (sl_distance * 1.2)
                tp = price - (tp_distance * 0.8)
            else:  # Long
                sl = price - (sl_distance * 1.2)
                tp = price + (tp_distance * 0.8)

        elif risk_level == "HIGH":
            # SL más lejano (0.8x), TP agresivo (1.2x)
            sl_distance = abs(price - sl)
            tp_distance = abs(price - tp)

            if sl > price:  # Short
                sl = price + (sl_distance * 0.8)
                tp = price - (tp_distance * 1.2)
            else:  # Long
                sl = price - (sl_distance * 0.8)
                tp = price + (tp_distance * 1.2)

        # MEDIUM: sin ajustes

        return sl, tp

    def calculate_signal_confidence(self, signal_result, df, index):
        """
        Calcula un score de confianza (0-1) para la señal.

        Factores:
        - Número de confirmaciones en Momentum
        - Distancia de precio a niveles clave
        - Volumen relativo
        """
        confidence = 0.5  # Base

        # Boost por confirmaciones (Momentum)
        if 'confirmations' in signal_result:
            num_confirmations = len(signal_result['confirmations'])
            confidence += (num_confirmations / 3) * 0.3

        # Penalización por rechazos
        if 'rejections' in signal_result:
            num_rejections = len(signal_result['rejections'])
            confidence -= (num_rejections / 3) * 0.2

        # Boost por volumen alto
        if index >= 20:
            current_volume = df.loc[index, 'volume']
            avg_volume = df.loc[index-20:index-1, 'volume'].mean()

            if current_volume > avg_volume * 1.5:
                confidence += 0.1

        # Clamp entre 0 y 1
        confidence = max(0.0, min(1.0, confidence))

        return confidence

    def calculate_position_size(self, balance, price, sl, risk_per_trade_pct=2.0):
        """
        Calcula el tamaño de posición óptimo basado en:
        - Capital disponible
        - Distancia al Stop Loss
        - % de riesgo por trade

        Formula: Position Size = (Balance * Risk%) / (Entry - SL)
        """
        risk_amount = balance * (risk_per_trade_pct / 100)
        sl_distance = abs(price - sl)

        if sl_distance == 0:
            return 0

        # Cantidad de monedas que podemos comprar con el riesgo permitido
        position_size = risk_amount / sl_distance

        # Limitar al % máximo del capital
        max_position_value = balance * (self.params['max_position_size_pct'] / 100)
        max_position_size = max_position_value / price

        return min(position_size, max_position_size)

    def get_regime_info(self):
        """
        Devuelve información sobre el régimen actual y estrategia activa.
        Útil para debugging y UI.
        """
        return {
            'regime': self.current_regime,
            'active_strategy': self.active_strategy,
            'params': self.params
        }

    def detect_signal(self, df, trend_direction=None, risk_level="LOW", params=None):
        """
        BACKWARD COMPATIBILITY con backtester antiguo.

        Envuelve get_signal() para mantener compatibilidad con el backtester.

        Returns:
            tuple: (signal, reason, atr)
                - signal: 'BUY'/'SELL'/None
                - reason: str explicando la señal
                - atr: valor ATR para cálculos de riesgo
        """
        # Reset index para que funcione con windows
        df = df.reset_index(drop=True)

        # Obtener el índice de la última vela
        index = len(df) - 1

        # Llamar al método principal
        result = self.get_signal(df, index, risk_level=risk_level)

        # Calcular ATR para compatibilidad
        atr = self.calculate_atr(df, index, period=14)

        # Convertir el resultado al formato antiguo
        signal = result.get('signal')
        reason = f"[{result.get('regime', 'UNKNOWN')}|{result.get('strategy', 'UNKNOWN')}] {result.get('reason', '')}"

        return signal, reason, atr

    def calculate_support_resistance(self, df, params=None):
        """
        BACKWARD COMPATIBILITY - Wrapper para función standalone.
        """
        return calculate_support_resistance(df, params)


# Backward compatibility con código existente
def calculate_support_resistance(df, params=None):
    """
    Función legacy para compatibilidad con backtester existente.
    Añade indicadores técnicos al DataFrame.
    """
    if df is None or df.empty:
        return None

    # Parámetros default
    if params is None:
        params = {
            'resistance_period': 50,
            'rsi_period': 14,
            'atr_period': 14
        }

    period = int(params.get('resistance_period', 50))
    rsi_n = int(params.get('rsi_period', 14))
    atr_n = int(params.get('atr_period', 14))

    # Support/Resistance
    df['resistance'] = df['high'].rolling(window=period).max().shift(1)
    df['support'] = df['low'].rolling(window=period).min().shift(1)

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_n).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # ATR
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift(1))
    df['tr3'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=atr_n).mean()

    return df
