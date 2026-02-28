#!/usr/bin/env python3
"""
scaling_config.py - Gradual Scaling Configuration
==================================================

Defines scaling stages for live trading:

| Stage    | Capital | Strategies | Leverage | Criteria to advance            |
|----------|---------|------------|----------|-------------------------------|
| Week 1-2 | $500    | 1          | 1x       | 14 days, 10+ trades, WR>40%, PnL>=$0 |
| Week 3-4 | $1000   | 2          | 1x       | 14 days, 20+ trades, PnL>$10  |
| Month 2  | $1000   | 2          | 2x (20%) | 30 days, WR>42%, PnL>$30      |
| Month 3+ | $2000   | 3          | 5x max   | Only if month 2 was profitable|

Usage:
    from scaling_config import ScalingManager
    manager = ScalingManager()
    stage = manager.get_current_stage(trading_days=15, total_trades=12, ...)
"""

import json
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ScalingStage:
    """Configuration for a scaling stage."""
    name: str
    capital: float
    max_strategies: int
    max_leverage: int
    futures_pct: float  # Max % of capital in futures
    # Criteria to advance to next stage
    min_days: int
    min_trades: int
    min_win_rate: float
    min_pnl: float


# Scaling stages
STAGES = [
    ScalingStage(
        name="Stage 1: Initial",
        capital=500,
        max_strategies=1,
        max_leverage=1,
        futures_pct=0.0,
        min_days=14,
        min_trades=10,
        min_win_rate=40.0,
        min_pnl=0.0,
    ),
    ScalingStage(
        name="Stage 2: Validation",
        capital=1000,
        max_strategies=2,
        max_leverage=1,
        futures_pct=0.0,
        min_days=14,
        min_trades=20,
        min_win_rate=40.0,
        min_pnl=10.0,
    ),
    ScalingStage(
        name="Stage 3: Expansion",
        capital=1000,
        max_strategies=2,
        max_leverage=2,
        futures_pct=0.20,
        min_days=30,
        min_trades=30,
        min_win_rate=42.0,
        min_pnl=30.0,
    ),
    ScalingStage(
        name="Stage 4: Full",
        capital=2000,
        max_strategies=3,
        max_leverage=5,
        futures_pct=0.30,
        min_days=0,  # No advancement needed
        min_trades=0,
        min_win_rate=0,
        min_pnl=0,
    ),
]


class ScalingManager:
    """Manages gradual scaling of live trading."""

    def __init__(self, db_path: str = "/tmp/risk_manager.db"):
        self.db_path = db_path
        self.current_stage_idx = 0
        self._load_stage()

    def _load_stage(self):
        """Load current stage from state file."""
        state_file = "/tmp/scaling_state.json"
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            self.current_stage_idx = state.get('stage_idx', 0)
            self.stage_start_date = state.get('stage_start_date', datetime.now().isoformat())
        except (FileNotFoundError, json.JSONDecodeError):
            self.current_stage_idx = 0
            self.stage_start_date = datetime.now().isoformat()

    def _save_stage(self):
        """Save current stage to state file."""
        state_file = "/tmp/scaling_state.json"
        with open(state_file, 'w') as f:
            json.dump({
                'stage_idx': self.current_stage_idx,
                'stage_start_date': self.stage_start_date,
                'updated_at': datetime.now().isoformat(),
            }, f, indent=2)

    @property
    def current_stage(self) -> ScalingStage:
        """Get current scaling stage."""
        idx = min(self.current_stage_idx, len(STAGES) - 1)
        return STAGES[idx]

    def get_current_stage(self, trading_days: int = 0, total_trades: int = 0,
                          win_rate: float = 0, total_pnl: float = 0) -> ScalingStage:
        """
        Determine current stage based on performance.

        Automatically advances if criteria are met.

        Args:
            trading_days: Number of days trading in current stage
            total_trades: Total trades in current stage
            win_rate: Win rate percentage in current stage
            total_pnl: Total PnL in current stage

        Returns:
            Current ScalingStage
        """
        stage = self.current_stage

        # Check if we can advance
        if self.current_stage_idx < len(STAGES) - 1:
            if (trading_days >= stage.min_days and
                total_trades >= stage.min_trades and
                win_rate >= stage.min_win_rate and
                total_pnl >= stage.min_pnl):

                self.current_stage_idx += 1
                self.stage_start_date = datetime.now().isoformat()
                self._save_stage()
                print(f"SCALING: Advanced to {STAGES[self.current_stage_idx].name}")

        return self.current_stage

    def get_trading_stats(self) -> Dict:
        """Get trading stats for current stage from risk manager DB."""
        if not self.db_path or not __import__('os').path.exists(self.db_path):
            return {'days': 0, 'trades': 0, 'win_rate': 0, 'pnl': 0}

        start_date = self.stage_start_date[:10]  # YYYY-MM-DD

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            SELECT COUNT(*), COALESCE(SUM(pnl), 0),
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)
            FROM trades
            WHERE date(timestamp, 'unixepoch') >= ?
        """, (start_date,))

        row = c.fetchone()
        total_trades = row[0] or 0
        total_pnl = row[1] or 0
        wins = row[2] or 0
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        # Count distinct trading days
        c.execute("""
            SELECT COUNT(DISTINCT date(timestamp, 'unixepoch'))
            FROM trades
            WHERE date(timestamp, 'unixepoch') >= ?
        """, (start_date,))
        trading_days = c.fetchone()[0] or 0

        conn.close()

        return {
            'days': trading_days,
            'trades': total_trades,
            'win_rate': round(win_rate, 1),
            'pnl': round(total_pnl, 2),
        }

    def get_status(self) -> Dict:
        """Get full scaling status."""
        stage = self.current_stage
        stats = self.get_trading_stats()

        return {
            'current_stage': stage.name,
            'stage_idx': self.current_stage_idx,
            'capital': stage.capital,
            'max_strategies': stage.max_strategies,
            'max_leverage': stage.max_leverage,
            'futures_allowed': stage.futures_pct > 0,
            'futures_pct': stage.futures_pct,
            'stage_start': self.stage_start_date,
            'stats': stats,
            'advancement_criteria': {
                'min_days': stage.min_days,
                'min_trades': stage.min_trades,
                'min_win_rate': stage.min_win_rate,
                'min_pnl': stage.min_pnl,
            },
            'progress': {
                'days': f"{stats['days']}/{stage.min_days}",
                'trades': f"{stats['trades']}/{stage.min_trades}",
                'win_rate': f"{stats['win_rate']:.1f}%/{stage.min_win_rate:.1f}%",
                'pnl': f"${stats['pnl']:.2f}/${stage.min_pnl:.2f}",
            }
        }

    def print_status(self):
        """Print scaling status."""
        status = self.get_status()

        print("\n" + "=" * 50)
        print("SCALING STATUS")
        print("=" * 50)
        print(f"Current: {status['current_stage']}")
        print(f"Capital: ${status['capital']}")
        print(f"Strategies: {status['max_strategies']}")
        print(f"Leverage: {status['max_leverage']}x")
        print(f"Futures: {'Yes' if status['futures_allowed'] else 'No'}")
        print()
        print("Progress to next stage:")
        for key, val in status['progress'].items():
            print(f"  {key}: {val}")
        print("=" * 50)


if __name__ == "__main__":
    manager = ScalingManager()
    manager.print_status()
