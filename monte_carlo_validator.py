#!/usr/bin/env python3
"""
monte_carlo_validator.py - Monte Carlo Validation for Strategy Robustness (FASE 3C)
====================================================================================

Valida la robustez de estrategias usando Monte Carlo simulation:

1. Toma los trades de una estrategia
2. Randomiza el orden 1000 veces
3. Calcula PnL distribution, VaR, CVaR
4. Calcula Probability of Ruin
5. Determina si la estrategia es estadísticamente robusta

Uso:
    from monte_carlo_validator import MonteCarloValidator
    validator = MonteCarloValidator(trades, initial_capital=10000)
    results = validator.run_simulation(n_simulations=1000)
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time

# ============================================================================
# MONTE CARLO CONFIGURATION
# ============================================================================

DEFAULT_N_SIMULATIONS = 1000
DEFAULT_CONFIDENCE_LEVEL = 0.95  # 95% for VaR

# Risk thresholds
MAX_PROBABILITY_OF_RUIN = 0.05    # Max 5% chance of ruin
MIN_ROBUSTNESS_PERCENTILE = 0.10  # 10th percentile must be positive
MAX_VAR_THRESHOLD = 0.15          # Max 15% VaR


@dataclass
class MonteCarloResult:
    """Resultados de Monte Carlo simulation."""
    # PnL Distribution
    mean_pnl: float
    median_pnl: float
    std_pnl: float

    # Percentiles
    pnl_5th: float
    pnl_10th: float
    pnl_25th: float
    pnl_75th: float
    pnl_90th: float
    pnl_95th: float

    # Risk Metrics
    var_95: float              # Value at Risk (95%)
    cvar_95: float             # Conditional VaR (Expected Shortfall)
    probability_of_ruin: float # Probability of losing >50% capital
    max_drawdown_avg: float

    # Robustness
    robustness_score: float    # 0-100
    is_robust: bool
    pass_rate: float           # % of simulations profitable

    # Raw data
    simulation_results: np.ndarray


class MonteCarloValidator:
    """
    Monte Carlo simulation for strategy validation.
    """

    def __init__(
        self,
        trades: List[Dict],
        initial_capital: float = 10000.0,
        max_loss_pct: float = 0.50,  # Ruin threshold
    ):
        """
        Initialize Monte Carlo validator.

        Args:
            trades: List of trade dicts with 'pnl' key
            initial_capital: Starting capital
            max_loss_pct: % loss considered "ruin" (default 50%)
        """
        self.trades = trades
        self.initial_capital = initial_capital
        self.max_loss_pct = max_loss_pct
        self.ruin_threshold = initial_capital * (1 - max_loss_pct)

        # Extract PnLs
        self.trade_pnls = np.array([t.get('pnl', 0) for t in trades if 'pnl' in t])

        if len(self.trade_pnls) == 0:
            raise ValueError("No valid trades with 'pnl' key found")

    def run_simulation(
        self,
        n_simulations: int = DEFAULT_N_SIMULATIONS,
        seed: Optional[int] = None,
        progress_callback=None
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation by randomizing trade order.

        Args:
            n_simulations: Number of random scenarios
            seed: Random seed for reproducibility
            progress_callback: Optional callback for progress

        Returns:
            MonteCarloResult with all metrics
        """
        if seed is not None:
            np.random.seed(seed)

        n_trades = len(self.trade_pnls)
        simulation_pnls = np.zeros(n_simulations)
        simulation_max_dds = np.zeros(n_simulations)
        simulation_ruins = np.zeros(n_simulations)

        for i in range(n_simulations):
            # Shuffle trade order
            shuffled_pnls = np.random.permutation(self.trade_pnls)

            # Calculate cumulative PnL
            cumulative = np.cumsum(shuffled_pnls)
            final_pnl = cumulative[-1]

            # Calculate max drawdown
            peak = np.maximum.accumulate(np.concatenate([[0], cumulative]))
            drawdowns = (peak[1:] - cumulative) / (self.initial_capital + peak[:-1] + 1e-10)
            max_dd = np.max(drawdowns) if len(drawdowns) > 0 else 0

            # Check for ruin
            min_capital = self.initial_capital + np.min(cumulative)
            is_ruin = min_capital < self.ruin_threshold

            simulation_pnls[i] = final_pnl
            simulation_max_dds[i] = max_dd
            simulation_ruins[i] = 1 if is_ruin else 0

            if progress_callback and (i + 1) % 100 == 0:
                progress_callback(i + 1, n_simulations)

        # Calculate statistics
        mean_pnl = np.mean(simulation_pnls)
        median_pnl = np.median(simulation_pnls)
        std_pnl = np.std(simulation_pnls)

        # Percentiles
        pnl_5th = np.percentile(simulation_pnls, 5)
        pnl_10th = np.percentile(simulation_pnls, 10)
        pnl_25th = np.percentile(simulation_pnls, 25)
        pnl_75th = np.percentile(simulation_pnls, 75)
        pnl_90th = np.percentile(simulation_pnls, 90)
        pnl_95th = np.percentile(simulation_pnls, 95)

        # VaR and CVaR
        var_95 = -pnl_95th / self.initial_capital  # 95% VaR (worst 5%)
        cvar_95 = -np.mean(simulation_pnls[simulation_pnls <= pnl_5th]) / self.initial_capital

        # Probability of Ruin
        probability_of_ruin = np.mean(simulation_ruins)

        # Average max drawdown
        max_drawdown_avg = np.mean(simulation_max_dds)

        # Pass rate (% profitable)
        pass_rate = np.mean(simulation_pnls > 0)

        # Robustness score (0-100)
        robustness_score = self._calculate_robustness_score(
            mean_pnl=mean_pnl,
            pnl_10th=pnl_10th,
            std_pnl=std_pnl,
            probability_of_ruin=probability_of_ruin,
            pass_rate=pass_rate,
            var_95=var_95
        )

        # Is robust?
        is_robust = (
            probability_of_ruin <= MAX_PROBABILITY_OF_RUIN and
            pnl_10th > 0 and
            var_95 <= MAX_VAR_THRESHOLD
        )

        return MonteCarloResult(
            mean_pnl=mean_pnl,
            median_pnl=median_pnl,
            std_pnl=std_pnl,
            pnl_5th=pnl_5th,
            pnl_10th=pnl_10th,
            pnl_25th=pnl_25th,
            pnl_75th=pnl_75th,
            pnl_90th=pnl_90th,
            pnl_95th=pnl_95th,
            var_95=var_95,
            cvar_95=cvar_95,
            probability_of_ruin=probability_of_ruin,
            max_drawdown_avg=max_drawdown_avg,
            robustness_score=robustness_score,
            is_robust=is_robust,
            pass_rate=pass_rate,
            simulation_results=simulation_pnls
        )

    def _calculate_robustness_score(
        self,
        mean_pnl: float,
        pnl_10th: float,
        std_pnl: float,
        probability_of_ruin: float,
        pass_rate: float,
        var_95: float
    ) -> float:
        """
        Calculate overall robustness score (0-100).

        Components:
        - Mean PnL positive (25 points)
        - 10th percentile positive (25 points)
        - Low volatility (15 points)
        - Low probability of ruin (20 points)
        - High pass rate (15 points)
        """
        score = 0.0

        # Mean PnL positive
        if mean_pnl > 0:
            score += 25
            if mean_pnl > self.initial_capital * 0.1:  # >10% return
                score += 5

        # 10th percentile positive (worst case still profitable)
        if pnl_10th > 0:
            score += 25
        elif pnl_10th > -self.initial_capital * 0.05:  # <5% loss
            score += 10

        # Low volatility (Sharpe-like)
        if std_pnl > 0:
            sharpe_like = mean_pnl / std_pnl
            if sharpe_like > 1.0:
                score += 15
            elif sharpe_like > 0.5:
                score += 10
            elif sharpe_like > 0:
                score += 5

        # Low probability of ruin
        if probability_of_ruin < 0.01:
            score += 20
        elif probability_of_ruin < 0.05:
            score += 15
        elif probability_of_ruin < 0.10:
            score += 10
        elif probability_of_ruin < 0.20:
            score += 5

        # High pass rate
        if pass_rate > 0.90:
            score += 15
        elif pass_rate > 0.80:
            score += 12
        elif pass_rate > 0.70:
            score += 8
        elif pass_rate > 0.60:
            score += 4

        return min(score, 100.0)

    def print_summary(self, result: MonteCarloResult):
        """Print formatted summary of results."""
        print("\n" + "="*60)
        print("           MONTE CARLO VALIDATION RESULTS")
        print("="*60)

        print(f"\n📊 PnL Distribution ({len(self.trade_pnls)} trades, 1000 sims):")
        print(f"   Mean:   ${result.mean_pnl:>10.2f}")
        print(f"   Median: ${result.median_pnl:>10.2f}")
        print(f"   Std:    ${result.std_pnl:>10.2f}")

        print(f"\n📈 Percentiles:")
        print(f"   5th:  ${result.pnl_5th:>10.2f}")
        print(f"   10th: ${result.pnl_10th:>10.2f}  {'🟢' if result.pnl_10th > 0 else '🔴'}")
        print(f"   25th: ${result.pnl_25th:>10.2f}")
        print(f"   75th: ${result.pnl_75th:>10.2f}")
        print(f"   95th: ${result.pnl_95th:>10.2f}")

        print(f"\n⚠️ Risk Metrics:")
        print(f"   VaR (95%):     {result.var_95*100:>6.1f}%")
        print(f"   CVaR (95%):    {result.cvar_95*100:>6.1f}%")
        print(f"   Prob of Ruin:  {result.probability_of_ruin*100:>6.1f}%  {'🟢' if result.probability_of_ruin < 0.05 else '🔴'}")
        print(f"   Avg Max DD:    {result.max_drawdown_avg*100:>6.1f}%")

        print(f"\n✅ Robustness:")
        print(f"   Score:     {result.robustness_score:>5.0f}/100")
        print(f"   Pass Rate: {result.pass_rate*100:>5.1f}%")
        print(f"   Is Robust: {'✅ YES' if result.is_robust else '❌ NO'}")

        print("="*60)


