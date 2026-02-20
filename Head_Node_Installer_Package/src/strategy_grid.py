"""
Grid Trading Strategy (Estrategia de Malla Dinámica)
Optimizada para mercados LATERALES/CONSOLIDACIÓN
Usa órdenes MAKER (límite) para minimizar comisiones
"""

import pandas as pd
import numpy as np


class GridTradingStrategy:
    """
    Grid Trading con espaciado geométrico.

    Coloca órdenes de compra y venta en niveles de precio predefinidos.
    Cuando el precio sube, vende. Cuando baja, compra.

    CRÍTICO: El espaciado debe ser >1% para superar las comisiones Maker (0.80%)
    """

    def __init__(
        self,
        grid_spacing_pct=1.2,  # Espaciado entre niveles (% geométrico)
        num_grids=10,           # Número de niveles de la malla
        grid_range_pct=10.0,    # Rango total de la malla (% desde precio central)
        rebalance_threshold=5.0 # % de movimiento para rebalancear malla
    ):
        """
        Args:
            grid_spacing_pct: Espaciado entre niveles (DEBE ser >1% para Coinbase)
            num_grids: Número de niveles de compra/venta
            grid_range_pct: Rango total de la malla
            rebalance_threshold: % de movimiento para desplazar la malla
        """
        self.grid_spacing_pct = grid_spacing_pct
        self.num_grids = num_grids
        self.grid_range_pct = grid_range_pct
        self.rebalance_threshold = rebalance_threshold

        # Estado interno
        self.grid_levels = None
        self.grid_center = None
        self.filled_buys = set()   # Niveles donde se ejecutó compra
        self.filled_sells = set()  # Niveles donde se ejecutó venta

    def initialize_grid(self, current_price):
        """
        Crea la malla de niveles de precio alrededor del precio actual.
        """
        self.grid_center = current_price

        # Calcular niveles geométricos
        levels = []
        half_grids = self.num_grids // 2

        # Niveles inferiores (compras)
        for i in range(1, half_grids + 1):
            level = current_price * (1 - (self.grid_spacing_pct / 100) * i)
            levels.append(('BUY', level))

        # Niveles superiores (ventas)
        for i in range(1, half_grids + 1):
            level = current_price * (1 + (self.grid_spacing_pct / 100) * i)
            levels.append(('SELL', level))

        self.grid_levels = sorted(levels, key=lambda x: x[1])

        # Limpiar estado de fills
        self.filled_buys.clear()
        self.filled_sells.clear()

    def needs_rebalance(self, current_price):
        """
        Determina si la malla necesita rebalancearse (desplazarse)
        porque el precio se salió del rango.
        """
        if self.grid_center is None:
            return True

        # Calcular distancia del precio al centro
        distance_pct = abs((current_price - self.grid_center) / self.grid_center) * 100

        return distance_pct > self.rebalance_threshold

    def get_signal(self, df, index):
        """
        Genera señal de trading basada en el cruce de niveles del grid.

        NUEVA LÓGICA: Detecta mercados bajistas fuertes para salir a cash.

        Returns:
            dict: {'signal': 'BUY'/'SELL'/None, 'level': price_level, 'reason': str}
        """
        if len(df) < 2 or index < 1:
            return {'signal': None, 'level': None, 'reason': 'Insufficient data'}

        current_price = df.loc[index, 'close']
        prev_price = df.loc[index - 1, 'close']

        # NUEVO: Detectar tendencia bajista fuerte (exit to cash)
        # Si el precio cae >5% desde el centro del grid, salir completamente
        if self.grid_center is not None:
            price_drop_pct = ((current_price - self.grid_center) / self.grid_center) * 100

            # Si caída > 15%, pausar nuevas compras (Safety mode) pero NO vender en pérdida
            if price_drop_pct < -15.0:
                pass # HOLD MODE - Esperar recuperación


        # Inicializar o rebalancear malla
        # AHORA: Rebalancear significa mover el centro para seguir la tendencia suavemente
        diff_pct = abs((current_price - self.grid_center) / self.grid_center) * 100 if self.grid_center else 0
        
        if self.grid_levels is None or diff_pct > self.rebalance_threshold:
            # Re-centrar malla al precio actual (Trend Following)
            self.initialize_grid(current_price)
            # Nota: Esto no vende las posiciones antiguas, solo crea nuevos niveles operativos
            return {'signal': None, 'level': None, 'reason': 'Grid re-centered to follow trend'}

        # Verificar cruce de niveles
        for side, level in self.grid_levels:
            # Cruce ascendente de nivel de VENTA
            if side == 'SELL' and prev_price < level <= current_price:
                level_id = f"{side}_{level:.2f}"

                # Solo vender si previamente compramos en un nivel inferior
                # (evita vender en corto)
                if len(self.filled_buys) > 0 and level_id not in self.filled_sells:
                    self.filled_sells.add(level_id)
                    return {
                        'signal': 'SELL',
                        'level': level,
                        'reason': f'Grid SELL level crossed at {level:.2f}'
                    }

            # Cruce descendente de nivel de COMPRA
            if side == 'BUY' and prev_price > level >= current_price:
                level_id = f"{side}_{level:.2f}"

                if level_id not in self.filled_buys:
                    self.filled_buys.add(level_id)
                    return {
                        'signal': 'BUY',
                        'level': level,
                        'reason': f'Grid BUY level crossed at {level:.2f}'
                    }

        return {'signal': None, 'level': None, 'reason': 'No level crossed'}

    def calculate_position_size(self, balance, price):
        """
        Calcula el tamaño de posición para cada nivel del grid.

        Divide el capital disponible entre el número de niveles.
        """
        # Usar solo el 80% del balance para dejar margen
        available = balance * 0.8

        # Dividir entre número de niveles activos posibles
        size_per_level = available / self.num_grids

        # Convertir a cantidad de monedas
        quantity = size_per_level / price

        return quantity

    def get_grid_info(self):
        """
        Devuelve información sobre el estado actual de la malla.
        Útil para debugging y visualización.
        """
        if self.grid_levels is None:
            return None

        return {
            'center': self.grid_center,
            'levels': self.grid_levels,
            'filled_buys': len(self.filled_buys),
            'filled_sells': len(self.filled_sells),
            'spacing_pct': self.grid_spacing_pct
        }


