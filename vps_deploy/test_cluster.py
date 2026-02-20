#!/usr/bin/env python3
"""
Simple script to test Ray cluster distribution across multiple Macs.
This verifies that tasks are being distributed correctly.
"""
import ray
import time
import os

# Enable macOS cluster mode
os.environ["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "1"

@ray.remote
def heavy_task(task_id):
    """Simulate a CPU-intensive task"""
    import socket
    import time
    
    start = time.time()
    # Simulate work
    total = 0
    for i in range(10_000_000):
        total += i ** 2
    
    duration = time.time() - start
    hostname = socket.gethostname()
    
    return {
        'task_id': task_id,
        'hostname': hostname,
        'duration': round(duration, 2),
        'result': total % 1000
    }

if __name__ == "__main__":
    # Connect to existing cluster
    ray.init(address='auto')
    
    print("=" * 60)
    print("RAY CLUSTER TEST")
    print("=" * 60)
    
    # Show cluster resources
    resources = ray.cluster_resources()
    print(f"\n📊 Cluster Resources:")
    print(f"   Total CPUs: {resources.get('CPU', 0)}")
    print(f"   Total Memory: {resources.get('memory', 0) / (1024**3):.2f} GB")
    
    # Get cluster nodes
    nodes = ray.nodes()
    print(f"\n🖥️  Active Nodes: {len(nodes)}")
    for node in nodes:
        print(f"   - {node['NodeManagerHostname']} ({node['NodeManagerAddress']})")
        print(f"     CPUs: {node['Resources'].get('CPU', 0)}")
    
    print("\n" + "=" * 60)
    print("RUNNING DISTRIBUTED TASKS...")
    print("=" * 60)
    
    # Launch tasks
    num_tasks = 50
    print(f"\n🚀 Launching {num_tasks} tasks...")
    
    start_time = time.time()
    futures = [heavy_task.remote(i) for i in range(num_tasks)]
    
    print("⏳ Waiting for results...")
    results = ray.get(futures)
    
    total_time = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    # Group by hostname
    by_host = {}
    for r in results:
        host = r['hostname']
        if host not in by_host:
            by_host[host] = []
        by_host[host].append(r)
    
    print(f"\n✅ Completed {num_tasks} tasks in {total_time:.2f} seconds\n")
    
    for hostname, tasks in by_host.items():
        print(f"📍 {hostname}:")
        print(f"   Tasks processed: {len(tasks)}")
        avg_duration = sum(t['duration'] for t in tasks) / len(tasks)
        print(f"   Average task duration: {avg_duration:.2f}s")
        print(f"   Task IDs: {', '.join(str(t['task_id']) for t in tasks[:10])}" + 
              (f" ... +{len(tasks)-10} more" if len(tasks) > 10 else ""))
        print()
    
    print("=" * 60)
    print("✅ CLUSTER TEST COMPLETE!")
    print("=" * 60)
    
    ray.shutdown()
