#!/usr/bin/env python3
"""
position_sizing.py - Gestión de Tamaño de Posición
==================================================

Implementa métodos profesionales para determinar el tamaño óptimo de posición:
- Kelly Criterion (fraccional)
- Risk Parity
- Volatility-based sizing
- Fixed Fractional

Uso:
    from position_sizing import KellyCriterion, PositionSizer

    # Kelly Criterion
    kelly = KellyCriterion(win_rate=0.55, avg_win=100, avg_loss=80)
    optimal_size = kelly.fractional(fraction=0.5)  # 50% Kelly

    # O usando PositionSizer
    sizer = PositionSizer(capital=10000, method='kelly')
    size = sizer.calculate(win_rate=0.55, avg_win=100, avg_loss=80)
"""

import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PositionSizeResult:
    """Resultado del cálculo de tamaño de posición."""
    size_pct: float          # Porcentaje del capital
    size_usd: float          # Tamaño en USD
    method: str              # Método usado
    kelly_raw: Optional[float] = None  # Kelly raw (si aplica)
    risk_amount: Optional[float] = None  # Riesgo en USD
    metadata: Optional[Dict] = None


class KellyCriterion:
    """
    Kelly Criterion para tamaño óptimo de posición.

    f* = (p * b - q) / b

    donde:
    - p = probabilidad de ganar (win rate)
    - q = 1 - p (loss rate)
    - b = ratio avg_win / avg_loss

    Kelly óptimo puede ser muy agresivo, por eso usamos Kelly fraccional
    (típicamente 25-50% del Kelly óptimo).
    """

    def __init__(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        capital: float = 10000
    ):
        """
        Args:
            win_rate: Tasa de ganancia (0-1)
            avg_win: Ganancia promedio por trade ganador
            avg_loss: Pérdida promedio por trade perdedor (positivo)
            capital: Capital total disponible
        """
        self.win_rate = win_rate
        self.avg_win = abs(avg_win)
        self.avg_loss = abs(avg_loss)
        self.capital = capital

        # Validate
        if win_rate < 0 or win_rate > 1:
            raise ValueError("win_rate debe estar entre 0 y 1")
        if avg_loss == 0:
            self.avg_loss = 0.01  # Prevent division by zero

    @property
    def loss_rate(self) -> float:
        """Probabilidad de perder."""
        return 1 - self.win_rate

    @property
    def win_loss_ratio(self) -> float:
        """Ratio ganancia/pérdida."""
        return self.avg_win / self.avg_loss if self.avg_loss > 0 else 1

    def raw_kelly(self) -> float:
        """
        Calcula el Kelly Criterion crudo.

        Returns:
            float: Fracción óptima del capital (puede ser negativo)
        """
        p = self.win_rate
        q = self.loss_rate
        b = self.win_loss_ratio

        # f* = (p*b - q) / b
        kelly = (p * b - q) / b

        return kelly

    def fractional(self, fraction: float = 0.5) -> float:
        """
        Kelly fraccional (más conservador).

        Args:
            fraction: Fracción del Kelly a usar (0.5 = 50% Kelly)

        Returns:
            float: Fracción del capital a apostar
        """
        raw = self.raw_kelly()

        # Si Kelly es negativo, no apostar
        if raw <= 0:
            return 0

        # Aplicar fracción
        fractional_kelly = raw * fraction

        # Cap máximo en 25% del capital
        return min(fractional_kelly, 0.25)

    def optimal_size_usd(self, fraction: float = 0.5) -> float:
        """
        Tamaño óptimo en USD.

        Returns:
            float: Tamaño de posición en dólares
        """
        return self.capital * self.fractional(fraction)

    def get_metrics(self) -> Dict:
        """Retorna métricas del Kelly Criterion."""
        raw = self.raw_kelly()
        return {
            'win_rate': self.win_rate,
            'loss_rate': self.loss_rate,
            'win_loss_ratio': self.win_loss_ratio,
            'kelly_raw': raw,
            'kelly_25pct': max(0, raw * 0.25),
            'kelly_50pct': max(0, raw * 0.50),
            'kelly_75pct': max(0, raw * 0.75),
            'optimal_size_25pct': self.capital * max(0, raw * 0.25),
            'optimal_size_50pct': self.capital * max(0, raw * 0.50),
            'recommendation': self._get_recommendation()
        }

    def _get_recommendation(self) -> str:
        """Genera recomendación basada en Kelly."""
        raw = self.raw_kelly()

        if raw < 0:
            return "NO OPERAR - Expectativa negativa"
        elif raw < 0.05:
            return "Posición muy pequeña (edge mínimo)"
        elif raw < 0.15:
            return f"Usar 50% Kelly: {self.fractional(0.5)*100:.1f}% del capital"
        elif raw < 0.25:
            return f"Usar 50% Kelly: {self.fractional(0.5)*100:.1f}% del capital"
        else:
            return f"Edge alto pero usar 25% Kelly: {self.fractional(0.25)*100:.1f}% del capital"


