import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from fpdf import FPDF

# Configuración de página con estilos CSS personalizados
st.set_page_config(page_title="Mueblería A&G - Panel de Gestión", page_icon="🪑", layout="centered")

# --- ESTILOS CSS PERSONALIZADOS (Diseño Móvil / Premium) ---
st.markdown("""
    <style>
    /* Estilo general y botones */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    /* Tarjetas de información */
    .card-info {
        background-color: #f8f9fa;
        border-left: 5px solid #1f3a52;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    /* Encabezados laterales */
    [data-testid="stSidebar"] {
        background-color: #1f3a52;
        color: white;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONTROL DE SESIÓN (LOGIN) ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

def pantalla_login():
    st.markdown("<h2 style='text-align: center;'>🪑 Mueblería A&G</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Sistema Interno de Gestión de Cobros</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        usuario = st.text_input("👤 Usuario")
        contrasena = st.text_input("🔑 Contraseña", type="password")
        
        if st.button("🔓 Iniciar Sesión", type="primary", use_container_width=True):
            if usuario.strip().lower() == "muebleriaag" and contrasena == "ayg":
                st.session_state["autenticado"] = True
                st.success("¡Bienvenido!")
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")

if not st.session_state["autenticado"]:
    pantalla_login()
else:
    # --- MENÚ DE NAVEGACIÓN EN SIDEBAR ---
    st.sidebar.markdown("### 🪑 Mueblería A&G")
    st.sidebar.caption("Posadas, Misiones")
    st.sidebar.markdown("---")
    
    opcion = st.sidebar.radio("Navegación", ["💳 Registrar Pago", "👤 Registrar Cliente"])
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()

    # Enlaces de Google Sheets
    SHEET_ID = "1boPTg4KSnNYBgI-hFwVWBgf_jst-wRl9IBFLLAY9GqE"
    GID = "409487884"
    CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    
    # ⚠️ REEMPLAZAR CON TU URL DE APPS SCRIPT
    SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyarQpV1w8XWaAwAcUQ7NXpvOkYkuHi-lXYOnmoDJoENncjJlZQPrepzUyeonhOHUEN-A/exec"

    # ==========================================
    # MÓDULO 1: REGISTRAR PAGO
    # ==========================================
    if opcion == "💳 Registrar Pago":
        st.title("💳 Registro de Cobros")
        st.caption("Gestiona los pagos de cuotas e imprime comprobantes al instante.")

        @st.cache_data(ttl=0)
        def cargar_datos():
            try:
                df = pd.read_csv(CSV_URL, header=2)
                df.columns = [str(col).strip() for col in df.columns]
                return df
            except Exception as e:
                st.error(f"Error al conectar con Google Sheets: {e}")
                return None

        df = cargar_datos()

        if df is not None:
            col_cliente = next((c for c in df.columns if "CLIENTE" in c.upper()), None)
            col_cuota = next((c for c in df.columns if "CUOTA" in c.upper()), None)
            col_estado = next((c for c in df.columns if "ESTADO" in c.upper()), None)
            col_monto = next((c for c in df.columns if "MONTO" in c.upper()), None)
            col_mueble = next((c for c in df.columns if any(p in c.upper() for p in ["MUEBLE", "CONCEPTO", "PRODUCTO"])), None)
            col_fecha = next((c for c in df.columns if any(p in c.upper() for p in ["FECHA", "VENC"])), None)

            if not all([col_cliente, col_cuota, col_estado, col_monto]):
                st.error("⚠️ Estructura de tabla no válida en Google Sheets.")
            else:
                df[col_cliente] = df[col_cliente].replace(r'^\s*$', None, regex=True).ffill()
                if col_mueble:
                    df[col_mueble] = df[col_mueble].ffill()

                df_valid = df.dropna(subset=[col_cliente]).copy()
                df_valid[col_cliente] = df_valid[col_cliente].astype(str).str.strip()
                df_valid = df_valid[~df_valid[col_cliente].str.upper().isin(['CLIENTE', 'NAN', 'NONE', ''])]

                clientes = sorted(df_valid[col_cliente].unique())

                col_fecha_pago, col_sel_cli = st.columns([1, 2])
                with col_fecha_pago:
                    fecha_pago = st.date_input("Fecha de Cobro", value=date.today())
                with col_sel_cli:
                    cliente_sel = st.selectbox(f"Cliente ({len(clientes)} activos)", options=[""] + clientes)

                if cliente_sel:
                    m_cliente = df_valid[col_cliente].str.upper() == cliente_sel.upper()
                    estado_str = df_valid[col_estado].astype(str).str.strip().str.lower()
                    m_pendiente = ~estado_str.isin(['pagado', 'pago', 'cancelado', 'cobrado'])
                    
                    cuotas_pendientes = df_valid[m_cliente & m_pendiente]

                    if cuotas_pendientes.empty:
                        st.success(f"🎉 El cliente **{cliente_sel}** no tiene cuotas pendientes.")
                    else:
                        opciones_cuota = cuotas_pendientes[col_cuota].astype(str).str.strip().tolist()
                        cuota_sel = st.selectbox("Seleccionar Cuota a Cobrar", options=opciones_cuota)

                        if cuota_sel:
                            fila_cuota = cuotas_pendientes[cuotas_pendientes[col_cuota].astype(str).str.strip() == cuota_sel].iloc[0]
                            mueble = str(fila_cuota[col_mueble]) if col_mueble and pd.notna(fila_cuota[col_mueble]) else "Mueble / Servicio"

                            try:
                                monto_raw = str(fila_cuota[col_monto]).replace('$', '').replace('.', '').replace(',', '.').strip()
                                monto_base = float(monto_raw)
                            except:
                                monto_base = float(fila_cuota[col_monto])

                            try:
                                fecha_venc = pd.to_datetime(fila_cuota[col_fecha]).date()
                                dias_atraso = (fecha_pago - fecha_venc).days
                            except:
                                dias_atraso = 0

                            if dias_atraso > 0:
                                porcentaje_mora = 0.01 * dias_atraso
                                monto_mora = monto_base * porcentaje_mora
                                monto_total = monto_base + monto_mora
                                st.warning(f"⚠️ **Atraso de {dias_atraso} días** (Vencía: {fecha_venc.strftime('%d/%m/%Y')}). Mora 1% diario: **+${monto_mora:,.2f}**")
                            else:
                                dias_atraso = 0
                                monto_mora = 0.0
                                monto_total = monto_base
                                st.info("✅ Pago a término sin recargos.")

                            st.metric(label="Monto Final a Cobrar", value=f"$ {monto_total:,.2f}")

                            if st.button("🚀 Registrar Pago y Generar Comprobante PDF", type="primary", use_container_width=True):
                                excel_row = int(fila_cuota.name) + 4
                                exito_guardado = False
                                
                                if "script.google.com" in SCRIPT_URL:
                                    try:
                                        res = requests.get(SCRIPT_URL, params={"action": "cobrar", "row": excel_row, "estado": "pagado"}, timeout=10)
                                        if res.status_code == 200 and "OK" in res.text:
                                            exito_guardado = True
                                    except Exception as e:
                                        st.error(f"Error al conectar con Google Sheets: {e}")

                                # Generación de comprobante PDF
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
                                    st.success("🎉 ¡Pago registrado en Google Sheets y PDF listo!")
                                    st.cache_data.clear()
                                else:
                                    st.info("📄 Comprobante PDF generado correctamente.")

                                with open(pdf_filename, "rb") as file:
                                    st.download_button(
                                        label="📥 Descargar Comprobante PDF",
                                        data=file,
                                        file_name=pdf_filename,
                                        mime="application/pdf",
                                        use_container_width=True
                                    )

    # ==========================================
    # MÓDULO 2: REGISTRAR CLIENTE
    # ==========================================
    elif opcion == "👤 Registrar Cliente":
        st.title("👤 Alta de Nuevo Cliente")
        st.caption("Carga los datos de la venta para proyectar automáticamente el plan de cuotas.")

        @st.cache_data(ttl=0)
        def obtener_siguiente_id():
            try:
                df = pd.read_csv(CSV_URL, header=2)
                col_id = next((c for c in df.columns if "ID" in c.upper()), None)
                if col_id and not df[col_id].dropna().empty:
                    ids_validos = pd.to_numeric(df[col_id], errors='coerce').dropna()
                    ultimo_id = int(ids_validos.max()) if not ids_validos.empty else 0
                    return ultimo_id + 1
            except:
                pass
            return 1

        nuevo_id = obtener_siguiente_id()
        st.info(f"🆔 **ID Asignado Automáticamente:** `{nuevo_id:04d}`")

        with st.form("form_nuevo_cliente", clear_on_submit=False):
            col_a, col_b = st.columns(2)
            with col_a:
                nombre_cliente = st.text_input("Nombre Completo del Cliente")
                mueble_concepto = st.text_input("Mueble / Producto Vendido")
                monto_cuota = st.number_input("Monto por Cuota ($)", min_value=1.0, value=50000.0, step=1000.0)

            with col_b:
                num_cuotas = st.selectbox("Cantidad de Cuotas", options=list(range(1, 21)), index=5)
                dia_vencimiento = st.selectbox("Día de Vencimiento de Cobro", options=list(range(1, 31)), index=9)
                fecha_primer_venc = st.date_input("Fecha del 1º Vencimiento", value=date.today())

            monto_total_venta = monto_cuota * num_cuotas
            st.markdown(f"**💰 Total de la Venta proyectado:** `${monto_total_venta:,.2f}`")

            btn_guardar = st.form_submit_button("💾 Guardar Cliente y Generar Cuotas", type="primary", use_container_width=True)

        if btn_guardar:
            if not nombre_cliente.strip() or not mueble_concepto.strip():
                st.error("⚠️ Por favor completa el Nombre del Cliente y el Mueble/Producto.")
            else:
                # Generar el arreglo de cuotas (Idéntico a la Macro de Excel)
                cuotas_list = []
                meses_es = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
                
                for i in range(1, num_cuotas + 1):
                    fecha_cuota = fecha_primer_venc + relativedelta(months=i-1)
                    # Ajustar el día seleccionado
                    try:
                        fecha_cuota = fecha_cuota.replace(day=dia_vencimiento)
                    except ValueError:
                        fecha_cuota = fecha_cuota.replace(day=28) # Evitar errores en febrero

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

                # Enviar datos al Apps Script
                if "script.google.com" in SCRIPT_URL:
                    try:
                        payload = {"action": "nuevo_cliente", "data": json.dumps(cuotas_list)}
                        res = requests.get(SCRIPT_URL, params=payload, timeout=15)
                        if res.status_code == 200 and "OK" in res.text:
                            st.success(f"🎉 ¡Cliente **{nombre_cliente.upper()}** registrado exitosamente con {num_cuotas} cuotas!")
                            st.cache_data.clear()
                        else:
                            st.error(f"Error al guardar en Google Sheets: {res.text}")
                    except Exception as e:
                        st.error(f"Error de conexión: {e}")
                else:
                    st.warning("⚠️ Configura la URL del Apps Script en la variable `SCRIPT_URL`.")
