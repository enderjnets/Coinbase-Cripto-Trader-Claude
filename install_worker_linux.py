#!/usr/bin/env python3
"""
Crypto Worker Installer - Linux GUI Version
Native installer with graphical interface for Linux
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib, Gdk
    HAS_GTK = True
except ImportError:
    HAS_GTK = False

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

class LinuxWorkerInstaller(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="🧬 Crypto Worker Installer - Linux")
        self.set_default_size(600, 500)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        self.setup_ui()
        self.check_dependencies()
        
    def setup_ui(self):
        # Main box
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(box)
        
        # Header
        header = Gtk.Label()
        header.set_markup("<span font='16' weight='bold'>🧬 Sistema de Trading Distribuido</span>")
        header.set_margin_top(20)
        header.set_margin_bottom(10)
        box.pack_start(header, False, False, 0)
        
        # Scrolled window for log
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_margin_left(20)
        scrolled.set_margin_right(20)
        
        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView.new_with_buffer(self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.override_font(Pango.FontDescription("Monospace 10"))
        scrolled.add(self.log_view)
        box.pack_start(scrolled, True, True, 0)
        
        # Progress bar
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        self.progress.set_margin_left(20)
        self.progress.set_margin_right(20)
        box.pack_start(self.progress, False, False, 0)
        
        # Button box
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_margin_top(10)
        btn_box.set_margin_bottom(20)
        
        self.install_btn = Gtk.Button.new_with_label("🚀 INSTALAR")
        self.install_btn.connect("clicked", self.on_install_clicked)
        btn_box.pack_start(self.install_btn, True, True, 0)
        
        self.quit_btn = Gtk.Button.new_with_label("❌ SALIR")
        self.quit_btn.connect("clicked", lambda w: self.destroy())
        btn_box.pack_start(self.quit_btn, True, True, 0)
        
        box.pack_start(btn_box, False, False, 0)
        
        # Status
        self.status = Gtk.Label(label="Listo para instalar")
        self.status.set_margin_bottom(10)
        box.pack_start(self.status, False, False, 0)
        
    def log(self, message):
        def _log():
            end_iter = self.log_buffer.get_end_iter()
            self.log_buffer.insert(end_iter, message + "\n")
            scroll = self.log_view.get_vadjustment()
            scroll.set_value(scroll.get_upper() - scroll.get_page_size())
        GLib.idle_add(_log)
        
    def set_progress(self, value):
        def _set():
            self.progress.set_fraction(value)
        GLib.idle_add(_set)
        
    def set_status(self, message):
        def _set():
            self.status.set_label(message)
        GLib.idle_add(_set)
        
    def check_dependencies(self):
        self.log("🔍 Verificando dependencias...")
        
        # Check Python
        try:
            result = subprocess.run(['python3', '--version'], capture_output=True)
            if result.returncode == 0:
                self.log(f"✅ Python: {result.stdout.decode().strip()}")
        except:
            self.log("❌ Python no encontrado")
            
        # Check git
        try:
            result = subprocess.run(['which', 'git'], capture_output=True)
            if result.returncode == 0:
                self.log("✅ Git encontrado")
            else:
                self.log("⚠️  Git no encontrado (se instalará)")
        except:
            pass
            
        self.set_status("Listo para instalar")
        
    def on_install_clicked(self, widget):
        self.install_btn.set_sensitive(False)
        threading.Thread(target=self.install_process, daemon=True).start()
        
    def run_command(self, cmd, cwd=None):
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
        
    def install_process(self):
        try:
            self.log("\n" + "="*60)
            self.log("📦 INSTALACIÓN INICIADA")
            self.log("="*60)
            
            self.set_progress(0.1)
            self.set_status("Instalando dependencias...")
            
            # Step 1: Install system deps
            self.log("\n📦 Paso 1/5: Actualizando sistema...")
            
            if subprocess.run(['which', 'apt-get'], capture_output=True).returncode == 0:
                subprocess.run(['sudo', 'apt-get', 'update', '-qq'], stdout=subprocess.DEVNULL)
                subprocess.run(['sudo', 'apt-get', 'install', '-y', 'python3', 'python3-pip', 'git', '-qq'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif subprocess.run(['which', 'dnf'], capture_output=True).returncode == 0:
                subprocess.run(['sudo', 'dnf', 'install', '-y', 'python3', 'python3-pip', 'git'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif subprocess.run(['which', 'yum'], capture_output=True).returncode == 0:
                subprocess.run(['sudo', 'yum', 'install', '-y', 'python3', 'python3-pip', 'git'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                              
            self.log("✅ Dependencias del sistema instaladas")
            self.set_progress(0.3)
            
            # Step 2: Clone project
            self.log("\n📥 Paso 2/5: Configurando proyecto...")
            
            project_dir = Path.home() / "Coinbase-Cripto-Trader-Claude"
            
            if project_dir.exists():
                self.log("📥 Actualizando proyecto...")
                subprocess.run(['git', 'pull', 'origin', 'main'], cwd=str(project_dir),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                self.log("📥 Clonando proyecto...")
                subprocess.run(['git', 'clone', 
                               'https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git',
                               str(project_dir)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
            self.log(f"✅ Proyecto: {project_dir}")
            self.set_progress(0.5)
            
            # Step 3: Python deps
            self.log("\n🐍 Paso 3/5: Instalando Python packages...")
            
            subprocess.run(['pip3', 'install', '--quiet', 'requests', 'pandas', 'numpy'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log("✅ Paquetes instalados")
            self.set_progress(0.7)
            
            # Step 4: Start workers
            self.log("\n🚀 Paso 4/5: Iniciando workers...")
            
            # Get CPUs
            try:
                result = subprocess.run(['nproc'], capture_output=True, text=True)
                cpus = int(result.stdout.strip())
            except:
                cpus = 4
                
            workers = max(1, cpus - 2)
            self.log(f"💻 CPUs: {cpus} - Workers: {workers}")
            
            # Kill existing
            subprocess.run(['pkill', '-f', 'crypto_worker'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
            
            # Start workers
            for i in range(1, workers + 1):
                cmd = f'WORKER_INSTANCE={i} nohup python3 {project_dir}/crypto_worker.py > ~/crypto_worker_{i}.log 2>&1 &'
                subprocess.run(cmd, shell=True)
                self.log(f"   Worker {i} iniciado")
                time.sleep(0.3)
                
            self.set_progress(0.9)
            
            # Step 5: Auto-start
            self.log("\n⏰ Paso 5/5: Configurando auto-arranque...")
            
            # Create systemd service
            service_dir = Path.home() / ".config" / "systemd" / "user"
            service_dir.mkdir(parents=True, exist_ok=True)
            
            service_file = service_dir / "crypto-worker.service"
            with open(service_file, 'w') as f:
                f.write(f"""[Unit]