class PositionSizer:
    """
    Calculador de tamaño de posición con múltiples métodos.

    Métodos disponibles:
    - 'kelly': Kelly Criterion fraccional (50%)
    - 'kelly_25': Kelly Criterion 25% (muy conservador)
    - 'kelly_75': Kelly Criterion 75% (agresivo)
    - 'fixed': Fixed fractional (porcentaje fijo)
    - 'risk_parity': Risk parity (basado en volatilidad)
    - 'volatility': Volatility-adjusted sizing
    """

    METHODS = ['kelly', 'kelly_25', 'kelly_75', 'fixed', 'risk_parity', 'volatility']

    def __init__(
        self,
        capital: float = 10000,
        method: str = 'kelly',
        max_size_pct: float = 0.30,  # Máximo 30% del capital
        min_size_pct: float = 0.01,  # Mínimo 1% del capital
        default_fixed_pct: float = 0.10  # Para método fixed
    ):
        """
        Args:
            capital: Capital total
            method: Método de sizing
            max_size_pct: Tamaño máximo como fracción del capital
            min_size_pct: Tamaño mínimo como fracción del capital
            default_fixed_pct: Porcentaje fijo para método 'fixed'
        """
        self.capital = capital
        self.method = method
        self.max_size_pct = max_size_pct
        self.min_size_pct = min_size_pct
        self.default_fixed_pct = default_fixed_pct

    def calculate(
        self,
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None,
        volatility: Optional[float] = None,
        target_risk: float = 0.02  # 2% riesgo por trade
    ) -> PositionSizeResult:
        """
        Calcula el tamaño de posición según el método configurado.

        Args:
            win_rate: Win rate (necesario para Kelly)
            avg_win: Ganancia promedio (necesario para Kelly)
            avg_loss: Pérdida promedio (necesario para Kelly)
            volatility: Volatilidad anualizada (necesario para risk_parity)
            target_risk: Riesgo objetivo por trade

        Returns:
            PositionSizeResult con el tamaño calculado
        """
        if self.method == 'kelly':
            return self._kelly_sizing(win_rate, avg_win, avg_loss, fraction=0.5)
        elif self.method == 'kelly_25':
            return self._kelly_sizing(win_rate, avg_win, avg_loss, fraction=0.25)
        elif self.method == 'kelly_75':
            return self._kelly_sizing(win_rate, avg_win, avg_loss, fraction=0.75)
        elif self.method == 'fixed':
            return self._fixed_sizing()
        elif self.method == 'risk_parity':
            return self._risk_parity_sizing(volatility, target_risk)
        elif self.method == 'volatility':
            return self._volatility_sizing(volatility, target_risk)
        else:
            raise ValueError(f"Método desconocido: {self.method}")

    def _kelly_sizing(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float
    ) -> PositionSizeResult:
        """Kelly Criterion sizing."""
        if win_rate is None or avg_win is None or avg_loss is None:
            raise ValueError("Kelly requiere win_rate, avg_win y avg_loss")

        kelly = KellyCriterion(win_rate, avg_win, avg_loss, self.capital)
        raw = kelly.raw_kelly()
        size_pct = kelly.fractional(fraction)

        # Aplicar límites
        size_pct = max(self.min_size_pct, min(size_pct, self.max_size_pct))

        return PositionSizeResult(
            size_pct=size_pct,
            size_usd=self.capital * size_pct,
            method=f'kelly_{int(fraction*100)}pct',
            kelly_raw=raw,
            metadata=kelly.get_metrics()
        )

    def _fixed_sizing(self) -> PositionSizeResult:
        """Fixed fractional sizing."""
        size_pct = self.default_fixed_pct
        return PositionSizeResult(
            size_pct=size_pct,
            size_usd=self.capital * size_pct,
            method='fixed',
            metadata={'description': f'Fixed {size_pct*100:.1f}% of capital'}
        )

    def _risk_parity_sizing(
        self,
        volatility: Optional[float],
        target_risk: float
    ) -> PositionSizeResult:
        """
        Risk parity: igualar contribución al riesgo.

        Si volatilidad es alta, reducir tamaño.
        Si volatilidad es baja, aumentar tamaño.
        """
        if volatility is None:
            volatility = 0.30  # Default 30% annual vol

        # Target risk contribution
        # size * volatility = target_risk * capital
        # size = (target_risk * capital) / volatility
        size_pct = target_risk / volatility

        # Aplicar límites
        size_pct = max(self.min_size_pct, min(size_pct, self.max_size_pct))

        return PositionSizeResult(
            size_pct=size_pct,
            size_usd=self.capital * size_pct,
            method='risk_parity',
            risk_amount=self.capital * target_risk,
            metadata={
                'volatility': volatility,
                'target_risk': target_risk,
                'description': f'Risk parity: {size_pct*100:.1f}% for {volatility*100:.0f}% vol'
            }
        )

    def _volatility_sizing(
        self,
        volatility: Optional[float],
        target_risk: float
    ) -> PositionSizeResult:
        """Volatility-adjusted sizing (similar a risk parity)."""
        return self._risk_parity_sizing(volatility, target_risk)

    def update_capital(self, new_capital: float):
        """Actualiza el capital base."""
        self.capital = new_capital


