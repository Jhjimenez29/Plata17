from io import BytesIO
import datetime
import os
import pandas as pd
import streamlit as st
import unicodedata

# Librerías para formato avanzado de Excel
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
st.set_page_config(page_title="Catálogo & Auditoría", page_icon="📱", layout="wide")

CLAVE_SUPERVISOR = "super123"

# Estilos CSS
st.markdown("""
    <style>
    .sombra-tenue {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 10px 14px;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        margin-bottom: 12px;
    }
    .titulo-negro {
        color: #000000 !important;
        font-weight: 600;
        margin: 0;
    }
    .alerta-ultima-auditoria {
        background-color: #FEF3C7;
        border: 1px solid #F59E0B;
        color: #92400E;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 13px;
        margin-top: 8px;
    }
    </style>
""", unsafe_allow_html=True)

def inicializar_estado_sesion():
    """Inicializa todas las variables globales de sesión"""
    defaults = {
        "pantalla": "login",
        "vista_catalogo": "productos",
        "filtro_familia": "-- Selecciona una familia --",
        "busqueda_rapida": "",
        "tipo_cliente_seleccion": "Uso libre / Consulta",
        "cliente_nombre": "",
        "cliente_numero": "",
        "productos_seleccionados": {},
        "marcas_seleccionadas": {}
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

inicializar_estado_sesion()

# ==========================================
# 2. FUNCIONES DE UTILIDAD Y LIMPIEZA
# ==========================================
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def limpiar_casillas_y_seleccion():
    """Restablece los componentes de la interfaz y limpia la memoria temporal"""
    for key in list(st.session_state.keys()):
        if key.startswith("chk_p_") or key.startswith("chk_m_") or key.startswith("sel_ubic_") or key.startswith("sel_ubi_m_"):
            del st.session_state[key]
    st.session_state.productos_seleccionados = {}
    st.session_state.marcas_seleccionadas = {}

# ==========================================
# 3. GESTIÓN DE ARCHIVOS Y PERSISTENCIA (CSV/DATOS)
# ==========================================
@st.cache_data
def cargar_productos():
    for enc in ["utf-8", "latin1"]:
        try:
            return pd.read_csv("productos.csv", encoding=enc)
        except Exception:
            continue
    return None

@st.cache_data
def cargar_marcas():
    for n in ["marcas.csv", "Marcas.csv", "marcas.xlsx", "Marcas.xlsx"]:
        if n.endswith(".csv"):
            for enc in ["utf-8", "latin1"]:
                try:
                    df = pd.read_csv(n, encoding=enc)
                    if df is not None and not df.empty:
                        return df
                except Exception:
                    continue
        elif n.endswith(".xlsx"):
            try:
                df = pd.read_excel(n)
                if df is not None and not df.empty:
                    return df
            except Exception:
                continue
    return None

def cargar_catalogo_clientes():
    archivo = "clientes_directorio.csv"
    if os.path.exists(archivo):
        try:
            df = pd.read_csv(archivo, encoding='utf-8', dtype=str)
            df["Numero Cliente"] = df["Numero Cliente"].fillna("").astype(str).str.strip()
            df["Nombre Cliente"] = df["Nombre Cliente"].fillna("").astype(str).str.strip()
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=["Numero Cliente", "Nombre Cliente"])

def guardar_catalogo_clientes_completo(df):
    df.to_csv("clientes_directorio.csv", index=False, encoding='utf-8')

def guardar_cliente_directorio(num_cliente, nombre_cliente):
    num, nom = str(num_cliente).strip(), str(nombre_cliente).strip()
    if not num or not nom:
        return
        
    df_existente = cargar_catalogo_clientes()
    if not df_existente.empty:
        coincidencias = df_existente[
            (df_existente["Numero Cliente"].str.lower() == num.lower()) & 
            (df_existente["Nombre Cliente"].str.lower() == nom.lower())
        ]
        if not coincidencias.empty:
            return
            
    nuevo_df = pd.DataFrame([{"Numero Cliente": num, "Nombre Cliente": nom}])
    df_final = pd.concat([df_existente, nuevo_df], ignore_index=True)
    guardar_catalogo_clientes_completo(df_final)

def cargar_historial_maestro():
    archivo = "historial_revisiones.csv"
    if os.path.exists(archivo):
        try:
            return pd.read_csv(archivo, encoding='utf-8')
        except Exception:
            pass
    return pd.DataFrame()

