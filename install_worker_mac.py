#!/usr/bin/env python3
"""
Crypto Worker Installer - macOS GUI Version
Native installer with graphical interface for macOS
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

class WorkerInstaller:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🧬 Crypto Worker Installer - macOS")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6)
        style.configure("TLabel", font=("Helvetica", 10))
        style.configure("Header.TLabel", font=("Helvetica", 14, "bold"))
        
        self.setup_ui()
        self.check_python()
        
    def setup_ui(self):
        # Header
        header = ttk.Label(self.root, text="🧬 Sistema de Trading Distribuido", style="Header.TLabel")
        header.pack(pady=20)
        
        # Status area
        self.status = scrolledtext.ScrolledText(self.root, height=15, width=70, font=("Consolas", 9))
        self.status.pack(pady=10, padx=20)
        self.status.config(state='disabled')
        
        # Progress
        self.progress = ttk.Progressbar(self.root, mode='determinate', maximum=100)
        self.progress.pack(pady=10, padx=20, fill='x')
        
        # Buttons frame
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=15)
        
        self.install_btn = ttk.Button(btn_frame, text="🚀 INSTALAR", command=self.start_install)
        self.install_btn.pack(side='left', padx=10)
        
        self.quit_btn = ttk.Button(btn_frame, text="❌ SALIR", command=self.root.quit)
        self.quit_btn.pack(side='left', padx=10)
        
        # Footer
        footer = ttk.Label(self.root, text="Instalador para macOS | GitHub: enderjnets/Coinbase-Cripto-Trader-Claude")
        footer.pack(pady=10)
        
    def log(self, msg):
        def _log():
            self.status.config(state='normal')
            self.status.insert('end', msg + "\n")
            self.status.see('end')
            self.status.config(state='disabled')
        self.root.after(0, _log)
        
    def check_python(self):
        try:
            result = subprocess.run(['python3', '--version'], capture_output=True)
            self.log(f"✅ Python encontrado: {result.stdout.decode().strip()}")
        except:
            self.log("❌ Python no encontrado")
            self.log("💡 Instala Python desde python.org/downloads")
            
    def run_command(self, cmd, cwd=None):
        """Run command and stream output"""
        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        for line in process.stdout:
            self.log(line.strip())
            
        process.wait()
        return process.returncode
        
    def start_install(self):
        self.install_btn.config(state='disabled')
        self.progress['value'] = 10
        self.root.update()
        
        threading.Thread(target=self.install_process, daemon=True).start()
        
    def install_process(self):
        try:
            # Step 1: Homebrew
            self.log("\n" + "="*50)
            self.log("📦 Paso 1/5: Verificando Homebrew...")
            self.root.after(0, lambda: self.progress.config(value=20))
            
            has_brew = subprocess.run(['which', 'brew'], capture_output=True).returncode == 0
            
            if not has_brew:
                self.log("📥 Instalando Homebrew...")
                self.log("💡 Esto puede tomar unos minutos...")
                code = self.run_command(
                    '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
                )
            else:
                self.log("✅ Homebrew ya instalado")
                
            self.root.after(0, lambda: self.progress.config(value=30))
            
            # Step 2: Git
            self.log("\n" + "="*50)
            self.log("📦 Paso 2/5: Verificando Git...")
            self.root.after(0, lambda: self.progress.config(value=40))
            
            has_git = subprocess.run(['which', 'git'], capture_output=True).returncode == 0
            
            if not has_git:
                self.log("📥 Instalando Git...")
                self.run_command("brew install git")
            else:
                self.log("✅ Git ya instalado")
                
            self.root.after(0, lambda: self.progress.config(value=50))
            
            # Step 3: Clone/Update Project
            self.log("\n" + "="*50)
            self.log("📥 Paso 3/5: Clonando proyecto...")
            self.root.after(0, lambda: self.progress.config(value=60))
            
            project_dir = Path.home() / "Coinbase-Cripto-Trader-Claude"
            
            if project_dir.exists():
                self.log("📥 Actualizando proyecto existente...")
                self.run_command("git pull origin main", cwd=str(project_dir))
            else:
                self.log("📥 Clonando proyecto...")
                self.run_command(f"git clone https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git {project_dir}")
                
            self.root.after(0, lambda: self.progress.config(value=70))
            
            # Step 4: Install Python deps
            self.log("\n" + "="*50)
            self.log("🐍 Paso 4/5: Instalando dependencias Python...")
            self.root.after(0, lambda: self.progress.config(value=80))
            
            self.run_command("pip3 install --quiet requests pandas numpy", cwd=str(project_dir))
            self.log("✅ Dependencias instaladas")
            
            self.root.after(0, lambda: self.progress.config(value=90))
            
            # Step 5: Start Workers
            self.log("\n" + "="*50)
            self.log("🚀 Paso 5/5: Iniciando workers...")
            
            # Get CPU cores
            cpu_output = subprocess.run(['sysctl', '-n', 'hw.ncpu'], capture_output=True)
            cpu_cores = int(cpu_output.stdout.decode().strip())
            workers = max(1, cpu_cores - 2)
            
            self.log(f"💻 Detectados {cpu_cores} CPUs - Iniciando {workers} workers...")
            
            # Kill existing
            subprocess.run("pkill -f crypto_worker", shell=True)
            time.sleep(1)
            
            # Start workers
            for i in range(1, workers + 1):
                cmd = f'WORKER_INSTANCE={i} nohup python3 {project_dir}/crypto_worker.py > ~/crypto_worker_{i}.log 2>&1 &'
                subprocess.run(cmd, shell=True)
                self.log(f"   Worker {i} iniciado")
                time.sleep(0.5)
                
            self.root.after(0, lambda: self.progress.config(value=100))
            
            # Done
            self.log("\n" + "="*50)
            self.log("✅ ¡INSTALACIÓN COMPLETADA!")
            self.log("="*50)
            self.log("\n📊 RESUMEN:")
            self.log(f"   Workers iniciados: {workers}")
            self.log(f"   Proyecto: {project_dir}")
            self.log(f"   Logs: ~/crypto_worker_*.log")
            self.log("\n🌐 Ver dashboard: http://100.77.179.14:5001")
            
            self.root.after(0, lambda: messagebox.showinfo("¡Listo!", 
                f"Instalación completada!\n\nWorkers: {workers}\n\nVerificar en: http://100.77.179.14:5001"))
                
        except Exception as e:
            self.log(f"\n❌ Error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.root.after(0, lambda: self.install_btn.config(state='normal'))
            
    def run(self):
        self.root.mainloop()

def main():
    if not HAS_TKINTER:
        print("❌ tkinter no disponible. Usando modo terminal...")
        os.system("bash auto_install_worker.sh")
        return
        
    app = WorkerInstaller()
    app.run()

if __name__ == "__main__":
    main()
