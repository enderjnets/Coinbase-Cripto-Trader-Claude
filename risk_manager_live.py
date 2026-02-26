#!/usr/bin/env python3
"""
risk_manager_live.py - Sistema de Gestión de Riesgo para Trading Real
=====================================================================

Protege el capital con múltiples capas de seguridad:
- Límites de pérdida diaria/mensual
- Circuit breakers por volatilidad
- Límites de posición y apalancamiento
- Protección contra correlación
- Monitoreo de liquidaciones
- Alertas automáticas

CRÍTICO: Este módulo debe validarse exhaustivamente antes de operar con dinero real.

Autor: Strategy Miner Team
Fecha: Feb 2026
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import sqlite3

# ============================================================================
# CONFIGURACIÓN DE RIESGO
# ============================================================================

@dataclass
class RiskConfig:
    """Configuración de límites de riesgo."""

    # === LÍMITES DE PÉRDIDA ===
    max_daily_loss_pct: float = 0.03      # 3% pérdida máxima diaria
    max_weekly_loss_pct: float = 0.07     # 7% pérdida máxima semanal
    max_monthly_loss_pct: float = 0.15    # 15% pérdida máxima mensual
    max_drawdown_pct: float = 0.20        # 20% drawdown máximo histórico

    # === LÍMITES DE POSICIÓN ===
    max_positions: int = 5                # Máximo posiciones simultáneas
    max_position_size_pct: float = 0.10   # 10% del capital por posición
    max_total_exposure_pct: float = 0.50  # 50% exposición total máxima
    max_leverage: int = 5                 # Apalancamiento máximo
    max_leverage_total: int = 15          # Suma de leverages máxima

    # === LÍMITES POR ACTIVO ===
    max_same_asset_positions: int = 2     # Máximo posiciones en mismo activo
    max_correlated_exposure_pct: float = 0.30  # 30% en activos correlacionados

    # === CIRCUIT BREAKERS ===
    volatility_spike_threshold: float = 0.05   # 5% movimiento en 5min
    price_gap_threshold: float = 0.02           # 2% gap de precio
    funding_rate_threshold: float = 0.001       # 0.1% funding rate

    # === COOLDOWNS ===
    loss_cooldown_minutes: int = 30        # Pausa después de pérdida grande
    liquidation_cooldown_hours: int = 2    # Pausa después de liquidación
    daily_trade_limit: int = 50            # Máximo trades por día

    # === ALERTAS ===
    alert_loss_threshold_pct: float = 0.015    # Alertar al 1.5% pérdida
    alert_drawdown_threshold_pct: float = 0.10  # Alertar al 10% drawdown
    alert_margin_usage_pct: float = 0.70        # Alertar al 70% uso de margen


class RiskLevel(Enum):
    """Niveles de riesgo."""
    SAFE = "SAFE"              # Operación normal
    CAUTION = "CAUTION"        # Precaución, reducir exposición
    WARNING = "WARNING"        # Advertencia, no abrir nuevas posiciones
    CRITICAL = "CRITICAL"      # Crítico, cerrar posiciones
    HALT = "HALT"              # Detener todo trading


@dataclass
class TradeRecord:
    """Registro de un trade."""
    timestamp: float
    product_id: str
    side: str
    pnl: float
    pnl_pct: float
    reason: str
    leverage: int
    margin_used: float


@dataclass
class DailyStats:
    """Estadísticas diarias."""
    date: str
    starting_balance: float
    current_balance: float
    total_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    max_drawdown: float = 0.0
    liquidations: int = 0
    peak_balance: float = 0.0


# ============================================================================
# RISK MANAGER
# ============================================================================

class RiskManager:
    """
    Sistema de gestión de riesgo en tiempo real.

    Funciones principales:
    1. Validar operaciones antes de ejecutar
    2. Monitorear posiciones y balance
    3. Activar circuit breakers
    4. Generar alertas
    5. Registrar historial
    """

    def __init__(
        self,
        initial_balance: float,
        config: RiskConfig = None,
        db_path: str = "/tmp/risk_manager.db"
    ):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.config = config or RiskConfig()
        self.db_path = db_path

        # State
        self.risk_level = RiskLevel.SAFE
        self.daily_stats: Dict[str, DailyStats] = {}
        self.trade_history: List[TradeRecord] = []
        self.position_tracking: Dict[str, dict] = {}

        # Circuit breakers
        self.cooldown_until: Optional[float] = None
        self.halt_trading: bool = False
        self.halt_reason: str = ""

        # Lock para thread safety
        self._lock = threading.RLock()

        # Initialize
        self._init_db()
        self._load_state()
        self._init_daily_stats()

    # ========== DATABASE ==========

    def _init_db(self):
        """Inicializa base de datos de riesgo."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                product_id TEXT,
                side TEXT,
                pnl REAL,
                pnl_pct REAL,
                reason TEXT,
                leverage INTEGER,
                margin_used REAL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                starting_balance REAL,
                ending_balance REAL,
                total_pnl REAL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                max_drawdown REAL,
                liquidations INTEGER
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                event_type TEXT,
                risk_level TEXT,
                message TEXT,
                action_taken TEXT
            )
        """)

        conn.commit()
        conn.close()

    def _load_state(self):
        """Carga estado desde DB."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Cargar trades del día
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("""
            SELECT timestamp, product_id, side, pnl, pnl_pct, reason, leverage, margin_used
            FROM trades
            WHERE date(timestamp, 'unixepoch') = ?
            ORDER BY timestamp
        """, (today,))

        for row in c.fetchall():
            self.trade_history.append(TradeRecord(
                timestamp=row[0],
                product_id=row[1],
                side=row[2],
                pnl=row[3],
                pnl_pct=row[4],
                reason=row[5],
                leverage=row[6],
                margin_used=row[7]
            ))

        conn.close()

    def _init_daily_stats(self):
        """Inicializa estadísticas del día."""
        today = datetime.now().strftime("%Y-%m-%d")

        if today not in self.daily_stats:
            self.daily_stats[today] = DailyStats(
                date=today,
                starting_balance=self.current_balance,
                current_balance=self.current_balance,
                peak_balance=self.current_balance
            )

    def _save_trade(self, trade: TradeRecord):
        """Guarda trade en DB."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            INSERT INTO trades (timestamp, product_id, side, pnl, pnl_pct, reason, leverage, margin_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.timestamp,
            trade.product_id,
            trade.side,
            trade.pnl,
            trade.pnl_pct,
            trade.reason,
            trade.leverage,
            trade.margin_used
        ))

        conn.commit()
        conn.close()

    def _save_risk_event(self, event_type: str, risk_level: RiskLevel,
                         message: str, action: str):
        """Guarda evento de riesgo en DB."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            INSERT INTO risk_events (timestamp, event_type, risk_level, message, action_taken)
            VALUES (?, ?, ?, ?, ?)
        """, (time.time(), event_type, risk_level.value, message, action))

        conn.commit()
        conn.close()

    # ========== CORE VALIDATION ==========

    def can_open_position(
        self,
        product_id: str,
        side: str,
        leverage: int,
        margin_usd: float,
        current_positions: Dict[str, dict]
    ) -> Tuple[bool, str]:
        """
        Valida si se puede abrir una nueva posición.

        Returns:
            (can_open: bool, reason: str)
        """
        with self._lock:
            # 1. Check halt
            if self.halt_trading:
                return False, f"Trading detenido: {self.halt_reason}"

            # 2. Check cooldown
            if self.cooldown_until and time.time() < self.cooldown_until:
                remaining = int(self.cooldown_until - time.time())
                return False, f"En cooldown ({remaining}s restantes)"

            # 3. Check risk level
            if self.risk_level in [RiskLevel.WARNING, RiskLevel.CRITICAL]:
                return False, f"Nivel de riesgo: {self.risk_level.value}"

            # 4. Check daily loss
            daily_pnl_pct = self._get_daily_pnl_pct()
            if daily_pnl_pct <= -self.config.max_daily_loss_pct:
                self._trigger_cooldown("loss_limit")
                return False, f"Pérdida diaria alcanzada: {daily_pnl_pct:.2%}"

            # 5. Check max positions
            if len(current_positions) >= self.config.max_positions:
                return False, f"Máximo posiciones alcanzado ({self.config.max_positions})"

            # 6. Check leverage
            if leverage > self.config.max_leverage:
                return False, f"Leverage excede máximo ({leverage}x > {self.config.max_leverage}x)"

            # 7. Check total leverage
            total_leverage = sum(p.get('leverage', 1) for p in current_positions.values())
            if total_leverage + leverage > self.config.max_leverage_total:
                return False, f"Leverage total excede límite ({total_leverage + leverage}x)"

            # 8. Check margin
            if margin_usd > self.current_balance * self.config.max_position_size_pct:
                return False, f"Margen excede límite por posición ({self.config.max_position_size_pct:.0%})"

            available_margin = self.current_balance * (1 - self._get_margin_usage_pct(current_positions))
            if margin_usd > available_margin:
                return False, f"Margen insuficiente (disponible: ${available_margin:.2f})"

            # 9. Check same asset exposure
            same_asset = sum(1 for p in current_positions if product_id.split('-')[0] in p)
            if same_asset >= self.config.max_same_asset_positions:
                return False, f"Máximo posiciones en {product_id.split('-')[0]} alcanzado"

            # 10. Check daily trade limit
            today = datetime.now().strftime("%Y-%m-%d")
            if today in self.daily_stats:
                if self.daily_stats[today].total_trades >= self.config.daily_trade_limit:
                    return False, f"Límite diario de trades alcanzado ({self.config.daily_trade_limit})"

            # All checks passed
            return True, "OK"

    def can_increase_position(
        self,
        product_id: str,
        current_size: int,
        additional_size: int,
        current_positions: Dict[str, dict]
    ) -> Tuple[bool, str]:
        """Valida si se puede aumentar una posición existente."""
        with self._lock:
            # Similar checks pero más permisivo para añadir a posición existente
            if self.halt_trading:
                return False, f"Trading detenido: {self.halt_reason}"

            if self.risk_level == RiskLevel.CRITICAL:
                return False, f"Nivel de riesgo crítico"

            # Check exposure
            new_exposure = sum(
                p.get('size', 0) * p.get('entry_price', 0) * p.get('leverage', 1)
                for p in current_positions.values()
            )
            max_exposure = self.current_balance * self.config.max_total_exposure_pct

            if new_exposure > max_exposure:
                return False, f"Exposición total excedería límite"

            return True, "OK"

    # ========== RISK MONITORING ==========

    def update_balance(self, new_balance: float):
        """Actualiza balance y recalcula riesgo."""
        with self._lock:
            old_balance = self.current_balance
            self.current_balance = new_balance

            # Update daily stats
            today = datetime.now().strftime("%Y-%m-%d")
            if today in self.daily_stats:
                stats = self.daily_stats[today]
                stats.current_balance = new_balance
                stats.total_pnl = new_balance - stats.starting_balance

                if new_balance > stats.peak_balance:
                    stats.peak_balance = new_balance

                # Calculate drawdown
                if stats.peak_balance > 0:
                    dd = (stats.peak_balance - new_balance) / stats.peak_balance
                    if dd > stats.max_drawdown:
                        stats.max_drawdown = dd

            # Recalculate risk level
            self._update_risk_level()

    def record_trade(
        self,
        product_id: str,
        side: str,
        pnl: float,
        pnl_pct: float,
        reason: str,
        leverage: int,
        margin_used: float
    ):
        """Registra un trade completado."""
        with self._lock:
            trade = TradeRecord(
                timestamp=time.time(),
                product_id=product_id,
                side=side,
                pnl=pnl,
                pnl_pct=pnl_pct,
                reason=reason,
                leverage=leverage,
                margin_used=margin_used
            )

            self.trade_history.append(trade)
            self._save_trade(trade)

            # Update daily stats
            today = datetime.now().strftime("%Y-%m-%d")
            if today in self.daily_stats:
                stats = self.daily_stats[today]
                stats.total_trades += 1
                stats.total_pnl += pnl

                if pnl > 0:
                    stats.winning_trades += 1
                else:
                    stats.losing_trades += 1

                if "liquidation" in reason.lower():
                    stats.liquidations += 1

            # Check for loss cooldown
            if pnl_pct <= -0.05:  # Pérdida grande
                self._trigger_cooldown("large_loss")

    def record_liquidation(self, product_id: str, pnl: float):
        """Registra una liquidación."""
        with self._lock:
            self.record_trade(
                product_id=product_id,
                side="LIQUIDATION",
                pnl=pnl,
                pnl_pct=-1.0,
                reason="liquidation",
                leverage=0,
                margin_used=0
            )

            # Extended cooldown after liquidation
            self.cooldown_until = time.time() + (self.config.liquidation_cooldown_hours * 3600)

            self._save_risk_event(
                "LIQUIDATION",
                RiskLevel.CRITICAL,
                f"Liquidación en {product_id}: ${pnl:.2f}",
                f"Cooldown {self.config.liquidation_cooldown_hours}h activado"
            )

    def check_positions(self, positions: Dict[str, dict], prices: Dict[str, float]) -> List[str]:
        """
        Revisa todas las posiciones y retorna acciones recomendadas.

        Returns:
            Lista de acciones recomendadas (ej. ["CLOSE:BIP-USD:stop_loss"])
        """
        actions = []

        with self._lock:
            for product_id, pos in positions.items():
                current_price = prices.get(product_id, pos.get('mark_price', 0))
                entry_price = pos.get('entry_price', 0)
                side = pos.get('side', 'LONG')
                leverage = pos.get('leverage', 1)
                liquidation_price = pos.get('liquidation_price', 0)

                if entry_price == 0:
                    continue

                # Check liquidation risk
                liq_distance = abs(current_price - liquidation_price) / current_price
                if liq_distance < 0.01:  # Menos de 1% de liquidación
                    actions.append(f"URGENT:{product_id}:near_liquidation")
                    continue

                # Check unrealized loss
                if side == 'LONG':
                    pnl_pct = (current_price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - current_price) / entry_price

                pnl_pct *= leverage

                if pnl_pct <= -0.10:  # Pérdida 10%
                    actions.append(f"CLOSE:{product_id}:large_loss")

                elif pnl_pct <= -0.05:  # Pérdida 5%
                    actions.append(f"WARNING:{product_id}:approaching_loss_limit")

        return actions

    # ========== CIRCUIT BREAKERS ==========

    def check_volatility_spike(self, product_id: str, price_change_pct: float) -> bool:
        """Detecta spike de volatilidad."""
        if abs(price_change_pct) >= self.config.volatility_spike_threshold:
            self._save_risk_event(
                "VOLATILITY_SPIKE",
                RiskLevel.WARNING,
                f"{product_id}: movimiento {price_change_pct:.2%} en 5min",
                "Reduce position sizes recommended"
            )
            return True
        return False

    def check_funding_rate(self, product_id: str, funding_rate: float) -> bool:
        """Verifica funding rate extremo."""
        if abs(funding_rate) >= self.config.funding_rate_threshold:
            self._save_risk_event(
                "HIGH_FUNDING",
                RiskLevel.CAUTION,
                f"{product_id}: funding rate {funding_rate:.4%}",
                "Consider closing position before funding"
            )
            return True
        return False

    def _trigger_cooldown(self, reason: str):
        """Activa período de cooldown."""
        self.cooldown_until = time.time() + (self.config.loss_cooldown_minutes * 60)

        self._save_risk_event(
            "COOLDOWN",
            self.risk_level,
            f"Cooldown activado: {reason}",
            f"No trading por {self.config.loss_cooldown_minutes} minutos"
        )

    def trigger_halt(self, reason: str):
        """Detiene todo trading."""
        with self._lock:
            self.halt_trading = True
            self.halt_reason = reason
            self.risk_level = RiskLevel.HALT

            self._save_risk_event(
                "HALT",
                RiskLevel.HALT,
                reason,
                "All trading suspended"
            )

    def clear_halt(self):
        """Limpia estado de halt (manual)."""
        with self._lock:
            self.halt_trading = False
            self.halt_reason = ""
            self.risk_level = RiskLevel.SAFE

    # ========== HELPERS ==========

    def _update_risk_level(self):
        """Actualiza nivel de riesgo basado en estado actual."""
        daily_pnl_pct = self._get_daily_pnl_pct()
        drawdown = self._get_current_drawdown()

        # Determine risk level
        new_level = RiskLevel.SAFE

        if self.halt_trading:
            new_level = RiskLevel.HALT
        elif daily_pnl_pct <= -self.config.max_daily_loss_pct:
            new_level = RiskLevel.HALT
            self.trigger_halt("Daily loss limit reached")
        elif drawdown >= self.config.max_drawdown_pct:
            new_level = RiskLevel.HALT
            self.trigger_halt("Max drawdown reached")
        elif daily_pnl_pct <= -self.config.alert_loss_threshold_pct:
            new_level = RiskLevel.WARNING
        elif daily_pnl_pct <= -self.config.max_daily_loss_pct * 0.5:
            new_level = RiskLevel.CAUTION

        if new_level != self.risk_level:
            self.risk_level = new_level
            self._save_risk_event(
                "RISK_LEVEL_CHANGE",
                new_level,
                f"Nivel cambiado a {new_level.value}",
                ""
            )

    def _get_daily_pnl_pct(self) -> float:
        """Obtiene PnL porcentual del día."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today in self.daily_stats:
            stats = self.daily_stats[today]
            if stats.starting_balance > 0:
                return (stats.current_balance - stats.starting_balance) / stats.starting_balance
        return 0.0

    def _get_current_drawdown(self) -> float:
        """Obtiene drawdown actual."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today in self.daily_stats:
            return self.daily_stats[today].max_drawdown
        return 0.0

    def _get_margin_usage_pct(self, positions: Dict[str, dict]) -> float:
        """Obtiene porcentaje de margen usado."""
        if self.current_balance == 0:
            return 1.0

        total_margin = sum(p.get('margin', 0) for p in positions.values())
        return total_margin / self.current_balance

    # ========== STATUS & REPORTS ==========

    def get_status(self) -> dict:
        """Obtiene estado completo del risk manager."""
        with self._lock:
            today = datetime.now().strftime("%Y-%m-%d")
            stats = self.daily_stats.get(today, DailyStats(
                date=today,
                starting_balance=self.current_balance,
                current_balance=self.current_balance
            ))

            return {
                "risk_level": self.risk_level.value,
                "can_trade": not self.halt_trading and (self.cooldown_until is None or time.time() >= self.cooldown_until),
                "halt_active": self.halt_trading,
                "halt_reason": self.halt_reason,
                "cooldown_remaining": max(0, (self.cooldown_until - time.time())) if self.cooldown_until else 0,

                "balance": {
                    "current": self.current_balance,
                    "initial": self.initial_balance,
                    "pnl_total": self.current_balance - self.initial_balance,
                    "pnl_pct": (self.current_balance - self.initial_balance) / self.initial_balance if self.initial_balance > 0 else 0
                },

                "daily": {
                    "starting": stats.starting_balance,
                    "current": stats.current_balance,
                    "pnl": stats.total_pnl,
                    "pnl_pct": stats.total_pnl / stats.starting_balance if stats.starting_balance > 0 else 0,
                    "trades": stats.total_trades,
                    "wins": stats.winning_trades,
                    "losses": stats.losing_trades,
                    "win_rate": stats.winning_trades / stats.total_trades * 100 if stats.total_trades > 0 else 0,
                    "drawdown": stats.max_drawdown,
                    "liquidations": stats.liquidations
                },

                "limits": {
                    "max_daily_loss": self.config.max_daily_loss_pct,
                    "max_positions": self.config.max_positions,
                    "max_leverage": self.config.max_leverage,
                    "daily_trade_limit": self.config.daily_trade_limit
                },

                "trade_count_today": len([t for t in self.trade_history
                                          if datetime.fromtimestamp(t.timestamp).strftime("%Y-%m-%d") == today])
            }

    def get_report(self) -> str:
        """Genera reporte legible."""
        status = self.get_status()

        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║              RISK MANAGER STATUS REPORT                          ║
╠══════════════════════════════════════════════════════════════════╣
║ Risk Level: {status['risk_level']:<10}  Can Trade: {'✅' if status['can_trade'] else '❌':<5}               ║
╠══════════════════════════════════════════════════════════════════╣
║ BALANCE                                                          ║
║   Current:  ${status['balance']['current']:>12,.2f}                              ║
║   PnL:     ${status['balance']['pnl_total']:>+12,.2f} ({status['balance']['pnl_pct']:+.2%})                   ║
╠══════════════════════════════════════════════════════════════════╣
║ TODAY                                                            ║
║   PnL:     ${status['daily']['pnl']:>+12,.2f} ({status['daily']['pnl_pct']:+.2%})                   ║
║   Trades:  {status['daily']['trades']:>5}  Win Rate: {status['daily']['win_rate']:>5.1f}%                     ║
║   Max DD:  {status['daily']['drawdown']:>5.2%}  Liquidations: {status['daily']['liquidations']:>3}                   ║
╠══════════════════════════════════════════════════════════════════╣
║ LIMITS                                                           ║
║   Max Daily Loss: {status['limits']['max_daily_loss']:.1%}  Max Positions: {status['limits']['max_positions']}              ║
║   Max Leverage: {status['limits']['max_leverage']}x  Daily Trade Limit: {status['limits']['daily_trade_limit']}              ║
╚══════════════════════════════════════════════════════════════════╝
"""
        if status['halt_active']:
            report += f"\n⚠️  HALT ACTIVE: {status['halt_reason']}\n"

        if status['cooldown_remaining'] > 0:
            report += f"\n⏳ COOLDOWN: {int(status['cooldown_remaining'])}s remaining\n"

        return report


