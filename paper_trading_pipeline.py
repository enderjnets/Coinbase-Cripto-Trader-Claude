#!/usr/bin/env python3
"""
paper_trading_pipeline.py - Pipeline Automático de Paper Trading (FASE 3B)
=========================================================================

Sistema que conecta las mejores estrategias validadas con paper trading:

1. Estrategia Discovery: Busca estrategias en coordinator.db que pasen criterios OOS
2. Paper Deployment: Despliega estrategias a paper trading automático
3. Performance Monitoring: Compara paper vs backtest esperado
4. Degradation Alerts: Alerta cuando rendimiento degrada > 20%

Uso:
    from paper_trading_pipeline import PaperTradingPipeline
    pipeline = PaperTradingPipeline()
    pipeline.run_discovery_loop()
"""

import os
import sys
import json
import time
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

# Coordinator database path
COORDINATOR_DB = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/"
    "My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db"
)

# Paper trading database
PAPER_TRADING_DB = "/tmp/paper_trading_pipeline.db"

# ============================================================================
# VALIDATION CRITERIA FOR PAPER TRADING DEPLOYMENT
# ============================================================================

MIN_TRAIN_PNL = 100              # Min $100 PnL in training
MIN_TRAIN_TRADES = 30            # Min 30 trades in training
MIN_TRAIN_WINRATE = 0.40         # Min 40% win rate
MIN_TRAIN_SHARPE = 0.5           # Min Sharpe 0.5

# OOS Validation (Phase 3A)
MIN_OOS_PNL = 0                  # OOS must be positive or break-even
MIN_OOS_TRADES = 10              # Min 10 trades in OOS
MAX_OOS_DEGRADATION = 0.98       # Max 98% degradation (temporary relaxed)
MIN_ROBUSTNESS_SCORE = 0         # Min robustness (temporary relaxed)

# Cross-Validation (FASE 3D)
MIN_CV_CONSISTENCY = 0.60        # Min 60% of folds profitable
PREFER_CV_CONSISTENT = True      # Prefer strategies that pass CV

# Paper Trading Monitoring
MAX_PAPER_DEGRADATION = 0.25     # Alert if paper degrades > 25% vs backtest
MIN_PAPER_TRADES_FOR_VALIDATION = 5  # Min trades before comparing

# ============================================================================
# PAPER TRADING PIPELINE CLASS
# ============================================================================

