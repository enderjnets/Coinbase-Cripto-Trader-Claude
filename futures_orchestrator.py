#!/usr/bin/env python3
"""
futures_orchestrator.py - Orquestador de Trading de Futuros
===========================================================

Coordina todos los componentes del sistema de trading:
- Strategy Miner (descubrimiento de estrategias)
- Paper Trading (validación)
- Live Trading (ejecución real)
- Risk Manager (protección)
- Telegram Alerts (notificaciones)

Flujo de trabajo:
1. Mining → Descubre estrategias óptimas
2. Validation → Prueba en paper trading
3. Activation → Activa para trading real si cumple criterios
4. Monitoring → Monitorea performance y desactiva si degrada

Autor: Strategy Miner Team
Fecha: Feb 2026
"""

import os
import sys
import json
import time
import sqlite3
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np

# Componentes internos
from strategy_miner import StrategyMiner
from numba_futures_backtester import numba_evaluate_futures_population
from paper_futures_trader import PaperFuturesTrader
from live_futures_executor import LiveFuturesExecutor, PositionSide
from risk_manager_live import RiskManager, RiskLevel, RiskConfig
from scaling_config import ScalingManager

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, "coordinator.db")

# Criterios para activar estrategia
ACTIVATION_CRITERIA = {
    "min_trades": 20,           # Mínimo 20 trades en backtest
    "min_win_rate": 45,          # Mínimo 45% win rate
    "min_sharpe": 1.0,           # Mínimo Sharpe 1.0
    "max_drawdown": 0.25,        # Máximo 25% drawdown
    "min_pnl_pct": 0.05,         # Mínimo 5% retorno
    "max_liquidations": 3,       # Máximo 3 liquidaciones
    "paper_validation_hours": 4, # Horas en paper antes de activar
}

# Productos a trading
PRODUCTS_CONFIG = {
    # Perpetuos (alta liquidez)
    "perpetuals": [
        "BIP-20DEC30-CDE",  # BTC Perpetual
        "ETP-20DEC30-CDE",  # ETH Perpetual
        "SLP-20DEC30-CDE",  # SOL Perpetual
    ],
    # Dated (selección de alta liquidez)
    "dated": [
        "BIT-27FEB26-CDE",
        "ET-27FEB26-CDE",
        "SOL-27FEB26-CDE",
    ],
}


class StrategyStatus(Enum):
    """Estado de una estrategia."""
    MINING = "MINING"           # En proceso de minería
    BACKTESTED = "BACKTESTED"   # Backtest completado
    PAPER_TESTING = "PAPER_TESTING"  # En paper trading
    VALIDATED = "VALIDATED"     # Validada para live
    ACTIVE = "ACTIVE"           # Activa en live trading
    PAUSED = "PAUSED"           # Pausada
    DEPRECATED = "DEPRECATED"   # Deprecada por mala performance


@dataclass
class StrategyRecord:
    """Registro de una estrategia."""
    strategy_id: str
    genome: dict
    status: StrategyStatus
    backtest_metrics: dict
    paper_metrics: dict
    live_metrics: dict
    product_id: str
    created_at: float
    activated_at: Optional[float] = None
    deactivated_at: Optional[float] = None
    deactivation_reason: str = ""


# ============================================================================
# FUTURES ORCHESTRATOR
# ============================================================================

