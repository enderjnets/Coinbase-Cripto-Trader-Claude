"""
Momentum Scalping Strategy
Optimizada para mercados TENDENCIALES
Usa indicadores de alta precisión: SMA(5/12), VWAP, RSI(4), Bollinger Bands
"""

import pandas as pd
import numpy as np


class MomentumScalpingStrategy:
    """
    Scalping de Momentum con confirmación multi-indicador.

    Señales solo cuando TODOS los indicadores confirman:
    - Cruce de SMAs rápidas (5/12)
    - Precio respecto a VWAP (filtro de calidad)
    - RSI(4) para timing de entrada
    - Bollinger Bands para detección de breakouts
    """

    def __init__(
        self,
        sma_fast=5,           # SMA rápida
        sma_slow=12,          # SMA lenta
        rsi_period=4,         # RSI de corto plazo
        rsi_overbought=80,    # RSI sobrecompra
        rsi_oversold=20,      # RSI sobreventa
        bb_period=20,         # Periodo Bollinger Bands
        bb_std=2.0,           # Desviación estándar BB
        min_move_pct=1.2      # Reducido de 1.5% a 1.2% para capturar más movimientos
    ):
        """
        Args:
            sma_fast: Periodo SMA rápida
            sma_slow: Periodo SMA lenta
            rsi_period: Periodo RSI (4 es óptimo para scalping)
            rsi_overbought/oversold: Umbrales RSI
            bb_period: Periodo Bollinger Bands
            bb_std: Desviación estándar BB
            min_move_pct: Movimiento mínimo requerido
        """
        self.sma_fast = sma_fast
        self.sma_slow = sma_slow
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.min_move_pct = min_move_pct

    def calculate_sma(self, df, period):
        """Simple Moving Average"""
        return df['close'].rolling(window=period).mean()

    def calculate_vwap(self, df):
        """
        Volume Weighted Average Price
        Precio promedio ponderado por volumen.
        Usado como filtro de calidad:
        - LONG solo si precio > VWAP
        - SHORT solo si precio < VWAP
        """
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return vwap

    def calculate_rsi(self, df, period):
        """
        Relative Strength Index
        RSI(4) para scalping: detecta agotamiento inmediato
        """
        delta = df['close'].diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_bollinger_bands(self, df, period, std_dev):
        """
        Bollinger Bands
        Detecta "squeezes" (contracciones) seguidas de expansión
        """
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        bandwidth = (upper_band - lower_band) / sma * 100

        return upper_band, lower_band, bandwidth

    def detect_bollinger_squeeze(self, bandwidth, lookback=10):
        """
        Detecta Bollinger Squeeze: contracción de volatilidad
        que suele preceder a un movimiento explosivo.
        """
        if len(bandwidth) < lookback:
            return False

        current_bw = bandwidth.iloc[-1]
        avg_bw = bandwidth.iloc[-lookback:-1].mean()

        # Squeeze = bandwidth actual < 80% del promedio
        return current_bw < (avg_bw * 0.8)

    def get_signal(self, df, index):
        """
        Genera señal de trading con confirmación multi-indicador.

        LONG cuando:
        1. SMA(5) cruza por encima de SMA(12)
        2. Precio > VWAP
        3. RSI(4) no está sobrecomprado (< 80)
        4. Bollinger breakout alcista

        SHORT cuando:
        1. SMA(5) cruza por debajo de SMA(12)
        2. Precio < VWAP
        3. RSI(4) no está sobrevendido (> 20)
        4. Bollinger breakout bajista
        """
        if len(df) < max(self.sma_slow, self.bb_period, self.rsi_period) + 1:
            return {'signal': None, 'reason': 'Insufficient data'}

        if index < max(self.sma_slow, self.bb_period, self.rsi_period):
            return {'signal': None, 'reason': 'Warming up indicators'}

        # Calcular indicadores
        df_slice = df.loc[:index].copy()

        sma_fast = self.calculate_sma(df_slice, self.sma_fast)
        sma_slow = self.calculate_sma(df_slice, self.sma_slow)
        vwap = self.calculate_vwap(df_slice)
        rsi = self.calculate_rsi(df_slice, self.rsi_period)
        bb_upper, bb_lower, bb_width = self.calculate_bollinger_bands(
            df_slice, self.bb_period, self.bb_std
        )

        # Valores actuales y previos
        price = df.loc[index, 'close']
        price_prev = df.loc[index - 1, 'close']

        sma_fast_curr = sma_fast.iloc[-1]
        sma_fast_prev = sma_fast.iloc[-2]
        sma_slow_curr = sma_slow.iloc[-1]
        sma_slow_prev = sma_slow.iloc[-2]

        vwap_curr = vwap.iloc[-1]
        rsi_curr = rsi.iloc[-1]

        bb_upper_curr = bb_upper.iloc[-1]
        bb_lower_curr = bb_lower.iloc[-1]

        # Detectar cruces de SMA
        bullish_cross = (sma_fast_prev <= sma_slow_prev) and (sma_fast_curr > sma_slow_curr)
        bearish_cross = (sma_fast_prev >= sma_slow_prev) and (sma_fast_curr < sma_slow_curr)

        # Detectar Bollinger Breakouts
        bb_squeeze = self.detect_bollinger_squeeze(bb_width)
        bb_breakout_up = (price_prev <= bb_upper_curr) and (price > bb_upper_curr)
        bb_breakout_down = (price_prev >= bb_lower_curr) and (price < bb_lower_curr)

        # SEÑAL LONG
        if bullish_cross:
            confirmations = []
            rejections = []

            # Filtro VWAP
            if price > vwap_curr:
                confirmations.append('Price > VWAP')
            else:
                rejections.append('Price < VWAP')

            # Filtro RSI
            if rsi_curr < self.rsi_overbought:
                confirmations.append(f'RSI {rsi_curr:.1f} not overbought')
            else:
                rejections.append(f'RSI {rsi_curr:.1f} overbought')

            # Bollinger favorable
            if bb_squeeze or bb_breakout_up:
                confirmations.append('Bollinger favorable')
            else:
                rejections.append('Bollinger unfavorable')

            # Requiere al menos 1 confirmación si hay "Cruce Dorado" fuerte, o 2 normal
            # Se relajó de ">= 2" estricto a permitir entradas más agresivas
            min_confirmations = 1 if len(confirmations) > 0 else 2
            
            if len(confirmations) >= min_confirmations:
                return {
                    'signal': 'BUY',
                    'reason': f'Bullish momentum: {", ".join(confirmations)}',
                    'confirmations': confirmations,
                    'rejections': rejections,
                    'rsi': rsi_curr
                }

        # SEÑAL SELL (Exit to Cash - para mercados bajistas)
        # En Coinbase Spot, SELL significa "vender todo y quedarse en USD"
        if bearish_cross:
            confirmations = []
            rejections = []

            # Filtro VWAP (precio bajo presión vendedora)
            if price < vwap_curr:
                confirmations.append('Price < VWAP (bearish pressure)')
            else:
                rejections.append('Price > VWAP')

            # Filtro RSI (confirmar momento bajista, no sobreventa extrema)
            if rsi_curr > self.rsi_oversold and rsi_curr < 50:
                confirmations.append(f'RSI {rsi_curr:.1f} in bearish zone')
            else:
                rejections.append(f'RSI {rsi_curr:.1f} not in bearish zone')

            # Bollinger favorable (breakout bajista)
            if bb_squeeze or bb_breakout_down:
                confirmations.append('Bollinger bearish breakout')
            else:
                rejections.append('Bollinger unfavorable')

            # Requiere al menos 1 confirmación si hay "Cruce Dorado" fuerte, o 2 normal
            # Se relajó de ">= 2" estricto a permitir entradas más agresivas
            min_confirmations = 1 if len(confirmations) > 0 else 2
            
            if len(confirmations) >= min_confirmations:
                return {
                    'signal': 'SELL',
                    'reason': f'EXIT TO CASH - Bearish trend: {", ".join(confirmations)}',
                    'confirmations': confirmations,
                    'rejections': rejections,
                    'rsi': rsi_curr,
                    'exit_type': 'FULL'
                }

        return {'signal': None, 'reason': 'No confirmed signal'}

    def calculate_dynamic_take_profit(self, entry_price, df, index, direction):
        """
        Calcula Take Profit dinámico basado en ATR y movimiento mínimo.

        Para superar comisiones Maker (0.80%), el movimiento debe ser >1%.
        Usamos min_move_pct (1.5% default) para asegurar rentabilidad.
        """
        # Calcular ATR
        high = df.loc[:index, 'high']
        low = df.loc[:index, 'low']
        close = df.loc[:index, 'close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(window=14).mean().iloc[-1]

        # TP basado en ATR o movimiento mínimo (lo que sea mayor)
        atr_based_move = atr * 2  # 2x ATR
        min_move = entry_price * (self.min_move_pct / 100)

        target_move = max(atr_based_move, min_move)

        if direction == 'LONG':
            tp = entry_price + target_move
        else:  # SHORT
            tp = entry_price - target_move

        return tp

    def calculate_dynamic_stop_loss(self, entry_price, df, index):
        """
        Stop Loss dinámico basado en ATR.
        Más conservador que TP para proteger capital.
        """
        # Calcular ATR
        high = df.loc[:index, 'high']
        low = df.loc[:index, 'low']
        close = df.loc[:index, 'close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(window=14).mean().iloc[-1]

        # SL = 2.5x ATR (Antes 1.5x) - Más espacio para respirar
        # Crypto es volátil; stops muy ajustados causan pérdidas innecesarias
        sl_distance = atr * 2.5

        return sl_distance


if __name__ == "__main__":
    print("Momentum Scalping Strategy - Test")

    # Crear datos de mercado tendencial simulado
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=500, freq='1min')

    # Tendencia alcista con volatilidad
    trend = np.linspace(100, 120, 500)
    noise = np.random.randn(500) * 0.5
    prices = trend + noise

    df_test = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices + np.abs(np.random.randn(500) * 0.3),
        'low': prices - np.abs(np.random.randn(500) * 0.3),
        'close': prices,
        'volume': np.random.randint(100, 2000, 500)
    })

    df_test = df_test.reset_index(drop=True)

    strategy = MomentumScalpingStrategy()

    # Probar señales
    signals = []
    for i in range(len(df_test)):
        signal = strategy.get_signal(df_test, i)
        if signal['signal']:
            signals.append({
                'index': i,
                'timestamp': df_test.loc[i, 'timestamp'],
                'signal': signal['signal'],
                'reason': signal['reason'],
                'price': df_test.loc[i, 'close']
            })

    print(f"\n📊 Señales generadas: {len(signals)}")
    for sig in signals[:5]:  # Mostrar primeras 5
        print(f"{sig['timestamp']}: {sig['signal']} at ${sig['price']:.2f} - {sig['reason']}")