Description=Crypto Trading Worker
After=network.target

[Service]
Type=simple
ExecStart={project_dir}/start_workers.sh
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
""")
            
            subprocess.run(['systemctl', '--user', 'daemon-reload'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['systemctl', '--user', 'enable', 'crypto-worker'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['systemctl', '--user', 'start', 'crypto-worker'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.log("✅ Auto-arranque configurado")
            self.set_progress(1.0)
            
            # Done
            self.log("\n" + "="*60)
            self.log("✅ ¡INSTALACIÓN COMPLETADA!")
            self.log("="*60)
            self.log(f"\n📊 RESUMEN:")
            self.log(f"   Workers: {workers}")
            self.log(f"   Proyecto: {project_dir}")
            self.log(f"   Logs: ~/crypto_worker_*.log")
            self.log(f"\n🌐 Dashboard: http://100.77.179.14:5001")
            
            GLib.idle_add(lambda: messagebox.showinfo("¡Listo!", 
                f"Instalación completada!\n\nWorkers: {workers}\n\nVerificar en:\nhttp://100.77.179.14:5001"))
                
        except Exception as e:
            self.log(f"\n❌ Error: {e}")
            GLib.idle_add(lambda: messagebox.showerror("Error", str(e)))
        finally:
            GLib.idle_add(lambda: self.install_btn.set_sensitive(True))
            
    def run(self):
        self.show_all()

def main():
    if HAS_GTK:
        app = LinuxWorkerInstaller()
        app.connect("destroy", lambda w: Gtk.main_quit())
        app.run()
    elif HAS_TKINTER:
        # Fallback to tkinter
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.title("🧬 Crypto Worker Installer - Linux")
        root.geometry("600x400")
        root.withdraw()
        
        messagebox.showinfo("GUI no disponible",
            "GTK/Tkinter no disponible.\n\nEjecutando instalador de terminal...")
        
        root.destroy()
        os.system("bash auto_install_worker.sh")
    else:
        print("❌ No hay GUI disponible. Ejecutando instalador de terminal...")
        os.system("bash auto_install_worker.sh")

if __name__ == "__main__":
    main()
