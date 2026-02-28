#!/usr/bin/env python3
"""
daily_trading_report.py - Daily P&L Trading Report
===================================================

Reads risk_manager.db daily and generates:
- Trades of the day (wins/losses)
- Total PnL and drawdown
- Sends report via Telegram at 8 PM
- Command /daily_report for manual query

Usage:
    python daily_trading_report.py              # Generate report now
    python daily_trading_report.py --send       # Generate and send via Telegram
    python daily_trading_report.py --daemon     # Run as daemon (sends at 8 PM)
"""

import os
import json
import time
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Database paths
RISK_DB = "/tmp/risk_manager.db"
ORCHESTRATOR_DB = "/tmp/spot_orchestrator.db"
PAPER_DB = "/tmp/paper_trading_pipeline.db"

# Telegram config
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Report time
REPORT_HOUR = 20  # 8 PM


def send_telegram(message: str) -> bool:
    """Send message via Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[No Telegram config - printing to console]")
        print(message)
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
        print(f"Telegram error: {e}")
        return False


def get_trades_today(db_path: str = RISK_DB) -> List[Dict]:
    """Get all trades from today."""
    if not os.path.exists(db_path):
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT timestamp, product_id, side, pnl, pnl_pct, reason, leverage, margin_used
        FROM trades
        WHERE date(timestamp, 'unixepoch') = ?
        ORDER BY timestamp
    """, (today,))

    trades = [dict(row) for row in c.fetchall()]
    conn.close()
    return trades


def get_live_trades_today(db_path: str = ORCHESTRATOR_DB) -> List[Dict]:
    """Get live spot trades from today."""
    if not os.path.exists(db_path):
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT timestamp, strategy_id, product_id, side, size, price, pnl, dry_run
        FROM live_trades
        WHERE date(timestamp, 'unixepoch') = ?
        ORDER BY timestamp
    """, (today,))

    trades = [dict(row) for row in c.fetchall()]
    conn.close()
    return trades


def generate_report() -> str:
    """Generate daily trading report."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    lines = [
        f"<b>Daily Trading Report</b>",
        f"Date: {today}",
        "",
    ]

    # Risk manager trades
    risk_trades = get_trades_today()
    if risk_trades:
        total_pnl = sum(t['pnl'] for t in risk_trades)
        wins = sum(1 for t in risk_trades if t['pnl'] > 0)
        losses = len(risk_trades) - wins
        win_rate = (wins / len(risk_trades) * 100) if risk_trades else 0

        # Calculate drawdown
        equity = 0
        peak = 0
        max_dd = 0
        for t in risk_trades:
            equity += t['pnl']
            if equity > peak:
                peak = equity
            if peak > 0:
                dd = (peak - equity) / peak
                if dd > max_dd:
                    max_dd = dd

        lines.append("<b>Futures/Risk Manager:</b>")
        lines.append(f"  Trades: {len(risk_trades)} (W:{wins} L:{losses})")
        lines.append(f"  Win Rate: {win_rate:.1f}%")
        lines.append(f"  PnL: ${total_pnl:+.2f}")
        lines.append(f"  Max Drawdown: {max_dd*100:.1f}%")
        lines.append("")

    # Live spot trades
    live_trades = get_live_trades_today()
    if live_trades:
        real_trades = [t for t in live_trades if not t['dry_run']]
        dry_trades = [t for t in live_trades if t['dry_run']]

        if real_trades:
            real_pnl = sum(t['pnl'] for t in real_trades)
            lines.append("<b>Spot (REAL):</b>")
            lines.append(f"  Trades: {len(real_trades)}")
            lines.append(f"  PnL: ${real_pnl:+.2f}")
            lines.append("")

        if dry_trades:
            dry_pnl = sum(t['pnl'] for t in dry_trades)
            lines.append(f"<b>Spot (Dry Run):</b>")
            lines.append(f"  Trades: {len(dry_trades)}")
            lines.append(f"  PnL: ${dry_pnl:+.2f}")
            lines.append("")

    if not risk_trades and not live_trades:
        lines.append("No trades today.")

    # Paper trading summary
    if os.path.exists(PAPER_DB):
        try:
            conn = sqlite3.connect(PAPER_DB)
            c = conn.cursor()
            c.execute("""
                SELECT COUNT(*), COALESCE(SUM(pnl), 0)
                FROM paper_trades
                WHERE date(timestamp) = ?
            """, (today,))
            row = c.fetchone()
            conn.close()

            if row and row[0] > 0:
                lines.append(f"<b>Paper Trading:</b>")
                lines.append(f"  Trades: {row[0]} | PnL: ${row[1]:+.2f}")
                lines.append("")
        except Exception:
            pass

    return "\n".join(lines)


def run_daemon():
    """Run as daemon, sending report at configured hour."""
    print(f"Daily report daemon started. Report time: {REPORT_HOUR}:00")

    last_report_date = None

    while True:
        now = datetime.now()

        if now.hour == REPORT_HOUR and last_report_date != now.date():
            report = generate_report()
            send_telegram(report)
            print(f"[{now.strftime('%H:%M')}] Sent daily report")
            last_report_date = now.date()

        time.sleep(60)  # Check every minute


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Daily Trading Report")
    parser.add_argument("--send", action="store_true", help="Generate and send via Telegram")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon (sends at 8 PM)")
    args = parser.parse_args()

    if args.daemon:
        try:
            run_daemon()
        except KeyboardInterrupt:
            print("Daemon stopped.")
    elif args.send:
        report = generate_report()
        send_telegram(report)
        print("Report sent.")
    else:
        report = generate_report()
        # Strip HTML tags for console display
        clean = report.replace('<b>', '').replace('</b>', '')
        print(clean)


if __name__ == "__main__":
    main()
