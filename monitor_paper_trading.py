#!/usr/bin/env python3
"""
monitor_paper_trading.py - Paper Trading Monitor
=================================================

Monitors paper trading performance vs backtest expectations:
- Reads paper_trading_pipeline.db every hour
- Calculates running metrics (Sharpe, win rate, drawdown) per strategy
- Compares paper vs backtest: degradation = 1 - (paper_pnl / backtest_pnl)
- If degradation > 50% -> marks strategy as not viable
- Sends daily report via Telegram

Usage:
    python monitor_paper_trading.py              # Run once
    python monitor_paper_trading.py --loop       # Continuous monitoring
    python monitor_paper_trading.py --report     # Send report now
"""

import os
import sys
import json
import time
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Paths
PAPER_DB = "/tmp/paper_trading_pipeline.db"
COORDINATOR_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coordinator.db")

# Monitoring config
CHECK_INTERVAL = 3600  # 1 hour
MAX_DEGRADATION = 0.50  # 50% degradation = not viable
DAILY_REPORT_HOUR = 20  # 8 PM

# Telegram config
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


def send_telegram(message: str):
    """Send message via Telegram bot."""
    if not BOT_TOKEN or not CHAT_ID:
        print(f"[Telegram] {message}")
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'HTML',
        }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"[Telegram Error] {e}")
        return False


def get_paper_strategies() -> List[Dict]:
    """Get all active paper trading strategies with metrics."""
    if not os.path.exists(PAPER_DB):
        return []

    conn = sqlite3.connect(PAPER_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT strategy_id, contract, market_type,
               train_pnl, train_trades, train_winrate, train_sharpe,
               oos_pnl, oos_trades, oos_degradation, robustness_score,
               paper_pnl, paper_trades, paper_winrate, paper_sharpe,
               status, degradation_vs_paper, alerts_count,
               deployed_at, last_updated
        FROM paper_strategies
        WHERE status = 'active'
        ORDER BY paper_pnl DESC
    """)

    strategies = []
    for row in c.fetchall():
        strategies.append(dict(row))

    conn.close()
    return strategies


def get_paper_trades(strategy_id: str, limit: int = 50) -> List[Dict]:
    """Get recent paper trades for a strategy."""
    if not os.path.exists(PAPER_DB):
        return []

    conn = sqlite3.connect(PAPER_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT * FROM paper_trades
        WHERE strategy_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (strategy_id, limit))

    trades = [dict(row) for row in c.fetchall()]
    conn.close()
    return trades


def calculate_running_metrics(trades: List[Dict]) -> Dict:
    """Calculate running metrics from trade list."""
    if not trades:
        return {'sharpe': 0, 'win_rate': 0, 'drawdown': 0, 'total_pnl': 0, 'count': 0}

    pnls = [t.get('pnl', 0) for t in trades]
    total_pnl = sum(pnls)
    wins = sum(1 for p in pnls if p > 0)
    win_rate = (wins / len(pnls) * 100) if pnls else 0

    # Sharpe ratio (annualized, assuming daily)
    import numpy as np
    if len(pnls) > 1:
        mean_ret = np.mean(pnls)
        std_ret = np.std(pnls)
        sharpe = (mean_ret / std_ret) * (252 ** 0.5) if std_ret > 0 else 0
    else:
        sharpe = 0

    # Max drawdown
    equity = 0
    peak = 0
    max_dd = 0
    for pnl in pnls:
        equity += pnl
        if equity > peak:
            peak = equity
        if peak > 0:
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd

    return {
        'sharpe': round(sharpe, 2),
        'win_rate': round(win_rate, 1),
        'drawdown': round(max_dd, 4),
        'total_pnl': round(total_pnl, 2),
        'count': len(pnls),
    }


def check_degradation(strategies: List[Dict]) -> List[Dict]:
    """Check each strategy for degradation and return alerts."""
    alerts = []

    for s in strategies:
        strategy_id = s['strategy_id']
        train_pnl = s.get('train_pnl', 0)
        paper_pnl = s.get('paper_pnl', 0)
        paper_trades = s.get('paper_trades', 0)

        # Need minimum trades before comparing
        if paper_trades < 5:
            continue

        # Calculate degradation
        if train_pnl and train_pnl > 0:
            degradation = 1 - (paper_pnl / train_pnl)
        else:
            degradation = 1.0 if paper_pnl < 0 else 0

        if degradation > MAX_DEGRADATION:
            alerts.append({
                'strategy_id': strategy_id,
                'degradation': degradation,
                'paper_pnl': paper_pnl,
                'train_pnl': train_pnl,
                'paper_trades': paper_trades,
                'message': f"Strategy {strategy_id} degraded {degradation*100:.1f}%: "
                          f"paper ${paper_pnl:.2f} vs train ${train_pnl:.2f}"
            })

            # Mark as not viable in DB
            if os.path.exists(PAPER_DB):
                conn = sqlite3.connect(PAPER_DB)
                c = conn.cursor()
                c.execute("""
                    UPDATE paper_strategies
                    SET status = 'degraded', degradation_vs_paper = ?
                    WHERE strategy_id = ?
                """, (degradation, strategy_id))
                conn.commit()
                conn.close()

    return alerts


def generate_report(strategies: List[Dict]) -> str:
    """Generate daily paper trading report."""
    if not strategies:
        return "Paper Trading Report\n\nNo active strategies."

    lines = ["<b>Paper Trading Daily Report</b>", ""]
    lines.append(f"Active strategies: {len(strategies)}")
    lines.append("")

    total_paper_pnl = 0
    total_paper_trades = 0

    for s in strategies:
        sid = s['strategy_id']
        paper_pnl = s.get('paper_pnl', 0)
        paper_trades = s.get('paper_trades', 0)
        train_pnl = s.get('train_pnl', 0)
        degradation = s.get('degradation_vs_paper', 0)

        total_paper_pnl += paper_pnl
        total_paper_trades += paper_trades

        status_icon = "+" if paper_pnl >= 0 else "-"
        deg_pct = degradation * 100 if degradation else 0

        lines.append(f"[{status_icon}] {sid}")
        lines.append(f"  Paper: ${paper_pnl:.2f} ({paper_trades} trades)")
        lines.append(f"  Train: ${train_pnl:.2f} | Deg: {deg_pct:.0f}%")

    lines.append("")
    lines.append(f"<b>Total Paper PnL: ${total_paper_pnl:.2f}</b>")
    lines.append(f"Total Paper Trades: {total_paper_trades}")

    return "\n".join(lines)


def run_check():
    """Run a single monitoring check."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running paper trading check...")

    strategies = get_paper_strategies()

    if not strategies:
        print("  No active paper trading strategies found.")
        return

    print(f"  Found {len(strategies)} active strategies")

    # Check degradation
    alerts = check_degradation(strategies)

    if alerts:
        for alert in alerts:
            msg = f"PAPER TRADING ALERT\n\n{alert['message']}"
            send_telegram(msg)
            print(f"  ALERT: {alert['message']}")
    else:
        print("  All strategies within acceptable degradation.")

    # Print summary
    for s in strategies:
        print(f"  {s['strategy_id']}: paper=${s.get('paper_pnl', 0):.2f} "
              f"({s.get('paper_trades', 0)} trades) "
              f"| train=${s.get('train_pnl', 0):.2f}")