def guardar_en_historial_maestro(df_nuevas_filas):
    archivo = "historial_revisiones.csv"
    header = not os.path.exists(archivo)
    df_nuevas_filas.to_csv(archivo, mode='a', header=header, index=False, encoding='utf-8')

def obtener_ultima_auditoria(nombre_cliente, num_cliente):
    df_h = cargar_historial_maestro()
    if df_h.empty:
        return None
    condicion = pd.Series(False, index=df_h.index)
    if nombre_cliente and "Nombre Cliente" in df_h.columns:
        condicion |= (df_h["Nombre Cliente"].astype(str).str.strip().str.lower() == str(nombre_cliente).strip().lower())
    if num_cliente and "Numero Cliente" in df_h.columns:
        condicion |= (df_h["Numero Cliente"].astype(str).str.strip() == str(num_cliente).strip())
        
    df_cliente = df_h[condicion]
    if not df_cliente.empty:
        return df_cliente["Fecha_Hora"].iloc[-1] if "Fecha_Hora" in df_cliente.columns else df_cliente["Fecha"].iloc[-1]
    return None

def consolidar_visita_actual():
    """Genera el DataFrame unificado con las selecciones de la visita"""
    nombre_c = st.session_state.cliente_nombre or "Cliente General"
    num_c = st.session_state.cliente_numero or "1001"
    
    filas = []
    fecha_std = datetime.date.today().strftime("%Y-%m-%d")
    fecha_hora_actual = datetime.datetime.now().strftime("%d de %B a las %I:%M %p").lower()
    
    for k, v in st.session_state.productos_seleccionados.items():
        filas.append({
            "Fecha": fecha_std,
            "Fecha_Hora": fecha_hora_actual,
            "Numero Cliente": num_c,
            "Nombre Cliente": nombre_c,
            "Esquema": "Esquema Comercial 2017",
            "Tipo Registro": "PRODUCTO",
            "Identificador / Código": k,
            "Descripción / Detalle": v["datos"].get("Descripcion de producto", str(v["datos"])),
            "Ubicación": v["ubicacion"]
        })

    for k, v in st.session_state.marcas_seleccionadas.items():
        filas.append({
            "Fecha": fecha_std,
            "Fecha_Hora": fecha_hora_actual,
            "Numero Cliente": num_c,
            "Nombre Cliente": nombre_c,
            "Esquema": "Esquema Comercial 2017",
            "Tipo Registro": "MARCA",
            "Identificador / Código": k,
            "Descripción / Detalle": f"Exhibidor / Marca: {k}",
            "Ubicación": v["ubicacion"]
        })

    return pd.DataFrame(filas)

def consolidar_y_guardar_visita_actual():
    df_rep = consolidar_visita_actual()
    if not df_rep.empty:
        guardar_en_historial_maestro(df_rep)
        if st.session_state.cliente_nombre and st.session_state.cliente_numero:
            guardar_cliente_directorio(st.session_state.cliente_numero, st.session_state.cliente_nombre)
        return True
    return False