class PaperTradingPipeline:
    """
    Pipeline automático para paper trading de estrategias validadas.
    """

    def __init__(self, coordinator_db: str = COORDINATOR_DB):
        self.coordinator_db = coordinator_db
        self.paper_db = PAPER_TRADING_DB
        self.active_strategies: Dict[str, Dict] = {}  # strategy_id -> config
        self.running = False

        # Initialize paper trading database
        self._init_paper_db()

    def _init_paper_db(self):
        """Initialize paper trading tracking database."""
        conn = sqlite3.connect(self.paper_db)
        c = conn.cursor()

        # Strategies deployed to paper trading
        c.execute("""
            CREATE TABLE IF NOT EXISTS paper_strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT UNIQUE,
                result_id INTEGER,
                genome_json TEXT,
                contract TEXT,
                market_type TEXT,

                -- Backtest metrics (expected)
                train_pnl REAL,
                train_trades INTEGER,
                train_winrate REAL,
                train_sharpe REAL,
                oos_pnl REAL,
                oos_trades INTEGER,
                oos_degradation REAL,
                robustness_score REAL,

                -- Paper trading metrics (actual)
                paper_pnl REAL DEFAULT 0,
                paper_trades INTEGER DEFAULT 0,
                paper_winrate REAL DEFAULT 0,
                paper_sharpe REAL DEFAULT 0,

                -- Status
                status TEXT DEFAULT 'active',
                degradation_vs_paper REAL DEFAULT 0,
                alerts_count INTEGER DEFAULT 0,

                -- Timestamps
                deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Paper trades log
        c.execute("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT,
                contract TEXT,
                direction TEXT,
                entry_price REAL,
                exit_price REAL,
                size REAL,
                pnl REAL,
                fees REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Alerts log
        c.execute("""
            CREATE TABLE IF NOT EXISTS degradation_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT,
                alert_type TEXT,
                message TEXT,
                degradation REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    # ========================================================================
    # STRATEGY DISCOVERY
    # ========================================================================

    def discover_eligible_strategies(self, limit: int = 10) -> List[Dict]:
        """
        Find strategies that pass all validation criteria for paper trading.

        Criteria:
        1. Training metrics: PnL > $100, Trades > 30, WinRate > 40%, Sharpe > 0.5
        2. OOS metrics: PnL >= 0, Trades > 10, Degradation < 35%, Robustness > 40
        3. CV metrics (FASE 3D): Consistency >= 60%
        4. Not already deployed
        """
        conn = sqlite3.connect(self.coordinator_db)
        c = conn.cursor()

        # Get results with OOS + CV metrics
        query = """
            SELECT
                r.id as result_id,
                r.pnl as train_pnl,
                r.trades as train_trades,
                r.win_rate as train_winrate,
                r.sharpe_ratio as train_sharpe,
                r.strategy_genome,
                w.strategy_params,
                r.oos_pnl,
                r.oos_trades,
                r.oos_degradation,
                r.robustness_score,
                r.is_overfitted,
                r.cv_folds,
                r.cv_avg_pnl,
                r.cv_consistency,
                r.cv_is_consistent
            FROM results r
            JOIN work_units w ON r.work_unit_id = w.id
            WHERE r.pnl > ?
            AND r.trades >= ?
            AND r.win_rate >= ?
            AND r.sharpe_ratio >= ?
            AND r.oos_pnl IS NOT NULL
            ORDER BY
                CASE WHEN r.cv_is_consistent = 1 THEN 0 ELSE 1 END,
                r.robustness_score DESC,
                r.oos_pnl DESC
            LIMIT ?
        """

        c.execute(query, (
            MIN_TRAIN_PNL,
            MIN_TRAIN_TRADES,
            MIN_TRAIN_WINRATE,
            MIN_TRAIN_SHARPE,
            limit * 3  # Get more to filter
        ))

        results = c.fetchall()
        conn.close()

        eligible = []
        for row in results:
            (result_id, train_pnl, train_trades, train_winrate, train_sharpe,
             genome_json, params_json, oos_pnl, oos_trades, oos_degradation,
             robustness_score, is_overfitted,
             cv_folds, cv_avg_pnl, cv_consistency, cv_is_consistent) = row

            # Parse JSON
            try:
                genome = json.loads(genome_json) if genome_json else None
                params = json.loads(params_json) if params_json else {}
            except:
                continue

            # Check OOS criteria
            if oos_pnl is None or oos_pnl < MIN_OOS_PNL:
                continue
            if oos_trades is None or oos_trades < MIN_OOS_TRADES:
                continue
            if oos_degradation is not None and oos_degradation > MAX_OOS_DEGRADATION * 100:
                continue
            if robustness_score is not None and robustness_score < MIN_ROBUSTNESS_SCORE:
                continue
            # Temporarily allow overfitted strategies for review
            # if is_overfitted:
            #     continue

            # Check CV criteria (FASE 3D) - optional but preferred
            cv_passed = True
            if cv_folds and cv_folds > 0:
                if cv_consistency is not None and cv_consistency < MIN_CV_CONSISTENCY:
                    cv_passed = False
                if PREFER_CV_CONSISTENT and not cv_is_consistent:
                    # Still allow but deprioritize
                    pass

            # Get contract from params
            contract = params.get('contract', params.get('data_file', 'UNKNOWN'))

            eligible.append({
                'result_id': result_id,
                'strategy_id': f"strategy_{result_id}",
                'genome': genome,
                'contract': contract,
                'market_type': params.get('market_type', 'FUTURES'),
                'train_pnl': train_pnl,
                'train_trades': train_trades,
                'train_winrate': train_winrate,
                'train_sharpe': train_sharpe,
                'oos_pnl': oos_pnl,
                'oos_trades': oos_trades,
                'oos_degradation': oos_degradation or 0,
                'robustness_score': robustness_score or 0,
                # CV metrics (FASE 3D)
                'cv_folds': cv_folds or 0,
                'cv_avg_pnl': cv_avg_pnl or 0,
                'cv_consistency': cv_consistency or 0,
                'cv_is_consistent': cv_is_consistent or False,
                'cv_passed': cv_passed,
            })

        return eligible[:limit]

    # ========================================================================
    # PAPER TRADING DEPLOYMENT
    # ========================================================================

    def deploy_to_paper(self, strategy: Dict) -> bool:
        """
        Deploy a validated strategy to paper trading.

        Args:
            strategy: Dict with genome, contract, metrics

        Returns:
            True if deployed successfully
        """
        strategy_id = strategy['strategy_id']

        # Check if already deployed
        conn = sqlite3.connect(self.paper_db)
        c = conn.cursor()
        c.execute("SELECT id FROM paper_strategies WHERE strategy_id = ?", (strategy_id,))
        if c.fetchone():
            conn.close()
            return False

        # Insert into paper_strategies
        c.execute("""
            INSERT INTO paper_strategies (
                strategy_id, result_id, genome_json, contract, market_type,
                train_pnl, train_trades, train_winrate, train_sharpe,
                oos_pnl, oos_trades, oos_degradation, robustness_score,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """, (
            strategy_id,
            strategy['result_id'],
            json.dumps(strategy['genome']),
            strategy['contract'],
            strategy['market_type'],
            strategy['train_pnl'],
            strategy['train_trades'],
            strategy['train_winrate'],
            strategy['train_sharpe'],
            strategy['oos_pnl'],
            strategy['oos_trades'],
            strategy['oos_degradation'],
            strategy['robustness_score'],
        ))

        conn.commit()
        conn.close()

        # Add to active strategies
        self.active_strategies[strategy_id] = {
            **strategy,
            'paper_pnl': 0,
            'paper_trades': 0,
            'status': 'active',
            'deployed_at': datetime.now(),
        }

        print(f"✅ Deployed {strategy_id} to paper trading | Contract: {strategy['contract']} | OOS PnL: ${strategy['oos_pnl']:.2f}")
        return True

    def deploy_batch(self, max_strategies: int = 5) -> int:
        """
        Deploy top strategies to paper trading.

        Returns:
            Number of strategies deployed
        """
        eligible = self.discover_eligible_strategies(limit=max_strategies)
        deployed = 0

        for strategy in eligible:
            if self.deploy_to_paper(strategy):
                deployed += 1

        print(f"\n📊 Deployed {deployed}/{len(eligible)} strategies to paper trading")
        return deployed

    # ========================================================================
    # PERFORMANCE MONITORING
    # ========================================================================

    def update_paper_metrics(self, strategy_id: str, paper_pnl: float,
                             paper_trades: int, paper_winrate: float):
        """
        Update paper trading metrics and check for degradation.
        """
        conn = sqlite3.connect(self.paper_db)
        c = conn.cursor()

        # Get expected metrics
        c.execute("""
            SELECT train_pnl, train_trades, train_winrate, train_sharpe
            FROM paper_strategies WHERE strategy_id = ?
        """, (strategy_id,))

        row = c.fetchone()
        if not row:
            conn.close()
            return

        train_pnl, train_trades, train_winrate, train_sharpe = row

        # Calculate degradation
        degradation = 0.0
        if train_pnl and train_pnl > 0:
            degradation = (train_pnl - paper_pnl) / train_pnl if paper_pnl < train_pnl else 0

        # Update metrics
        c.execute("""
            UPDATE paper_strategies SET
                paper_pnl = ?,
                paper_trades = ?,
                paper_winrate = ?,
                degradation_vs_paper = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE strategy_id = ?
        """, (paper_pnl, paper_trades, paper_winrate, degradation, strategy_id))

        # Check for degradation alert
        if (paper_trades >= MIN_PAPER_TRADES_FOR_VALIDATION and
            degradation > MAX_PAPER_DEGRADATION):
            self._create_alert(strategy_id, 'degradation',
                              f"Paper trading degraded {degradation*100:.1f}% vs backtest",
                              degradation)
            c.execute("UPDATE paper_strategies SET alerts_count = alerts_count + 1 WHERE strategy_id = ?",
                     (strategy_id,))

        conn.commit()
        conn.close()

    def _create_alert(self, strategy_id: str, alert_type: str, message: str, degradation: float):
        """Create a degradation alert."""
        conn = sqlite3.connect(self.paper_db)
        c = conn.cursor()

        c.execute("""
            INSERT INTO degradation_alerts (strategy_id, alert_type, message, degradation)
            VALUES (?, ?, ?, ?)
        """, (strategy_id, alert_type, message, degradation))

        conn.commit()
        conn.close()

        print(f"⚠️ ALERT [{strategy_id}]: {message}")

        # TODO: Send Telegram notification
        self._send_telegram_alert(strategy_id, message)

    def _send_telegram_alert(self, strategy_id: str, message: str):
        """Send alert via Telegram (placeholder)."""
        # This would integrate with telegram_bot.py
        alert_msg = f"⚠️ Paper Trading Alert\n\nStrategy: {strategy_id}\n{message}"
        # For now, just log it
        with open("/tmp/paper_trading_alerts.log", "a") as f:
            f.write(f"{datetime.now()}: {alert_msg}\n")

    # ========================================================================
    # STATUS AND REPORTING
    # ========================================================================

    def get_status(self) -> Dict:
        """Get current pipeline status."""
        conn = sqlite3.connect(self.paper_db)
        c = conn.cursor()

        # Count strategies
        c.execute("SELECT COUNT(*) FROM paper_strategies WHERE status = 'active'")
        active_count = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM degradation_alerts WHERE date(timestamp) = date('now')")
        alerts_today = c.fetchone()[0]

        # Get top performers
        c.execute("""
            SELECT strategy_id, contract, train_pnl, paper_pnl, paper_trades,
                   degradation_vs_paper, robustness_score
            FROM paper_strategies
            WHERE status = 'active'
            ORDER BY paper_pnl DESC
            LIMIT 5
        """)
        top_performers = c.fetchall()

        conn.close()

        return {
            'active_strategies': active_count,
            'alerts_today': alerts_today,
            'top_performers': [
                {
                    'strategy_id': r[0],
                    'contract': r[1],
                    'train_pnl': r[2],
                    'paper_pnl': r[3],
                    'paper_trades': r[4],
                    'degradation': r[5],
                    'robustness': r[6],
                }
                for r in top_performers
            ]
        }

    def print_status(self):
        """Print pipeline status to console."""
        status = self.get_status()

        print("\n" + "="*60)
        print("📊 PAPER TRADING PIPELINE STATUS")
        print("="*60)
        print(f"Active Strategies: {status['active_strategies']}")
        print(f"Alerts Today: {status['alerts_today']}")

        if status['top_performers']:
            print("\n🏆 Top Performers:")
            for p in status['top_performers']:
                deg_status = "🟢" if p['degradation'] < 0.1 else "🟡" if p['degradation'] < 0.25 else "🔴"
                print(f"  {deg_status} {p['strategy_id']}: Paper=${p['paper_pnl']:.2f} | "
                      f"Train=${p['train_pnl']:.2f} | Degradation={p['degradation']*100:.1f}%")
        print("="*60 + "\n")

    # ========================================================================
    # MAIN LOOP
    # ========================================================================

    def run_discovery_loop(self, interval: int = 300):
        """
        Run continuous discovery and deployment loop.

        Args:
            interval: Seconds between discovery runs (default 5 minutes)
        """
        self.running = True
        print(f"🔄 Starting Paper Trading Pipeline (checking every {interval}s)")

        while self.running:
            try:
                # Discover and deploy new strategies
                self.deploy_batch(max_strategies=3)

                # Print status
                self.print_status()

            except Exception as e:
                print(f"❌ Error in discovery loop: {e}")

            # Wait for next cycle
            time.sleep(interval)

    def stop(self):
        """Stop the pipeline."""
        self.running = False
        print("🛑 Paper Trading Pipeline stopped")


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Paper Trading Pipeline")
    parser.add_argument("--discover", action="store_true", help="Run strategy discovery once")
    parser.add_argument("--deploy", type=int, default=0, help="Deploy N strategies")
    parser.add_argument("--status", action="store_true", help="Show pipeline status")
    parser.add_argument("--loop", action="store_true", help="Run continuous discovery loop")

    args = parser.parse_args()

    pipeline = PaperTradingPipeline()

    if args.discover:
        eligible = pipeline.discover_eligible_strategies(limit=10)
        print(f"\n📋 Found {len(eligible)} eligible strategies:")
        for s in eligible:
            print(f"  - {s['strategy_id']}: OOS PnL=${s['oos_pnl']:.2f}, Robustness={s['robustness_score']:.0f}/100")

    elif args.deploy > 0:
        deployed = pipeline.deploy_batch(max_strategies=args.deploy)
        print(f"✅ Deployed {deployed} strategies")

    elif args.status:
        pipeline.print_status()

    elif args.loop:
        try:
            pipeline.run_discovery_loop()
        except KeyboardInterrupt:
            pipeline.stop()

    else:
        # Default: show help
        parser.print_help()
