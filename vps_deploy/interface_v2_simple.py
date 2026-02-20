# Version simplificada del optimizer tab - SIN THREADS
# Para agregar al interface.py existente

"""
REEMPLAZO para el tab de Optimizer en interface.py

Esta versión:
- NO usa threads (Ray no funciona bien en threads)
- Corre de forma bloqueante
- Muestra progreso con st.empty() containers
- Funciona correctamente con Ray
"""

# Código para reemplazar el tab_opt en interface.py:

with tab_opt:
    st.header("Parameter Optimization")
    st.markdown("Find the best strategy parameters by testing combinations.")

    col_o1, col_o2 = st.columns([1, 2])

    with col_o1:
        st.subheader("1. Ranges")

        # Resistance Period
        st.markdown("**Breakout Period (Candles)**")
        res_min = st.number_input("Min", 10, 100, 20, key="res_min")
        res_max = st.number_input("Max", 20, 200, 60, key="res_max")
        res_step = st.number_input("Step", 5, 50, 10, key="res_step")

        # RSI Period
        st.markdown("**RSI Period**")
        rsi_min = st.number_input("Min", 10, 20, 10, key="rsi_min")
        rsi_max = st.number_input("Max", 10, 30, 20, key="rsi_max")
        rsi_step = st.number_input("Step", 1, 5, 2, key="rsi_step")

        # SL Multiplier
        st.markdown("**SL Multiplier (ATR)**")
        sl_min = st.number_input("Min", 1.0, 3.0, 1.0, 0.1, key="sl_min")
        sl_max = st.number_input("Max", 1.0, 5.0, 2.0, 0.1, key="sl_max")
        sl_step = st.number_input("Step", 0.1, 1.0, 0.5, 0.1, key="sl_step")

        # TP Multiplier
        st.markdown("**TP Multiplier (ATR)**")
        tp_min = st.number_input("Min", 1.5, 5.0, 2.0, 0.1, key="tp_min")
        tp_max = st.number_input("Max", 2.0, 8.0, 4.0, 0.1, key="tp_max")
        tp_step = st.number_input("Step", 0.5, 2.0, 1.0, 0.1, key="tp_step")

        # Risk Level
        st.markdown("**Risk Levels to Test**")
        risk_options = st.multiselect("Select Levels", ["LOW", "MEDIUM", "HIGH"], default=["LOW"])

    with col_o2:
        st.subheader("2. Run Optimization")

        if 'bt_data' not in st.session_state:
            st.warning("Please download data in the **Backtester** tab first.")
        else:
            # Method Selection
            st.markdown("**Optimization Method**")
            opt_method = st.radio("Select Algorithm",
                                 ["Grid Search (Exhaustive)", "Genetic Algorithm (Evolutionary)"],
                                 label_visibility="collapsed")

            ga_gens, ga_pop, ga_mut = 10, 50, 0.1
            if opt_method == "Genetic Algorithm (Evolutionary)":
                st.info("🧬 **Genetic Algorithm**: Evolves parameters over generations.")
                col_ga1, col_ga2, col_ga3 = st.columns(3)
                ga_gens = col_ga1.number_input("Generations", 1, 200, 10)
                ga_pop = col_ga2.number_input("Population", 10, 1000, 50)
                ga_mut = col_ga3.number_input("Mutation Rate", 0.01, 0.5, 0.1, 0.01)
            else:
                st.info("🔍 **Grid Search**: Tests EVERY combination.")

            # Start Button
            if st.button("🚀 Start Optimization", type="primary"):
                # Prepare ranges
                def float_range(start, stop, step):
                    r = []
                    c = start
                    while c <= stop:
                        r.append(round(c, 2))
                        c += step
                    return r

                if not risk_options:
                    risk_options = ["LOW"]

                param_ranges = {
                    'resistance_period': list(range(int(res_min), int(res_max) + 1, int(res_step))),
                    'rsi_period': list(range(int(rsi_min), int(rsi_max) + 1, int(rsi_step))),
                    'sl_multiplier': float_range(sl_min, sl_max, sl_step),
                    'tp_multiplier': float_range(tp_min, tp_max, tp_step),
                    'risk_level': risk_options
                }

                total_combinations = (
                    len(param_ranges['resistance_period']) *
                    len(param_ranges['rsi_period']) *
                    len(param_ranges['sl_multiplier']) *
                    len(param_ranges['tp_multiplier']) *
                    len(param_ranges['risk_level'])
                )

                st.info(f"📊 Testing {total_combinations} combinations...")

                # Create containers for live updates
                progress_bar = st.progress(0)
                status_text = st.empty()
                log_container = st.empty()

                # Storage for logs
                logs = []

                def log_callback(msg):
                    logs.append(msg)
                    # Update log display (last 20 lines)
                    log_container.text_area(
                        "Live Logs",
                        value="\n".join(logs[-20:]),
                        height=300,
                        disabled=True,
                        label_visibility="collapsed"
                    )

                def progress_callback(pct):
                    progress_bar.progress(pct)
                    status_text.text(f"Progress: {int(pct * 100)}%")

                try:
                    # Create optimizer
                    if opt_method == "Genetic Algorithm (Evolutionary)":
                        from optimizer import GeneticOptimizer
                        optimizer = GeneticOptimizer(
                            population_size=ga_pop,
                            generations=ga_gens,
                            mutation_rate=ga_mut
                        )
                    else:
                        from optimizer import GridOptimizer
                        optimizer = GridOptimizer()

                    # Run optimization (BLOCKING - no threads)
                    results = optimizer.optimize(
                        st.session_state['bt_data'],
                        param_ranges,
                        risk_level=risk_options[0] if risk_options else "LOW",
                        progress_callback=progress_callback,
                        log_callback=log_callback
                    )

                    # Clear progress
                    progress_bar.empty()
                    status_text.empty()

                    # Store results
                    st.session_state['opt_results'] = results

                    st.success("✅ Optimization Complete!")

                except Exception as e:
                    st.error(f"❌ Optimization failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())

        # Display Results
        if 'opt_results' in st.session_state:
            df_res = st.session_state['opt_results']

            if not df_res.empty:
                st.subheader("📊 Top Results")
                st.dataframe(df_res.head(10))

                # Scatter Plot
                st.scatter_chart(df_res, x='Total Trades', y='Total PnL', color='Win Rate %')

                st.markdown("---")
                st.subheader("🎯 Select & Apply Configuration")

                # Selection
                df_res = df_res.reset_index(drop=True)
                options = []
                for idx, row in df_res.iterrows():
                    label = f"Rank #{idx+1} | PnL: ${row['Total PnL']} | Trades: {row['Total Trades']} | WR: {row['Win Rate %']}%"
                    options.append(label)

                selected_option = st.selectbox("Choose Configuration", options)

                col_apply, col_save = st.columns(2)

                with col_apply:
                    if st.button("✅ Apply to Backtester"):
                        idx = options.index(selected_option)
                        selected_row = df_res.iloc[idx]
                        metric_keys = ['Total Trades', 'Win Rate %', 'Total PnL', 'Final Balance']
                        best_params = {k: v for k, v in selected_row.to_dict().items() if k not in metric_keys}
                        st.session_state['active_strategy_params'] = best_params
                        st.success(f"✅ Applied Configuration #{idx+1}!")

                with col_save:
                    if st.button("💾 Save to JSON"):
                        idx = options.index(selected_option)
                        row_dict = df_res.iloc[idx].to_dict()
                        json_str = json.dumps(row_dict, indent=2)
                        st.download_button(
                            label="Download JSON",
                            data=json_str,
                            file_name=f"opt_config_rank_{idx+1}.json",
                            mime="application/json"
                        )
