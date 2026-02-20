#!/usr/bin/env python3
"""
📊 UNIFIED TRADING DASHBOARD v1.0
Dashboard completo para todo el sistema de trading

Incluye:
- Estado de descargas de datos
- Progreso de Work Units
- Rendimiento de Workers
- Métricas de IA
- Estado de Trading

Uso: python3 unified_trading_dashboard.py
"""

import streamlit as st
import pandas as pd
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
import time

# Configuración
st.set_page_config(page_title="Unified Trading Dashboard", layout="wide")

# Paths
BASE_DIR = Path(__file__).parent
COORDINATOR_DB = BASE_DIR / "coordinator.db"
DATA_DB = BASE_DIR / "data_multi/download_tracker.db"
IA_DB = BASE_DIR / "ia_trading.db"

# Título
st.title("🚀 UNIFIED TRADING DASHBOARD v1.0")
st.markdown("### 💰 Sistema Completo de Trading Automatizado")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    
    st.markdown("---")
    st.markdown("**💰 Capital**")
    st.metric("Capital Base", "$500")
    
    st.markdown("**🎯 Objetivos**")
    st.metric("Objetivo Diario", "5%")
    st.metric("Objetivo Mensual", "100%")
    
    st.markdown("---")
    st.markdown("**📊 Contadores**")
    
    if DATA_DB.exists():
        conn = sqlite3.connect(str(DATA_DB))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM descargas")
        data_files = c.fetchone()[0]
        st.metric("Archivos de Datos", data_files)
        conn.close()
    else:
        st.metric("Archivos de Datos", "0")
    
    if COORDINATOR_DB.exists():
        conn = sqlite3.connect(str(COORDINATOR_DB))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM workers WHERE (julianday('now') - last_seen) < (10.0/1440.0)")
        active = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM work_units")
        wus = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM work_units WHERE status='completed'")
        wus_done = c.fetchone()[0]
        conn.close()
        st.metric("Workers Activos", active)
        st.metric("Work Units", f"{wus_done}/{wus}")
    else:
        st.metric("Workers Activos", "N/A")
        st.metric("Work Units", "N/A")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📥 Datos", 
    "🧬 Work Units", 
    "🤖 Workers", 
    "🧠 IA Trading",
    "📈 Trading"
])

# TAB 1: DATOS
with tab1:
    st.header("📥 Descarga de Datos Multi-Timeframe")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Timeframes")
        st.write("✅ 1m (1 minuto)")
        st.write("✅ 5m (5 minutos)")
        st.write("✅ 15m (15 minutos)")
        st.write("✅ 30m (30 minutos)")
        st.write("✅ 1h (1 hora)")
    
    with col2:
        st.markdown("### Progreso de Descarga")
        
        if DATA_DB.exists():
            conn = sqlite3.connect(str(DATA_DB))
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM descargas WHERE estado='completado'")
            completados = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM descargas")
            total = c.fetchone()[0]
            conn.close()
            
            if total > 0:
                progress = completados / total
                st.progress(progress)
                st.write(f"{completados}/{total} archivos ({progress*100:.1f}%)")
            else:
                st.info("No hay descargas iniciadas")
        else:
            st.info("Ejecuta download_multi_data.py primero")
    
    with col3:
        st.markdown("### Acciones")
        
        if st.button("📥 Iniciar Descarga", type="primary"):
            st.info("Ejecuta: python3 download_multi_data.py")
        
        if st.button("🔄 Verificar Estado"):
            st.rerun()

# TAB 2: WORK UNITS
with tab2:
    st.header("🧬 Work Units Generados")
    
    if COORDINATOR_DB.exists():
        conn = sqlite3.connect(str(COORDINATOR_DB))
        
        # Resumen
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM work_units")
        total_wus = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM work_units WHERE status='completed'")
        done_wus = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'")
        pending_wus = c.fetchone()[0]
        conn.close()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total WUs", total_wus)
        col2.metric("Completados", done_wus)
        col3.metric("Pendientes", pending_wus)
        col4.metric("Progreso", f"{done_wus/total_wus*100:.1f}%" if total_wus > 0 else "0%")
        
        # Tabla de WUs recientes
        c = conn.cursor()
        c.execute('''
            SELECT id, status, created_at, completed_at, 
                   strategy_params
            FROM work_units 
            ORDER BY id DESC LIMIT 20
        ''')
        wus = c.fetchall()
        conn.close()
        
        if wus:
            df_wus = pd.DataFrame(wus, columns=['ID', 'Estado', 'Creado', 'Completado', 'Params'])
            st.dataframe(df_wus, use_container_width=True)
        else:
            st.info("No hay Work Units. Ejecuta generate_optimized_wus.py")
        
        if st.button("🧬 Generar Work Units Optimizados"):
            st.info("Ejecuta: python3 generate_optimized_wus.py")
    else:
        st.error("Coordinator no encontrado")

