# SKILL: Crypto Strategy Miner - Distributed Computing System
**Last Updated**: 2026-02-26

## Recent Updates (Feb 2026)

### New Files Added
- `live_paper_trader.py` - Paper trading with Coinbase WebSocket real-time data
- `monitor_daemon.py` - Autonomous monitoring and auto-restart system
- `risk_metrics.py` - Professional risk metrics (Sharpe, Sortino, VaR, CVaR, etc.)
- `production_checklist.py` - Pre-production validation checklist
- `position_sizing.py` - Kelly Criterion and position sizing methods

### Critical Bug Fixes
1. **Absurd PnL values** (100+ digits): Added safety limits in `numba_backtester.py`
   - `MAX_BALANCE = 1_000_000.0`
   - `MAX_POSITION_VALUE = 100_000.0`
   - `MAX_PNL = 1_000_000.0`
   - Data validation with `np.nan_to_num()`

2. **macOS Google Drive access blocked**: Workers now check local paths first
   - `~/trader_data/data/` and `~/trader_data/data_futures/`
   - `~/crypto_worker/data/`

### Workers Configuration (15 total)
| Machine | IP | Workers | Access |
|---------|-----|---------|--------|
| MacBook Pro | 10.0.0.232 | 3 | Local |
| MacBook Air | 10.0.0.97 | 4 | SSH (password: 571947) |
| Linux ROG | 10.0.0.240 | 5 | SSH key-based |
| Asus Dorada | 10.0.0.56 | 3 | SSH key-based |

### Monitor Daemon
Auto-restarts all services if:
- Coordinator not responding
- Less than 8 workers alive
- Telegram bot not running

---

## Project Identity
- **Name**: Coinbase Crypto Trader - Strategy Miner
- **Owner**: Ender Ocando (enderj)
- **Location**: /Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude
- **Purpose**: Discover optimal cryptocurrency trading strategies using genetic algorithms across distributed workers
- **Language**: User communicates in Spanish

---

## Architecture Overview

### System Components
```
Streamlit Dashboard (port 8501)
        |
Coordinator Server (Flask, port 5001) ←→ SQLite DB (coordinator.db)
        |
   REST API (/api/get_work, /api/submit_result, /api/status, /api/workers)
        |
   ┌────┴────────────────────────────┐
   |                                  |
Workers (MacBook Pro x3)    Workers (Linux x5)
   |                                  |
Strategy Miner (Genetic Algorithm)
   |
Backtester (PnL, Sharpe, Win Rate, Max Drawdown)
   |
Telegram Bot (monitoring & notifications)
```

### Key Files
| File | Purpose |
|------|---------|
| `coordinator_port5001.py` | Flask server distributing work units via REST API. Uses SQLite with `work_units`, `results`, `workers` tables |
| `crypto_worker.py` | Worker client: polls coordinator, runs backtests, submits results. Supports multi-instance via WORKER_INSTANCE env var |
| `strategy_miner.py` | Genetic algorithm: evolves population of trading genomes (indicators: RSI, SMA, EMA, VOLSMA). Uses Numba JIT when available |
| `numba_backtester.py` | Numba JIT accelerated backtester (Phase 1 GPU acceleration). 1000-4000x speedup over Python backtester |
| `optimizer.py` | Ray-based parallel backtest execution (optional, unstable on macOS) |
| `backtester.py` | Simulation engine: spot trading, PnL calculation, fee modeling (Python fallback) |
| `dynamic_strategy.py` | Genome interpreter: converts genome dict to trading signals |
| `interface.py` | Streamlit dashboard for monitoring and control |
| `telegram_bot.py` | Telegram bot for remote monitoring via commands |
| `multi_worker.sh` | Launches N worker instances with auto-restart |
| `config.py` | API keys, trading params, broker settings |
| `data_manager.py` | Smart incremental OHLCV data downloading |

### Database Schema (coordinator.db)
```sql
work_units: id, strategy_params (JSON), status, replicas_needed, replicas_completed, replicas_assigned, created_at
results: id, work_unit_id, worker_id, pnl, trades, win_rate, sharpe_ratio, strategy_genome (JSON)
workers: id, hostname, platform, last_seen, work_units_completed, total_execution_time, status
```

