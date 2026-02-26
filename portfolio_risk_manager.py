#!/usr/bin/env python3
"""
portfolio_risk_manager.py - Portfolio-Level Risk Management (FASE 3C)
======================================================================

Gestión de riesgo a nivel portfolio con:

1. Correlation Matrix - Detectar activos correlacionados
2. Portfolio VaR - Value at Risk agregado
3. Diversification Score - Medir concentración
4. Position Limits - Límites por correlación

Uso:
    from portfolio_risk_manager import PortfolioRiskManager
    risk_mgr = PortfolioRiskManager()
    risk = risk_mgr.calculate_portfolio_risk(positions)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import sqlite3
import os

# ============================================================================
# CONFIGURATION
# ============================================================================

# Correlation thresholds
MAX_CORRELATION = 0.7              # Max correlation between any 2 assets
MAX_SECTOR_CORRELATION = 0.85      # Max correlation within same sector
MIN_DIVERSIFICATION_SCORE = 0.4    # Min diversification (0-1)

# Portfolio limits
MAX_PORTFOLIO_VAAR = 0.05          # Max 5% daily VaR
MAX_SINGLE_ASSET_WEIGHT = 0.25     # Max 25% in single asset
MAX_SECTOR_WEIGHT = 0.50           # Max 50% in same sector

# Asset classification by sector
SECTORS = {
    # Crypto majors
    'BTC': 'crypto_major',
    'ETH': 'crypto_major',
    'SOL': 'crypto_major',

    # Crypto alts
    'XRP': 'crypto_alt',
    'ADA': 'crypto_alt',
    'DOT': 'crypto_alt',
    'LINK': 'crypto_alt',
    'AVAX': 'crypto_alt',
    'DOGE': 'crypto_alt',
    'SUI': 'crypto_alt',
    'XLM': 'crypto_alt',
    'HED': 'crypto_alt',
    'SHIB': 'crypto_alt',
    'LTC': 'crypto_alt',
    'BCH': 'crypto_alt',

    # Commodities
    'GOLD': 'commodity',
    'OIL': 'commodity',
    'NATGAS': 'commodity',
    'COPPER': 'commodity',
    'PLAT': 'commodity',

    # Indices
    'SP500': 'index',
    'SLR': 'crypto_alt',  # Solar/Solana related
}


@dataclass
class PortfolioRiskMetrics:
    """Métricas de riesgo del portfolio."""
    # VaR
    portfolio_var: float            # Portfolio Value at Risk (95%)
    portfolio_cvar: float           # Conditional VaR

    # Correlation
    avg_correlation: float          # Average pairwise correlation
    max_correlation: float          # Maximum correlation
    high_correlation_pairs: List[Tuple[str, str, float]]  # Pairs > 0.7

    # Diversification
    diversification_score: float    # 0-1 (higher = more diversified)
    effective_positions: float      # Number of uncorrelated positions
    herfindahl_index: float         # Concentration measure

    # Sector exposure
    sector_weights: Dict[str, float]
    max_sector_concentration: float

    # Risk limits
    is_within_limits: bool
    warnings: List[str]


class PortfolioRiskManager:
    """
    Portfolio-level risk management with correlation analysis.
    """

    def __init__(self, lookback_days: int = 30):
        """
        Initialize risk manager.

        Args:
            lookback_days: Days of historical data for correlation calc
        """
        self.lookback_days = lookback_days
        self.price_history: Dict[str, pd.Series] = {}
        self.correlation_matrix: Optional[pd.DataFrame] = None

    def load_price_history(self, price_data: Dict[str, pd.Series]):
        """
        Load historical price data for correlation calculation.

        Args:
            price_data: Dict of {asset: price_series}
        """
        self.price_history = price_data

        # Calculate returns
        returns_data = {}
        for asset, prices in price_data.items():
            if len(prices) > 1:
                returns_data[asset] = prices.pct_change().dropna()

        if returns_data:
            returns_df = pd.DataFrame(returns_data)
            self.correlation_matrix = returns_df.corr()

    def calculate_portfolio_risk(
        self,
        positions: Dict[str, Dict],
        total_capital: float
    ) -> PortfolioRiskMetrics:
        """
        Calculate comprehensive portfolio risk metrics.

        Args:
            positions: Dict of {asset: {'value': float, 'pnl_history': list}}
            total_capital: Total portfolio capital

        Returns:
            PortfolioRiskMetrics with all risk measures
        """
        warnings = []

        # 1. Calculate position weights
        weights = {}
        total_value = sum(p.get('value', 0) for p in positions.values())

        for asset, pos in positions.items():
            if total_value > 0:
                weights[asset] = pos.get('value', 0) / total_value
            else:
                weights[asset] = 0

        # 2. Calculate correlation metrics
        avg_corr = 0.0
        max_corr = 0.0
        high_corr_pairs = []

        if self.correlation_matrix is not None and len(weights) > 1:
            assets = [a for a in weights.keys() if a in self.correlation_matrix.columns]

            if len(assets) >= 2:
                correlations = []
                for i, a1 in enumerate(assets):
                    for a2 in assets[i+1:]:
                        if a1 in self.correlation_matrix.index and a2 in self.correlation_matrix.columns:
                            corr = abs(self.correlation_matrix.loc[a1, a2])
                            correlations.append(corr)

                            if corr > MAX_CORRELATION:
                                high_corr_pairs.append((a1, a2, corr))

                            if corr > max_corr:
                                max_corr = corr

                if correlations:
                    avg_corr = np.mean(correlations)

        # 3. Calculate diversification score
        if weights:
            # Herfindahl-Hirschman Index (lower = more diversified)
            hhi = sum(w**2 for w in weights.values())

            # Effective number of positions
            effective_positions = 1 / hhi if hhi > 0 else 1

            # Diversification score (0-1)
            max_hhi = 1.0  # All in one asset
            min_hhi = 1 / len(weights)  # Equal weight
            diversification_score = 1 - (hhi - min_hhi) / (max_hhi - min_hhi) if len(weights) > 1 else 0
        else:
            hhi = 0
            effective_positions = 0
            diversification_score = 1.0

        # 4. Calculate sector weights
        sector_weights = {}
        for asset, weight in weights.items():
            sector = SECTORS.get(asset, 'other')
            sector_weights[sector] = sector_weights.get(sector, 0) + weight

        max_sector_concentration = max(sector_weights.values()) if sector_weights else 0

        # 5. Calculate portfolio VaR
        portfolio_var = 0.0
        portfolio_cvar = 0.0

        if positions:
            # Aggregate daily PnLs
            all_pnls = []
            for asset, pos in positions.items():
                pnl_history = pos.get('pnl_history', [])
                if pnl_history:
                    all_pnls.extend(pnl_history)

            if all_pnls:
                all_pnls = np.array(all_pnls)
                portfolio_var = abs(np.percentile(all_pnls, 5)) / total_capital if total_capital > 0 else 0
                cvar_threshold = np.percentile(all_pnls, 5)
                tail_losses = all_pnls[all_pnls <= cvar_threshold]
                portfolio_cvar = abs(np.mean(tail_losses)) / total_capital if len(tail_losses) > 0 and total_capital > 0 else 0

        # 6. Check limits
        is_within_limits = True

        if max_corr > MAX_CORRELATION:
            is_within_limits = False
            warnings.append(f"High correlation: {max_corr:.1%} > {MAX_CORRELATION:.1%}")

        if max(weights.values()) > MAX_SINGLE_ASSET_WEIGHT:
            is_within_limits = False
            warnings.append(f"Single asset > {MAX_SINGLE_ASSET_WEIGHT:.0%}: {max(weights.values()):.1%}")

        if max_sector_concentration > MAX_SECTOR_WEIGHT:
            is_within_limits = False
            warnings.append(f"Sector concentration: {max_sector_concentration:.1%} > {MAX_SECTOR_WEIGHT:.0%}")

        if diversification_score < MIN_DIVERSIFICATION_SCORE:
            warnings.append(f"Low diversification: {diversification_score:.1%} < {MIN_DIVERSIFICATION_SCORE:.1%}")

        if portfolio_var > MAX_PORTFOLIO_VAAR:
            is_within_limits = False
            warnings.append(f"Portfolio VaR high: {portfolio_var:.1%} > {MAX_PORTFOLIO_VAAR:.1%}")

        return PortfolioRiskMetrics(
            portfolio_var=portfolio_var,
            portfolio_cvar=portfolio_cvar,
            avg_correlation=avg_corr,
            max_correlation=max_corr,
            high_correlation_pairs=high_corr_pairs,
            diversification_score=diversification_score,
            effective_positions=effective_positions,
            herfindahl_index=hhi,
            sector_weights=sector_weights,
            max_sector_concentration=max_sector_concentration,
            is_within_limits=is_within_limits,
            warnings=warnings
        )

    def suggest_position_adjustments(
        self,
        positions: Dict[str, Dict],
        total_capital: float
    ) -> List[Dict]:
        """
        Suggest position adjustments to improve portfolio risk.

        Returns:
            List of adjustment suggestions
        """
        metrics = self.calculate_portfolio_risk(positions, total_capital)
        suggestions = []

        # Reduce high correlation pairs
        for a1, a2, corr in metrics.high_correlation_pairs:
            suggestions.append({
                'type': 'reduce_correlation',
                'assets': [a1, a2],
                'correlation': corr,
                'suggestion': f"Reduce exposure to {a1} or {a2} (correlation: {corr:.1%})"
            })

        # Reduce concentration
        if metrics.herfindahl_index > 0.25:
            suggestions.append({
                'type': 'diversify',
                'current_hhi': metrics.herfindahl_index,
                'suggestion': f"Diversify more. Current concentration: {metrics.herfindahl_index:.1%}"
            })

        # Sector concentration
        for sector, weight in metrics.sector_weights.items():
            if weight > MAX_SECTOR_WEIGHT:
                suggestions.append({
                    'type': 'sector_concentration',
                    'sector': sector,
                    'weight': weight,
                    'suggestion': f"Reduce {sector} exposure from {weight:.1%} to < {MAX_SECTOR_WEIGHT:.0%}"
                })

        return suggestions

    def print_risk_report(self, metrics: PortfolioRiskMetrics):
        """Print formatted risk report."""
        print("\n" + "="*60)
        print("        📊 PORTFOLIO RISK REPORT")
        print("="*60)

        print(f"\n📉 Value at Risk:")
        print(f"   VaR (95%):  {metrics.portfolio_var*100:>6.2f}%")
        print(f"   CVaR (95%): {metrics.portfolio_cvar*100:>6.2f}%")

        print(f"\n🔗 Correlation Analysis:")
        print(f"   Average: {metrics.avg_correlation*100:>6.1f}%")
        print(f"   Maximum: {metrics.max_correlation*100:>6.1f}% {'🟢' if metrics.max_correlation < MAX_CORRELATION else '🔴'}")

        if metrics.high_correlation_pairs:
            print(f"   High correlation pairs:")
            for a1, a2, corr in metrics.high_correlation_pairs[:3]:
                print(f"      • {a1} ↔ {a2}: {corr:.1%}")

        print(f"\n🎯 Diversification:")
        print(f"   Score: {metrics.diversification_score*100:>6.1f}% {'🟢' if metrics.diversification_score >= MIN_DIVERSIFICATION_SCORE else '🔴'}")
        print(f"   Effective Positions: {metrics.effective_positions:.1f}")
        print(f"   Concentration (HHI): {metrics.herfindahl_index*100:.1f}%")

        print(f"\n📊 Sector Exposure:")
        for sector, weight in sorted(metrics.sector_weights.items(), key=lambda x: -x[1]):
            status = "🔴" if weight > MAX_SECTOR_WEIGHT else ""
            print(f"   {sector}: {weight*100:.1f}% {status}")

        print(f"\n{'✅ WITHIN LIMITS' if metrics.is_within_limits else '⚠️ LIMITS EXCEEDED'}")

        if metrics.warnings:
            print("\n⚠️ Warnings:")
            for w in metrics.warnings:
                print(f"   • {w}")

        print("="*60)


# ============================================================================
# INTEGRATION WITH LIVE TRADING
# ============================================================================

def check_portfolio_risk_before_trade(
    current_positions: Dict[str, Dict],
    new_trade: Dict,
    total_capital: float
) -> Tuple[bool, str]:
    """
    Check if new trade would violate portfolio risk limits.

    Args:
        current_positions: Current open positions
        new_trade: Proposed new trade {'asset': str, 'value': float}
        total_capital: Total capital

    Returns:
        (approved: bool, reason: str)
    """
    risk_mgr = PortfolioRiskManager()

    # Simulate new portfolio
    simulated = current_positions.copy()
    asset = new_trade.get('asset', 'UNKNOWN')

    if asset in simulated:
        simulated[asset]['value'] = simulated[asset].get('value', 0) + new_trade.get('value', 0)
    else:
        simulated[asset] = {'value': new_trade.get('value', 0)}

    # Calculate risk
    metrics = risk_mgr.calculate_portfolio_risk(simulated, total_capital)

    if not metrics.is_within_limits:
        return False, f"Portfolio risk limits exceeded: {'; '.join(metrics.warnings)}"

    return True, "Approved"


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    print("Portfolio Risk Manager - FASE 3C")
    print("Testing with sample positions...\n")

    # Sample positions
    positions = {
        'BTC': {'value': 30000, 'pnl_history': np.random.normal(0, 100, 100).tolist()},
        'ETH': {'value': 20000, 'pnl_history': np.random.normal(0, 80, 100).tolist()},
        'SOL': {'value': 10000, 'pnl_history': np.random.normal(0, 60, 100).tolist()},
        'GOLD': {'value': 15000, 'pnl_history': np.random.normal(0, 40, 100).tolist()},
    }

    total_capital = 100000

    # Generate sample price history
    np.random.seed(42)
    n_days = 30
    price_data = {
        'BTC': pd.Series(50000 * (1 + np.random.normal(0.001, 0.02, n_days)).cumprod()),
        'ETH': pd.Series(3000 * (1 + np.random.normal(0.001, 0.025, n_days)).cumprod()),
        'SOL': pd.Series(100 * (1 + np.random.normal(0.001, 0.03, n_days)).cumprod()),
        'GOLD': pd.Series(2000 * (1 + np.random.normal(0.0005, 0.01, n_days)).cumprod()),
    }

    risk_mgr = PortfolioRiskManager()
    risk_mgr.load_price_history(price_data)

    metrics = risk_mgr.calculate_portfolio_risk(positions, total_capital)
    risk_mgr.print_risk_report(metrics)

    # Suggestions
    suggestions = risk_mgr.suggest_position_adjustments(positions, total_capital)
    if suggestions:
        print("\n💡 Suggested Adjustments:")
        for s in suggestions:
            print(f"   • {s['suggestion']}")