# TAB 3: WORKERS
with tab3:
    st.header("🤖 Workers del Sistema")
    
    if COORDINATOR_DB.exists():
        conn = sqlite3.connect(str(COORDINATOR_DB))
        c = conn.cursor()
        
        # Resumen
        c.execute("SELECT COUNT(*) FROM workers")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM workers WHERE (julianday('now') - last_seen) < (10.0/1440.0)")
        active = c.fetchone()[0]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Workers", total)
        col2.metric("Activos", active)
        col3.metric("Inactivos", total - active)
        
        # Workers por máquina
        c.execute('''
            SELECT 
                CASE 
                    WHEN id LIKE '%MacBook-Pro%' THEN '🍎 MacBook Pro'
                    WHEN id LIKE '%MacBook-Air%' THEN '🪶 MacBook Air'
                    WHEN id LIKE '%rog%' THEN '🐧 Linux ROG'
                    ELSE '💻 Otro'
                END as maquina,
                COUNT(*) as total,
                SUM(CASE WHEN (julianday('now') - last_seen) < (10.0/1440.0) THEN 1 ELSE 0 END) as activos
            FROM workers 
            GROUP BY maquina
            ORDER BY total DESC
        ''')
        
        df_machines = pd.DataFrame(c.fetchall(), columns=['Máquina', 'Total', 'Activos'])
        st.dataframe(df_machines, use_container_width=True)
        
        # Top workers
        c.execute('''
            SELECT id, work_units_completed, ROUND(total_execution_time/3600, 2) as cpu_hours
            FROM workers 
            ORDER BY work_units_completed DESC 
            LIMIT 15
        ''')
        
        df_top = pd.DataFrame(c.fetchall(), columns=['Worker', 'WUs', 'CPU Hours'])
        st.dataframe(df_top, use_container_width=True)
        
        conn.close()
    else:
        st.error("Coordinator no encontrado")

# TAB 4: IA
with tab4:
    st.header("🧠 Agente de Trading con IA")
    
    if IA_DB.exists():
        conn = sqlite3.connect(str(IA_DB))
        c = conn.cursor()
        
        # Métricas
        c.execute("SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 1")
        metrics = c.fetchone()
        
        if metrics:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Trades", metrics[5])
            col2.metric("Ganadores", metrics[6])
            col3.metric("Perdedores", metrics[7])
            col4.metric("Win Rate", f"{metrics[1]:.1f}%")
        
        # Predicciones recientes
        c.execute('''
            SELECT symbol, prediction, confidence, price, created_at
            FROM predictions 
            ORDER BY created_at DESC LIMIT 20
        ''')
        
        df_pred = pd.DataFrame(c.fetchall(), columns=['Símbolo', 'Predicción', 'Confianza', 'Precio', 'Hora'])
        st.dataframe(df_pred, use_container_width=True)
        
        # Trades ejecutados
        c.execute('''
            SELECT symbol, signal, entry_price, exit_price, pnl, pnl_pct, resultado
            FROM executed_trades 
            WHERE resultado IS NOT NULL
            ORDER BY exit_time DESC LIMIT 20
        ''')
        
        df_trades = pd.DataFrame(c.fetchall(), columns=['Símbolo', 'Entrada', 'Salida', 'PnL $', 'PnL %', 'Resultado'])
        st.dataframe(df_trades, use_container_width=True)
        
        conn.close()
        
        if st.button("🧠 Entrenar IA"):
            st.info("Ejecuta: python3 ia_trading_agent.py --train")
    else:
        st.info("IA no inicializada. Ejecuta ia_trading_agent.py")

# TAB 5: TRADING
with tab5:
    st.header("📈 Estado de Trading")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Capital", "$500")
    col2.metric("🎯 Objetivo Diario", "+5%")
    col3.metric("📊 Win Rate Target", ">60%")
    col4.metric("🛑 Stop Loss", "5%")
    
    st.markdown("### 🎯 Parámetros de Trading")
    
    with st.expander("Ver Configuración"):
        st.write("""
        - **Capital Base:** $500
        - **Risk por Trade:** 2%
        - **Stop Loss:** 5%
        - **Take Profit:** 10%
        - **Trailing Stop:** 3%
        - **Timeframes:** 1m, 5m, 15m, 30m, 1h
        - **Activos:** Top 30 por liquidez
        """)
    
    # Progreso hacia objetivo
    objetivo_diario = 5  # 5%
    st.progress(0, texto="Progreso hacia objetivo diario")
    
    if st.button("🚀 Iniciar Sistema Completo"):
        st.markdown("""
        Ejecuta en terminal:
        ```
        python3 download_multi_data.py
        python3 generate_optimized_wus.py
        python3 ia_trading_agent.py --train
        python3 autonomous_trading_loop.py
        ```
        """)

# Footer
st.markdown("---")
st.markdown(
    """
    **📊 Unified Trading Dashboard v1.0** | 
    Sistema completo de trading automatizado con IA
    """
)