def calculate_position_from_trades(
    trades: list,
    capital: float = 10000,
    method: str = 'kelly'
) -> PositionSizeResult:
    """
    Calcula tamaño de posición desde historial de trades.

    Args:
        trades: Lista de trades con 'pnl' key
        capital: Capital actual
        method: Método de sizing

    Returns:
        PositionSizeResult
    """
    if not trades:
        # Default si no hay trades
        sizer = PositionSizer(capital, method='fixed')
        return sizer.calculate()

    pnls = [t.get('pnl', 0) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [abs(p) for p in pnls if p < 0]

    win_rate = len(wins) / len(trades) if trades else 0.5
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0

    sizer = PositionSizer(capital, method=method)
    return sizer.calculate(
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss
    )


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("POSITION SIZING - Test")
    print("=" * 60)

    # Test Kelly Criterion
    print("\n--- Kelly Criterion Tests ---")

    # Case 1: Good edge
    kelly1 = KellyCriterion(win_rate=0.55, avg_win=100, avg_loss=80, capital=10000)
    print(f"\nCase 1: WR=55%, AvgWin=$100, AvgLoss=$80")
    print(f"  Win/Loss Ratio: {kelly1.win_loss_ratio:.2f}")
    print(f"  Kelly Raw: {kelly1.raw_kelly():.4f} ({kelly1.raw_kelly()*100:.2f}%)")
    print(f"  Kelly 50%: {kelly1.fractional(0.5):.4f} ({kelly1.fractional(0.5)*100:.2f}%)")
    print(f"  Optimal Size (50%): ${kelly1.optimal_size_usd(0.5):,.2f}")
    print(f"  Recommendation: {kelly1._get_recommendation()}")

    # Case 2: Negative edge
    kelly2 = KellyCriterion(win_rate=0.40, avg_win=100, avg_loss=100, capital=10000)
    print(f"\nCase 2: WR=40%, AvgWin=$100, AvgLoss=$100")
    print(f"  Kelly Raw: {kelly2.raw_kelly():.4f} ({kelly2.raw_kelly()*100:.2f}%)")
    print(f"  Recommendation: {kelly2._get_recommendation()}")

    # Case 3: High edge
    kelly3 = KellyCriterion(win_rate=0.60, avg_win=150, avg_loss=100, capital=10000)
    print(f"\nCase 3: WR=60%, AvgWin=$150, AvgLoss=$100")
    print(f"  Kelly Raw: {kelly3.raw_kelly():.4f} ({kelly3.raw_kelly()*100:.2f}%)")
    print(f"  Kelly 50%: {kelly3.fractional(0.5):.4f} ({kelly3.fractional(0.5)*100:.2f}%)")
    print(f"  Optimal Size (50%): ${kelly3.optimal_size_usd(0.5):,.2f}")

    # Test PositionSizer
    print("\n--- PositionSizer Tests ---")

    sizer = PositionSizer(capital=50000, method='kelly')
    result = sizer.calculate(win_rate=0.55, avg_win=120, avg_loss=90)
    print(f"\nKelly Sizing (50k capital):")
    print(f"  Size: {result.size_pct*100:.2f}% = ${result.size_usd:,.2f}")
    print(f"  Kelly Raw: {result.kelly_raw*100:.2f}%")

    sizer.method = 'fixed'
    result = sizer.calculate()
    print(f"\nFixed Sizing:")
    print(f"  Size: {result.size_pct*100:.2f}% = ${result.size_usd:,.2f}")

    sizer.method = 'risk_parity'
    result = sizer.calculate(volatility=0.40, target_risk=0.02)
    print(f"\nRisk Parity (40% vol, 2% target risk):")
    print(f"  Size: {result.size_pct*100:.2f}% = ${result.size_usd:,.2f}")

    print("\n" + "=" * 60)
    print("Todos los tests completados")
    print("=" * 60 + "\n")
