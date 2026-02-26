#!/usr/bin/env python3
"""
risk_metrics.py - Métricas de Riesgo Profesionales
===================================================

Métricas de riesgo usadas por hedge funds profesionales:
- Sharpe Ratio
- Sortino Ratio (downside risk only)
- Calmar Ratio (return / max drawdown)
- Max Drawdown
- Value at Risk (VaR)
- Expected Shortfall (CVaR)
- Beta / Alpha (vs benchmark)
- Information Ratio
- Tail Ratio

Uso:
    from risk_metrics import ProfessionalRiskMetrics

    metrics = ProfessionalRiskMetrics(returns, benchmark_returns)
    report = metrics.full_report()
"""

import numpy as np
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class RiskReport:
    """Reporte completo de métricas de riesgo."""
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    var_95: float
    cvar_95: float
    beta: Optional[float]
    alpha: Optional[float]
    information_ratio: Optional[float]
    tail_ratio: float
    total_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    expectancy: float


class ProfessionalRiskMetrics:
    """
    Calcula métricas de riesgo profesionales para una serie de returns.

    Compatible con backtest results y paper trading results.
    """

    def __init__(
        self,
        returns: List[float],
        benchmark_returns: Optional[List[float]] = None,
        risk_free_rate: float = 0.02,
        trading_days: int = 252
    ):
        """
        Args:
            returns: Lista de returns por trade (decimales, no porcentajes)
            benchmark_returns: Returns del benchmark (opcional)
            risk_free_rate: Tasa libre de riesgo anual (default 2%)
            trading_days: Días de trading por año
        """
        self.returns = np.array(returns)
        self.benchmark = np.array(benchmark_returns) if benchmark_returns else None
        self.rf = risk_free_rate / trading_days  # Daily risk-free rate
        self.trading_days = trading_days

        # Filter NaN values
        self.returns = self.returns[~np.isnan(self.returns)]
        if self.benchmark is not None:
            self.benchmark = self.benchmark[~np.isnan(self.benchmark)]

    def sharpe_ratio(self) -> float:
        """
        Sharpe Ratio: Return ajustado por volatilidad total.

        SR = (E[R] - Rf) / σ * √252

        Interpretación:
        - < 1.0: Malo
        - 1.0 - 1.5: Bueno
        - 1.5 - 2.0: Muy bueno
        - > 2.0: Excelente (o data error)
        """
        if len(self.returns) < 2:
            return 0.0

        excess = self.returns - self.rf
        std = np.std(excess)

        if std < 1e-10:
            return 0.0

        return float(np.mean(excess) / std * np.sqrt(self.trading_days))

    def sortino_ratio(self) -> float:
        """
        Sortino Ratio: Return ajustado por downside volatility.

        Solo penaliza movimientos hacia abajo, más realista para trading.

        Interpretación: Similar a Sharpe, pero típicamente más alto
        porque ignora upside volatility.
        """
        if len(self.returns) < 2:
            return 0.0

        excess = self.returns - self.rf
        downside = self.returns[self.returns < 0]

        if len(downside) < 2:
            return float('inf') if np.mean(excess) > 0 else 0.0

        downside_std = np.std(downside)

        if downside_std < 1e-10:
            return 0.0

        return float(np.mean(excess) / downside_std * np.sqrt(self.trading_days))

    def max_drawdown(self) -> float:
        """
        Maximum Drawdown: Mayor pérdida desde pico.

        Retorna valor negativo (ej: -0.15 = 15% drawdown).
        """
        if len(self.returns) < 1:
            return 0.0

        # Calculate cumulative returns
        cumulative = np.cumprod(1 + self.returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max

        return float(np.min(drawdowns))

    def calmar_ratio(self) -> float:
        """
        Calmar Ratio: Return anualizado / Max Drawdown.

        CR = (CAGR) / |MaxDD|

        Interpretación:
        - < 0: Pérdida
        - 0 - 1: Malo
        - 1 - 3: Bueno
        - > 3: Excelente
        """
        max_dd = abs(self.max_drawdown())

        if max_dd < 1e-10:
            return 0.0

        # Annualized return
        annual_return = np.mean(self.returns) * self.trading_days

        return float(annual_return / max_dd)

    def value_at_risk(self, confidence: float = 0.95) -> float:
        """
        Value at Risk (VaR): Pérdida máxima esperada con X% confianza.

        "Con 95% confianza, no perderás más de X% por trade."

        Retorna valor negativo.
        """
        if len(self.returns) < 1:
            return 0.0

        return float(np.percentile(self.returns, (1 - confidence) * 100))

    def expected_shortfall(self, confidence: float = 0.95) -> float:
        """
        Expected Shortfall (CVaR): Promedio de pérdidas cuando exceden VaR.

        "Si pierdes más del VaR, cuánto perderás en promedio."

        Más conservador que VaR.
        """
        if len(self.returns) < 1:
            return 0.0

        var = self.value_at_risk(confidence)
        tail_losses = self.returns[self.returns <= var]

        if len(tail_losses) < 1:
            return var

        return float(np.mean(tail_losses))

    def beta(self) -> Optional[float]:
        """
        Beta: Sensibilidad al mercado (vs benchmark).

        β = Cov(Rp, Rm) / Var(Rm)

        Interpretación:
        - β < 1: Menos volátil que mercado
        - β = 1: Igual que mercado
        - β > 1: Más volátil que mercado
        """
        if self.benchmark is None or len(self.benchmark) < 2:
            return None

        # Align lengths
        min_len = min(len(self.returns), len(self.benchmark))
        r = self.returns[:min_len]
        b = self.benchmark[:min_len]

        covariance = np.cov(r, b)[0][1]
        market_variance = np.var(b)

        if market_variance < 1e-10:
            return None

        return float(covariance / market_variance)

    def alpha(self) -> Optional[float]:
        """
        Alpha: Excess return vs benchmark (ajustado por riesgo).

        α = Rp - β * Rm

        Interpretación:
        - α > 0: Estrategia supera al benchmark
        - α = 0: Igual al benchmark
        - α < 0: Estrategia subperforma
        """
        if self.benchmark is None or len(self.benchmark) < 1:
            return None

        beta_val = self.beta()
        if beta_val is None:
            return None

        return float(np.mean(self.returns) - beta_val * np.mean(self.benchmark))

    def information_ratio(self) -> Optional[float]:
        """
        Information Ratio: Return activo / Tracking error.

        IR = (Rp - Rm) / σ(Rp - Rm) * √252

        Interpretación:
        - < 0.5: Malo
        - 0.5 - 1.0: Bueno
        - > 1.0: Excelente
        """
        if self.benchmark is None or len(self.benchmark) < 2:
            return None

        min_len = min(len(self.returns), len(self.benchmark))
        active_return = self.returns[:min_len] - self.benchmark[:min_len]

        tracking_error = np.std(active_return)

        if tracking_error < 1e-10:
            return 0.0

        return float(np.mean(active_return) / tracking_error * np.sqrt(self.trading_days))

    def tail_ratio(self) -> float:
        """
        Tail Ratio: Ratio de colas (detecta fat tails).

        TR = 95th percentile / |5th percentile|

        Interpretación:
        - TR ≈ 1: Distribución simétrica
        - TR > 1: Más upside que downside
        - TR < 1: Más downside que upside (peligro)
        """
        if len(self.returns) < 10:
            return 1.0

        p95 = np.percentile(self.returns, 95)
        p5 = np.percentile(self.returns, 5)

        if abs(p5) < 1e-10:
            return 1.0

        return float(p95 / abs(p5))

    def win_rate(self) -> float:
        """Porcentaje de trades ganadores."""
        if len(self.returns) < 1:
            return 0.0
        return float(np.sum(self.returns > 0) / len(self.returns))

    def avg_win(self) -> float:
        """Ganancia promedio en trades ganadores."""
        wins = self.returns[self.returns > 0]
        return float(np.mean(wins)) if len(wins) > 0 else 0.0

    def avg_loss(self) -> float:
        """Pérdida promedio en trades perdedores."""
        losses = self.returns[self.returns < 0]
        return float(np.mean(losses)) if len(losses) > 0 else 0.0

    def profit_factor(self) -> float:
        """
        Profit Factor: Gross wins / Gross losses.

        Interpretación:
        - PF < 1: Pérdida
        - PF = 1: Break even
        - PF > 1.5: Bueno
        - PF > 2.0: Excelente
        """
        wins = self.returns[self.returns > 0]
        losses = self.returns[self.returns < 0]

        gross_wins = np.sum(wins)
        gross_losses = abs(np.sum(losses))

        if gross_losses < 1e-10:
            return float('inf') if gross_wins > 0 else 0.0

        return float(gross_wins / gross_losses)

    def expectancy(self) -> float:
        """
        Expectancy: Expected return per trade.

        E = (Win% * AvgWin) + (Loss% * AvgLoss)

        Interpretación:
        - E > 0: Sistema rentable
        - E < 0: Sistema perdedor
        """
        wr = self.win_rate()
        aw = self.avg_win()
        al = self.avg_loss()

        return float(wr * aw + (1 - wr) * al)

    def full_report(self) -> RiskReport:
        """Genera reporte completo de métricas."""
        return RiskReport(
            sharpe_ratio=self.sharpe_ratio(),
            sortino_ratio=self.sortino_ratio(),
            calmar_ratio=self.calmar_ratio(),
            max_drawdown=self.max_drawdown(),
            var_95=self.value_at_risk(0.95),
            cvar_95=self.expected_shortfall(0.95),
            beta=self.beta(),
            alpha=self.alpha(),
            information_ratio=self.information_ratio(),
            tail_ratio=self.tail_ratio(),
            total_trades=len(self.returns),
            win_rate=self.win_rate(),
            avg_win=self.avg_win(),
            avg_loss=self.avg_loss(),
            profit_factor=self.profit_factor(),
            expectancy=self.expectancy()
        )

    def to_dict(self) -> Dict:
        """Retorna reporte como diccionario para JSON."""
        report = self.full_report()
        return {
            'sharpe_ratio': round(report.sharpe_ratio, 4),
            'sortino_ratio': round(report.sortino_ratio, 4),
            'calmar_ratio': round(report.calmar_ratio, 4),
            'max_drawdown': round(report.max_drawdown, 4),
            'var_95': round(report.var_95, 4),
            'cvar_95': round(report.cvar_95, 4),
            'beta': round(report.beta, 4) if report.beta is not None else None,
            'alpha': round(report.alpha, 4) if report.alpha is not None else None,
            'information_ratio': round(report.information_ratio, 4) if report.information_ratio is not None else None,
            'tail_ratio': round(report.tail_ratio, 4),
            'total_trades': report.total_trades,
            'win_rate': round(report.win_rate, 4),
            'avg_win': round(report.avg_win, 4),
            'avg_loss': round(report.avg_loss, 4),
            'profit_factor': round(report.profit_factor, 4),
            'expectancy': round(report.expectancy, 4)
        }

    def print_report(self):
        """Imprime reporte formateado."""
        report = self.full_report()

        print("\n" + "=" * 60)
        print("PROFESSIONAL RISK METRICS REPORT")
        print("=" * 60)

        print("\n📊 RETURN METRICS")
        print(f"  Sharpe Ratio:     {report.sharpe_ratio:.4f}")
        print(f"  Sortino Ratio:    {report.sortino_ratio:.4f}")
        print(f"  Calmar Ratio:     {report.calmar_ratio:.4f}")

        print("\n📉 RISK METRICS")
        print(f"  Max Drawdown:     {report.max_drawdown*100:.2f}%")
        print(f"  VaR (95%):        {report.var_95*100:.2f}%")
        print(f"  CVaR (95%):       {report.cvar_95*100:.2f}%")
        print(f"  Tail Ratio:       {report.tail_ratio:.4f}")

        if report.beta is not None:
            print("\n📈 BENCHMARK METRICS")
            print(f"  Beta:             {report.beta:.4f}")
            print(f"  Alpha:            {report.alpha:.4f}")
            print(f"  Info Ratio:       {report.information_ratio:.4f}")

        print("\n💰 TRADE METRICS")
        print(f"  Total Trades:     {report.total_trades}")
        print(f"  Win Rate:         {report.win_rate*100:.2f}%")
        print(f"  Avg Win:          {report.avg_win*100:.2f}%")
        print(f"  Avg Loss:         {report.avg_loss*100:.2f}%")
        print(f"  Profit Factor:    {report.profit_factor:.4f}")
        print(f"  Expectancy:       {report.expectancy*100:.4f}%")

        print("\n" + "=" * 60)


def calculate_metrics_from_trades(trades: List[Dict]) -> Dict:
    """
    Calcula métricas desde lista de trades.

    Args:
        trades: Lista de trades con 'pnl_pct' o 'pnl' key

    Returns:
        Dict con métricas
    """
    if not trades:
        return {'error': 'No trades provided'}

    # Extract returns
    returns = []
    for t in trades:
        if 'pnl_pct' in t:
            returns.append(t['pnl_pct'])
        elif 'pnl' in t:
            # Assume pnl is absolute, need to calculate percentage
            # Use a default position size if not available
            size = t.get('size_usd', 1000)
            returns.append(t['pnl'] / size if size > 0 else 0)

    if not returns:
        return {'error': 'Could not extract returns from trades'}

    metrics = ProfessionalRiskMetrics(returns)
    return metrics.to_dict()


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("RISK METRICS - Test")
    print("=" * 60)

    # Generate sample returns
    np.random.seed(42)

    # Case 1: Good strategy (positive drift)
    good_returns = np.random.normal(0.002, 0.02, 200)  # 0.2% daily return, 2% vol

    print("\n--- Case 1: Good Strategy ---")
    metrics1 = ProfessionalRiskMetrics(good_returns)
    metrics1.print_report()

    # Case 2: Bad strategy (negative drift)
    bad_returns = np.random.normal(-0.001, 0.03, 200)  # -0.1% return, 3% vol

    print("\n--- Case 2: Bad Strategy ---")
    metrics2 = ProfessionalRiskMetrics(bad_returns)
    metrics2.print_report()

    # Case 3: With benchmark
    benchmark = np.random.normal(0.001, 0.015, 200)  # Market returns

    print("\n--- Case 3: Good Strategy vs Benchmark ---")
    metrics3 = ProfessionalRiskMetrics(good_returns, benchmark)
    metrics3.print_report()

    print("\n" + "=" * 60)
    print("Tests completed")
    print("=" * 60 + "\n")