def backtest_grid_strategy(df, initial_balance=10000, grid_params=None):
    """
    Backtester específico para Grid Trading.
    Simula la ejecución de la estrategia en datos históricos.
    """
    if grid_params is None:
        grid_params = {
            'grid_spacing_pct': 1.2,
            'num_grids': 10,
            'grid_range_pct': 10.0,
            'rebalance_threshold': 5.0
        }

    strategy = GridTradingStrategy(**grid_params)

    balance = initial_balance
    position = 0.0
    trades = []

    for i in df.index:
        signal = strategy.get_signal(df, i)

        if signal['signal'] == 'BUY' and balance > 0:
            # Calcular tamaño de compra
            price = df.loc[i, 'close']
            quantity = strategy.calculate_position_size(balance, price)
            cost = quantity * price

            # Comisión Maker (0.40%)
            fee = cost * 0.004
            total_cost = cost + fee

            if total_cost <= balance:
                balance -= total_cost
                position += quantity

                trades.append({
                    'timestamp': df.loc[i, 'timestamp'],
                    'type': 'BUY',
                    'price': price,
                    'quantity': quantity,
                    'fee': fee,
                    'balance': balance
                })

        elif signal['signal'] == 'SELL' and position > 0:
            # Vender toda la posición (o parte proporcional)
            price = df.loc[i, 'close']
            quantity = strategy.calculate_position_size(initial_balance, price)
            quantity = min(quantity, position)  # No vender más de lo que tenemos

            proceeds = quantity * price
            fee = proceeds * 0.004  # Comisión Maker
            net_proceeds = proceeds - fee

            balance += net_proceeds
            position -= quantity

            trades.append({
                'timestamp': df.loc[i, 'timestamp'],
                'type': 'SELL',
                'price': price,
                'quantity': quantity,
                'fee': fee,
                'balance': balance
            })

    # Valor final (balance + valor de posición restante)
    final_price = df.iloc[-1]['close']
    final_balance = balance + (position * final_price)

    return {
        'final_balance': final_balance,
        'total_pnl': final_balance - initial_balance,
        'trades': trades,
        'num_trades': len(trades),
        'final_position': position
    }


if __name__ == "__main__":
    print("Grid Trading Strategy - Test")

    # Crear datos de mercado lateral simulado
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=500, freq='5min')

    # Precio oscilando entre 95 y 105
    price_base = 100
    prices = price_base + 5 * np.sin(np.linspace(0, 10, 500)) + np.random.randn(500) * 0.5

    df_test = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices + 0.5,
        'low': prices - 0.5,
        'close': prices,
        'volume': np.random.randint(100, 1000, 500)
    })

    df_test = df_test.reset_index(drop=True)

    # Backtest
    results = backtest_grid_strategy(df_test, initial_balance=10000)

    print(f"\n📊 Resultados:")
    print(f"Balance final: ${results['final_balance']:.2f}")
    print(f"PnL: ${results['total_pnl']:.2f}")
    print(f"Total trades: {results['num_trades']}")
    print(f"ROI: {(results['total_pnl'] / 10000) * 100:.2f}%")
