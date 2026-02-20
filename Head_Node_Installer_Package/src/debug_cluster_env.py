import ray
import os
import sys
import time

def debug_cluster_env():
    print("🚀 STARTING DEBUG: Cluster Connection with Runtime Env")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"📂 Working Directory: {current_dir}")
    
    runtime_env = {
        "working_dir": current_dir,
        "excludes": ["data", "vps_package", ".venv", "worker_env", ".git", "__pycache__", "*.csv"]
    }
    
    print("\n📦 Configuring runtime_env (Code Sync):")
    print(runtime_env)
    
    print("\n🔗 Attempting ray.init(address='auto') - This mimics optimizer.py")
    try:
        ray.init(
            address='auto', 
            ignore_reinit_error=True, 
            runtime_env=runtime_env
        )
        print("✅ CONNECTED TO CLUSTER!")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    print("\n🧪 Testing Remote Import on Worker...")
    
    @ray.remote
    def test_import():
        import os
        try:
            # Try to import a local module to verify code sync
            import strategy
            return f"✅ Success! Imported strategy module on host: {os.uname().nodename}"
        except ImportError as e:
            return f"❌ ImportError: {e} on host: {os.uname().nodename}"
        except Exception as e:
            return f"❌ Error: {e} on host: {os.uname().nodename}"

    # Launch tasks
    refs = [test_import.remote() for _ in range(4)]
    
    print("⏳ Waiting for tasks...")
    results = ray.get(refs)
    
    for r in results:
        print(r)
        
    print("\n🏁 DEBUG COMPLETE. Shutting down...")
    ray.shutdown()

if __name__ == "__main__":
    debug_cluster_env()
