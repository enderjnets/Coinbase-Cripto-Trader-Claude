---
description: Debug and fix Ray Distributed Optimization issues (Zombies, Timeouts, Connections)
---

# Debugging Ray Distributed Optimization

Follow this workflow if the Grid/Bayesian Optimization is stuck, failing with timeouts, or not using all cluster resources.

## 1. Check Connection & Resources

First, verify that the Ray cluster is reachable and has the expected number of CPUs.

```bash
python3 verify_bayesian_real.py
# Look for: "✅ Conectado a Cluster Ray... CPUs: XX"
```

If it says "Modo Local" or 0 CPUs:
1. Ensure the Head Node is running (`start_cluster_head.py`).
2. Check `RAY_ADDRESS` environment variable.
3. Check firewall settings on both machines.

## 2. Fix "Zombie" Processes (Stuck CPU)

If you see high CPU usage but no progress in the UI, or after stopping an optimization:

```bash
# Clean up Workers
pkill -f "ray::"
pkill -f "raylet"

# Clean up Head (if local)
ray stop --force
```

// turbo
```bash
# Force kill all python ray processes just in case
pkill -9 -f "ray"
```

## 3. Fix Timeouts (Backtest exceeded Xs)

If trials fail with `TimeoutError`, you need to increase the safety limit in `optimizer.py`.

1. Open `optimizer.py`.
2. Search for `signal.alarm`.
3. Increase the value (e.g., from 120 to 600).

```python
# Example in optimizer.py
def handler(signum, frame):
    raise TimeoutError("Backtest exceeded 600s execution time limit")
signal.alarm(600) 
```

## 4. Enable Parallelism (Optuna)

If only 1 CPU is used despite having a cluster:

1. Open `optimizer.py`.
2. Ensure `n_jobs` in `study.optimize` matches the cluster CPU count.

```python
cluster_cpus = int(ray.cluster_resources().get('CPU', 1))
study.optimize(..., n_jobs=cluster_cpus)
```

## 5. Reinstall Ray (SegFaults)

If Ray crashes immediately with Segmentation Fault:

```bash
.venv/bin/python -m pip install --force-reinstall "ray[default]"
```
