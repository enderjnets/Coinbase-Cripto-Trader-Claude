import ray
import time
import socket
import collections

# Connect to existing cluster
try:
    ray.init(address='auto')
except:
    print("Could not connect to Ray cluster via 'auto'.")
    exit(1)

@ray.remote
def get_hostname():
    time.sleep(0.1)
    return socket.gethostname()

print(f"Cluster Resources: {ray.cluster_resources()}")

# Submit many tasks
futures = [get_hostname.remote() for _ in range(200)]

# Collect results
results = ray.get(futures)
counts = collections.Counter(results)

print("\nTask Distribution:")
for host, count in counts.items():
    print(f"{host}: {count}")

ray.shutdown()
