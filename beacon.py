import socket
import time
import sys

def broadcast_ip():
    # Helper to get actual LAN IP
    def get_local_ip():
        # 1. Try Tailscale first
        try:
            import subprocess
            ts_ip = subprocess.check_output(["tailscale", "ip", "-4"]).decode().strip()
            if ts_ip: return ts_ip
        except:
            pass
            
        # 2. Fallback to default LAN
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    my_ip = get_local_ip()
    BROADCAST_IP = '<broadcast>'
    PORT = 50000
    MESSAGE = f"RAY_HEAD:{my_ip}"

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    print(f"📡 Broadcasting Head Node IP ({my_ip}) on port {PORT}...")
    
    try:
        while True:
            sock.sendto(MESSAGE.encode(), (BROADCAST_IP, PORT))
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()

if __name__ == "__main__":
    broadcast_ip()
