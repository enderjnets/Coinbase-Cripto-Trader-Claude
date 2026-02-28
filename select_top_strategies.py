#!/usr/bin/env python3
"""
select_top_strategies.py - Select Top Strategies for Paper Trading
==================================================================

Queries coordinator.db for the top 5 spot strategies based on:
- is_canonical = 1, is_overfitted = 0
- trades >= 20, win_rate 40-75%, sharpe 1.5-20, drawdown <= 50%
- Filters for spot data (not futures)
- Orders by Sharpe ratio (more robust than PnL bruto)

Saves results to paper_trading_strategies.json

Usage:
    python select_top_strategies.py
    python select_top_strategies.py --top 10
    python select_top_strategies.py --db /path/to/coordinator.db
"""

import os
import sys
import json
import sqlite3
import argparse
from datetime import datetime
from typing import List, Dict, Optional

# Default paths
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(PROJECT_DIR, "coordinator.db")
OUTPUT_FILE = os.path.join(PROJECT_DIR, "paper_trading_strategies.json")

# Selection criteria (win_rate stored as decimal 0.0-1.0 in DB)
MIN_TRADES = 10
MIN_WIN_RATE = 0.40  # 40%
MAX_WIN_RATE = 0.80  # 80%
MIN_SHARPE = 1.5
MAX_SHARPE = 50.0  # Relaxed - old backtester produces high Sharpe
MAX_DRAWDOWN = 0.50  # 50%


