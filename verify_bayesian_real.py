
import pandas as pd
import numpy as np
import time
import sys
import os

# Ensure we can import modules
sys.path.append(os.getcwd())

from optimizer import BayesianOptimizer
import ray

def main():
    print("🧪 Verifying Bayesian Optimizer with REAL DATA...")
    
    file_path = "data/BTC-USD_ONE_MINUTE.csv"
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    print(f"📂 Loading {file_path}...")
    df = pd.read_csv(file_path)
    print(f"📊 Loaded {len(df)} candles")
    
    # Params
    param_ranges = {
        'fast_ma': [10.0, 50.0],
        'slow_ma': [50.0, 200.0],
        'rsi_period': [14, 14],
        'rsi_overbought': [70, 80],
        'rsi_oversold': [20, 30]
    }
    
    # Instantiate
    optimizer = BayesianOptimizer(
        n_trials=5,  # Small number for quick test
        pruning=False,
        force_local=True
    )
    
    print("🚀 Starting optimization...")
    try:
        results = optimizer.optimize(
            df=df, 
            param_ranges=param_ranges,
            risk_level="LOW",
            strategy_code="BTC_SPOT"
        )
        print("\n✅ Optimization Completed!")
        print(results)
    except Exception as e:
        print(f"\n❌ CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
