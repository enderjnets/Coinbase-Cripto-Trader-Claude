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
        pass

def main():
    print("\n" + "="*60)
    print("🚀 STARTING RAY CLUSTER HEAD NODE")
    print("="*60)

    # force kill 8501
    try:
        print("🧹 Cleaning up port 8501...")
        cmd = "lsof -ti:8501 | xargs kill -9"
        subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL)
    except:
        pass

    # [FIX] DETECT SPACES AND SWITCH TO SAFE SYMLINK
    current_exe = sys.executable
    if " " in current_exe:
        print("⚠️  Spaces detected in Python path. Switching to Safe Mode...")
        safe_base = os.path.expanduser("~/.ray_safe_project_link")
        project_root = os.getcwd()
        if not os.path.exists(safe_base):
            try:
                if os.path.exists(project_root):
                    os.symlink(project_root, safe_base)
                    print(f"🔗 Created symlink: {safe_base} -> {project_root}")
            except Exception as e:
                print(f"❌ Failed to create symlink: {e}")

        if project_root in current_exe:
            safe_exe = current_exe.replace(project_root, safe_base)
            if os.path.exists(safe_exe):
                print(f"🔄 Switched interpreter to: {safe_exe}")
                sys.executable = safe_exe 
                try:
                    os.chdir(safe_base)
                    print(f"📂 Changed CWD to: {safe_base}")
                except:
                    pass
            else:
                print(f"⚠️ Could not verify safe python path: {safe_exe}")

    # [FIX] Use python -m ray.scripts.scripts
    ray_cmd = [sys.executable, "-m", "ray.scripts.scripts"]
    print(f"DEBUG: Using Ray via module: {ray_cmd}")

    os.environ["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "1"
    
    print("\n[1/3] Stopping existing Ray instances...")
    run_command(ray_cmd + ["stop", "--force"])
    time.sleep(2)

    ip = get_ip()
    print(f"\n[2/3] Detected LAN IP: {ip}")

    print("🚀 Starting Ray Head Node...")
    os.environ["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "1"

    total_cores = os.cpu_count() or 4
    safe_cores = max(1, total_cores - 2)
    print(f"DEBUG: Head Node configured with {safe_cores} CPUs")

    cmd = ray_cmd + [
        "start", "--head",
        f"--port=6379",
        f"--node-ip-address=0.0.0.0",
        "--dashboard-host=0.0.0.0",
        "--disable-usage-stats",
        f"--num-cpus={safe_cores}"
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
        
        print("\n✅ Ready to accept connections.")
        
        # Launch Streamlit
        print("\n🎨 Launching Streamlit Interface...")
        
        script_path = os.path.join(os.getcwd(), "interface.py")
        
        streamlit_cmd = [
            sys.executable, "-m", "streamlit", "run", script_path,
            "--server.port=8501",
            "--server.address=0.0.0.0",
            "--server.headless=false"
        ]
        
        print(f"   Debug: CWD is {os.getcwd()}")
        print(f"   Exec: {' '.join(streamlit_cmd)}")
        
        try:
            print("   👉 Open http://localhost:8501 in your browser (Opening automatically...)")
            print("   (Head Node Active - Do not close this window)")
            
            # Launch and Wait
            subprocess.run(streamlit_cmd)
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping...")
        
    except Exception as e:
        print(f"\n❌ Error starting cluster: {e}")

if __name__ == "__main__":
    main()