---

## Coinbase API Authentication (Verified 2026-02-21)

### Key File
- **Path:** `/Users/enderj/Downloads/cdp_api_key.json`
- **Format:** `{"id": "<uuid>", "privateKey": "<base64-64bytes>"}`
- **Key ID:** `f2b19384-cbfd-4e6b-ab21-38a29f53650b`
- **NOTE:** The old `cdp_api_key.json` in the project root is an **expired ECDSA key** — always use the Downloads one.

### JWT Generation (Ed25519)
```python
import json, time, base64, requests
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

def load_coinbase_key(path="/Users/enderj/Downloads/cdp_api_key.json"):
    with open(path) as f:
        data = json.load(f)
    raw = base64.b64decode(data["privateKey"])
    return data["id"], Ed25519PrivateKey.from_private_bytes(raw[:32])  # first 32 bytes = seed

def make_jwt(key_id, private_key, method, path):
    now = int(time.time())
    def b64url(d):
        if isinstance(d, str): d = d.encode()
        return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
    header = b64url(json.dumps({"alg":"EdDSA","kid":key_id,"typ":"JWT"}, separators=(",",":")))
    payload = b64url(json.dumps({
        "iss":"cdp","nbf":now,"exp":now+120,"sub":key_id,
        "uri":f"{method} api.coinbase.com{path}"  # NO https://
    }, separators=(",",":")))
    msg = f"{header}.{payload}"
    return f"{msg}.{b64url(private_key.sign(msg.encode()))}"
```

### Key Endpoints
| Endpoint | Auth | Description |
|----------|------|-------------|
| `/api/v3/brokerage/market/products?product_type=FUTURE` | No | Public futures prices |
| `/api/v3/brokerage/products?product_type=FUTURE` | Yes | Authenticated futures |
| `/api/v3/brokerage/accounts` | Yes | All wallets + balances |
| `/api/v3/brokerage/cfm/balance_summary` | Yes | Futures CFM balance |
| `/api/v3/brokerage/cfm/positions` | Yes | Open futures positions |

### Account Balances (2026-02-21)
- BTC: 0.012496 BTC | SOL: 0.102893 SOL | USDC: $15.02
- CFM futures balance: null (no funds in futures)

---

## Network Configuration

### Machines
| Machine | IP (Local) | IP (Tailscale) | CPUs | Role |
|---------|-----------|----------------|------|------|
| MacBook Pro | 10.0.0.232 | 100.77.179.14 | 12 | Coordinator + 3 Workers |
| Linux ROG (Kubuntu) | 10.0.0.240 | - | 16 | 5 Workers |
| MacBook Air | variable | - | 8 | Optional workers |

### Ports
- **5001**: Coordinator REST API (port 5000 blocked by AirPlay on macOS)
- **8501**: Streamlit Dashboard
- **8265**: Ray Dashboard (when Ray is active)

### SSH Access
```bash
ssh enderj@10.0.0.240  # Linux ROG from MacBook Pro (key-based auth)
```

### Coordinator URLs (from each machine's perspective)
- From MacBook Pro: `http://localhost:5001`
- From Linux: `http://10.0.0.232:5001`
- From remote (Tailscale): `http://100.77.179.14:5001`

---

## Critical Lessons Learned

### 1. Ray GCS Crashes on macOS
**Problem**: Ray's GCS (Global Control Store) crashes after ~60 seconds on macOS, killing all workers.
**Solution**: Disable Ray completely with `USE_RAY=false`. Use `force_local=True` in StrategyMiner.
**Implementation**: Made Ray import optional in both `crypto_worker.py` and `strategy_miner.py`:
```python
try:
    import ray
    HAS_RAY = True
except ImportError:
    HAS_RAY = False
```