def select_top_strategies(db_path: str = DEFAULT_DB, top_n: int = 5,
                          require_canonical: bool = True) -> List[Dict]:
    """
    Query coordinator.db for top spot strategies.

    Args:
        db_path: Path to coordinator.db
        top_n: Number of strategies to return
        require_canonical: Whether to require is_canonical = 1

    Returns:
        List of strategy dicts with genome and metrics
    """
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found: {db_path}")
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Check which columns exist
    c.execute("PRAGMA table_info(results)")
    columns = {col[1] for col in c.fetchall()}

    has_canonical = 'is_canonical' in columns
    has_overfitted = 'is_overfitted' in columns
    has_max_dd = 'max_drawdown' in columns

    # Build query dynamically based on available columns
    conditions = [
        "r.trades >= ?",
        "r.win_rate >= ?",
        "r.win_rate <= ?",
        "r.sharpe_ratio >= ?",
        "r.sharpe_ratio <= ?",
        "r.pnl > 0",
    ]
    params = [MIN_TRADES, MIN_WIN_RATE, MAX_WIN_RATE, MIN_SHARPE, MAX_SHARPE]

    if has_canonical and require_canonical:
        conditions.append("r.is_canonical = 1")

    if has_overfitted:
        conditions.append("(r.is_overfitted = 0 OR r.is_overfitted IS NULL)")

    if has_max_dd:
        conditions.append(f"(r.max_drawdown <= ? OR r.max_drawdown IS NULL)")
        params.append(MAX_DRAWDOWN)

    # Filter for spot data (exclude futures contracts)
    # Futures data files contain patterns like BIP-, BIT-, ET-, SLP-, XPP-
    conditions.append("""
        NOT EXISTS (
            SELECT 1 FROM work_units w2 WHERE w2.id = r.work_unit_id
            AND (w2.strategy_params LIKE '%BIP-%'
                 OR w2.strategy_params LIKE '%BIT-%'
                 OR w2.strategy_params LIKE '%ET-%'
                 OR w2.strategy_params LIKE '%SLP-%'
                 OR w2.strategy_params LIKE '%XPP-%'
                 OR w2.strategy_params LIKE '%ETP-%'
                 OR w2.strategy_params LIKE '%FUTURE%')
        )
    """)

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            r.id as result_id,
            r.work_unit_id,
            r.pnl,
            r.trades,
            r.win_rate,
            r.sharpe_ratio,
            r.strategy_genome,
            {"r.max_drawdown," if has_max_dd else "NULL as max_drawdown,"}
            {"r.is_canonical," if has_canonical else "NULL as is_canonical,"}
            {"r.is_overfitted," if has_overfitted else "NULL as is_overfitted,"}
            w.strategy_params
        FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        WHERE {where_clause}
        ORDER BY r.sharpe_ratio DESC
        LIMIT ?
    """
    params.append(top_n * 3)  # Get more than needed for filtering

    try:
        c.execute(query, params)
        rows = c.fetchall()
    except Exception as e:
        print(f"ERROR: Query failed: {e}")
        conn.close()
        return []

    conn.close()

    strategies = []
    for row in rows:
        try:
            genome = json.loads(row['strategy_genome']) if row['strategy_genome'] else None
            strategy_params = json.loads(row['strategy_params']) if row['strategy_params'] else {}
        except (json.JSONDecodeError, TypeError):
            continue

        if not genome:
            continue

        # Extract data file from params
        data_file = strategy_params.get('data_file', 'unknown')

        strategies.append({
            'result_id': row['result_id'],
            'strategy_id': f"spot_strategy_{row['result_id']}",
            'genome': genome,
            'data_file': data_file,
            'metrics': {
                'pnl': round(row['pnl'], 2),
                'trades': row['trades'],
                'win_rate': round(row['win_rate'], 2),
                'sharpe_ratio': round(row['sharpe_ratio'], 4),
                'max_drawdown': round(row['max_drawdown'], 4) if row['max_drawdown'] else None,
            },
            'is_canonical': bool(row['is_canonical']),
            'selected_at': datetime.now().isoformat(),
        })

        if len(strategies) >= top_n:
            break

    return strategies


def save_strategies(strategies: List[Dict], output_path: str = OUTPUT_FILE):
    """Save selected strategies to JSON file."""
    output = {
        'selected_at': datetime.now().isoformat(),
        'count': len(strategies),
        'criteria': {
            'min_trades': MIN_TRADES,
            'win_rate_range': [MIN_WIN_RATE, MAX_WIN_RATE],
            'sharpe_range': [MIN_SHARPE, MAX_SHARPE],
            'max_drawdown': MAX_DRAWDOWN,
        },
        'strategies': strategies,
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Saved {len(strategies)} strategies to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Select top spot strategies for paper trading")
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to coordinator.db")
    parser.add_argument("--top", type=int, default=5, help="Number of strategies to select")
    parser.add_argument("--output", default=OUTPUT_FILE, help="Output JSON file")
    parser.add_argument("--no-canonical", action="store_true", help="Don't require is_canonical=1")
    args = parser.parse_args()

    print("=" * 60)
    print("SELECT TOP STRATEGIES FOR PAPER TRADING")
    print("=" * 60)
    print(f"Database: {args.db}")
    print(f"Top N: {args.top}")
    print(f"Criteria: trades>={MIN_TRADES}, win_rate {MIN_WIN_RATE*100:.0f}-{MAX_WIN_RATE*100:.0f}%, "
          f"sharpe {MIN_SHARPE}-{MAX_SHARPE}, drawdown<={MAX_DRAWDOWN*100}%")
    print()

    strategies = select_top_strategies(
        db_path=args.db,
        top_n=args.top,
        require_canonical=not args.no_canonical,
    )

    if not strategies:
        print("No strategies found matching criteria.")
        # Try again without canonical requirement
        if not args.no_canonical:
            print("Retrying without canonical requirement...")
            strategies = select_top_strategies(
                db_path=args.db,
                top_n=args.top,
                require_canonical=False,
            )

    if strategies:
        print(f"\nFound {len(strategies)} strategies:\n")
        for i, s in enumerate(strategies, 1):
            m = s['metrics']
            print(f"  {i}. {s['strategy_id']}")
            print(f"     PnL: ${m['pnl']:.2f} | Trades: {m['trades']} | "
                  f"Win Rate: {m['win_rate']*100:.1f}% | Sharpe: {m['sharpe_ratio']:.2f}")
            print(f"     Data: {s['data_file']}")
            print()

        save_strategies(strategies, args.output)
    else:
        print("\nNo eligible strategies found.")

    print("Done!")


if __name__ == "__main__":
    main()
