import ray
import time
import socket
import os

# Mimic Optimizer Runtime Env (Logic from test_distribution_env.py)
current_dir = os.path.dirname(os.path.abspath(__file__))
if " " in current_dir:
    safe_path = os.path.expanduser("~/.ray_safe_project_link")
    if os.path.exists(safe_path) or os.path.islink(safe_path):
         current_dir = safe_path

runtime_env = {
    "working_dir": current_dir,
    "excludes": ["data", "vps_package", ".venv", "worker_env", ".git", "__pycache__", "*.csv", "*.zip", "*.log"]
}

try:
    ray.init(address='auto', runtime_env=runtime_env)
except:
    print("Could not connect to Ray.")
    exit(1)

# Get Head Node IP
resources = ray.cluster_resources()
head_ip = "10.0.0.239" # From previous logs

print(f"Cluster Resources: {resources}")

@ray.remote(resources={f"node:{head_ip}": 0.01})
def run_on_head():
    return socket.gethostname()

try:
    print(f"Attempting to run on Head Node ({head_ip})...")
    # Run 10 tasks
    futures = [run_on_head.remote() for _ in range(10)]
    results = ray.get(futures)
    print(f"✅ Success! Executed on: {list(set(results))}")
except Exception as e:
    print(f"❌ Failed to run on Head Node: {e}")

ray.shutdown()
