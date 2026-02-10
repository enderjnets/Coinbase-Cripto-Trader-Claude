#!/usr/bin/env python3
"""
Crypto Worker Installer - Windows GUI Version
Native installer with graphical interface for Windows
"""

import os
import sys
import subprocess
import threading
import time
import urllib.request
import tempfile
from pathlib import Path

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

class WindowsWorkerInstaller:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🧬 Crypto Worker Installer - Windows")
        self.root.geometry("650x550")
        self.root.resizable(False, False)
        
        # Center window
        self.center_window()
        
        self.setup_ui()
        self.check_python()
        
    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
    def setup_ui(self):
        # Header with icon simulation
        header = tk.Frame(self.root, bg='#2E86AB', height=60)
        header.pack(fill='x')
        
        title = tk.Label(header, text="🧬 Sistema de Trading Distribuido", 
                       font=("Arial", 16, "bold"), bg='#2E86AB', fg='white')
        title.pack(pady=15)
        
        # Status area
        tk.Label(self.root, text="📋 Progreso de instalación:", anchor='w').pack(fill='x', padx=20, pady=(10,0))
        
        self.status = scrolledtext.ScrolledText(self.root, height=16, width=78, font=("Consolas", 9))
        self.status.pack(pady=5, padx=20)
        self.status.config(state='disabled', bg='#1E1E1E', fg='#00FF00')
        
        # Progress bar
        self.progress = ttk.Progressbar(self.root, mode='determinate', maximum=100)
        self.progress.pack(pady=10, padx=20, fill='x')
        
        # Buttons frame
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=15)
        
        self.install_btn = tk.Button(btn_frame, text="🚀 INSTALAR", 
                                    command=self.start_install,
                                    bg='#28A745', fg='white', font=("Arial", 11, "bold"),
                                    padx=30, pady=8, bd=0, cursor='hand2')
        self.install_btn.pack(side='left', padx=10)
        
        self.quit_btn = tk.Button(btn_frame, text="❌ SALIR", 
                                  command=self.root.quit,
                                  bg='#DC3545', fg='white', font=("Arial", 11, "bold"),
                                  padx=30, pady=8, bd=0, cursor='hand2')
        self.quit_btn.pack(side='left', padx=10)
        
        # Footer
        footer = tk.Label(self.root, 
                         text="📦 Instalador para Windows | GitHub: enderjnets/Coinbase-Cripto-Trader-Claude",
                         font=("Arial", 8), fg='gray')
        footer.pack(pady=10)
        
    def log(self, msg):
        def _log():
            self.status.config(state='normal')
            self.status.insert('end', msg + "\n")
            self.status.see('end')
            self.status.config(state='disabled')
        self.root.after(0, _log)
        
    def check_python(self):
        python_path = self.find_python()
        if python_path:
            self.log(f"✅ Python encontrado: {python_path}")
            return True
        else:
            self.log("❌ Python no encontrado")
            self.log("💡 El instalador lo descargará automáticamente")
            return False
            
    def find_python(self):
        """Find Python installation"""
        # Check PATH
        try:
            result = subprocess.run(['python', '--version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                return 'python'
        except:
            pass
            
        try:
            result = subprocess.run(['python3', '--version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                return 'python3'
        except:
            pass
            
        # Check common locations
        common_paths = [
            r"C:\Python39\python.exe",
            r"C:\Python310\python.exe",
            r"C:\Python311\python.exe",
            r"C:\Python312\python.exe",
            r"C:\Program Files\Python39\python.exe",
            r"C:\Program Files\Python310\python.exe",
            r"C:\Program Files\Python311\python.exe",
            r"C:\Program Files\Python312\python.exe",
            r"C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python39\python.exe",
            r"C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe",
            r"C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe",
            r"C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe",
        ]
        
        for path in common_paths:
            path = os.path.expandvars(path)
            if os.path.exists(path):
                return path
                
        return None
        
    def download_python(self):
        """Download and install Python"""
        self.log("\n📥 Descargando Python...")
        
        python_url = "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe"
        installer_path = os.path.join(tempfile.gettempdir(), "python_installer.exe")
        
        try:
            urllib.request.urlretrieve(python_url, installer_path)
            self.log("✅ Python descargado")
            self.log("📥 Ejecutando instalador...")
            self.log("💡 IMPORTANTE: Marca 'Add Python to PATH'")
            subprocess.run([installer_path, '/quiet', 'InstallAllUsers=1', 'PrependPath=1'])
            self.log("✅ Python instalado")
            return True
        except Exception as e:
            self.log(f"❌ Error descargando Python: {e}")
            return False
            
    def start_install(self):
        self.install_btn.config(state='disabled', bg='#6C757D')
        self.progress['value'] = 10
        self.root.update()
        
        threading.Thread(target=self.install_process, daemon=True).start()
        
    def install_process(self):
        try:
            # Step 1: Python
            self.log("\n" + "="*60)
            self.log("📦 Paso 1/5: Verificando Python...")
            
            python_path = self.find_python()
            if not python_path:
                if messagebox.askyesno("Python Required", 
                    "Python no está instalado.\n\n¿Deseas que lo descargue automáticamente?\n\nEsto puede tomar varios minutos."):
                    self.download_python()
                    python_path = self.find_python()
                else:
                    self.log("❌ Python es requerido")
                    return
            else:
                self.log("✅ Python encontrado")
                
            self.root.after(0, lambda: self.progress.config(value=20))
            
            # Step 2: Git
            self.log("\n" + "="*60)
            self.log("📦 Paso 2/5: Verificando Git...")
            
            has_git = subprocess.run(['where', 'git'], capture_output=True, returncode=0).returncode == 0
            
            if not has_git:
                self.log("📥 Git no encontrado. Descargando...")
                self.log("💡 Descarga Git desde: https://git-scm.com/download/win")
                self.log("💡 Después de instalar Git, ejecuta este instalador nuevamente")
                self.root.after(0, lambda: messagebox.showinfo("Git Required",
                    "Git no está instalado.\n\n1. Descarga Git desde: https://git-scm.com/download/win\n2. Instala Git (marca 'Add to PATH')\n3. Ejecuta este instalador nuevamente"))
                return
            else:
                self.log("✅ Git encontrado")
                
            self.root.after(0, lambda: self.progress.config(value=30))
            
            # Step 3: Clone Project
            self.log("\n" + "="*60)
            self.log("📥 Paso 3/5: Clonando proyecto...")
            
            project_dir = Path.home() / "Coinbase-Cripto-Trader-Claude"
            
            if project_dir.exists():
                self.log("📥 Actualizando proyecto existente...")
                subprocess.run(['git', 'pull', 'origin', 'main'], cwd=str(project_dir), 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                self.log("📥 Clonando proyecto...")
                subprocess.run(['git', 'clone', 
                              'https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git',
                              str(project_dir)])
                
            self.log(f"✅ Proyecto en: {project_dir}")
            self.root.after(0, lambda: self.progress.config(value=50))
            
            # Step 4: Install Python deps
            self.log("\n" + "="*60)
            self.log("🐍 Paso 4/5: Instalando dependencias Python...")
            
            subprocess.run([python_path, '-m', 'pip', 'install', '--quiet', 
                           'requests', 'pandas', 'numpy'],
                         cwd=str(project_dir), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log("✅ Dependencias instaladas")
            self.root.after(0, lambda: self.progress.config(value=70))
            
            # Step 5: Start Workers
            self.log("\n" + "="*60)
            self.log("🚀 Paso 5/5: Iniciando workers...")
            
            # Get CPU cores
            try:
                result = subprocess.run(['wmic', 'CPU', 'Get', 'NumberOfCores', '/value'],
                                       capture_output=True, text=True)
                cpu_cores = sum(int(line.split('=')[1]) for line in result.stdout.split('\n') 
                               if 'NumberOfCores=' in line)
            except:
                cpu_cores = 4
                
            workers = max(1, cpu_cores - 2)
            self.log(f"💻 Detectados {cpu_cores} cores - Iniciando {workers} workers...")
            
            # Kill existing
            subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            
            # Start workers
            coordinator_url = "http://100.77.179.14:5001"
            
            for i in range(1, workers + 1):
                cmd = f'start /B python "{project_dir}\\crypto_worker.py" {coordinator_url} > "{Path.home()}\\crypto_worker_{i}.log" 2>&1'
                subprocess.run(cmd, shell=True)
                self.log(f"   Worker {i} iniciado")
                time.sleep(0.5)
                
            self.root.after(0, lambda: self.progress.config(value=100))
            
            # Done
            self.log("\n" + "="*60)
            self.log("✅ ¡INSTALACIÓN COMPLETADA!")
            self.log("="*60)
            self.log(f"\n📊 RESUMEN:")
            self.log(f"   Workers iniciados: {workers}")
            self.log(f"   Proyecto: {project_dir}")
            self.log(f"   Logs: %USERPROFILE%\\crypto_worker_*.log")
            self.log("\n🌐 Ver dashboard: http://100.77.179.14:5001")
            
            self.root.after(0, lambda: messagebox.showinfo("¡Listo!", 
                f"Instalación completada!\n\nWorkers: {workers}\n\nVerificar en:\nhttp://100.77.179.14:5001"))
                
        except Exception as e:
            self.log(f"\n❌ Error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.root.after(0, lambda: self.install_btn.config(state='normal', bg='#28A745'))
            
    def run(self):
        self.root.mainloop()

def main():
    if not HAS_TKINTER:
        print("❌ tkinter no disponible.")
        print("Ejecutando versión batch: install_worker.bat")
        os.system("install_worker.bat")
        return
        
    app = WindowsWorkerInstaller()
    app.run()

if __name__ == "__main__":
    main()
