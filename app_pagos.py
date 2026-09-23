# ==========================================
    # MÓDULO 4: RESUMEN Y FLUJO DE EFECTIVO
    # ==========================================
    with tab_resumen:
        st.subheader("📊 Flujo de Efectivo y Balance del Mes")
        st.markdown(f"Resumen financiero para **{meses_es[mes_actual_num-1]} {anio_actual_num}**.")

        df_resumen = cargar_datos()
        
        # Cargar movimientos de caja desde Apps Script
        movimientos_caja = []
        try:
            res_caja = requests.get(SCRIPT_URL, params={"action": "getCaja"}, timeout=10)
            if res_caja.status_code == 200:
                movimientos_caja = res_caja.json()
        except:
            pass

        total_cobrado_cuotas = 0.0
        if df_resumen is not None:
            col_cliente_r = next((c for c in df_resumen.columns if "CLIENTE" in c.upper()), None)
            col_estado_r = next((c for c in df_resumen.columns if "ESTADO" in c.upper()), None)
            col_monto_r = next((c for c in df_resumen.columns if "MONTO" in c.upper()), None)
            col_pago_r = next((c for c in df_resumen.columns if "PAGO" in c.upper()), None)

            if col_cliente_r and col_estado_r and col_monto_r:
                df_resumen[col_cliente_r] = df_resumen[col_cliente_r].replace(r'^\s*$', None, regex=True).ffill()
                df_val = df_resumen.dropna(subset=[col_cliente_r]).copy()
                df_val = df_val[~df_val[col_cliente_r].astype(str).str.upper().isin(['CLIENTE', 'NAN', 'NONE', ''])]
                
                estado_clean = df_val[col_estado_r].astype(str).str.strip().str.lower()
                df_pagados_res = df_val[estado_clean.isin(['pagado', 'pago', 'cancelado', 'cobrado'])].copy()

                for _, row in df_pagados_res.iterrows():
                    monto_num = parse_monto(row[col_monto_r])
                    # Filtrar estrictamente por la fecha real de la columna J para el mes actual
                    if col_pago_r and pd.notna(row[col_pago_r]) and str(row[col_pago_r]).strip() != "":
                        val_fecha = str(row[col_pago_r]).strip()
                        try:
                            dt_pago = pd.to_datetime(val_fecha, format='%d/%m/%Y', errors='coerce')
                            if pd.isna(dt_pago):
                                dt_pago = pd.to_datetime(val_fecha, errors='coerce')
                            
                            if pd.notna(dt_pago) and dt_pago.month == mes_actual_num and dt_pago.year == anio_actual_num:
                                total_cobrado_cuotas += monto_num
                        except:
                            pass

        # Calcular ingresos extras y egresos del mes actual
        total_ingresos_extras = 0.0
        total_egresos_mes = 0.0

        mes_nombre_actual = meses_es[mes_actual_num - 1]
        for m in movimientos_caja:
            if str(m.get("mes")).strip().upper() == mes_nombre_actual and int(m.get("anio", anio_actual_num)) == anio_actual_num:
                monto_val = float(m.get("monto", 0))
                tipo = str(m.get("tipo"))
                if "➕" in tipo:
                    total_ingresos_extras += monto_val
                else:
                    total_egresos_mes += monto_val

        ingresos_totales_efectivo = total_cobrado_cuotas + total_ingresos_extras
        flujo_caja_neto = ingresos_totales_efectivo - total_egresos_mes

        st.markdown("---")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(label="📥 Cobros de Cuotas", value=f"$ {total_cobrado_cuotas:,.2f}")
        with col_m2:
            st.metric(label="➕ Ingresos Extras", value=f"$ {total_ingresos_extras:,.2f}")
        
        st.metric(label="💵 INGRESOS TOTALES EN EFECTIVO", value=f"$ {ingresos_totales_efectivo:,.2f}")
        st.metric(label="📉 TOTAL EGRESOS Y GASTOS", value=f"$ {total_egresos_mes:,.2f}")
        st.markdown("---")
        st.metric(label="📈 FLUJO NETO DE CAJA (Efectivo Final)", value=f"$ {flujo_caja_neto:,.2f}")

        st.markdown("---")
        if st.button("🔄 Actualizar Datos y Recalcular", use_container_width=True, key="btn_actualizar_resumen"):
            st.cache_data.clear()
            st.rerun()