# ============================================================================
# TEST
# ============================================================================

def test_risk_manager():
    """Prueba el risk manager."""
    print("="*70)
    print("🧪 RISK MANAGER - TEST")
    print("="*70)

    # Crear risk manager
    rm = RiskManager(initial_balance=10000)

    print(rm.get_report())

    # Test validación de posición
    print("\n📋 Test: ¿Puedo abrir posición?")
    can_open, reason = rm.can_open_position(
        product_id="BIP-USD",
        side="LONG",
        leverage=5,
        margin_usd=500,
        current_positions={}
    )
    print(f"   Resultado: {'✅' if can_open else '❌'} {reason}")

    # Simular trade
    print("\n📋 Test: Registrar trade perdedor...")
    rm.record_trade(
        product_id="BIP-USD",
        side="LONG",
        pnl=-250,
        pnl_pct=-0.05,
        reason="stop_loss",
        leverage=5,
        margin_used=500
    )

    # Actualizar balance
    rm.update_balance(9750)

    print(rm.get_report())

    # Test de nuevo con pérdida acumulada
    print("\n📋 Test: ¿Puedo seguir operando después de pérdida?")
    can_open, reason = rm.can_open_position(
        product_id="ETP-USD",
        side="LONG",
        leverage=3,
        margin_usd=300,
        current_positions={}
    )
    print(f"   Resultado: {'✅' if can_open else '❌'} {reason}")

    print("\n✅ Test completado")


if __name__ == "__main__":
    test_risk_manager()
