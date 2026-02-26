#!/usr/bin/env python3
"""
production_checklist.py - Checklist Pre-Producción
===================================================

Verifica que una estrategia está lista para capital real.
TODOS los criterios deben pasar antes de operar con dinero real.

Uso:
    from production_checklist import ProductionReadinessChecklist

    checklist = ProductionReadinessChecklist(backtest_results, oos_results, paper_results)
    if checklist.is_ready():
        print("Estrategia lista para producción")
    else:
        checklist.print_report()
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class CheckResult:
    """Result of a single check."""
    name: str
    passed: bool
    actual: float
    threshold: float
    description: str


class ProductionReadinessChecklist:
    """
    Verifica que la estrategia está lista para capital real.

    TODOS los criterios deben pasar para ser apto para producción.
    Estos criterios están basados en prácticas de hedge funds profesionales.
    """

    # === THRESHOLDS ===
    MIN_TRADES = 100              # Mínimo 100 trades para significancia estadística
    MIN_WIN_RATE = 0.40           # Win rate mínimo 40%
    MAX_WIN_RATE = 0.65           # Win rate máximo 65% (evitar overfitting)
    MIN_SHARPE = 1.0              # Sharpe ratio mínimo 1.0
    MIN_SORTINO = 1.5             # Sortino ratio mínimo 1.5
    MAX_DRAWDOWN = 0.20           # Máximo drawdown 20%
    MAX_OVERFIT_SCORE = 0.30      # Máximo 30% degradación OOS
    MIN_REGIME_CONSISTENCY = 0.50 # Consistencia mínima entre regímenes
    MIN_PAPER_DAYS = 30           # Mínimo 30 días de paper trading
    MIN_PAPER_TRADES = 20         # Mínimo 20 trades en paper trading

    def __init__(
        self,
        backtest_results: Dict,
        oos_results: Optional[Dict] = None,
        paper_results: Optional[Dict] = None,
        regime_results: Optional[Dict] = None
    ):
        """
        Args:
            backtest_results: Resultados del backtest en-sample
                - trades: int
                - win_rate: float (0-1)
                - sharpe_ratio: float
                - sortino_ratio: float
                - max_drawdown: float (0-1)
                - pnl: float

            oos_results: Resultados out-of-sample (walk-forward validation)
                - pnl: float
                - trades: int
                - overfit_score: float (0-1)

            paper_results: Resultados de paper trading
                - days: int (días de paper trading)
                - trades: int
                - pnl: float
                - win_rate: float

            regime_results: Resultados por régimen de mercado
                - consistency_score: float (0-1)
                - regimes: dict {regime_name: pnl}
        """
        self.backtest = backtest_results
        self.oos = oos_results or {}
        self.paper = paper_results or {}
        self.regime = regime_results or {}
        self.checks: List[CheckResult] = []

    def run_all_checks(self) -> List[CheckResult]:
        """Ejecuta todas las verificaciones y retorna resultados."""
        self.checks = []

        # === BACKTEST CHECKS ===
        self._check_min_trades()
        self._check_win_rate()
        self._check_sharpe_ratio()
        self._check_max_drawdown()

        # === OOS CHECKS ===
        if self.oos:
            self._check_overfit_score()

        # === REGIME CHECKS ===
        if self.regime:
            self._check_regime_consistency()

        # === PAPER TRADING CHECKS ===
        if self.paper:
            self._check_paper_duration()
            self._check_paper_trades()
            self._check_paper_profitability()

        return self.checks

    def _check_min_trades(self):
        """Mínimo número de trades para significancia estadística."""
        trades = self.backtest.get('trades', 0)
        passed = trades >= self.MIN_TRADES
        self.checks.append(CheckResult(
            name="Mínimo Trades",
            passed=passed,
            actual=trades,
            threshold=self.MIN_TRADES,
            description=f"Se requieren al menos {self.MIN_TRADES} trades para significancia estadística"
        ))

    def _check_win_rate(self):
        """Win rate en rango aceptable (evitar overfitting)."""
        win_rate = self.backtest.get('win_rate', 0)
        passed = self.MIN_WIN_RATE <= win_rate <= self.MAX_WIN_RATE
        self.checks.append(CheckResult(
            name="Win Rate",
            passed=passed,
            actual=win_rate,
            threshold=(self.MIN_WIN_RATE, self.MAX_WIN_RATE),
            description=f"Win rate debe estar entre {self.MIN_WIN_RATE*100:.0f}% y {self.MAX_WIN_RATE*100:.0f}%"
        ))

    def _check_sharpe_ratio(self):
        """Sharpe ratio mínimo para return ajustado por riesgo."""
        sharpe = self.backtest.get('sharpe_ratio', 0)
        passed = sharpe >= self.MIN_SHARPE
        self.checks.append(CheckResult(
            name="Sharpe Ratio",
            passed=passed,
            actual=sharpe,
            threshold=self.MIN_SHARPE,
            description=f"Sharpe ratio mínimo {self.MIN_SHARPE} (preferiblemente > 1.5)"
        ))

    def _check_max_drawdown(self):
        """Máximo drawdown aceptable."""
        max_dd = abs(self.backtest.get('max_drawdown', 1))
        passed = max_dd <= self.MAX_DRAWDOWN
        self.checks.append(CheckResult(
            name="Max Drawdown",
            passed=passed,
            actual=max_dd,
            threshold=self.MAX_DRAWDOWN,
            description=f"Drawdown máximo {self.MAX_DRAWDOWN*100:.0f}% (preferiblemente < 15%)"
        ))

    def _check_overfit_score(self):
        """Degradación out-of-sample aceptable."""
        overfit = self.oos.get('overfit_score', 1)
        passed = overfit <= self.MAX_OVERFIT_SCORE
        self.checks.append(CheckResult(
            name="Overfit Score",
            passed=passed,
            actual=overfit,
            threshold=self.MAX_OVERFIT_SCORE,
            description=f"Degradación OOS máxima {self.MAX_OVERFIT_SCORE*100:.0f}%"
        ))

    def _check_regime_consistency(self):
        """Consistencia entre diferentes regímenes de mercado."""
        consistency = self.regime.get('consistency_score', 0)
        passed = consistency >= self.MIN_REGIME_CONSISTENCY
        self.checks.append(CheckResult(
            name="Regime Consistency",
            passed=passed,
            actual=consistency,
            threshold=self.MIN_REGIME_CONSISTENCY,
            description=f"Consistencia mínima {self.MIN_REGIME_CONSISTENCY*100:.0f}% entre regímenes"
        ))

    def _check_paper_duration(self):
        """Días mínimos de paper trading."""
        days = self.paper.get('days', 0)
        passed = days >= self.MIN_PAPER_DAYS
        self.checks.append(CheckResult(
            name="Paper Trading Días",
            passed=passed,
            actual=days,
            threshold=self.MIN_PAPER_DAYS,
            description=f"Mínimo {self.MIN_PAPER_DAYS} días de paper trading"
        ))

    def _check_paper_trades(self):
        """Trades mínimos en paper trading."""
        trades = self.paper.get('trades', 0)
        passed = trades >= self.MIN_PAPER_TRADES
        self.checks.append(CheckResult(
            name="Paper Trading Trades",
            passed=passed,
            actual=trades,
            threshold=self.MIN_PAPER_TRADES,
            description=f"Mínimo {self.MIN_PAPER_TRADES} trades en paper trading"
        ))

    def _check_paper_profitability(self):
        """Paper trading debe ser rentable."""
        pnl = self.paper.get('pnl', 0)
        passed = pnl > 0
        self.checks.append(CheckResult(
            name="Paper Trading PnL",
            passed=passed,
            actual=pnl,
            threshold=0,
            description="Paper trading debe ser rentable"
        ))

    def is_ready(self) -> bool:
        """Retorna True solo si TODOS los checks pasan."""
        if not self.checks:
            self.run_all_checks()
        return all(c.passed for c in self.checks)

    def get_passed_count(self) -> int:
        """Número de checks que pasaron."""
        return sum(1 for c in self.checks if c.passed)

    def get_failed_checks(self) -> List[CheckResult]:
        """Retorna lista de checks que fallaron."""
        return [c for c in self.checks if not c.passed]

    def print_report(self):
        """Imprime reporte detallado."""
        if not self.checks:
            self.run_all_checks()

        print("\n" + "=" * 60)
        print("CHECKLIST PRE-PRODUCCIÓN")
        print("=" * 60)

        for check in self.checks:
            status = "✅" if check.passed else "❌"
            print(f"\n{status} {check.name}")
            print(f"   Actual: {check.actual:.4f}" if isinstance(check.actual, float) else f"   Actual: {check.actual}")
            if isinstance(check.threshold, tuple):
                print(f"   Rango: {check.threshold[0]:.2f} - {check.threshold[1]:.2f}")
            else:
                print(f"   Umbral: {check.threshold}")
            print(f"   {check.description}")

        print("\n" + "=" * 60)
        passed = self.get_passed_count()
        total = len(self.checks)
        print(f"RESULTADO: {passed}/{total} checks pasados")

        if self.is_ready():
            print("✅ ESTRATEGIA LISTA PARA PRODUCCIÓN")
        else:
            print("❌ ESTRATEGIA NO LISTA - Revisar checks fallidos")
        print("=" * 60 + "\n")

    def to_dict(self) -> Dict:
        """Retorna resultados como diccionario para API/JSON."""
        if not self.checks:
            self.run_all_checks()

        return {
            'is_ready': self.is_ready(),
            'passed_count': self.get_passed_count(),
            'total_checks': len(self.checks),
            'checks': [
                {
                    'name': c.name,
                    'passed': c.passed,
                    'actual': c.actual,
                    'threshold': c.threshold,
                    'description': c.description
                }
                for c in self.checks
            ]
        }


def check_strategy_from_db(strategy_id: int, db_path: str = "coordinator.db") -> Dict:
    """
    Verifica una estrategia específica de la base de datos.

    Args:
        strategy_id: ID de la estrategia en la tabla results
        db_path: Path a la base de datos SQLite

    Returns:
        Dict con resultado del checklist
    """
    import sqlite3

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Get backtest results
    c.execute("""
        SELECT trades, win_rate, sharpe_ratio, max_drawdown, pnl
        FROM results WHERE id = ?
    """, (strategy_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return {'error': f'Estrategia {strategy_id} no encontrada'}

    backtest = {
        'trades': row[0],
        'win_rate': row[1],
        'sharpe_ratio': row[2],
        'max_drawdown': row[3],
        'pnl': row[4]
    }

    checklist = ProductionReadinessChecklist(backtest)
    return checklist.to_dict()


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PRODUCTION CHECKLIST - Test")
    print("=" * 60)

    # Test case 1: Good strategy
    good_backtest = {
        'trades': 150,
        'win_rate': 0.55,
        'sharpe_ratio': 1.8,
        'sortino_ratio': 2.2,
        'max_drawdown': 0.12,
        'pnl': 5000
    }

    good_oos = {
        'pnl': 3500,
        'trades': 45,
        'overfit_score': 0.25
    }

    good_paper = {
        'days': 35,
        'trades': 28,
        'pnl': 150,
        'win_rate': 0.52
    }

    print("\n--- Test Case 1: Good Strategy ---")
    checklist = ProductionReadinessChecklist(good_backtest, good_oos, good_paper)
    checklist.print_report()

    # Test case 2: Overfitted strategy
    overfit_backtest = {
        'trades': 8,
        'win_rate': 0.95,  # Too high - suspicious
        'sharpe_ratio': 5.0,
        'sortino_ratio': 6.0,
        'max_drawdown': 0.02,
        'pnl': 10000
    }

    print("\n--- Test Case 2: Overfitted Strategy ---")
    checklist2 = ProductionReadinessChecklist(overfit_backtest)
    checklist2.print_report()