### 2. Work Distribution Race Condition
**Problem**: Multiple workers requesting work simultaneously got the same work unit.
**Solution**: Added `replicas_assigned` column to `work_units` table. Increment immediately in `get_pending_work()` within the same db_lock:
```python
def get_pending_work():
    with db_lock:
        # Query for work where replicas_assigned < replicas_needed
        # Increment replicas_assigned IMMEDIATELY in same transaction
        c.execute("UPDATE work_units SET replicas_assigned = replicas_assigned + 1 ...")
```

### 3. Replica Count Optimization
**Problem**: 6 replicas per work unit = very slow (only 1 WU processed at a time).
**Solution**: Reduce to 2 replicas. More parallel, still validated.

### 4. Multi-Worker Per Machine
**Problem**: Each machine ran only 1 worker, wasting CPUs.
**Solution**: Launch N workers per machine using WORKER_INSTANCE env var.
- MacBook Pro (12 CPUs): 3 workers
- Linux (16 CPUs): 5 workers
- Each worker gets unique ID: `{hostname}_{os}_W{instance}`

### 5. Port 5000 Blocked on macOS
**Problem**: macOS AirPlay Receiver uses port 5000.
**Solution**: Use `coordinator_port5001.py` on port 5001 instead.

### 6. Virtual Environment Issues with Google Drive
**Problem**: `.venv` in Google Drive creates broken symlinks.
**Solution**: Create venv outside Google Drive: `~/coinbase_trader_venv`

### 7. Process Management
**Problem**: `killall python3` doesn't work on macOS (binary is named `Python`).
**Solution**: Use `kill <PID>` or `pkill -f "pattern"` instead.

### 8. Orphaned Work Assignments
**Problem**: Workers die but their assigned replicas stay "in_progress" forever.
**Solution**: Reset orphaned assignments:
```sql
UPDATE work_units SET replicas_assigned = replicas_completed, status = 'pending' WHERE status != 'completed';
```

### 9. Stale Worker Detection
**Problem**: `/api/status` counted ALL workers ever registered as "active", showing inflated numbers (e.g., 12 workers when only 8 alive).
**Solution**: Count only workers seen in last 5 minutes using Julian Day arithmetic:
```python
c.execute("""SELECT COUNT(*) as active FROM workers
    WHERE status='active'
    AND (julianday('now') - last_seen) < (5.0 / 1440.0)""")
```
**Note**: SQLite stores `last_seen` as Julian Day via `julianday('now')`. 5 minutes = 5/1440 of a day.

### 10. Best Strategy Fallback
**Problem**: Dashboard showed "N/A" for best strategy because query filtered by `is_canonical = 1` but no results were canonical yet.
**Solution**: Two-pass query - first try canonical results, then fall back to best overall result:
```python
# Primary: canonical results
c.execute("SELECT ... FROM results WHERE is_canonical = 1 ORDER BY pnl DESC LIMIT 1")
best = c.fetchone()
# Fallback: best overall
if not best:
    c.execute("SELECT r.*, w.strategy_params FROM results r JOIN work_units w ON r.work_unit_id = w.id WHERE r.pnl > 0 ORDER BY r.pnl DESC LIMIT 1")
    best = c.fetchone()
```

### 11. Dashboard Log File Paths
**Problem**: Dashboard Logs tab read from project directory (`coordinator.log`, `worker_pro.log`) instead of actual log locations in `/tmp/`.
**Solution**: Updated all paths:
- Coordinator: `/tmp/coordinator.log` (not `coordinator.log`)
- MacBook Pro Workers: `/tmp/worker_{1,2,3}.log` with instance selector (not `worker_pro.log`)
- Linux Workers: Read via SSH `ssh enderj@10.0.0.240 "tail /tmp/worker_{1..5}.log"` (replaced old "MacBook Air" tab)

### 12. Dashboard Control Tab Alignment
**Problem**: Control tab referenced obsolete scripts (`start_worker.sh`, `worker_pro.pid`) and machines (MacBook Air).
**Solution**: Updated to match multi-worker architecture:
- Start workers: `multi_worker.sh 3` (not `start_worker.sh`)
- Stop workers: `pkill -f crypto_worker` (not `kill $(cat worker_pro.pid)`)
- Added Linux ROG controls via SSH to 10.0.0.240
- Removed MacBook Air references