# ============================================================================
# KELLY CRITERION (Task #15)
# ============================================================================

def calculate_kelly_fraction(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    safety_factor: float = 0.5  # Half-Kelly by default
) -> float:
    """
    Calculate Kelly Criterion optimal position size.

    Kelly = W - (1-W)/R
    where W = win rate, R = avg_win/avg_loss

    Args:
        win_rate: Win rate (0-1)
        avg_win: Average winning trade
        avg_loss: Average losing trade (positive number)
        safety_factor: Fraction of Kelly to use (0.5 = half-Kelly)

    Returns:
        Optimal fraction of capital to risk
    """
    if avg_loss <= 0:
        return 0.0

    r = avg_win / avg_loss  # Win/loss ratio
    kelly = win_rate - (1 - win_rate) / r

    # Apply safety factor
    kelly = kelly * safety_factor

    # Cap at 25% max
    return max(0, min(kelly, 0.25))


def calculate_kelly_from_trades(trades: List[Dict]) -> float:
    """Calculate Kelly fraction from trade history."""
    wins = [t['pnl'] for t in trades if t.get('pnl', 0) > 0]
    losses = [abs(t['pnl']) for t in trades if t.get('pnl', 0) < 0]

    if len(wins) + len(losses) == 0:
        return 0.0

    win_rate = len(wins) / (len(wins) + len(losses))
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0

    return calculate_kelly_fraction(win_rate, avg_win, avg_loss)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monte Carlo Validator")
    parser.add_argument("--test", action="store_true", help="Run test simulation")
    parser.add_argument("--n-sims", type=int, default=1000, help="Number of simulations")
    args = parser.parse_args()

    if args.test:
        # Generate sample trades
        np.random.seed(42)
        n_trades = 100

        # Simulate trades with slight positive edge
        trades = []
        for i in range(n_trades):
            if np.random.random() < 0.55:  # 55% win rate
                pnl = np.random.exponential(50)  # Avg win $50
            else:
                pnl = -np.random.exponential(40)  # Avg loss $40
            trades.append({'pnl': pnl})

        print(f"Generated {n_trades} sample trades")
        print(f"Win rate: {sum(1 for t in trades if t['pnl'] > 0) / n_trades * 100:.1f}%")

        # Run Monte Carlo
        validator = MonteCarloValidator(trades, initial_capital=10000)
        result = validator.run_simulation(n_simulations=args.n_sims)

        validator.print_summary(result)

        # Kelly
        kelly = calculate_kelly_from_trades(trades)
        print(f"\n💰 Kelly Criterion (Half-Kelly): {kelly*100:.1f}% of capital")

    else:
        parser.print_help()
