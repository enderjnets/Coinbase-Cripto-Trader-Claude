import ray
import time
import socket
import collections
import os

# Mimic Optimizer Runtime Env
current_dir = os.path.dirname(os.path.abspath(__file__))
if " " in current_dir:
    # Use the symlink workaround from optimizer.py
    safe_path = os.path.expanduser("~/.ray_safe_project_link")
    if os.path.exists(safe_path) or os.path.islink(safe_path):
        try: os.remove(safe_path)
        except: pass
    try:
        os.symlink(current_dir, safe_path)
        current_dir = safe_path
    except: pass

runtime_env = {
    "working_dir": current_dir,
    "excludes": ["data", "vps_package", ".venv", "worker_env", ".git", "__pycache__", "*.csv", "*.zip", "*.log"]
}

print(f"Testing with runtime_env working_dir: {current_dir}")

# Connect to existing cluster
try:
    # Note: re-init might be ignored if already connected, but usually test script is fresh process.
    # But if we want to FORCE the runtime_env, we need to pass it here.
    # IF the cluster is already running, 'ray.init(address="auto")' usually attaches as driver.
    # The runtime_env args in ray.init apply to this job.
    ray.init(address='auto', runtime_env=runtime_env)
except Exception as e:
    print(f"Could not connect to Ray cluster: {e}")
    exit(1)

@ray.remote
def get_hostname():
    time.sleep(0.1)
    return socket.gethostname()

print(f"Cluster Resources: {ray.cluster_resources()}")

# Submit tasks
futures = [get_hostname.remote() for _ in range(200)]

# Collect results
try:
    results = ray.get(futures)
    counts = collections.Counter(results)

    print("\nTask Distribution (with runtime_env):")
    for host, count in counts.items():
        print(f"{host}: {count}")
except Exception as e:
    print(f"\n❌ Error executing tasks: {e}")

ray.shutdown()