class FuturesOrchestrator:
    """
    Orquestador principal del sistema de trading de futuros.

    Responsabilidades:
    1. Coordina mining de estrategias
    2. Valida estrategias en paper trading
    3. Gestiona transición a live trading
    4. Monitorea performance en tiempo real
    5. Gestiona notificaciones
    """

    def __init__(
        self,
        initial_balance: float = 10000,
        dry_run: bool = True,
        auto_activate: bool = False,  # Si False, requiere aprobación manual
        telegram_bot = None
    ):
        self.initial_balance = initial_balance
        self.dry_run = dry_run
        self.auto_activate = auto_activate
        self.telegram_bot = telegram_bot

        # Componentes
        self.risk_manager = RiskManager(
            initial_balance=initial_balance,
            config=RiskConfig()
        )

        self.live_executor = LiveFuturesExecutor(dry_run=dry_run)

        # Scaling manager
        self.scaling = ScalingManager()

        # Paper traders activos
        self.paper_traders: Dict[str, PaperFuturesTrader] = {}

        # Estrategias
        self.strategies: Dict[str, StrategyRecord] = {}

        # Estado
        self.running = False
        self.mining_active = False
        self.trading_active = False

        # Threading
        self._orchestrator_thread = None
        self._stop_event = threading.Event()

        # Cargar estado previo
        self._load_state()

    # ========== STRATEGY MINING ==========

    def mine_strategies(
        self,
        product_id: str,
        data_file: str,
        population_size: int = 30,
        generations: int = 50,
        max_leverage: int = 5
    ) -> List[StrategyRecord]:
        """
        Ejecuta mining de estrategias para un producto.

        Returns:
            Lista de estrategias descubiertas
        """
        print(f"\n{'='*60}")
        print(f"⛏️ MINING ESTRATEGIAS: {product_id}")
        print(f"{'='*60}")

        # Cargar datos
        data_path = os.path.join(PROJECT_DIR, data_file)
        if not os.path.exists(data_path):
            print(f"❌ Datos no encontrados: {data_path}")
            return []

        df = pd.read_csv(data_path).tail(50000).copy()
        print(f"📊 {len(df):,} velas cargadas")

        # Detectar si es perpetuo
        is_perpetual = any(x in product_id for x in ['BIP', 'ETP', 'SLP', 'XPP', 'ADP'])

        # Crear miner
        miner = StrategyMiner(
            df=df,
            population_size=population_size,
            generations=generations,
            risk_level="MEDIUM",
            force_local=True,
            market_type="FUTURES",
            max_leverage=max_leverage,
            is_perpetual=is_perpetual
        )

        # Ejecutar mining
        self.mining_active = True

        def progress_callback(msg_type, data):
            if msg_type == "BEST_GEN":
                pnl = data.get('pnl', 0)
                trades = data.get('num_trades', 0)
                sharpe = data.get('sharpe', 0)
                print(f"   Gen {data.get('gen', 0)}: PnL=${pnl:.2f}, Trades={trades}, Sharpe={sharpe:.2f}")

        best_genome, best_pnl, best_metrics = miner.run(
            progress_callback=progress_callback,
            return_metrics=True
        )

        self.mining_active = False

        # Crear registro de estrategia
        strategy_id = f"{product_id}_{int(time.time())}"
        strategy = StrategyRecord(
            strategy_id=strategy_id,
            genome=best_genome,
            status=StrategyStatus.BACKTESTED,
            backtest_metrics=best_metrics,
            paper_metrics={},
            live_metrics={},
            product_id=product_id,
            created_at=time.time()
        )

        self.strategies[strategy_id] = strategy
        self._save_state()

        print(f"\n✅ Mining completado:")
        print(f"   Strategy ID: {strategy_id}")
        print(f"   PnL: ${best_pnl:.2f}")
        print(f"   Trades: {best_metrics.get('Total Trades', 0)}")
        print(f"   Win Rate: {best_metrics.get('Win Rate %', 0):.1f}%")
        print(f"   Sharpe: {best_metrics.get('Sharpe Ratio', 0):.2f}")
        print(f"   Leverage: {best_genome.get('params', {}).get('leverage', 'N/A')}x")

        return [strategy]

    def mine_all_products(self) -> Dict[str, List[StrategyRecord]]:
        """Ejecuta mining para todos los productos configurados."""
        results = {}

        for category, products in PRODUCTS_CONFIG.items():
            print(f"\n📁 Category: {category.upper()}")

            for product_id in products:
                # Determinar archivo de datos
                data_file = f"data_futures/{product_id}_FIVE_MINUTE.csv"

                strategies = self.mine_strategies(
                    product_id=product_id,
                    data_file=data_file,
                    population_size=20,
                    generations=30,
                    max_leverage=5
                )

                results[product_id] = strategies

        return results

    # ========== VALIDATION ==========

    def validate_strategy(self, strategy_id: str) -> Tuple[bool, str]:
        """
        Valida si una estrategia cumple criterios para activación.

        Returns:
            (is_valid: bool, reason: str)
        """
        if strategy_id not in self.strategies:
            return False, "Estrategia no encontrada"

        strategy = self.strategies[strategy_id]
        metrics = strategy.backtest_metrics

        # Check cada criterio
        checks = [
            ("trades", metrics.get('Total Trades', 0) >= ACTIVATION_CRITERIA['min_trades'],
             f"Trades {metrics.get('Total Trades', 0)} < {ACTIVATION_CRITERIA['min_trades']}"),

            ("win_rate", metrics.get('Win Rate %', 0) >= ACTIVATION_CRITERIA['min_win_rate'],
             f"Win Rate {metrics.get('Win Rate %', 0):.1f}% < {ACTIVATION_CRITERIA['min_win_rate']}%"),

            ("sharpe", metrics.get('Sharpe Ratio', 0) >= ACTIVATION_CRITERIA['min_sharpe'],
             f"Sharpe {metrics.get('Sharpe Ratio', 0):.2f} < {ACTIVATION_CRITERIA['min_sharpe']}"),

            ("drawdown", metrics.get('Max Drawdown', 1) <= ACTIVATION_CRITERIA['max_drawdown'],
             f"DD {metrics.get('Max Drawdown', 0):.2%} > {ACTIVATION_CRITERIA['max_drawdown']:.0%}"),

            ("liquidations", metrics.get('Liquidations', 0) <= ACTIVATION_CRITERIA['max_liquidations'],
             f"Liquidations {metrics.get('Liquidations', 0)} > {ACTIVATION_CRITERIA['max_liquidations']}"),
        ]

        failed = [f"{name}: {msg}" for name, passed, msg in checks if not passed]

        if failed:
            return False, "Failed: " + ", ".join(failed)

        return True, "All validation criteria passed"

    def start_paper_trading(self, strategy_id: str) -> bool:
        """Inicia paper trading para una estrategia."""
        if strategy_id not in self.strategies:
            print(f"❌ Estrategia {strategy_id} no encontrada")
            return False

        strategy = self.strategies[strategy_id]

        # Validar primero
        is_valid, reason = self.validate_strategy(strategy_id)
        if not is_valid:
            print(f"❌ Validación fallida: {reason}")
            return False

        # Crear paper trader
        try:
            # Extraer parámetros
            params = strategy.genome.get('params', {})
            leverage = params.get('leverage', 3)
            direction = params.get('direction', 'BOTH')

            trader = PaperFuturesTrader(
                strategy_genome=strategy.genome,
                initial_capital=self.initial_balance,
                leverage=leverage,
                direction=direction,
                is_perpetual=True
            )

            self.paper_traders[strategy_id] = trader

            # Iniciar en thread separado
            def run_paper():
                asyncio.run(trader.run(strategy.product_id))

            thread = threading.Thread(target=run_paper, daemon=True)
            thread.start()

            strategy.status = StrategyStatus.PAPER_TESTING
            self._save_state()

            print(f"✅ Paper trading iniciado para {strategy_id}")
            return True

        except Exception as e:
            print(f"❌ Error iniciando paper trading: {e}")
            return False

    # ========== LIVE TRADING ==========

    def activate_strategy(self, strategy_id: str, force: bool = False) -> Tuple[bool, str]:
        """
        Activa una estrategia para trading real.

        Args:
            strategy_id: ID de la estrategia
            force: Si True, ignora validación

        Returns:
            (success: bool, message: str)
        """
        if strategy_id not in self.strategies:
            return False, "Estrategia no encontrada"

        strategy = self.strategies[strategy_id]

        # Validar
        if not force:
            is_valid, reason = self.validate_strategy(strategy_id)
            if not is_valid:
                return False, f"Validación fallida: {reason}"

        # Check risk manager
        if self.risk_manager.risk_level in [RiskLevel.CRITICAL, RiskLevel.HALT]:
            return False, f"Risk level no permite activación: {self.risk_manager.risk_level.value}"

        # Activar
        strategy.status = StrategyStatus.ACTIVE
        strategy.activated_at = time.time()
        self._save_state()

        # Notificar
        message = f"""
🚀 ESTRATEGIA ACTIVADA

Strategy: {strategy_id}
Product: {strategy.product_id}

Backtest Metrics:
- PnL: ${strategy.backtest_metrics.get('Total PnL', 0):.2f}
- Trades: {strategy.backtest_metrics.get('Total Trades', 0)}
- Win Rate: {strategy.backtest_metrics.get('Win Rate %', 0):.1f}%
- Sharpe: {strategy.backtest_metrics.get('Sharpe Ratio', 0):.2f}
- Max DD: {strategy.backtest_metrics.get('Max Drawdown', 0):.2%}

⚠️ MONITOR CLOSELY
"""
        self._send_notification(message)

        return True, "Estrategia activada exitosamente"

    def deactivate_strategy(self, strategy_id: str, reason: str) -> bool:
        """Desactiva una estrategia."""
        if strategy_id not in self.strategies:
            return False

        strategy = self.strategies[strategy_id]

        # Cerrar posiciones si hay
        if strategy.product_id in self.live_executor.positions:
            self.live_executor.close_position(strategy.product_id, reason)

        strategy.status = StrategyStatus.PAUSED
        strategy.deactivated_at = time.time()
        strategy.deactivation_reason = reason
        self._save_state()

        self._send_notification(f"⏸️ Estrategia DESACTIVADA: {strategy_id}\nRazón: {reason}")

        return True

    def execute_strategy(self, strategy_id: str) -> Dict:
        """Ejecuta una señal de estrategia activa."""
        if strategy_id not in self.strategies:
            return {"error": "Estrategia no encontrada"}

        strategy = self.strategies[strategy_id]

        if strategy.status != StrategyStatus.ACTIVE:
            return {"error": f"Estrategia no está activa: {strategy.status.value}"}

        # Check risk manager
        can_trade, reason = self.risk_manager.can_open_position(
            product_id=strategy.product_id,
            side="LONG",  # Se determina por la estrategia
            leverage=strategy.genome.get('params', {}).get('leverage', 3),
            margin_usd=self.initial_balance * 0.05,  # 5% por trade
            current_positions=self.live_executor.positions
        )

        if not can_trade:
            return {"error": f"Risk manager bloqueó: {reason}"}

        # TODO: Evaluar señal y ejecutar
        # Por ahora retorna status
        return {
            "strategy_id": strategy_id,
            "can_execute": True,
            "risk_check": "passed"
        }

    # ========== MONITORING ==========

    def monitor_strategies(self):
        """Monitorea todas las estrategias activas."""
        for strategy_id, strategy in self.strategies.items():
            if strategy.status != StrategyStatus.ACTIVE:
                continue

            # Check performance
            # TODO: Comparar métricas live vs backtest

            # Check si necesita desactivación
            # TODO: Implementar lógica de desactivación automática

    def check_all_positions(self):
        """Verifica todas las posiciones activas."""
        positions = self.live_executor.get_positions()
        prices = {}  # TODO: Obtener precios actuales

        # Check con risk manager
        actions = self.risk_manager.check_positions(positions, prices)

        for action in actions:
            parts = action.split(":")
            action_type = parts[0]
            product_id = parts[1]
            reason = parts[2] if len(parts) > 2 else ""

            if action_type == "URGENT":
                self._send_notification(f"🚨 URGENT: {product_id} - {reason}")
            elif action_type == "CLOSE":
                self.live_executor.close_position(product_id, reason)
                self._send_notification(f"📉 Position closed: {product_id} - {reason}")

    # ========== ORCHESTRATION LOOP ==========

    def start(self):
        """Inicia el orquestador."""
        if self.running:
            print("⚠️ Orquestador ya está corriendo")
            return

        self.running = True
        self._stop_event.clear()

        def orchestration_loop():
            while not self._stop_event.is_set():
                try:
                    # 1. Monitor strategies
                    self.monitor_strategies()

                    # 2. Check positions
                    self.check_all_positions()

                    # 3. Update risk manager
                    balance = self.live_executor.get_balance()
                    self.risk_manager.update_balance(balance.get('balance', self.initial_balance))

                    # 4. Log status
                    if int(time.time()) % 300 == 0:  # Cada 5 min
                        self._log_status()

                except Exception as e:
                    print(f"⚠️ Error en loop de orquestación: {e}")

                time.sleep(10)  # Check cada 10 segundos

        self._orchestrator_thread = threading.Thread(target=orchestration_loop, daemon=True)
        self._orchestrator_thread.start()

        print("✅ Futures Orchestrator iniciado")
        print(f"   Dry Run: {self.dry_run}")
        print(f"   Balance: ${self.initial_balance:,.2f}")

    def stop(self):
        """Detiene el orquestador."""
        self.running = False
        self._stop_event.set()

        # Stop paper traders
        for trader in self.paper_traders.values():
            trader.stop()

        # Close all positions
        if self.live_executor.positions:
            self.live_executor.close_all_positions("orchestrator_shutdown")

        print("🛑 Futures Orchestrator detenido")

    # ========== STATE MANAGEMENT ==========

    def _load_state(self):
        """Carga estado desde archivo."""
        state_file = "/tmp/futures_orchestrator_state.json"
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                # TODO: Restaurar strategies
            except Exception as e:
                print(f"⚠️ Error cargando estado: {e}")

    def _save_state(self):
        """Guarda estado en archivo."""
        state_file = "/tmp/futures_orchestrator_state.json"

        state = {
            "strategies": {
                sid: {
                    "strategy_id": s.strategy_id,
                    "genome": s.genome,
                    "status": s.status.value,
                    "backtest_metrics": s.backtest_metrics,
                    "product_id": s.product_id,
                    "created_at": s.created_at,
                    "activated_at": s.activated_at
                }
                for sid, s in self.strategies.items()
            },
            "balance": self.initial_balance,
            "timestamp": time.time()
        }

        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error guardando estado: {e}")

    def _log_status(self):
        """Log del estado actual."""
        status = {
            "running": self.running,
            "mining_active": self.mining_active,
            "strategies_count": len(self.strategies),
            "active_strategies": sum(1 for s in self.strategies.values() if s.status == StrategyStatus.ACTIVE),
            "risk_level": self.risk_manager.risk_level.value,
            "balance": self.risk_manager.current_balance
        }
        print(f"\n[Orchestrator] {json.dumps(status)}")

    def _send_notification(self, message: str):
        """Envía notificación por Telegram."""
        print(f"\n📱 NOTIFICATION:\n{message}")

        if self.telegram_bot:
            try:
                # TODO: Implementar envío real
                pass
            except Exception as e:
                print(f"⚠️ Error enviando notificación: {e}")

    # ========== STATUS ==========

    def get_current_stage(self) -> dict:
        """
        Determine current scaling stage based on trading history.
        Adjusts capital and leverage limits automatically.
        """
        stats = self.scaling.get_trading_stats()
        stage = self.scaling.get_current_stage(
            trading_days=stats['days'],
            total_trades=stats['trades'],
            win_rate=stats['win_rate'],
            total_pnl=stats['pnl'],
        )
        return self.scaling.get_status()

    def get_status(self) -> dict:
        """Obtiene estado completo del orquestador."""
        return {
            "running": self.running,
            "dry_run": self.dry_run,

            "risk_manager": self.risk_manager.get_status(),
            "live_executor": self.live_executor.get_status(),
            "scaling": self.get_current_stage(),

            "strategies": {
                "total": len(self.strategies),
                "by_status": {
                    status.value: sum(1 for s in self.strategies.values() if s.status == status)
                    for status in StrategyStatus
                },
                "active": [
                    {
                        "id": s.strategy_id,
                        "product": s.product_id,
                        "pnl": s.backtest_metrics.get('Total PnL', 0),
                        "sharpe": s.backtest_metrics.get('Sharpe Ratio', 0)
                    }
                    for s in self.strategies.values()
                    if s.status == StrategyStatus.ACTIVE
                ]
            },

            "paper_traders": len(self.paper_traders)
        }

    def get_report(self) -> str:
        """Genera reporte completo."""
        status = self.get_status()
        rm_status = status['risk_manager']

        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║              FUTURES ORCHESTRATOR STATUS                          ║
