#!/usr/bin/env python3
"""
Verificación de Compatibilidad: Head Node vs Worker
Revisa que todas las configuraciones coincidan entre el Head y el Worker installer
"""

import sys
import subprocess
import re
from pathlib import Path

# Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def run_cmd(cmd):
    """Run command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except:
        return ""

def check_head_config():
    """Check Head Node configuration"""
    print(f"\n{BLUE}═══════════════════════════════════════════════════════════{NC}")
    print(f"{BLUE}📡 HEAD NODE CONFIGURATION{NC}")
    print(f"{BLUE}═══════════════════════════════════════════════════════════{NC}\n")

    head_config = {}

    # 1. Python version
    python_version = run_cmd(".venv/bin/python --version").replace("Python ", "")
    head_config['python_version'] = python_version
    print(f"   Python Version: {python_version}")

    # 2. Ray version
    ray_version = run_cmd(".venv/bin/pip show ray | grep Version").replace("Version: ", "")
    head_config['ray_version'] = ray_version
    print(f"   Ray Version: {ray_version}")

    # 3. GCS Address
    gcs_cmd = '.venv/bin/python3 -c "import ray; ray.init(address=\'auto\'); print(ray.get_runtime_context().gcs_address)" 2>/dev/null'
    gcs_address = run_cmd(gcs_cmd)
    head_config['gcs_address'] = gcs_address
    print(f"   GCS Address: {gcs_address}")

    # 4. Tailscale IP
    tailscale_ip = run_cmd("tailscale ip -4 2>/dev/null")
    head_config['tailscale_ip'] = tailscale_ip
    print(f"   Tailscale IP: {tailscale_ip}")

    # 5. Dashboard
    print(f"   Dashboard: http://{tailscale_ip}:8265")

    # 6. Number of nodes
    ray_status = run_cmd(".venv/bin/ray status 2>/dev/null | grep 'node_'")
    node_count = len([line for line in ray_status.split('\n') if 'node_' in line])
    head_config['node_count'] = node_count
    print(f"   Active Nodes: {node_count}")

    # 7. Total CPUs
    ray_cpus = run_cmd(".venv/bin/ray status 2>/dev/null | grep CPU")
    if "CPU" in ray_cpus:
        cpu_match = re.search(r'(\d+\.?\d*)/(\d+\.?\d*)\s+CPU', ray_cpus)
        if cpu_match:
            total_cpus = cpu_match.group(2)
            head_config['total_cpus'] = total_cpus
            print(f"   Total CPUs: {total_cpus}")

    return head_config

def check_worker_installer():
    """Check Worker Installer configuration"""
    print(f"\n{BLUE}═══════════════════════════════════════════════════════════{NC}")
    print(f"{BLUE}💼 WORKER INSTALLER CONFIGURATION{NC}")
    print(f"{BLUE}═══════════════════════════════════════════════════════════{NC}\n")

    worker_config = {}
    installer_path = Path("Worker_Installer_Package/install.sh")

    if not installer_path.exists():
        print(f"   {RED}❌ install.sh not found{NC}")
        return worker_config

    with open(installer_path, 'r') as f:
        content = f.read()

    # 1. Default Head IP
    match = re.search(r'DEFAULT_HEAD_IP="([^"]+)"', content)
    if match:
        worker_config['default_head_ip'] = match.group(1)
        print(f"   Default Head IP: {match.group(1)}")

    # 2. Ray version in pip install
    match = re.search(r'ray\[default\]==([0-9.]+)', content)
    if match:
        worker_config['ray_version'] = match.group(1)
        print(f"   Ray Version: {match.group(1)}")

    # 3. Python version (check what it installs)
    if 'python@3.9' in content:
        worker_config['python_version'] = '3.9.x (via Homebrew)'
        print(f"   Python Version: 3.9.x (Homebrew will install latest 3.9)")

    # 4. Version mismatch handling
    if 'RAY_IGNORE_VERSION_MISMATCH=1' in content:
        worker_config['ignore_version_mismatch'] = True
        print(f"   Version Mismatch Handling: {GREEN}ENABLED{NC}")

    # 5. Connection mode
    if 'Tailscale' in content:
        print(f"   Connection Mode: {GREEN}Supports Tailscale (Universal){NC}")

    return worker_config

def verify_compatibility(head_config, worker_config):
    """Verify compatibility between head and worker"""
    print(f"\n{BLUE}═══════════════════════════════════════════════════════════{NC}")
    print(f"{BLUE}🔍 COMPATIBILITY CHECK{NC}")
    print(f"{BLUE}═══════════════════════════════════════════════════════════{NC}\n")

    issues = []
    warnings = []

    # 1. Ray Version
    if head_config.get('ray_version') == worker_config.get('ray_version'):
        print(f"   {GREEN}✅ Ray Version: MATCH{NC} ({head_config.get('ray_version')})")
    else:
        issues.append(f"Ray version mismatch: Head={head_config.get('ray_version')}, Worker={worker_config.get('ray_version')}")
        print(f"   {RED}❌ Ray Version: MISMATCH{NC}")

    # 2. IP Configuration
    head_tailscale = head_config.get('tailscale_ip', '')
    worker_default_ip = worker_config.get('default_head_ip', '')

    if head_tailscale == worker_default_ip:
        print(f"   {GREEN}✅ Head IP: MATCH{NC} ({head_tailscale})")
    else:
        issues.append(f"Head IP mismatch: Head Tailscale={head_tailscale}, Worker Default={worker_default_ip}")
        print(f"   {RED}❌ Head IP: MISMATCH{NC}")
        print(f"      Head Tailscale IP: {head_tailscale}")
        print(f"      Worker Default IP: {worker_default_ip}")

    # 3. Python Version
    head_py = head_config.get('python_version', '')
    if head_py.startswith('3.9'):
        if worker_config.get('python_version', '').startswith('3.9'):
            print(f"   {GREEN}✅ Python Major Version: COMPATIBLE{NC} (3.9.x)")
            if not head_py == '3.9.6':
                warnings.append(f"Head uses Python {head_py}, worker will install latest 3.9.x via Homebrew")
                print(f"   {YELLOW}⚠️  Minor version may differ{NC}")
                print(f"      Head: {head_py}")
                print(f"      Worker: Will install latest 3.9.x")
                print(f"      {BLUE}INFO: RAY_IGNORE_VERSION_MISMATCH is enabled{NC}")
        else:
            issues.append(f"Python major version mismatch")
            print(f"   {RED}❌ Python Version: INCOMPATIBLE{NC}")

    # 4. Cluster Status
    node_count = head_config.get('node_count', 0)
    total_cpus = head_config.get('total_cpus', 0)

    print(f"\n   {BLUE}Current Cluster State:{NC}")
    print(f"      Active Nodes: {node_count}")
    print(f"      Total CPUs: {total_cpus}")

    if node_count >= 2 and float(total_cpus) >= 20:
        print(f"   {GREEN}✅ Worker appears connected{NC}")
    elif node_count == 1:
        warnings.append(f"Only 1 node active - worker not connected yet")
        print(f"   {YELLOW}⚠️  Only Head Node active - Worker needs to connect{NC}")

    return issues, warnings

def main():
    print(f"\n{GREEN}╔═══════════════════════════════════════════════════════════╗{NC}")
    print(f"{GREEN}║   HEAD NODE ↔ WORKER COMPATIBILITY VERIFICATION           ║{NC}")
    print(f"{GREEN}╚═══════════════════════════════════════════════════════════╝{NC}")

    head_config = check_head_config()
    worker_config = check_worker_installer()
    issues, warnings = verify_compatibility(head_config, worker_config)

    # Summary
    print(f"\n{BLUE}═══════════════════════════════════════════════════════════{NC}")
    print(f"{BLUE}📊 SUMMARY{NC}")
    print(f"{BLUE}═══════════════════════════════════════════════════════════{NC}\n")

    if not issues:
        print(f"   {GREEN}✅ ALL COMPATIBILITY CHECKS PASSED{NC}\n")
        print(f"   The Worker Installer is correctly configured to connect")
        print(f"   to this Head Node.\n")
    else:
        print(f"   {RED}❌ ISSUES FOUND:{NC}\n")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print()

    if warnings:
        print(f"   {YELLOW}⚠️  WARNINGS:{NC}\n")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
        print()

    # Recommendations
    print(f"\n{BLUE}═══════════════════════════════════════════════════════════{NC}")
    print(f"{BLUE}💡 RECOMMENDATIONS{NC}")
    print(f"{BLUE}═══════════════════════════════════════════════════════════{NC}\n")

    if issues:
        print(f"   {RED}Fix the issues above before installing the worker.{NC}\n")
        if any('IP' in issue for issue in issues):
            print(f"   To fix IP mismatch:")
            print(f"   1. Update Worker_Installer_Package/install.sh line 26")
            print(f"   2. Set DEFAULT_HEAD_IP=\"{head_config.get('tailscale_ip', '')}\"")
            print(f"   3. Recreate Worker_Installer_LISTO.zip\n")
    else:
        print(f"   {GREEN}✅ Ready to deploy!{NC}\n")
        print(f"   Next steps:")
        print(f"   1. Copy Worker_Installer_LISTO.zip to MacBook Pro")
        print(f"   2. Extract and run: bash install.sh")
        print(f"   3. Verify connection: .venv/bin/ray status\n")

    print(f"{BLUE}═══════════════════════════════════════════════════════════{NC}\n")

    return 0 if not issues else 1

if __name__ == '__main__':
    sys.exit(main())