# ==========================================
# 4. MOTOR DE GENERACIÓN DE EXCEL PROFESIONAL
# ==========================================
def generar_excel_profesional(df, titulo_reporte="REPORTE DE AUDITORÍA DE CAMPO"):
    """Genera un archivo Excel con formato profesional"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte_Auditoria"
    ws.views.sheetView[0].showGridLines = True

    # Estilos
    fuente_titulo = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    fuente_subtitulo = Font(name="Calibri", size=11, italic=True, color="D9D9D9")
    fuente_meta_bold = Font(name="Calibri", size=10, bold=True, color="1F497D")
    fuente_meta_val = Font(name="Calibri", size=10, color="000000")
    fuente_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    fuente_datos = Font(name="Calibri", size=10, color="000000")

    fill_header_principal = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    fill_header_tabla = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    fill_cebra = PatternFill(start_color="F2F4F8", end_color="F2F4F8", fill_type="solid")

    borde_fino = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    # Encabezado
    ws.merge_cells('A1:F1')
    ws['A1'] = f"  {titulo_reporte.upper()}"
    ws['A1'].font = fuente_titulo
    ws['A1'].fill = fill_header_principal
    ws['A1'].alignment = Alignment(vertical='center')

    ws.merge_cells('A2:F2')
    ws['A2'] = f"  Generado el: {datetime.datetime.now().strftime('%d/%m/%Y a las %H:%M hrs')}"
    ws['A2'].font = fuente_subtitulo
    ws['A2'].fill = fill_header_principal
    ws['A2'].alignment = Alignment(vertical='center')

    ws.row_dimensions[1].height = 25
    ws.row_dimensions[2].height = 18

    # Resumen
    nombre_cli = st.session_state.cliente_nombre or "Cliente General"
    num_cli = st.session_state.cliente_numero or "N/A"
    total_prod = len(df[df["Tipo Registro"] == "PRODUCTO"]) if "Tipo Registro" in df.columns else 0
    total_marcas = len(df[df["Tipo Registro"] == "MARCA"]) if "Tipo Registro" in df.columns else 0

    metadatos = [
        ("Cliente:", nombre_cli, "Número Cliente:", num_cli),
        ("Total Productos:", total_prod, "Total Marcas:", total_marcas)
    ]

    row_idx = 4
    for r in metadatos:
        ws.cell(row=row_idx, column=1, value=r[0]).font = fuente_meta_bold
        ws.cell(row=row_idx, column=2, value=r[1]).font = fuente_meta_val
        ws.cell(row=row_idx, column=4, value=r[2]).font = fuente_meta_bold
        ws.cell(row=row_idx, column=5, value=r[3]).font = fuente_meta_val
        row_idx += 1

    # Tabla de Datos
    start_row = 7
    df_export = df.drop(columns=["Fecha_Hora"], errors="ignore")
    
    for col_idx, col_name in enumerate(df_export.columns, start=1):
        cell = ws.cell(row=start_row, column=col_idx, value=str(col_name))
        cell.font = fuente_header
        cell.fill = fill_header_tabla
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws.row_dimensions[start_row].height = 22

    for r_idx, row_data in enumerate(df_export.itertuples(index=False), start=start_row + 1):
        ws.row_dimensions[r_idx].height = 20
        usar_cebra = (r_idx % 2 == 0)
        for c_idx, val in enumerate(row_data, start=1):
            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            cell.font = fuente_datos
            cell.border = borde_fino
            cell.alignment = Alignment(vertical='center')
            if usar_cebra:
                cell.fill = fill_cebra

    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.row >= start_row and cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    output = BytesIO()
    wb.save(output)
    return output.getvalue()

# ==========================================
# 5. CARGA Y DETECCIÓN AUTOMÁTICA DE COLUMNAS
# ==========================================
df_productos = cargar_productos()
df_marcas = cargar_marcas()

columna_familia_real = None
columna_codigo_real = None
columna_clave_real = None
columna_num_fam_real = None
columna_desc_prod_real = None

if df_productos is not None:
    df_productos.columns = df_productos.columns.str.strip()
    for col in df_productos.columns:
        col_norm = normalizar_texto(col)
        if "familia" in col_norm and "numero" not in col_norm and "num" not in col_norm:
            columna_familia_real = col
        elif col_norm in ["codigo", "cod", "sku", "id"]:
            columna_codigo_real = col
        elif col_norm in ["clave", "clv"]:
            columna_clave_real = col
        elif "numero de familia" in col_norm or "num de familia" in col_norm or "num familia" in col_norm or "n_familia" in col_norm:
            columna_num_fam_real = col
        elif "descripcion" in col_norm or "desc" in col_norm or "producto" in col_norm:
            if not columna_desc_prod_real:
                columna_desc_prod_real = col

    # Respaldo si no detectó por nombre exacto
    if not columna_familia_real:
        # Busca cualquier columna que contenga la palabra 'familia'
        fam_cols = [c for c in df_productos.columns if "familia" in normalizar_texto(c)]
        if fam_cols:
            columna_familia_real = fam_cols[0]

    if not columna_desc_prod_real and len(df_productos.columns) >= 2:
        columna_desc_prod_real = df_productos.columns[1]

    renombrar_dict = {}
    if columna_num_fam_real:
        renombrar_dict[columna_num_fam_real] = "Numero de familia"
    if columna_desc_prod_real:
        renombrar_dict[columna_desc_prod_real] = "Descripcion de producto"
        
    if renombrar_dict:
        df_productos = df_productos.rename(columns=renombrar_dict)

    # Columnas visibles por defecto
    st.session_state.columnas_seleccionadas = [c for c in df_productos.columns if c not in ["Fecha", "Fecha_Hora"]]

# ==========================================
# 6. VISTAS DE LA APLICACIÓN
# ==========================================

# --- PANTALLA: LOGIN ---
if st.session_state.pantalla == "login":
    st.markdown("<h1 style='text-align: center;'>🖼️</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #000000;'>Visualizador de Catálogo & Auditoría</h2>", unsafe_allow_html=True)
    st.markdown("---")

    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        usuario = st.text_input("Usuario", placeholder="Introduce tu usuario", key="input_user")
        contrasena = st.text_input("Contraseña", type="password", placeholder="Introduce tu contraseña", key="input_pass")
        st.write("")
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if usuario == "admin" and contrasena == "1234":
                st.session_state.pantalla = "resultados"
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

# --- PANTALLA: GESTIÓN DE CLIENTES ---
elif st.session_state.pantalla == "gestion_clientes":
    col_g1, col_g2 = st.columns([7, 3])
    with col_g1:
        st.markdown("<h3 style='margin:0;'>👥 Directorio, Alta y Modificación de Clientes</h3>", unsafe_allow_html=True)
    with col_g2:
        if st.button("← Volver a Búsqueda", use_container_width=True, type="primary"):
            st.session_state.pantalla = "resultados"
            st.rerun()

    st.markdown("---")
    col_alta1, col_alta2 = st.columns([4, 6])

    with col_alta1:
        st.markdown("#### ➕ Registrar Nuevo Cliente")
        with st.form("form_alta_cliente", clear_on_submit=True):
            n_cli = st.text_input("Número / Código de Cliente:")
            nom_cli = st.text_input("Nombre / Razón Social:")
            if st.form_submit_button("💾 Guardar Registro", use_container_width=True, type="primary"):
                if n_cli and nom_cli:
                    guardar_cliente_directorio(n_cli, nom_cli)
                    st.success(f"✅ ¡Registro '{nom_cli}' ({n_cli}) agregado con éxito!")
                    st.rerun()
                else:
                    st.error("⚠️ Debes completar número y nombre del cliente.")

    with col_alta2:
        st.markdown("#### 📁 Directorio de Clientes")
        df_dir = cargar_catalogo_clientes()
        if df_dir.empty:
            st.info("ℹ️ Aún no hay clientes registrados.")
        else:
            tab_ver, tab_editar, tab_eliminar = st.tabs(["👁️ Ver Directorio", "✏️ Editar Registro", "🗑️ Eliminar"])
            
            with tab_ver:
                st.dataframe(df_dir, use_container_width=True, hide_index=True, height=280)

            with tab_editar:
                opciones = [f"{i} - {r['Nombre Cliente']} {r['Numero Cliente']}" for i, r in df_dir.iterrows()]
                sel = st.selectbox("Selecciona cliente a modificar:", options=["-- Seleccionar --"] + opciones)
                if sel != "-- Seleccionar --":
                    idx = int(sel.split(" - ")[0])
                    r = df_dir.iloc[idx]
                    with st.form("form_edit"):
                        num_m = st.text_input("Nuevo Número:", value=str(r["Numero Cliente"]))
                        nom_m = st.text_input("Nuevo Nombre:", value=str(r["Nombre Cliente"]))
                        if st.form_submit_button("💾 Guardar Cambios", use_container_width=True, type="primary"):
                            if num_m and nom_m:
                                df_dir.at[idx, "Numero Cliente"] = str(num_m).strip()
                                df_dir.at[idx, "Nombre Cliente"] = str(nom_m).strip()
                                guardar_catalogo_clientes_completo(df_dir)
                                st.success("✅ Registro actualizado!")
                                st.rerun()

            with tab_eliminar:
                opciones_del = [f"{i} - {r['Nombre Cliente']} {r['Numero Cliente']}" for i, r in df_dir.iterrows()]
                sel_del = st.selectbox("Selecciona cliente a eliminar:", options=["-- Seleccionar --"] + opciones_del)
                if sel_del != "-- Seleccionar --":
                    idx_d = int(sel_del.split(" - ")[0])
                    st.warning(f"⚠️ Estás por eliminar: **{df_dir.iloc[idx_d]['Nombre Cliente']}**")
                    clave = st.text_input("🔒 Clave de Supervisor:", type="password")
                    if st.button("🚨 Confirmar Eliminación", type="primary", use_container_width=True):
                        if clave == CLAVE_SUPERVISOR:
                            df_dir = df_dir.drop(index=idx_d).reset_index(drop=True)
                            guardar_catalogo_clientes_completo(df_dir)
                            st.success("✅ Registro eliminado.")
                            st.rerun()
                        else:
                            st.error("❌ Clave incorrecta.")

# --- PANTALLA: REPORTE DE LA VISITA ACTUAL ---
elif st.session_state.pantalla == "reporte_auditoria":
    col_nav1, col_nav2 = st.columns([7, 3])
    with col_nav1:
        st.markdown("<h3 style='color: #000000; margin:0;'>📋 Reporte de Visita Actual</h3>", unsafe_allow_html=True)
    with col_nav2:
        if st.button("← Volver a Búsqueda", use_container_width=True, type="primary"):
            st.session_state.pantalla = "resultados"
            st.rerun()

    st.markdown("---")
    df_reporte_actual = consolidar_visita_actual()

    if df_reporte_actual.empty:
        st.info("ℹ️ Aún no has seleccionado productos ni marcas para este cliente.")
    else:
        st.markdown("#### 👤 Datos del Cliente / Revisión")
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            st.session_state.cliente_nombre = st.text_input("Nombre del Cliente:", value=st.session_state.cliente_nombre or "Cliente General")
        with col_c2:
            st.session_state.cliente_numero = st.text_input("Número de Cliente:", value=st.session_state.cliente_numero or "1001")
        with col_c3:
            st.date_input("Fecha de Revisión:", datetime.date.today())
        with col_c4:
            st.text_input("Esquema:", value="Esquema Comercial 2017", disabled=True)

        st.markdown("---")
        st.dataframe(df_reporte_actual.drop(columns=["Fecha_Hora"], errors="ignore"), use_container_width=True, hide_index=True, height=300)

        st.markdown("---")
        col_acc1, col_acc2, col_acc3 = st.columns(3)
        
        with col_acc1:
            if st.button("💾 Guardar y Finalizar Visita", use_container_width=True, type="primary"):
                if consolidar_y_guardar_visita_actual():
                    st.success(f"✅ ¡Visita de '{st.session_state.cliente_nombre}' guardada exitosamente!")
                limpiar_casillas_y_seleccion()
                st.session_state.tipo_cliente_seleccion = "Uso libre / Consulta"
                st.session_state.cliente_nombre = ""
                st.session_state.cliente_numero = ""
                st.session_state.pantalla = "resultados"
                st.rerun()

        with col_acc2:
            bytes_excel = generar_excel_profesional(df_reporte_actual, titulo_reporte="REPORTE DE VISITA Y AUDITORÍA")
            st.download_button(
                label="📥 Descargar Reporte en Excel Pro",
                data=bytes_excel,
                file_name=f"Visita_{st.session_state.cliente_numero}_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with col_acc3:
            if st.button("🗑️ Descartar Selección Actual", use_container_width=True):
                limpiar_casillas_y_seleccion()
                st.rerun()

# --- PANTALLA: HISTORIAL GENERAL ---
elif st.session_state.pantalla == "historial":
    col_h1, col_h2 = st.columns([7, 3])
    with col_h1:
        st.markdown("<h3 style='margin:0;'>📊 Historial de Revisiones Realizadas</h3>", unsafe_allow_html=True)
    with col_h2:
        if st.button("← Volver a Búsqueda", use_container_width=True, type="primary"):
            st.session_state.pantalla = "resultados"
            st.rerun()

    st.markdown("---")
    df_historial = cargar_historial_maestro()

    if df_historial.empty:
        st.info("ℹ️ Aún no hay visitas guardadas en el historial.")
    else:
        st.markdown("#### 🔍 Filtros de Consulta")
        col_f1, col_f2 = st.columns(2)
        opcion_default = "-- Seleccionar --"
        
        with col_f1:
            cliente_sel = st.selectbox("Filtrar por Cliente:", options=[opcion_default] + sorted(df_historial["Nombre Cliente"].dropna().unique().tolist()))
        with col_f2:
            fecha_sel = st.selectbox("Filtrar por Fecha:", options=[opcion_default] + sorted(df_historial["Fecha"].dropna().unique().tolist(), reverse=True))

        filtro_cli = (cliente_sel != opcion_default)
        filtro_fec = (fecha_sel != opcion_default)

        if filtro_cli or filtro_fec:
            df_filtrado = df_historial.copy()
            if filtro_cli:
                df_filtrado = df_filtrado[df_filtrado["Nombre Cliente"] == cliente_sel]
            if filtro_fec:
                df_filtrado = df_filtrado[df_filtrado["Fecha"] == fecha_sel]

            st.markdown("---")
            st.markdown(f"**Registros encontrados:** `{len(df_filtrado)}` filas")
            
            if not df_filtrado.empty:
                st.dataframe(df_filtrado.drop(columns=["Fecha_Hora"], errors="ignore"), use_container_width=True, hide_index=True, height=350)
                
                bytes_excel_h = generar_excel_profesional(df_filtrado, titulo_reporte="HISTORIAL DE REVISIONES Y AUDITORÍAS")
                st.download_button(
                    label="📥 Descargar Historial Filtrado (Excel Pro)",
                    data=bytes_excel_h,
                    file_name=f"Historial_Consulta_{datetime.date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )
            else:
                st.warning("⚠️ No se encontraron registros para los filtros seleccionados.")
        else:
            st.info("💡 Selecciona un filtro para consultar los registros guardados.")

# --- PANTALLA PRINCIPAL: BÚSQUEDA Y AUDITORÍA ---
elif st.session_state.pantalla == "resultados":
    total_sel = len(st.session_state.productos_seleccionados) + len(st.session_state.marcas_seleccionadas)
    
    col_sup1, col_sup2 = st.columns([4, 6])
    with col_sup1:
        st.markdown("<h3 style='margin:0;'>Esquema comercial 2017</h3>", unsafe_allow_html=True)
    with col_sup2:
        col_b1, col_b2, col_b3, col_b4 = st.columns([3, 2.5, 1.5, 2])
        with col_b1:
            lbl = f"📋 Ver Visita ({total_sel})" if total_sel > 0 else "📋 Ver Visita"
            if st.button(lbl, use_container_width=True, type="primary" if total_sel > 0 else "secondary"):
                st.session_state.pantalla = "reporte_auditoria"
                st.rerun()
        with col_b2:
            if st.button("📊 Historial", use_container_width=True):
                st.session_state.pantalla = "historial"
                st.rerun()
        with col_b3:
            if st.button("⋮", use_container_width=True, help="Menú Opciones / Clientes"):
                st.session_state.pantalla = "gestion_clientes"
                st.rerun()
        with col_b4:
            if st.button("← Salir", use_container_width=True):
                st.session_state.pantalla = "login"
                st.rerun()

    st.markdown("---")
    col_panel_filtros, col_panel_resultados = st.columns([3, 7])
    
    # -------------------------------------------------------------
    # PANEL LATERAL DE FILTROS Y SEGMENTACIÓN (LADO IZQUIERDO)
    # -------------------------------------------------------------
    with col_panel_filtros:
        # 1. Selección de Cliente
        st.markdown("<div class='sombra-tenue'><h4 class='titulo-negro'>👤 Selección de Cliente</h4></div>", unsafe_allow_html=True)
        
        opciones_modo = ["Cliente Preexistente", "Cliente Nuevo", "Uso libre / Consulta"]
        idx_m = opciones_modo.index(st.session_state.tipo_cliente_seleccion) if st.session_state.tipo_cliente_seleccion in opciones_modo else 2
        tipo_cli_sel = st.radio("Modo de atención:", options=opciones_modo, index=idx_m)
        
        if tipo_cli_sel != st.session_state.tipo_cliente_seleccion:
            st.session_state.tipo_cliente_seleccion = tipo_cli_sel

        df_dir_clientes = cargar_catalogo_clientes()

        if tipo_cli_sel == "Cliente Preexistente":
            if df_dir_clientes.empty:
                st.caption("⚠️ No hay clientes en el directorio.")
            else:
                dict_clientes = {}
                opciones_combo = ["-- Seleccionar --"]
                for _, row in df_dir_clientes.iterrows():
                    nom, num = str(row['Nombre Cliente']).strip(), str(row['Numero Cliente']).strip()
                    etiqueta = f"{nom} {num}".strip()
                    opciones_combo.append(etiqueta)
                    dict_clientes[etiqueta] = (nom, num)
                
                cli_sel_str = st.selectbox("Selecciona el cliente:", options=opciones_combo)
                if cli_sel_str != "-- Seleccionar --":
                    nom_sel, num_sel = dict_clientes[cli_sel_str]
                    st.session_state.cliente_nombre = nom_sel
                    st.session_state.cliente_numero = num_sel
                    
                    ultima_aud = obtener_ultima_auditoria(nom_sel, num_sel)
                    if ultima_aud:
                        st.markdown(f"<div class='alerta-ultima-auditoria'>📌 <b>Última auditoría:</b> {ultima_aud}</div>", unsafe_allow_html=True)

        elif tipo_cli_sel == "Cliente Nuevo":
            st.session_state.cliente_nombre = st.text_input("Nombre del Cliente Nuevo:", value=st.session_state.cliente_nombre)
            st.session_state.cliente_numero = st.text_input("Número de Cliente:", value=st.session_state.cliente_numero)

        elif tipo_cli_sel == "Uso libre / Consulta":
            st.session_state.cliente_nombre = ""
            st.session_state.cliente_numero = ""

        # Botones de Acción
        if total_sel > 0:
            st.markdown("---")
            if st.button("💾 Finalizar y Guardar Visita", use_container_width=True, type="primary"):
                if consolidar_y_guardar_visita_actual():
                    st.success("✅ ¡Visita guardada con éxito!")
                limpiar_casillas_y_seleccion()
                st.session_state.cliente_nombre = ""
                st.session_state.cliente_numero = ""
                st.rerun()

            if st.button("🧹 Limpiar Casillas del Cliente", use_container_width=True):
                limpiar_casillas_y_seleccion()
                st.toast("🧹 Casillas restablecidas.")
                st.rerun()

        # 2. Modo de Consulta (Vista)
        st.markdown("---")
        st.markdown("<div class='sombra-tenue'><h4 class='titulo-negro'>Modo de Consulta</h4></div>", unsafe_allow_html=True)
        modo_sel = st.radio("Vista:", options=["🔎 Catálogo de Productos", "🏷️ Listado de Marcas"], index=0 if st.session_state.vista_catalogo == "productos" else 1, label_visibility="collapsed")
        
        nuevo_m = "productos" if "Productos" in modo_sel else "marcas"
        if nuevo_m != st.session_state.vista_catalogo:
            st.session_state.vista_catalogo = nuevo_m
            st.rerun()

        # 3. Segmentación por Familia
        if st.session_state.vista_catalogo == "productos":
            st.markdown("<div class='sombra-tenue'><h4 class='titulo-negro'>Segmentación</h4></div>", unsafe_allow_html=True)
            
            if df_productos is not None:
                # Obtener la lista de familias disponibles
                if columna_familia_real and columna_familia_real in df_productos.columns:
                    lista_familias = sorted(df_productos[columna_familia_real].dropna().unique().tolist())
                else:
                    # Intenta encontrar cualquier columna adecuada
                    posibles_cols = [c for c in df_productos.columns if "familia" in normalizar_texto(c)]
                    if posibles_cols:
                        columna_familia_real = posibles_cols[0]
                        lista_familias = sorted(df_productos[columna_familia_real].dropna().unique().tolist())
                    else:
                        lista_familias = []

                op_def = "-- Selecciona una familia --"
                fams = [op_def] + lista_familias
                
                idx_f = fams.index(st.session_state.filtro_familia) if st.session_state.filtro_familia in fams else 0
                sel_f = st.selectbox("Familia:", options=fams, index=idx_f, label_visibility="collapsed")
                
                if sel_f != st.session_state.filtro_familia:
                    st.session_state.filtro_familia = sel_f
                    st.rerun()

            # Botón para limpiar filtros activos
            if st.session_state.filtro_familia != "-- Selecciona una familia --" or st.session_state.busqueda_rapida != "":
                if st.button("🔄 Limpiar Filtros", use_container_width=True):
                    st.session_state.filtro_familia = "-- Selecciona una familia --"
                    st.session_state.busqueda_rapida = ""
                    st.rerun()

    # -------------------------------------------------------------
    # PANEL DE RESULTADOS Y PRODUCTOS (LADO DERECHO)
    # -------------------------------------------------------------
    with col_panel_resultados:
        if st.session_state.vista_catalogo == "productos":
            if df_productos is None:
                st.error("⚠️ No se pudo cargar 'productos.csv'. Asegúrate de que el archivo esté en la carpeta del proyecto.")
            else:
                df_filtrado = df_productos.copy()
                
                # Caja de Búsqueda Rápida
                busqueda = st.text_input("🔤 Búsqueda rápida:", value=st.session_state.busqueda_rapida, placeholder="Escribe código, clave o descripción...")

                if busqueda != st.session_state.busqueda_rapida:
                    st.session_state.busqueda_rapida = busqueda
                    st.rerun()

                # Aplicar Filtro de Familia
                fam_activa = st.session_state.filtro_familia != "-- Selecciona una familia --"
                if fam_activa and columna_familia_real and columna_familia_real in df_filtrado.columns:
                    df_filtrado = df_filtrado[df_filtrado[columna_familia_real] == st.session_state.filtro_familia]

                # Aplicar Filtro de Texto
                if st.session_state.busqueda_rapida.strip():
                    cond = pd.Series(False, index=df_filtrado.index)
                    for col_val in df_filtrado.columns:
                        cond |= df_filtrado[col_val].astype(str).str.contains(st.session_state.busqueda_rapida, case=False, na=False)
                    df_filtrado = df_filtrado[cond]

                # Mostrar Tarjetas Informativas
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"<div class='sombra-tenue'><span style='color:#6B7280;font-size:11px;'>Familia Seleccionada</span><br><strong>{st.session_state.filtro_familia if fam_activa else 'Todas'}</strong></div>", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"<div class='sombra-tenue'><span style='color:#6B7280;font-size:11px;'>Coincidencias</span><br><strong style='color:#2563EB;'>{len(df_filtrado)}</strong></div>", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"<div class='sombra-tenue'><span style='color:#6B7280;font-size:11px;'>Total Catálogo</span><br><strong>{len(df_productos)}</strong></div>", unsafe_allow_html=True)

                # Mostrar Resultados y Checkboxes
                if not df_filtrado.empty:
                    # Mostrar Tabla General
                    cols_a_mostrar = [c for c in st.session_state.columnas_seleccionadas if c in df_filtrado.columns]
                    st.dataframe(df_filtrado[cols_a_mostrar], use_container_width=True, hide_index=True, height=260)
                    
                    st.markdown("---")
                    st.markdown("#### 📌 Marcar productos de esta vista:")
                    
                    # Iterar primeros 30 registros
                    for idx, row in df_filtrado.head(30).iterrows():
                        p_id = str(row.iloc[0]) if len(row) > 0 else f"PROD_{idx}"
                        
                        marcado = p_id in st.session_state.productos_seleccionados
                        ubi_act = st.session_state.productos_seleccionados[p_id]["ubicacion"] if marcado else "Piso de Venta"

                        cdet, cubi, cchk = st.columns([6, 3, 1])
                        with cdet:
                            desc = row.get("Descripcion de producto", str(row.iloc[1] if len(row)>1 else p_id))
                            st.write(f"**{p_id}** - {desc}")
                        with cubi:
                            u_sel = st.selectbox("Ubicación", ["Piso de Venta", "Almacén", "Ambos"], index=["Piso de Venta", "Almacén", "Ambos"].index(ubi_act), key=f"sel_ubic_{p_id}_{idx}", label_visibility="collapsed")
                        with cchk:
                            chk = st.checkbox("", value=marcado, key=f"chk_p_{p_id}_{idx}")

                        if chk:
                            st.session_state.productos_seleccionados[p_id] = {"datos": row.to_dict(), "ubicacion": u_sel}
                        elif p_id in st.session_state.productos_seleccionados:
                            del st.session_state.productos_seleccionados[p_id]

                        st.markdown("<hr style='margin:2px 0; border:0; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
                else:
                    st.warning("⚠️ No se encontraron productos con los filtros seleccionados.")

        else:
            st.markdown("<h4 style='color: #000000;'>🏷️ Listado de Marcas</h4>", unsafe_allow_html=True)
            st.markdown("---")
            if df_marcas is None:
                st.warning("⚠️ No se cargó 'marcas.csv' o 'marcas.xlsx'.")
            else:
                col_m = df_marcas.columns[0]
                for idx, row in df_marcas.iterrows():
                    nom_m = str(row[col_m]).strip()
                    if not nom_m or nom_m.lower() == "nan":
                        continue

                    marcado_m = nom_m in st.session_state.marcas_seleccionadas
                    ubi_m_act = st.session_state.marcas_seleccionadas[nom_m]["ubicacion"] if marcado_m else "Piso de Venta"

                    cnom, cubi, cchk = st.columns([6, 3, 1])
                    with cnom:
                        st.markdown(f"🏷️ **{nom_m}**")
                    with cubi:
                        u_m_sel = st.selectbox("Ubicación Marca", ["Piso de Venta", "Almacén", "Ambos"], index=["Piso de Venta", "Almacén", "Ambos"].index(ubi_m_act), key=f"sel_ubi_m_{nom_m}_{idx}", label_visibility="collapsed")
                    with cchk:
                        chk_m = st.checkbox("", value=marcado_m, key=f"chk_m_{nom_m}_{idx}")

                    if chk_m:
                        st.session_state.marcas_seleccionadas[nom_m] = {"ubicacion": u_m_sel}
                    elif nom_m in st.session_state.marcas_seleccionadas:
                        del st.session_state.marcas_seleccionadas[nom_m]

                    st.markdown("<hr style='margin:2px 0; border:0; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
