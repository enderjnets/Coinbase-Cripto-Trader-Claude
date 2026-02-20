import ray
import datetime

def check_nodes():
    try:
        # Connect to existing cluster
        ray.init(address='auto', ignore_reinit_error=True)
        
        nodes = ray.nodes()
        resources = ray.cluster_resources()
        
        print(f"\nTime: {datetime.datetime.now()}")
        print(f"Total Cluster CPUs: {resources.get('CPU', 0)}")
        print("-" * 50)
        
        active_count = 0
        for node in nodes:
            status = "✅ ALIVE" if node['Alive'] else "❌ DEAD"
            if node['Alive']: active_count += 1
            
            print(f"Node ID: {node['NodeID']}")
            print(f"  IP: {node.get('NodeManagerAddress', 'Unknown')}")
            print(f"  Hostname: {node.get('NodeName', 'Unknown')}")
            print(f"  Status: {status}")
            print(f"  Resources: {node.get('Resources', {})}")
            print("-" * 50)
            
        print(f"Active Nodes Count: {active_count}")
        
    except Exception as e:
        print(f"Could not connect to Ray: {e}")

if __name__ == "__main__":
    check_nodes()