╠══════════════════════════════════════════════════════════════════╣
║ Running: {'✅' if status['running'] else '❌'}  Dry Run: {'✅' if status['dry_run'] else '❌'}                              ║
╠══════════════════════════════════════════════════════════════════╣
║ RISK LEVEL: {rm_status['risk_level']:<10}                                        ║
║ Balance: ${rm_status['balance']['current']:>12,.2f} ({rm_status['balance']['pnl_pct']:+.2%})               ║
╠══════════════════════════════════════════════════════════════════╣
║ STRATEGIES                                                        ║
║   Total: {status['strategies']['total']:<3}  Active: {status['strategies']['by_status'].get('ACTIVE', 0):<3}                         ║
║   By Status:                                                      ║
"""
        for st, count in status['strategies']['by_status'].items():
            if count > 0:
                report += f"║     {st}: {count:<3}                                             ║\n"

        report += "╚══════════════════════════════════════════════════════════════════╝"

        return report


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Interfaz de línea de comandos."""
    import argparse

    parser = argparse.ArgumentParser(description="Futures Orchestrator")
    parser.add_argument("--mine", action="store_true", help="Run strategy mining")
    parser.add_argument("--product", type=str, help="Product to mine")
    parser.add_argument("--start", action="store_true", help="Start orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--balance", type=float, default=10000, help="Initial balance")
    parser.add_argument("--status", action="store_true", help="Show status")

    args = parser.parse_args()

    orchestrator = FuturesOrchestrator(
        initial_balance=args.balance,
        dry_run=args.dry_run
    )

    if args.mine:
        if args.product:
            orchestrator.mine_strategies(
                product_id=args.product,
                data_file=f"data_futures/{args.product}_FIVE_MINUTE.csv"
            )
        else:
            orchestrator.mine_all_products()

    elif args.start:
        print("\n🚀 Iniciando Futures Orchestrator...")
        orchestrator.start()

        try:
            while True:
                time.sleep(60)
                print(orchestrator.get_report())
        except KeyboardInterrupt:
            orchestrator.stop()

    elif args.status:
        print(orchestrator.get_report())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
