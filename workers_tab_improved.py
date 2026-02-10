#!/usr/bin/env python3
"""
INTERFAZ DE WORKERS - MEJORADA
===============================
Esta es la sección mejorada de la pestaña "Workers" que muestra
TODOS los workers registrados (conectados e inactivos) claramente.

Sustituye la sección "TAB 2: Workers" en interface.py
"""

# ===== TAB 2: Workers - VERSIÓN MEJORADA =====
with tab2:
    st.subheader("👥 Workers Registry")
    st.markdown("""
    **Sistema distribuido**: Cada worker ejecuta backtests en paralelo.
    Los workers deben registrarse con el coordinator para recibir trabajo.
    """)

    if not coordinator_running:
        st.error("❌ Coordinator no está ejecutando. Inicia el coordinator primero.")
    else:
        workers = get_workers()
        
        if workers:
            # Clasificar workers
            def format_exec_time(seconds):
                if seconds < 60:
                    return f"{seconds:.0f}s"
                elif seconds < 3600:
                    return f"{seconds/60:.0f} min"
                else:
                    return f"{seconds/3600:.1f} hrs"

            def is_worker_alive(w):
                mins = w.get('last_seen_minutes_ago')
                if mins is not None:
                    return mins < 5.0
                return w.get('status') == 'active'

            def get_machine_from_id(worker_id):
                """Extrae el nombre de la máquina del worker ID"""
                wid = worker_id.lower()
                if "macbook-pro" in wid:
                    return "MacBook Pro"
                elif "macbook-air" in wid:
                    return "MacBook Air"
                elif "macbook" in wid:
                    return "MacBook"
                elif "rog" in wid or "linux" in wid:
                    return "Linux ROG"
                elif "linux" in wid:
                    return "Linux"
                return "Unknown"

            def get_short_name(worker_id):
                """Obtiene nombre corto para display"""
                if "_W" in worker_id:
                    parts = worker_id.rsplit("_W", 1)
                    if len(parts) == 2:
                        return f"W{parts[1]}"
                return worker_id.split("_")[0][:10]

            # Clasificar
            alive = [w for w in workers if is_worker_alive(w)]
            inactive = [w for w in workers if not is_worker_alive(w)]
            never_seen = [w for w in inactive if w.get('last_seen_minutes_ago', 0) > 60]  # > 1 hora

            # Contadores
            total_registered = len(workers)
            total_alive = len(alive)
            total_inactive = len(inactive)
            total_never_seen = len(never_seen)

            # ===== MÉTRICAS DE RESUMEN =====
            col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)

            with col_stats1:
                st.metric("Total Registrados", total_registered, 
                         delta=f"{total_alive} activos", delta_color="normal")

            with col_stats2:
                st.metric("Activos (≤5 min)", total_alive, 
                         delta="conectados", delta_color="normal")

            with col_stats3:
                st.metric("Inactivos (>5 min)", total_inactive,
                         delta=f"{total_never_seen} nunca vistos", delta_color="off")

            with col_stats4:
                # Calcular capacidad total
                alive_cpus = sum(4 for _ in alive)  # ~4 CPUs por worker
                st.metric("Capacidad", f"~{alive_cpus} CPUs",
                         delta="disponibles")

            st.divider()

            # ===== FILTROS =====
            col_filter1, col_filter2 = st.columns([3, 1])

            with col_filter1:
                filter_machine = st.multiselect(
                    "🔍 Filtrar por máquina",
                    options=["MacBook Pro", "MacBook Air", "Linux ROG", "Linux", "Unknown"],
                    default=[]
                )

            with col_filter2:
                show_never_seen = st.checkbox("Mostrar nunca vistos", value=False)

            # ===== WORKERS ACTIVOS =====
            st.markdown("### 🟢 Workers Activos (Conectados)")

            if not alive:
                st.info("No hay workers activos. Inicia workers desde la pestaña 'Control'.")
            else:
                # Filtrar por máquina
                if filter_machine:
                    alive_filtered = [w for w in alive if get_machine_from_id(w['id']) in filter_machine]
                else:
                    alive_filtered = alive

                if not alive_filtered:
                    st.warning("No hay workers activos que coincidan con el filtro.")
                else:
                    # Agrupar por máquina
                    from collections import defaultdict
                    machines_alive = defaultdict(list)
                    for w in alive_filtered:
                        machine = get_machine_from_id(w['id'])
                        machines_alive[machine].append(w)

                    for machine, w_list in machines_alive.items():
                        icon = "🍎" if "MacBook" in machine else ("🐧" if "Linux" in machine else "💻")
                        with st.expander(f"{icon} {machine} ({len(w_list)} workers)", expanded=True):
                            # Tabla de workers activos
                            cols = st.columns([2, 1, 1, 1, 2])
                            with cols[0]:
                                st.write("**Worker ID**")
                            with cols[1]:
                                st.write("**WU Completados**")
                            with cols[2]:
                                st.write("**Tiempo Total**")
                            with cols[3]:
                                st.write("**Último Seen**")
                            with cols[4]:
                                st.write("**Estado**")

                            for w in w_list:
                                cols = st.columns([2, 1, 1, 1, 2])
                                short_name = get_short_name(w['id'])
                                mins = w.get('last_seen_minutes_ago', 0)
                                
                                with cols[0]:
                                    st.code(f"{short_name}")
                                    st.caption(f"📍 {w.get('hostname', '?')}")
                                with cols[1]:
                                    wu = w.get('work_units_completed', 0)
                                    st.metric("", f"{wu}")
                                with cols[2]:
                                    exec_t = format_exec_time(w.get('total_execution_time', 0))
                                    st.write(exec_t)
                                with cols[3]:
                                    st.write(f"🟢 {mins:.1f}m")
                                with cols[4]:
                                    st.success("● Conectado", icon="✅")

                                st.divider()

            st.divider()

            # ===== WORKERS INACTIVOS =====
            inactive_to_show = [w for w in inactive if not (w in never_seen and not show_never_seen)]

            if filter_machine:
                inactive_to_show = [w for w in inactive_to_show if get_machine_from_id(w['id']) in filter_machine]

            if inactive_to_show:
                st.markdown("### 🔴 Workers Inactivos (Desconectados)")

                # Agrupar por máquina
                from collections import defaultdict
                machines_inactive = defaultdict(list)
                for w in inactive_to_show:
                    machine = get_machine_from_id(w['id'])
                    machines_inactive[machine].append(w)

                for machine, w_list in machines_inactive.items():
                    icon = "🍎" if "MacBook" in machine else ("🐧" if "Linux" in machine else "💻")
                    with st.expander(f"{icon} {machine} ({len(w_list)} workers)", expanded=False):
                        for w in w_list:
                            mins = w.get('last_seen_minutes_ago', 9999)
                            short_name = get_short_name(w['id'])
                            
                            col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                            
                            with col1:
                                st.write(f"**{short_name}**")
                                st.caption(f"ID: {w.get('id', '?')[:30]}...")
                            with col2:
                                st.write(f"WU: {w.get('work_units_completed', 0)}")
                            with col3:
                                st.write(f"⏰ {mins:.0f} min")
                            with col4:
                                if mins > 60:
                                    st.error(f"💀 Offline ({mins/60:.0f}h)")
                                else:
                                    st.warning(f"🟡 Inactivo ({mins:.0f}m)")

            # ===== WORKERS NUNCA VISTOS =====
            if show_never_seen and never_seen:
                st.markdown("### ⚫ Workers Registrados Nunca Vistos")
                st.caption("Workers que se registraron pero nunca volvieron a conectarse")

                for w in never_seen:
                    short_name = get_short_name(w['id'])
                    mins = w.get('last_seen_minutes_ago', 9999)
                    machine = get_machine_from_id(w['id'])
                    
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                    
                    with col1:
                        st.write(f"**{short_name}**")
                        st.caption(f"📍 {machine}")
                    with col2:
                        st.write(f"WU: {w.get('work_units_completed', 0)}")
                    with col3:
                        st.write(f"⏰ {mins/60:.0f}h")
                    with col4:
                        st.error("❌ Nunca se conectó")

            st.divider()

            # ===== ACCIONES RÁPIDAS =====
            st.markdown("### ⚡ Acciones Rápidas")

            col_action1, col_action2 = st.columns(2)

            with col_action1:
                if st.button("🔄 Actualizar Lista", use_container_width=True):
                    st.rerun()

            with col_action2:
                if st.button("🗑️ Limpiar Workers Antiguos", use_container_width=True,
                           help="Elimina workers no vistos en las últimas 24 horas"):
                    try:
                        conn = sqlite3.connect(COORDINATOR_DB)
                        c = conn.cursor()
                        # Eliminar workers no vistos en 24 horas (1440 minutos)
                        c.execute("DELETE FROM workers WHERE (julianday('now') - last_seen) > 1.0")  # 1 día
                        deleted = c.rowcount
                        conn.commit()
                        conn.close()
                        st.success(f"Eliminados {deleted} workers antiguos")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            # ===== API DATA BRUTA =====
            with st.expander("🔍 Ver datos crudos de la API", expanded=False):
                st.json(workers)

        else:
            st.info("""
            **No hay workers registrados aún.**

            Para añadir workers:
            1. Asegúrate de que el coordinator esté ejecutándose
            2. En cada máquina worker, ejecuta:
            
            ```bash
            cd <directorio_del_proyecto>
            export COORDINATOR_URL=http://<IP_COORDINATOR>:5001
            python3 crypto_worker.py
            ```

            O para múltiples workers en la misma máquina:
            ```bash
            for i in 1 2 3; do
                COORDINATOR_URL=http://<IP>:5001 WORKER_INSTANCE=$i \
                nohup python3 crypto_worker.py > /tmp/worker_$i.log 2>&1 &
                sleep 2
            done
            ```
            """)

        # Footer
        st.caption(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
