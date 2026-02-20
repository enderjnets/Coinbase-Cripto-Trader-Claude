---
description: Setup a distributed Ray Cluster for Python optimization on macOS
---

1. **Prerequisites**
   - Ensure all machines are on the same local network (e.g., connected to the same Wi-Fi).
   - Ensure strict Python version matching (e.g., both 3.9.x).
   - **CRITICAL**: Dependency versions must match exactly, especially `numpy`.

2. **Head Node Setup (Main Machine)**
   - Create a script to start Ray with `address='auto'` or implicit head.
   - Example command: `ray start --head --port=6379 --include-dashboard=true`
   - In Python:
     ```python
     # optimizer.py
     ray.init(address='auto', runtime_env={"working_dir": ".", "excludes": [...]})
     ```

3. **Worker Node Setup (Secondary Machine)**
   - Create a `setup_worker.sh` script.
   - **Step A: Environment**: Create a venv (`python3 -m venv worker_env`).
   - **Step B: Dependencies**: Install EXACT same versions as Head.
     - `numpy`: If Head has 2.0.2, Worker MUST have 2.0.2. Do not pin `<2.0` on worker if Head is new.
     - `python-dotenv`: Required for config loading.
     - `coinbase-advanced-py` (or others): Required if imported by any shared module, even if unused on worker.
   - **Step C: Connect**:
     - Auto-discover Head IP (e.g., via `nmap` or manual entry).
     - Command: `ray start --address=<HEAD_IP>:6379`

4. **Code Synchronization**
   - Use `runtime_env` in `ray.init` on the Head Node.
   - This automatically zips and ships the current directory to workers.
   - **Troubleshooting**: If workers crash with `ImportError`, check:
     - Is the file excluded in `excludes`?
     - Are all dependencies installed on the worker? (Check `OPTIMIZER_CRASH.txt` via entry point wrapper).

5. **Debugging Crashes**
   - Ray errors on workers can be silent or fleeting.
   - **Technique**: Wrap the worker task execution in a `try/except` block and write the traceback to a file (`CRASH_LOG.txt`) on the disk. This persists the error message that otherwise disappears with the process.

6. **Common "Gotchas"**
   - **NumPy Mismatch**: `ModuleNotFoundError: No module named 'numpy._core.numeric'` -> Worker has older NumPy than Head.
   - **Missing Dotenv**: `No module named 'dotenv'` -> Forgot to install `python-dotenv`.
   - **Implicit Imports**: `No module named 'coinbase'` -> `scanner.py` imports it, so Worker needs it even for backtesting.
