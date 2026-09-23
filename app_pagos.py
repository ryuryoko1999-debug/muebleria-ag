import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from fpdf import FPDF

# Configuración de página adaptada a móviles
st.set_page_config(page_title="Mueblería A&G", page_icon="🪑", layout="centered", initial_sidebar_state="collapsed")

# Estilos CSS optimizados para dispositivos móviles (Negro y Naranja)
st.markdown("""
    <style>
    .stApp {
        background-color: #0d0d0d;
        color: #f5f5f5;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #1a1a1a;
        padding: 6px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        background-color: #262626;
        border-radius: 8px;
        color: #ffffff;
        font-weight: bold;
        font-size: 13px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ff6600 !important;
        color: #ffffff !important;
    }
    .stButton>button {
        background-color: #ff6600;
        color: white;
        border-radius: 10px;
        font-weight: bold;
        border: none;
        height: 48px;
    }
    .stButton>button:hover {
        background-color: #e65c00;
        color: white;
    }
    div[data-testid="stMetricValue"] {
        color: #ff6600;
        font-size: 26px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONTROL DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

def pantalla_login():
    st.markdown("<h2 style='text-align: center; color: #ff6600;'>🪑 MUEBLERÍA A&G</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #aaa;'>Gestión Móvil de Cobros y Caja</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    usuario = st.text_input("👤 Usuario")
    contrasena = st.text_input("🔑 Contraseña", type="password")
    
    if st.button("🔓 INICIAR SESIÓN", type="primary", use_container_width=True):
        if usuario.strip().lower() == "muebleriaag" and contrasena == "ayg":
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("❌ Credenciales incorrectas")

if not st.session_state["autenticado"]:
    pantalla_login()
else:
    # Encabezado principal
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.markdown("<h3 style='margin:0; color:#ff6600;'>🪑 Mueblería A&G</h3>", unsafe_allow_html=True)
    with col_head2:
        if st.button("🚪 Salir", use_container_width=True, key="btn_salir"):
            st.session_state["autenticado"] = False
            st.rerun()

    st.markdown("---")

    # Enlaces de Google Sheets y Apps Script
    SHEET_ID = "1boPTg4KSnNYBgI-hFwVWBgf_jst-wRl9IBFLLAY9GqE"
    GID = "409487884"
    CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    
    SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyarQpV1w8XWaAwAcUQ7NXpvOkYkuHi-lXYOnmoDJoENncjJlZQPrepzUyeonhOHUEN-A/exec"

    # --- 4 PESTAÑAS PRINCIPALES ---
    tab_pago, tab_cliente, tab_finanzas, tab_resumen = st.tabs([
        "💳 COBRAR", "👤 CLIENTE", "💰 CAJA & GASTOS", "📊 RESUMEN"
    ])

    # Funciones auxiliares
    def parse_monto(val):
        try:
            clean = str(val).replace('$', '').replace('.', '').replace(',', '.').strip()
            return float(clean)
        except:
            return 0.0

    def parse_fecha_flexible(val):
        if pd.isna(val) or str(val).strip() == "" or str(val).upper() in ["NAN", "NONE", "NAT"]:
            return None
        val_str = str(val).strip()
        try:
            if isinstance(val, (pd.Timestamp, datetime, date)):
                return pd.to_datetime(val)
            dt = pd.to_datetime(val_str, format='%Y-%m-%d', errors='coerce')
            if pd.notna(dt):
                return dt
            dt = pd.to_datetime(val_str, format='%d/%m/%Y', errors='coerce')
            if pd.notna(dt):
                return dt
            dt = pd.to_datetime(val_str, errors='coerce')
            return dt if pd.notna(dt) else None
        except:
            return None

    @st.cache_data(ttl=0)
    def cargar_datos():
        try:
            df = pd.read_csv(CSV_URL, header=2)
            df.columns = [str(col).strip() for col in df.columns]
            return df
        except Exception as e:
            st.error(f"Error al conectar con la planilla: {e}")
            return None

    meses_es = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
    mes_actual_num = datetime.now().month
    anio_actual_num = datetime.now().year

    # ==========================================
    # MÓDULO 1: REGISTRAR PAGO (Cuotas Clientes)
    # ==========================================
    with tab_pago:
        st.subheader("💳 Registrar Cobro de Cuota")
        df = cargar_datos()

        if df is not None:
            col_cliente = next((c for c in df.columns if "CLIENTE" in c.upper()), None)
            col_cuota = next((c for c in df.columns if "CUOTA" in c.upper()), None)
            col_estado = next((c for c in df.columns if "ESTADO" in c.upper()), None)
            col_monto = next((c for c in df.columns if "MONTO" in c.upper()), None)
            col_mueble = next((c for c in df.columns if any(p in c.upper() for p in ["MUEBLE", "CONCEPTO", "PRODUCTO"])), None)
            col_fecha = next((c for c in df.columns if any(p in c.upper() for p in ["FECHA", "VENC"])), None)

            if not all([col_cliente, col_cuota, col_estado, col_monto]):
                st.error("⚠️ Error en la estructura de columnas.")
            else:
                df[col_cliente] = df[col_cliente].replace(r'^\s*$', None, regex=True).ffill()
                if col_mueble:
                    df[col_mueble] = df[col_mueble].ffill()

                df_valid = df.dropna(subset=[col_cliente]).copy()
                df_valid[col_cliente] = df_valid[col_cliente].astype(str).str.strip()
                df_valid = df_valid[~df_valid[col_cliente].str.upper().isin(['CLIENTE', 'NAN', 'NONE', ''])]

                clientes = sorted(df_valid[col_cliente].unique())

                fecha_pago = st.date_input("Fecha de Cobro", value=date.today())
                cliente_sel = st.selectbox(f"Seleccionar Cliente ({len(clientes)} activos)", options=[""] + clientes)

                if cliente_sel:
                    m_cliente = df_valid[col_cliente].str.upper() == cliente_sel.upper()
                    estado_str = df_valid[col_estado].astype(str).str.strip().str.lower()
                    m_pendiente = ~estado_str.isin(['pagado', 'pago', 'cancelado', 'cobrado'])
                    
                    cuotas_pendientes = df_valid[m_cliente & m_pendiente]

                    if cuotas_pendientes.empty:
                        st.success(f"🎉 **{cliente_sel}** está al día (sin cuotas pendientes).")
                    else:
                        opciones_cuota = cuotas_pendientes[col_cuota].astype(str).str.strip().tolist()
                        cuota_sel = st.selectbox("Cuota Pendiente", options=opciones_cuota)

                        if cuota_sel:
                            fila_cuota = cuotas_pendientes[cuotas_pendientes[col_cuota].astype(str).str.strip() == cuota_sel].iloc[0]
                            mueble = str(fila_cuota[col_mueble]) if col_mueble and pd.notna(fila_cuota[col_mueble]) else "Mueble / Servicio"

                            monto_base = parse_monto(fila_cuota[col_monto])

                            try:
                                fecha_venc = pd.to_datetime(fila_cuota[col_fecha]).date()
                                dias_atraso = (fecha_pago - fecha_venc).days
                            except:
                                dias_atraso = 0

                            if dias_atraso > 0:
                                porcentaje_mora = 0.01 * dias_atraso
                                monto_mora = monto_base * porcentaje_mora
                                monto_total = monto_base + monto_mora
                                st.warning(f"⚠️ **{dias_atraso} días de atraso.** Recargo 1% diario: **+${monto_mora:,.2f}**")
                            else:
                                dias_atraso = 0
                                monto_mora = 0.0
                                monto_total = monto_base
                                st.info("✅ Pago en término.")

                            st.metric(label="Monto Final a Cobrar", value=f"$ {monto_total:,.2f}")

                            if st.button("🚀 CONFIRMAR PAGO Y GENERAR PDF", use_container_width=True):
                                excel_row = int(fila_cuota.name) + 4
                                exito_guardado = False
                                
                                if "script.google.com" in SCRIPT_URL:
                                    try:
                                        res = requests.get(SCRIPT_URL, params={"action": "cobrar", "row": excel_row, "estado": "pagado"}, timeout=10)
                                        if res.status_code == 200 and "OK" in res.text:
                                            exito_guardado = True
                                    except Exception as e:
                                        st.error(f"Error al conectar con Google Sheets: {e}")

                                # PDF Comprobante
                                num_comprobante = f"REC-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                                pdf = FPDF()
                                pdf.add_page()
                                pdf.set_fill_color(31, 58, 82)
                                pdf.rect(0, 0, 210, 32, 'F')
                                pdf.set_font("Helvetica", "B", 16)
                                pdf.set_text_color(255, 255, 255)
                                pdf.cell(0, 10, "MUEBLERIA A&G", ln=True, align="C")
                                pdf.set_font("Helvetica", "", 10)
                                pdf.cell(0, 5, "COMPROBANTE OFICIAL DE PAGO", ln=True, align="C")
                                pdf.ln(15)
                                pdf.set_text_color(0, 0, 0)
                                pdf.set_font("Helvetica", "B", 10)
                                pdf.cell(45, 6, "N° Comprobante:", 0)
                                pdf.set_font("Helvetica", "", 10)
                                pdf.cell(0, 6, num_comprobante, 0, 1)
                                pdf.set_font("Helvetica", "B", 10)
                                pdf.cell(45, 6, "Fecha de Pago:", 0)
                                pdf.set_font("Helvetica", "", 10)
                                pdf.cell(0, 6, fecha_pago.strftime("%d/%m/%Y"), 0, 1)
                                pdf.set_font("Helvetica", "B", 10)
                                pdf.cell(45, 6, "Cliente:", 0)
                                pdf.set_font("Helvetica", "", 10)
                                pdf.cell(0, 6, cliente_sel.upper(), 0, 1)
                                pdf.ln(6)
                                pdf.set_fill_color(240, 243, 246)
                                pdf.set_font("Helvetica", "B", 9)
                                pdf.cell(80, 8, " CONCEPTO / PRODUCTO", 1, 0, 'L', True)
                                pdf.cell(50, 8, "DETALLE DE CUOTA", 1, 0, 'C', True)
                                pdf.cell(50, 8, "ESTADO", 1, 1, 'R', True)
                                pdf.set_font("Helvetica", "", 10)
                                pdf.cell(80, 8, f" {mueble}", 1)
                                pdf.cell(50, 8, f"Cuota {cuota_sel}", 1, 0, 'C')
                                pdf.set_text_color(34, 139, 34)
                                pdf.set_font("Helvetica", "B", 10)
                                pdf.cell(50, 8, "PAGADO ", 1, 1, 'R')
                                pdf.set_text_color(0, 0, 0)
                                pdf.ln(4)
                                pdf.set_fill_color(235, 243, 250)
                                pdf.set_font("Helvetica", "B", 11)
                                pdf.cell(130, 10, "TOTAL ABONADO: ", 1, 0, 'R', True)
                                pdf.set_font("Helvetica", "B", 13)
                                pdf.set_text_color(31, 58, 82)
                                pdf.cell(50, 10, f"$ {monto_total:,.2f} ", 1, 1, 'R', True)
                                pdf.ln(10)
                                pdf.set_font("Helvetica", "I", 9)
                                pdf.set_text_color(120, 120, 120)
                                pdf.cell(0, 5, "¡Muchas gracias por su preferencia!", 0, 1, 'C')
                                
                                pdf_filename = f"Comprobante_{cliente_sel.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                                pdf.output(pdf_filename)

                                if exito_guardado:
                                    st.success("🎉 ¡Pago guardado en Google Sheets y PDF listo!")
                                    st.cache_data.clear()
                                else:
                                    st.info("📄 Comprobante PDF generado.")

                                with open(pdf_filename, "rb") as file:
                                    st.download_button(
                                        label="📥 DESCARGAR COMPROBANTE PDF",
                                        data=file,
                                        file_name=pdf_filename,
                                        mime="application/pdf",
                                        use_container_width=True
                                    )

    # ==========================================
    # MÓDULO 2: REGISTRAR CLIENTE
    # ==========================================
    with tab_cliente:
        st.subheader("👤 Alta de Nuevo Cliente")

        def obtener_siguiente_id():
            try:
                df = cargar_datos()
                col_id = next((c for c in df.columns if "ID" in c.upper()), None)
                if col_id and not df[col_id].dropna().empty:
                    ids_validos = pd.to_numeric(df[col_id], errors='coerce').dropna()
                    ultimo_id = int(ids_validos.max()) if not ids_validos.empty else 0
                    return ultimo_id + 1
            except:
                pass
            return 1

        nuevo_id = obtener_siguiente_id()
        st.markdown(f"🆔 **ID Asignado:** `{nuevo_id:04d}`")

        nombre_cliente = st.text_input("Nombre Completo del Cliente")
        mueble_concepto = st.text_input("Mueble / Producto Vendido")
        
        c_monto, c_cuotas = st.columns(2)
        with c_monto:
            monto_cuota = st.number_input("Monto por Cuota ($)", min_value=1.0, value=50000.0, step=1000.0)
        with c_cuotas:
            num_cuotas = st.selectbox("Cantidad de Cuotas", options=list(range(1, 21)), index=5)

        c_dia, c_fecha = st.columns(2)
        with c_dia:
            dia_vencimiento = st.selectbox("Día de Cobro (1-30)", options=list(range(1, 31)), index=9)
        with c_fecha:
            fecha_primer_venc = st.date_input("Fecha 1º Vencimiento", value=date.today())

        total_venta_calculado = float(monto_cuota) * int(num_cuotas)
        st.markdown("---")
        st.metric(label="💰 Total de la Venta Proyectado", value=f"$ {total_venta_calculado:,.2f}")

        if st.button("💾 GUARDAR CLIENTE Y PLAN DE CUOTAS", use_container_width=True, type="primary"):
            if not nombre_cliente.strip() or not mueble_concepto.strip():
                st.error("⚠️ Por favor completa el Nombre del Cliente y el Mueble/Producto.")
            else:
                cuotas_list = []
                for i in range(1, num_cuotas + 1):
                    fecha_cuota = fecha_primer_venc + relativedelta(months=i-1)
                    try:
                        fecha_cuota = fecha_cuota.replace(day=dia_vencimiento)
                    except ValueError:
                        fecha_cuota = fecha_cuota.replace(day=28)

                    nombre_mes = meses_es[fecha_cuota.month - 1]

                    cuotas_list.append({
                        "id": f"{nuevo_id:04d}",
                        "cliente": nombre_cliente.strip().upper(),
                        "mueble": mueble_concepto.strip().upper(),
                        "mes": nombre_mes,
                        "cuota": f"{i} de {num_cuotas}",
                        "fecha": fecha_cuota.strftime("%d/%m/%Y"),
                        "monto": f"$ {monto_cuota:,.2f}",
                        "estado": "Pendiente"
                    })

                if "script.google.com" in SCRIPT_URL:
                    try:
                        payload = json.dumps({"action": "nuevo_cliente", "cuotas": cuotas_list})
                        res = requests.post(SCRIPT_URL, data=payload, headers={'Content-Type': 'application/json'}, timeout=15)
                        if res.status_code == 200 and "OK" in res.text:
                            st.success(f"🎉 ¡Cliente **{nombre_cliente.upper()}** guardado exitosamente con {num_cuotas} cuotas!")
                            st.cache_data.clear()
                        else:
                            st.error(f"Respuesta de Google Sheets: {res.text}")
                    except Exception as e:
                        st.error(f"Error de conexión: {e}")
                else:
                    st.warning("⚠️ Configura la URL del Apps Script en la variable `SCRIPT_URL`.")

    # ==========================================
    # MÓDULO 3: INGRESOS EXTRAS Y GASTOS (CAJA)
    # ==========================================
    with tab_finanzas:
        st.subheader("💰 Control de Ingresos y Egresos del Mes")
        st.markdown("Registra aquí **ingresos extras** (ventas contado, reparaciones) y los **gastos o préstamos** del mes.")

        with st.form("form_caja"):
            tipo_movimiento = st.selectbox(
                "Tipo de Movimiento", 
                ["➕ Ingreso Extra", "➖ Gasto Fijo", "➖ Gasto Variable", "💳 Préstamo / Financiero"]
            )
            concepto_mov = st.text_input("Concepto (ej. Venta mesa contado, Compra hierro)")
            monto_mov = st.number_input("Monto ($)", min_value=0.0, step=1000.0)
            
            c_m1, c_m2 = st.columns(2)
            with c_m1:
                mes_mov = st.selectbox("Mes Correspondiente", options=meses_es, index=mes_actual_num - 1, key="mes_caja_form")
            with c_m2:
                anio_mov = st.number_input("Año", value=anio_actual_num, step=1, key="anio_caja_form")
                
            fecha_mov = st.date_input("Fecha del Movimiento", value=date.today())

            submitted_mov = st.form_submit_button("💾 GUARDAR MOVIMIENTO EN CAJA", type="primary")
            if submitted_mov:
                if not concepto_mov.strip():
                    st.error("⚠️ Debes ingresar un concepto.")
                else:
                    payload = {
                        "action": "nuevo_movimiento",
                        "tipo": tipo_movimiento,
                        "concepto": concepto_mov.strip().upper(),
                        "monto": float(monto_mov),
                        "mes": mes_mov,
                        "anio": int(anio_mov),
                        "fecha": fecha_mov.strftime("%d/%m/%Y")
                    }
                    try:
                        res = requests.post(SCRIPT_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=15)
                        if res.status_code == 200 and "OK" in res.text:
                            st.success(f"🎉 Movimiento guardado exitosamente en Google Sheets.")
                            st.cache_data.clear()
                        else:
                            st.error(f"Error al guardar: {res.text}")
                    except Exception as e:
                        st.error(f"Error de conexión: {e}")

        st.markdown("---")
        st.markdown("### 📋 Planilla de Flujo de Caja Mensual")
        st.markdown("Selecciona el mes y año para consultar la planilla detallada de todo el dinero que entró y salió.")

        col_fc1, col_fc2 = st.columns(2)
        with col_fc1:
            mes_sel_fc = st.selectbox("Mes a Consultar", options=meses_es, index=mes_actual_num - 1, key="mes_fc")
        with col_fc2:
            anio_sel_fc = st.number_input("Año a Consultar", value=anio_actual_num, step=1, key="anio_fc")

        if st.button("📊 MOSTRAR PLANILLA DE FLUJO DE CAJA", use_container_width=True):
            with st.spinner("Generando planilla desde Clientes y Caja..."):
                registros_flujo = []
                mes_idx_fc = meses_es.index(mes_sel_fc) + 1

                # 1. Traer cobros de clientes pagados filtrados por la fecha de pago (Columna J) o vencimiento
                df_cli = cargar_datos()
                if df_cli is not None:
                    col_cliente_c = next((c for c in df_cli.columns if "CLIENTE" in c.upper()), None)
                    col_estado_c = next((c for c in df_cli.columns if "ESTADO" in c.upper()), None)
                    col_monto_c = next((c for c in df_cli.columns if "MONTO" in c.upper()), None)
                    col_cuota_c = next((c for c in df_cli.columns if "CUOTA" in c.upper()), None)
                    col_pago_c = next((c for c in df_cli.columns if "PAGO" in c.upper()), None)
                    col_fecha_c = next((c for c in df_cli.columns if any(p in c.upper() for p in ["FECHA", "VENC"])), None)

                    if col_cliente_c and col_estado_c and col_monto_c:
                        df_cli[col_cliente_c] = df_cli[col_cliente_c].replace(r'^\s*$', None, regex=True).ffill()
                        df_val_c = df_cli.dropna(subset=[col_cliente_c]).copy()
                        df_val_c = df_val_c[~df_val_c[col_cliente_c].astype(str).str.upper().isin(['CLIENTE', 'NAN', 'NONE', ''])]
                        
                        estado_clean = df_val_c[col_estado_c].astype(str).str.strip().str.lower()
                        df_pagados = df_val_c[estado_clean.isin(['pagado', 'pago', 'cancelado', 'cobrado'])].copy()

                        for idx, row in df_pagados.iterrows():
                            monto_num = parse_monto(row[col_monto_c])
                            cliente_nom = str(row[col_cliente_c]).strip().upper()
                            cuota_str = str(row[col_cuota_c]) if col_cuota_c else "Cuota"
                            
                            dt_pago = None
                            if col_pago_c and col_pago_c in row:
                                dt_pago = parse_fecha_flexible(row[col_pago_c])
                            
                            # Fallback a fecha de cuota si la columna J está vacía
                            if not dt_pago and col_fecha_c and col_fecha_c in row:
                                dt_pago = parse_fecha_flexible(row[col_fecha_c])

                            if dt_pago and dt_pago.month == mes_idx_fc and dt_pago.year == int(anio_sel_fc):
                                registros_flujo.append({
                                    "Fecha": dt_pago.strftime("%d/%m/%Y"),
                                    "Categoría": "📥 Cobro de Cuota",
                                    "Detalle": f"Cliente: {cliente_nom} ({cuota_str})",
                                    "Ingreso (+)": monto_num,
                                    "Egreso (-)": 0.0
                                })

                # 2. Traer movimientos de caja (Ingresos extras y Egresos) de forma segura con parse_monto
                try:
                    res_caja = requests.get(SCRIPT_URL, params={"action": "getCaja"}, timeout=10)
                    if res_caja.status_code == 200:
                        movs = res_caja.json()
                        for m in movs:
                            if str(m.get("mes")).strip().upper() == mes_sel_fc and int(m.get("anio", anio_actual_num)) == anio_sel_fc:
                                monto_val = parse_monto(m.get("monto", 0))
                                tipo_m = str(m.get("tipo"))
                                concepto_m = str(m.get("concepto"))
                                fecha_m = str(m.get("fecha"))

                                if "➕" in tipo_m:
                                    registros_flujo.append({
                                        "Fecha": fecha_m,
                                        "Categoría": "➕ Ingreso Extra",
                                        "Detalle": concepto_m,
                                        "Ingreso (+)": monto_val,
                                        "Egreso (-)": 0.0
                                    })
                                else:
                                    registros_flujo.append({
                                        "Fecha": fecha_m,
                                        "Categoría": f"📉 {tipo_m.replace('➖ ', '').replace('💳 ', '')}",
                                        "Detalle": concepto_m,
                                        "Ingreso (+)": 0.0,
                                        "Egreso (-)": monto_val
                                    })
                except Exception as e:
                    st.warning(f"No se pudieron cargar los movimientos de caja: {e}")

                if len(registros_flujo) > 0:
                    df_flujo = pd.DataFrame(registros_flujo)
                    
                    total_ingresos = df_flujo["Ingreso (+)"].sum()
                    total_egresos = df_flujo["Egreso (-)"].sum()
                    neto_caja = total_ingresos - total_egresos

                    st.markdown(f"#### 📊 Resumen de Caja: {mes_sel_fc} {anio_sel_fc}")
                    
                    col_r1, col_r2, col_r3 = st.columns(3)
                    col_r1.metric("Total Ingresos", f"$ {total_ingresos:,.2f}")
                    col_r2.metric("Total Egresos", f"$ {total_egresos:,.2f}")
                    col_r3.metric("Neto en Efectivo", f"$ {neto_caja:,.2f}")

                    st.markdown("---")
                    st.dataframe(df_flujo, use_container_width=True)
                else:
                    st.info(f"ℹ️ No hay movimientos registrados para **{mes_sel_fc} {anio_sel_fc}**.")

    # ==========================================
    # MÓDULO 4: RESUMEN Y FLUJO DE EFECTIVO
    # ==========================================
    with tab_resumen:
        st.subheader("📊 Flujo de Efectivo y Balance del Mes")
        st.markdown(f"Resumen financiero para **{meses_es[mes_actual_num-1]} {anio_actual_num}**.")

        df_resumen = cargar_datos()
        
        # Cargar movimientos de caja desde Apps Script de forma segura con parse_monto
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
            col_fecha_r = next((c for c in df_resumen.columns if any(p in c.upper() for p in ["FECHA", "VENC"])), None)

            if col_cliente_r and col_estado_r and col_monto_r:
                df_resumen[col_cliente_r] = df_resumen[col_cliente_r].replace(r'^\s*$', None, regex=True).ffill()
                df_val = df_resumen.dropna(subset=[col_cliente_r]).copy()
                df_val = df_val[~df_val[col_cliente_r].astype(str).str.upper().isin(['CLIENTE', 'NAN', 'NONE', ''])]
                
                estado_clean = df_val[col_estado_r].astype(str).str.strip().str.lower()
                df_pagados_res = df_val[estado_clean.isin(['pagado', 'pago', 'cancelado', 'cobrado'])].copy()

                for _, row in df_pagados_res.iterrows():
                    monto_num = parse_monto(row[col_monto_r])
                    
                    dt_pago = None
                    if col_pago_r and col_pago_r in row:
                        dt_pago = parse_fecha_flexible(row[col_pago_r])
                    
                    if not dt_pago and col_fecha_r and col_fecha_r in row:
                        dt_pago = parse_fecha_flexible(row[col_fecha_r])

                    if dt_pago and dt_pago.month == mes_actual_num and dt_pago.year == anio_actual_num:
                        total_cobrado_cuotas += monto_num

        # Calcular ingresos extras y egresos del mes actual de forma segura con parse_monto
        total_ingresos_extras = 0.0
        total_egresos_mes = 0.0

        mes_nombre_actual = meses_es[mes_actual_num - 1]
        for m in movimientos_caja:
            if str(m.get("mes")).strip().upper() == mes_nombre_actual and int(m.get("anio", anio_actual_num)) == anio_actual_num:
                monto_val = parse_monto(m.get("monto", 0))
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