### 13. API Workers Format
**Problem**: `/api/workers` returned `last_seen` as raw Julian Day number (unintelligible) and `total_execution_time` as raw seconds.
**Solution**: Convert Julian Day to readable datetime and add computed fields:
```python
last_seen_unix = (last_seen_jd - 2440587.5) * 86400.0
last_seen_str = datetime.fromtimestamp(last_seen_unix).strftime('%Y-%m-%d %H:%M:%S')
minutes_ago = (time.time() - last_seen_unix) / 60.0
is_alive = minutes_ago < 5.0
```
API now returns: `last_seen` (formatted), `last_seen_minutes_ago`, `status` (computed from liveness).

---

## Standard Operating Procedures

### Starting the Full System (from MacBook Pro)

#### Step 1: Start Coordinator
```bash
cd "<project_dir>"
source ~/coinbase_trader_venv/bin/activate
PYTHONUNBUFFERED=1 nohup python -u coordinator_port5001.py > /tmp/coordinator.log 2>&1 &
# Verify: curl http://localhost:5001/api/status
```

#### Step 2: Start MacBook Pro Workers (3 instances)
```bash
for i in 1 2 3; do
    COORDINATOR_URL="http://localhost:5001" NUM_WORKERS="3" WORKER_INSTANCE="$i" USE_RAY="false" \
    PYTHONUNBUFFERED=1 nohup python -u crypto_worker.py > /tmp/worker_$i.log 2>&1 &
    sleep 3
done
```

#### Step 3: Start Linux Workers (5 instances)
```bash
ssh enderj@10.0.0.240 'cd ~/crypto_worker && for i in 1 2 3 4 5; do
    COORDINATOR_URL="http://10.0.0.232:5001" NUM_WORKERS="5" WORKER_INSTANCE="$i" USE_RAY="false" \
    PYTHONUNBUFFERED=1 nohup python3 -u crypto_worker.py > /tmp/worker_$i.log 2>&1 &
    sleep 3
done'
```

#### Step 4: Start Telegram Bot
```bash
PYTHONUNBUFFERED=1 nohup python -u telegram_bot.py > /tmp/telegram_bot.log 2>&1 &
```

#### Step 5: Start Streamlit Dashboard
```bash
nohup python -m streamlit run interface.py > /tmp/streamlit.log 2>&1 &
# Access: http://localhost:8501
```

### Creating Work Units
Work units are created through the Streamlit interface or directly via API:
```bash
curl -X POST http://localhost:5001/api/create_work_unit \
  -H "Content-Type: application/json" \
  -d '{"strategy_params": {"population_size": 20, "generations": 100, "risk_level": "MEDIUM", "data_file": "BTC-USD_ONE_MINUTE.csv", "max_candles": 100000}, "replicas": 2}'
```

### Monitoring Progress
- **Telegram**: /status, /workers, /progress, /linux, /macpro
- **Web Dashboard**: http://localhost:8501
- **Coordinator API**: http://localhost:5001/api/status
- **Worker Logs**: /tmp/worker_{1,2,3}.log (Mac), ssh to Linux for /tmp/worker_{1..5}.log

### Stopping Everything
```bash
# MacBook Pro
kill $(pgrep -f crypto_worker) $(pgrep -f coordinator_port5001) $(pgrep -f telegram_bot) 2>/dev/null

# Linux
ssh enderj@10.0.0.240 "killall python3; exit 0"
```

### Resetting Stuck Work Units
```bash
sqlite3 coordinator.db "UPDATE work_units SET replicas_assigned = replicas_completed, status = CASE WHEN replicas_completed >= replicas_needed THEN 'completed' ELSE 'pending' END WHERE status = 'in_progress';"
```

---

## Telegram Bot Configuration
- **Bot Name**: Eko_MacPro_bot
- **Bot Token**: TELEGRAM_BOT_TOKEN_REDACTED
- **Chat ID**: 771213858
- **Commands**: /status, /workers, /progress, /linux, /macpro, /help
- **Auto-reports**: Every 30 minutes
- **Notifications**: On work unit completion

