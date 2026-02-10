"""
Market Regime Detector
Identifica si el mercado está en condiciones LATERALES (rango) o TENDENCIALES
para seleccionar la estrategia óptima.
"""

import pandas as pd
import numpy as np


class MarketRegimeDetector:
    """
    Detecta el régimen del mercado usando múltiples indicadores:
    - ADX (Average Directional Index): Fuerza de tendencia
    - Volatilidad relativa (ATR/Precio)
    - Rango de precio (High-Low range)
    """

    def __init__(self, adx_period=14, adx_threshold=25, volatility_window=20):
        """
        Args:
            adx_period: Periodo para calcular ADX
            adx_threshold: Umbral ADX (>25 = tendencia, <25 = lateral)
            volatility_window: Ventana para calcular volatilidad
        """
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.volatility_window = volatility_window

    def calculate_adx(self, df):
        """
        Calcula el Average Directional Index (ADX)
        ADX mide la FUERZA de la tendencia (no la dirección)
        Valores > 25 indican tendencia fuerte
        Valores < 20 indican mercado lateral/débil
        """
        high = df['high']
        low = df['low']
        close = df['close']

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        # Smoothed TR and DM
        atr = pd.Series(tr).rolling(window=self.adx_period).mean()
        plus_di = 100 * (pd.Series(plus_dm).rolling(window=self.adx_period).mean() / atr)
        minus_di = 100 * (pd.Series(minus_dm).rolling(window=self.adx_period).mean() / atr)

        # ADX calculation
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=self.adx_period).mean()

        return adx

    def calculate_volatility_ratio(self, df):
        """
        Calcula la volatilidad relativa (ATR / Precio)
        Alta volatilidad suele indicar movimientos tendenciales
        """
        high = df['high']
        low = df['low']
        close = df['close']

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR
        atr = tr.rolling(window=self.volatility_window).mean()

        # Volatilidad relativa
        volatility_ratio = (atr / close) * 100

        return volatility_ratio

    def calculate_price_range_pct(self, df, periods=20):
        """
        Calcula el rango de precio (High-Low) en los últimos N periodos
        como porcentaje del precio. Rangos estrechos = mercado lateral.
        """
        high = df['high'].rolling(window=periods).max()
        low = df['low'].rolling(window=periods).min()
        close = df['close']

        range_pct = ((high - low) / close) * 100

        return range_pct

    def detect_regime(self, df):
        """
        Detecta el régimen del mercado en cada vela.

        Returns:
            Series con valores:
            - 'RANGING': Mercado lateral (usar Grid Trading)
            - 'TRENDING': Mercado con tendencia (usar Momentum Scalping)
        """
        # Calcular indicadores
        adx = self.calculate_adx(df)
        volatility = self.calculate_volatility_ratio(df)
        range_pct = self.calculate_price_range_pct(df, periods=20)

        # Lógica de detección
        regime = pd.Series(index=df.index, dtype='object')

        # Criterios para TRENDING:
        # 1. ADX > threshold (tendencia fuerte)
        # 2. Volatilidad alta (> mediana)
        # 3. Rango amplio (> mediana)

        vol_median = volatility.median()
        range_median = range_pct.median()

        trending_mask = (
            (adx > self.adx_threshold) &
            (volatility > vol_median) &
            (range_pct > range_median)
        )

        # RANGING: Todo lo demás
        ranging_mask = ~trending_mask

        regime[trending_mask] = 'TRENDING'
        regime[ranging_mask] = 'RANGING'

        return regime

    def get_regime_stats(self, df):
        """
        Obtiene estadísticas sobre el régimen detectado.
        Útil para análisis y debugging.
        """
        regime = self.detect_regime(df)

        stats = {
            'total_candles': len(regime),
            'trending_pct': (regime == 'TRENDING').sum() / len(regime) * 100,
            'ranging_pct': (regime == 'RANGING').sum() / len(regime) * 100,
            'current_regime': regime.iloc[-1] if len(regime) > 0 else None
        }

        return stats

    def get_current_regime(self, df):
        """
        Devuelve el régimen actual (última vela).
        """
        regime = self.detect_regime(df)
        return regime.iloc[-1] if len(regime) > 0 else 'RANGING'


if __name__ == "__main__":
    # Test básico
    print("Market Regime Detector - Test")

    # Crear datos de prueba
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=1000, freq='5min')

    # Simular mercado lateral
    price_base = 100
    df_ranging = pd.DataFrame({
        'timestamp': dates[:500],
        'open': price_base + np.random.randn(500) * 0.5,
        'high': price_base + np.random.randn(500) * 0.5 + 0.3,
        'low': price_base + np.random.randn(500) * 0.5 - 0.3,
        'close': price_base + np.random.randn(500) * 0.5,
        'volume': np.random.randint(100, 1000, 500)
    })

    # Simular mercado tendencial
    trend = np.linspace(0, 20, 500)
    df_trending = pd.DataFrame({
        'timestamp': dates[500:],
        'open': price_base + trend + np.random.randn(500) * 0.5,
        'high': price_base + trend + np.random.randn(500) * 0.5 + 0.5,
        'low': price_base + trend + np.random.randn(500) * 0.5 - 0.5,
        'close': price_base + trend + np.random.randn(500) * 0.5,
        'volume': np.random.randint(100, 1000, 500)
    })

    df_test = pd.concat([df_ranging, df_trending], ignore_index=True)

    detector = MarketRegimeDetector()
    stats = detector.get_regime_stats(df_test)

    print("\n📊 Estadísticas del mercado:")
    print(f"Total velas: {stats['total_candles']}")
    print(f"Trending: {stats['trending_pct']:.1f}%")
    print(f"Ranging: {stats['ranging_pct']:.1f}%")
    print(f"Régimen actual: {stats['current_regime']}")