def run_loop():
    """Run continuous monitoring loop."""
    print("Starting Paper Trading Monitor (continuous)")
    print(f"  Check interval: {CHECK_INTERVAL}s")
    print(f"  Daily report at: {DAILY_REPORT_HOUR}:00")

    last_report_date = None

    while True:
        try:
            run_check()

            # Daily report at configured hour
            now = datetime.now()
            if now.hour == DAILY_REPORT_HOUR and last_report_date != now.date():
                strategies = get_paper_strategies()
                report = generate_report(strategies)
                send_telegram(report)
                print(f"  Sent daily report")
                last_report_date = now.date()

        except Exception as e:
            print(f"  ERROR: {e}")

        time.sleep(CHECK_INTERVAL)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Paper Trading Monitor")
    parser.add_argument("--loop", action="store_true", help="Run continuous monitoring")
    parser.add_argument("--report", action="store_true", help="Generate and send report now")
    parser.add_argument("--check", action="store_true", help="Run single check (default)")
    args = parser.parse_args()

    if args.report:
        strategies = get_paper_strategies()
        report = generate_report(strategies)
        print(report)
        send_telegram(report)
    elif args.loop:
        try:
            run_loop()
        except KeyboardInterrupt:
            print("\nMonitor stopped.")
    else:
        run_check()


if __name__ == "__main__":
    main()
