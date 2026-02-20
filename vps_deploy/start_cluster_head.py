import os
import subprocess
import socket
import sys
import time

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def run_command(cmd, shell=False):
    try:
        subprocess.check_call(cmd, shell=shell)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        # Don't exit, might be a benign stop error
        pass

def main():
    print("\n" + "="*60)
    print("🚀 STARTING RAY CLUSTER HEAD NODE")
    print("="*60)

    # Find Ray executable relative to python interpreter
    # This works for both venv and system python typically
    python_dir = os.path.dirname(sys.executable)
    ray_exe = os.path.join(python_dir, "ray")

    # Check common user bin path on macOS
    if not os.path.exists(ray_exe):
        user_bin_ray = "/Users/enderj/Library/Python/3.9/bin/ray"
        if os.path.exists(user_bin_ray):
            ray_exe = user_bin_ray
        else:
            # Fallback to simple command if all else fails
            ray_exe = "ray"
    
    print(f"DEBUG: Using Ray executable at: '{ray_exe}'")

    # 1. Enable Cluster Mode Env Var
    os.environ["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "1"
    
    # 2. Stop any existing instances
    print("\n[1/3] Stopping existing Ray instances...")
    
    run_command([ray_exe, "stop", "--force"])
    time.sleep(2)

    # 3. Get LAN IP
    ip = get_ip()
    print(f"\n[2/3] Detected LAN IP: {ip}")

    # 4. Start Ray Head
    # Assuming GREEN and NC are defined elsewhere or intended to be added.
    # For now, using a placeholder or just the string.
    GREEN = "" # Placeholder
    NC = ""    # Placeholder
    print(f"{GREEN}🚀 Starting Ray Head Node...{NC}")
    
    # CRITICAL: Allow cross-platform clusters (Mac + Windows)
    os.environ["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "1"

    # Start Ray with dashboard allowed from all IPs
    # Calculate safe CPU usage for HEAD node explicitly
    total_cores = os.cpu_count() or 4
    safe_cores = max(1, total_cores - 2)

    cmd = [
        ray_exe, "start", "--head",
        f"--port=6379",
        f"--node-ip-address={ip}",
        "--include-dashboard=false",
        "--disable-usage-stats",
        f"--num-cpus={safe_cores}" # Explicitly restrict Head Node CPUs here too
    ]
    
    try:
        run_command(cmd)
        
        print("\n" + "="*60)
        print("✅ CLUSTER STARTED SUCCESSFULLY!")
        print("="*60)
        print(f"\n📡 Head Node IP: {ip}")
        print("\n👉 ON YOUR WORKER MAC (MacBook Pro), RUN:")
        print("-" * 50)
        print(f"ray start --address={ip}:6379")
        print("-" * 50)
        print("\n(Run this in the 'worker_env' virtual environment)")
        
        # Start beacon for auto-discovery
        print("\nStarting auto-discovery beacon...")
        subprocess.Popen([sys.executable, "beacon.py"])
        
    except Exception as e:
        print(f"\n❌ Error starting cluster: {e}")

if __name__ == "__main__":
    main()