---

## Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| COORDINATOR_URL | Coordinator REST API URL | http://100.118.215.73:5000 |
| WORKER_INSTANCE | Instance number (1, 2, 3...) | 1 |
| NUM_WORKERS | Total workers on this machine | 1 |
| USE_RAY | Enable Ray parallel processing | false |
| RAY_ADDRESS | Ray cluster address (if using Ray) | auto |

---

## Data Files
```
data/BTC-USD_ONE_MINUTE.csv    # 100K+ candles, primary backtest data (74MB)
data/BTC-USD_FIVE_MINUTE.csv   # 59K candles, faster backtests (4MB)
data/BTC-USD_FIFTEEN_MINUTE.csv # 15-min granularity (2.6MB)
```

---

## Genetic Algorithm Parameters
- **Population Size**: 20 (per generation)
- **Generations**: 50-100 (per work unit)
- **Risk Levels**: LOW, MEDIUM, HIGH
- **Genome Structure**: Entry rules (indicator comparisons), exit rules, risk params
- **Indicators**: RSI, SMA, EMA, VOLSMA (Volume SMA)
- **Operators**: >, <, crosses_above, crosses_below
- **Periods**: 10, 14, 20, 50, 100, 200
- **Fitness Function**: PnL (profit and loss) from backtester

---

## Worker Installer Package
Located at: `~/Desktop/Worker_Installer_Package/` and `~/Desktop/Worker_Installer.zip`
Contains:
- `install_mac.sh` - macOS setup (homebrew, venv, dependencies)
- `install_linux.sh` - Linux setup (apt, venv, dependencies)
- `install_windows.bat` - Windows setup (Python, venv, dependencies)
- `crypto_worker.py`, `strategy_miner.py`, `optimizer.py`, etc.
- Pre-configured with coordinator URL

---

## Troubleshooting Guide

### Workers not getting work
1. Check coordinator: `curl http://localhost:5001/api/status`
2. Check DB: `sqlite3 coordinator.db "SELECT id, status, replicas_assigned, replicas_needed FROM work_units;"`
3. If all assigned but workers idle: reset orphaned assignments (see above)

### Workers crashing on macOS
1. Check for Ray GCS errors in logs: `grep "GCS" /tmp/worker_*.log`
2. Ensure `USE_RAY=false` is set
3. Use auto-restart script (multi_worker.sh)

### Linux workers can't connect
1. Verify coordinator is running: `curl http://10.0.0.232:5001/api/status` from Linux
2. Check firewall: `sudo ufw status` on Linux
3. Try Tailscale IP if local network fails

### Coordinator database locked
1. Stop all processes
2. Check for zombie connections: `fuser coordinator.db`
3. Restart coordinator

### SSH connection issues to Linux
1. `ssh -o ConnectTimeout=10 enderj@10.0.0.240 "hostname"`
2. Check if machine is on: ping 10.0.0.240
3. Verify SSH key: `ssh-add -l`

---

## Key API Endpoints (Coordinator)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | System overview (work units, workers) |
| `/api/workers` | GET | List of all registered workers |
| `/api/get_work?worker_id=X` | GET | Request work assignment |
| `/api/submit_result` | POST | Submit backtest result |
| `/api/results` | GET | All completed results |
| `/api/create_work_unit` | POST | Create new work unit |

---

## Streamlit Dashboard - Sistema Distribuido (5 Tabs)

### Tab 1: Dashboard
- System overview: total work units, completed, in progress, pending
- Active workers count (only workers seen in last 5 minutes)
- Best strategy found (PnL, Sharpe, Win Rate) with fallback query
- Progress bar for overall completion

### Tab 2: Workers
- Workers grouped by machine (MacBook Pro, Linux ROG)
- Each worker shows: ID, status (alive/dead based on 5-min threshold), last seen (formatted datetime), work units completed, execution time (formatted hours:minutes)
- Visual separation between active and inactive workers
- Color coding: green for alive, red for dead/stale

