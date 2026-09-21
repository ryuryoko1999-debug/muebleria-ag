import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
from fpdf import FPDF

# Configuración de la página
st.set_page_config(page_title="Mueblería A&G - Gestión", page_icon="🪑", layout="centered")

# --- CONTROL DE SESIÓN (LOGIN) ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

def pantalla_login():
    st.title("🪑 Mueblería A&G")
    st.subheader("🔐 Iniciar Sesión")
    
    usuario = st.text_input("Nombre de usuario")
    contrasena = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar", type="primary", use_container_width=True):
        if usuario.strip() == "muebleriaag" and contrasena == "ayg":
            st.session_state["autenticado"] = True
            st.success("¡Acceso concedido!")
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")

# Si no está logueado, muestra la pantalla de inicio de sesión
if not st.session_state["autenticado"]:
    pantalla_login()
else:
    # --- MENÚ NAVEGACIÓN PRINCIPAL ---
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2252/2252076.png", width=100)
    st.sidebar.title("Mueblería A&G")
    st.sidebar.caption("Sistema de Gestión")
    
    opcion = st.sidebar.radio("Menú Principal", ["Registrar Pago", "Registrar Cliente"])
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    # Configuración de Google Sheets
    SHEET_ID = "1boPTg4KSnNYBgI-hFwVWBgf_jst-wRl9IBFLLAY9GqE"
    GID = "409487884"
    CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    SCRIPT_URL = "https://script.google.com/macros/s/TU_SCRIPT_ID_AQUI/exec"  # Reemplazar con tu Apps Script

    # ==========================================
    # MÓDULO 1: REGISTRAR PAGO
    # ==========================================
    if opcion == "Registrar Pago":
        st.title("💳 Registrar Pago de Cuotas")

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
                st.error("⚠️ No se detectaron correctamente las columnas requeridas en la planilla.")
            else:
                df[col_cliente] = df[col_cliente].replace(r'^\s*$', None, regex=True).ffill()
                if col_mueble:
                    df[col_mueble] = df[col_mueble].ffill()

                df_valid = df.dropna(subset=[col_cliente]).copy()
                df_valid[col_cliente] = df_valid[col_cliente].astype(str).str.strip()
                df_valid = df_valid[~df_valid[col_cliente].str.upper().isin(['CLIENTE', 'NAN', 'NONE', ''])]

                clientes = sorted(df_valid[col_cliente].unique())

                fecha_pago = st.date_input("Fecha de Pago", value=date.today())
                cliente_sel = st.selectbox(f"Seleccionar Cliente ({len(clientes)} registrados)", options=[""] + clientes)

                if cliente_sel:
                    m_cliente = df_valid[col_cliente].str.upper() == cliente_sel.upper()
                    estado_str = df_valid[col_estado].astype(str).str.strip().str.lower()
                    m_pendiente = ~estado_str.isin(['pagado', 'pago', 'cancelado', 'cobrado'])
                    
                    cuotas_pendientes = df_valid[m_cliente & m_pendiente]

                    if cuotas_pendientes.empty:
                        st.info(f"El cliente **{cliente_sel}** no tiene cuotas pendientes.")
                    else:
                        opciones_cuota = cuotas_pendientes[col_cuota].astype(str).str.strip().tolist()
                        cuota_sel = st.selectbox("Seleccionar Cuota Pendiente", options=opciones_cuota)

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
                                st.warning(f"⚠️ **Atraso:** {dias_atraso} días (Vencimiento: {fecha_venc.strftime('%d/%m/%Y')}). Recargo 1% diario: **+${monto_mora:,.2f}**")
                            else:
                                dias_atraso = 0
                                monto_mora = 0.0
                                monto_total = monto_base
                                st.success("✅ Pago realizado en término.")

                            st.metric(label="Monto Final a Cobrar", value=f"$ {monto_total:,.2f}")

                            if st.button("🚀 Registrar Pago y Generar PDF", type="primary", use_container_width=True):
                                excel_row = int(fila_cuota.name) + 4
                                exito_guardado = False
                                
                                if "script.google.com" in SCRIPT_URL:
                                    try:
                                        res = requests.get(SCRIPT_URL, params={"row": excel_row, "estado": "pagado"}, timeout=10)
                                        if res.status_code == 200 and "OK" in res.text:
                                            exito_guardado = True
                                    except Exception as e:
                                        st.error(f"Error al conectar con Google Sheets: {e}")

                                # Generar comprobante PDF
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
                                    st.success("🎉 ¡Pago registrado en Google Sheets y PDF generado!")
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
    elif opcion == "Registrar Cliente":
        st.title("👤 Registrar Nuevo Cliente")
        st.info("📌 Pásame el modelo o la lista de campos que quieres incluir para este formulario.")
