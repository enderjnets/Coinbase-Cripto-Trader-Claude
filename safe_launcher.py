import os
import sys
import subprocess
import shutil
import time

def main():
    # 1. Detect if current path has spaces
    current_dir = os.getcwd()
    
    if " " not in current_dir:
        # No spaces, just run the command directly
        print(f"✅ Path is safe (no spaces): {current_dir}")
        run_command(sys.argv[1:])
        return

    print(f"⚠️  Path contains spaces: '{current_dir}'")
    print("🚀 Switching to Safe Mode (Symlink Strategy)...")

    # 2. Create Symlink
    # We use a hidden directory in user home to be safe and consistent
    home_dir = os.path.expanduser("~")
    safe_link_name = ".ray_safe_project_link"
    safe_path = os.path.join(home_dir, safe_link_name)

    # Remove existing link/dir if present
    if os.path.exists(safe_path) or os.path.islink(safe_path):
        try:
            if os.path.isdir(safe_path) and not os.path.islink(safe_path):
                shutil.rmtree(safe_path)
            else:
                os.remove(safe_path)
        except Exception as e:
            print(f"❌ Failed to clean up old link: {e}")
            sys.exit(1)

    # Create new symlink
    try:
        os.symlink(current_dir, safe_path)
        print(f"🔗 Symlink created: {safe_path} -> {current_dir}")
    except Exception as e:
        print(f"❌ Failed to create symlink: {e}")
        print("💡 Try running with sudo if permissions are an issue.")
        sys.exit(1)

    # 3. Construct new command
    # We need to run the SAME command but from the safe_path
    # And we must ensure we use the same python interpreter if possible, 
    # but invoked via the new path?
    # Actually, if we just chdir to safe_path and run, that might be enough 
    # IF we ignore that the virtualenv is still in the old path?
    # Ray usually resolves absolute paths. 
    # If we run FROM the safe path, 'os.getcwd()' will return the safe path (usually, if shell follows link).
    
    # We will execute the command using the absolute path of the python executable 
    # to ensure we use the correct environment, but we set CWD to safe_path.
    
    python_exe = sys.executable
    
    # Arguments passed to this script
    args = sys.argv[1:]
    
    if not args:
        print("❌ No command provided. Usage: python safe_launcher.py [script] [args]")
        print("Example: python safe_launcher.py -m streamlit run interface.py")
        sys.exit(1)

    print(f"📂 Changing execution directory to: {safe_path}")
    
    # We invoke subprocess with cwd=safe_path
    # We accept that the python executable path might still have spaces (users/.../Google Drive/.venv/bin/python)
    # BUT Ray cares mostly about 'runtime_env={"working_dir": ...}' which defaults to CWD.
    # If CWD is safe, Ray should be happy sending that to workers.
    
    env = os.environ.copy()
    env["PYTHONPATH"] = safe_path + os.pathsep + env.get("PYTHONPATH", "")
    
    try:
        # On macOS, sometimes realpath is resolved automatically. 
        # We assume the user shell/OS handles the CWD as the symlink path.
        subprocess.check_call([python_exe] + args, cwd=safe_path, env=env)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup? Maybe keep it for inspection or next run.
        # Removing it might break running processes if they rely on it?
        # Better to leave it.
        pass

def run_command(args):
    try:
        subprocess.check_call([sys.executable] + args)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