### Tab 3: Control
- **MacBook Pro**: Start 3 workers via `multi_worker.sh 3`, stop via `pkill -f crypto_worker`
- **Linux ROG**: Start 5 workers via SSH, stop via SSH `killall python3`
- **Coordinator**: Start/stop coordinator process
- **Telegram Bot**: Start/stop bot process
- All commands use `nohup` + background execution

### Tab 4: Logs
- **Coordinator**: Reads from `/tmp/coordinator.log` (last 100 lines)
- **MacBook Pro Workers**: Radio selector for Worker 1/2/3, reads `/tmp/worker_{N}.log`
- **Linux ROG Workers**: Reads via `ssh enderj@10.0.0.240 "tail /tmp/worker_{N}.log"`
- Auto-refresh toggle

### Tab 5: Crear Work Units
- Form to create new work units with parameters: population_size, generations, risk_level, data_file, max_candles
- Replicas selector (default: 2)
- Auto-calculator: estimates total cores = `int(num_workers * 3.5)`
- Inserts with `replicas_assigned = 0` to prevent race conditions
- Batch creation support

---

## Performance Benchmarks

### With Numba JIT (Phase 1 GPU Acceleration - 2026-02-05)
- Single backtest (59K candles): **0.001s** (was 4.5s = **4,300x speedup**)
- 20 gen x 20 pop (400 backtests): **0.4s** (was ~30 min = **4,343x speedup**)
- 100 gen x 20 pop (2000 backtests): **~2s** (was ~2-4 hours)
- Indicator pre-computation (all 24 indicators): 0.02s per generation
- JIT warmup (first run only): ~1s (cached after)

### Without Numba (Python fallback)
- Single worker, 100 generations, 20 population, 100K candles: ~2-4 hours
- 8 workers (3 Mac + 5 Linux), 2 replicas: ~8 WU/day
- Linux worker (single): ~25% faster than MacBook Pro per generation

### Results
- Max observed PnL: $230.50 (Numba test, 20 gen x 20 pop, 2026-02-05)
- Previous best PnL: $164.77 (Python backtester, 2026-02-04)

---

## Numba JIT Acceleration (numba_backtester.py)

### How It Works
1. **Pre-computes ALL 24 indicators** (RSI, SMA, EMA, VOLSMA x 6 periods) as a numpy matrix ONCE per generation
2. **Encodes genomes** as fixed-size float64 arrays (18 values: sl_pct, tp_pct, rules)
3. **Numba @njit** compiles the backtest loop to native machine code (cached after first run)
4. Falls back to original Python backtester if Numba unavailable

### Integration
- `strategy_miner.py` imports `numba_backtester` and calls `warmup_jit()` at module load
- `_evaluate_local()` tries Numba first, falls back to Python on error
- No changes needed to `crypto_worker.py`, `coordinator_port5001.py`, or `interface.py`
- Linux workers need: `pip install numba` + `numba_backtester.py` in working directory

### Phase 2: CUDA GPU (Future)
- Numba CUDA kernel: run 20+ genomes in parallel on NVIDIA GPU (Linux ROG)
- PyTorch MPS: batch tensor evaluation on Apple Silicon Metal GPU (MacBook Pro)
- Expected additional speedup: 10-20x on top of Phase 1

---

## Future Improvements to Consider
1. ~~Enable Ray on Linux only (more stable than macOS)~~ - Ray disabled everywhere, local mode is fast enough
2. Implement work unit timeout/reassignment for dead workers
3. ~~Add GPU acceleration for indicator calculations~~ - Phase 1 (Numba JIT) implemented 2026-02-05, 4000x speedup
4. Implement early stopping (if no improvement for N generations)
5. Add more sophisticated crossover/mutation operators
6. Implement elitism (carry top N genomes to next generation unchanged)
7. Add real-time strategy deployment from best results
8. Add worker health monitoring with auto-restart from coordinator side
9. Implement persistent worker sessions (resume from crash point)
10. Phase 2 GPU: CUDA kernels for Linux ROG, PyTorch MPS for MacBook Pro
11. Increase population size (100-500) now that evaluation is near-instant
