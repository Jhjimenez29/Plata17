from io import BytesIO
import datetime
import os
import pandas as pd
import streamlit as st
import unicodedata

# Configuración de la página
st.set_page_config(page_title="Catálogo & Auditoría", page_icon="📱", layout="wide")

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

CLAVE_SUPERVISOR = "super123"

# --- CONTROL DE ESTADOS DE LA SESIÓN ---
if "pantalla" not in st.session_state:
    st.session_state.pantalla = "login"
if "vista_catalogo" not in st.session_state:
    st.session_state.vista_catalogo = "productos"  # 'productos' o 'marcas'
if "filtro_familia" not in st.session_state:
    st.session_state.filtro_familia = "-- Selecciona una familia --"
if "busqueda_rapida" not in st.session_state:
    st.session_state.busqueda_rapida = ""

# CONFIGURACIÓN DEL CLIENTE ACTUAL
if "tipo_cliente_seleccion" not in st.session_state:
    st.session_state.tipo_cliente_seleccion = "Uso libre / Consulta"
if "cliente_nombre" not in st.session_state:
    st.session_state.cliente_nombre = ""
if "cliente_numero" not in st.session_state:
    st.session_state.cliente_numero = ""

# REGISTROS SELECCIONADOS DE LA VISITA ACTUAL
if "productos_seleccionados" not in st.session_state:
    st.session_state.productos_seleccionados = {}
if "marcas_seleccionadas" not in st.session_state:
    st.session_state.marcas_seleccionadas = {}

def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.strip().lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto

def limpiar_casillas_y_seleccion():
    """Limpia los estados temporales de casillas de verificación para evitar contaminación"""
    for key in list(st.session_state.keys()):
        if key.startswith("chk_p_") or key.startswith("chk_m_") or key.startswith("sel_ubic_") or key.startswith("sel_ubi_m_"):
            del st.session_state[key]
    st.session_state.productos_seleccionados = {}
    st.session_state.marcas_seleccionadas = {}

# --- CARGA Y GUARDADO DE DATOS ---
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
    nombres = ["marcas.csv", "Marcas.csv", "marcas.xlsx", "Marcas.xlsx"]
    for n in nombres:
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

def guardar_en_historial_maestro(df_nuevas_filas):
    archivo_historial = "historial_revisiones.csv"
    if os.path.exists(archivo_historial):
        df_nuevas_filas.to_csv(archivo_historial, mode='a', header=False, index=False, encoding='utf-8')
    else:
        df_nuevas_filas.to_csv(archivo_historial, mode='w', header=True, index=False, encoding='utf-8')

def cargar_historial_maestro():
    archivo_historial = "historial_revisiones.csv"
    if os.path.exists(archivo_historial):
        try:
            return pd.read_csv(archivo_historial, encoding='utf-8')
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

# GESTIÓN DEL CATÁLOGO DE CLIENTES PREEXISTENTES
def cargar_catalogo_clientes():
    archivo = "clientes_directorio.csv"
    if os.path.exists(archivo):
        try:
            df = pd.read_csv(archivo, encoding='utf-8', dtype=str)
            df["Numero Cliente"] = df["Numero Cliente"].fillna("").astype(str).str.strip()
            df["Nombre Cliente"] = df["Nombre Cliente"].fillna("").astype(str).str.strip()
            return df
        except Exception:
            return pd.DataFrame(columns=["Numero Cliente", "Nombre Cliente"])
    return pd.DataFrame(columns=["Numero Cliente", "Nombre Cliente"])

def guardar_catalogo_clientes_completo(df):
    archivo = "clientes_directorio.csv"
    df.to_csv(archivo, index=False, encoding='utf-8')

def guardar_cliente_directorio(num_cliente, nombre_cliente):
    num = str(num_cliente).strip()
    nom = str(nombre_cliente).strip()
    
    if not num or not nom:
        return
        
    df_existente = cargar_catalogo_clientes()
    
    existe_exacto = False
    if not df_existente.empty:
        coincidencias = df_existente[
            (df_existente["Numero Cliente"].str.lower() == num.lower()) & 
            (df_existente["Nombre Cliente"].str.lower() == nom.lower())
        ]
        if not coincidencias.empty:
            existe_exacto = True
            
    if not existe_exacto:
        nuevo_df = pd.DataFrame([{"Numero Cliente": num, "Nombre Cliente": nom}])
        df_final = pd.concat([df_existente, nuevo_df], ignore_index=True)
        guardar_catalogo_clientes_completo(df_final)

def obtener_ultima_auditoria(nombre_cliente, num_cliente):
    df_h = cargar_historial_maestro()
    if df_h.empty or ("Nombre Cliente" not in df_h.columns and "Numero Cliente" not in df_h.columns):
        return None
    
    condicion = pd.Series(False, index=df_h.index)
    if nombre_cliente and "Nombre Cliente" in df_h.columns:
        condicion = condicion | (df_h["Nombre Cliente"].astype(str).str.strip().str.lower() == str(nombre_cliente).strip().lower())
    if num_cliente and "Numero Cliente" in df_h.columns:
        condicion = condicion | (df_h["Numero Cliente"].astype(str).str.strip() == str(num_cliente).strip())
        
    df_cliente = df_h[condicion]
    if not df_cliente.empty:
        if "Fecha_Hora" in df_cliente.columns:
            return df_cliente["Fecha_Hora"].iloc[-1]
        elif "Fecha" in df_cliente.columns:
            return df_cliente["Fecha"].iloc[-1]
    return None

def consolidar_y_guardar_visita_actual():
    """Consolida las selecciones actuales y las guarda en el historial maestro"""
    nombre_c = st.session_state.cliente_nombre if st.session_state.cliente_nombre else "Cliente General"
    num_c = st.session_state.cliente_numero if st.session_state.cliente_numero else "1001"
    
    filas = []
    fecha_std = datetime.date.today().strftime("%Y-%m-%d")
    fecha_hora_actual = datetime.datetime.now().strftime("%d de %B a las %I:%M %p").lower()
    
    for k, v in st.session_state.productos_seleccionados.items():
        item = {
            "Fecha": fecha_std,
            "Fecha_Hora": fecha_hora_actual,
            "Numero Cliente": num_c,
            "Nombre Cliente": nombre_c,
            "Esquema": "Esquema Comercial 2017",
            "Tipo Registro": "PRODUCTO",
            "Identificador / Código": k,
            "Descripción / Detalle": v["datos"].get("Descripcion de producto", str(v["datos"])),
            "Ubicación": v["ubicacion"]
        }
        filas.append(item)

    for k, v in st.session_state.marcas_seleccionadas.items():
        item = {
            "Fecha": fecha_std,
            "Fecha_Hora": fecha_hora_actual,
            "Numero Cliente": num_c,
            "Nombre Cliente": nombre_c,
            "Esquema": "Esquema Comercial 2017",
            "Tipo Registro": "MARCA",
            "Identificador / Código": k,
            "Descripción / Detalle": f"Exhibidor / Marca: {k}",
            "Ubicación": v["ubicacion"]
        }
        filas.append(item)

    if filas:
        df_rep = pd.DataFrame(filas)
        guardar_en_historial_maestro(df_rep)
        if st.session_state.cliente_nombre and st.session_state.cliente_numero:
            guardar_cliente_directorio(st.session_state.cliente_numero, st.session_state.cliente_nombre)
        return True
    return False

df_productos = cargar_productos()
df_marcas = cargar_marcas()

# IDENTIFICACIÓN DE COLUMNAS DE PRODUCTOS
columna_familia_real = None
columna_codigo_real = None
columna_clave_real = None
columna_num_fam_real = None
columna_desc_prod_real = None

if df_productos is not None:
    df_productos.columns = df_productos.columns.str.strip()
    for col in df_productos.columns:
        col_norm = normalizar_texto(col)
        if col_norm == "familia":
            columna_familia_real = col
        elif col_norm == "codigo":
            columna_codigo_real = col
        elif col_norm == "clave":
            columna_clave_real = col
        elif "numero de familia" in col_norm or "num de familia" in col_norm or "num familia" in col_norm:
            columna_num_fam_real = col
        elif "descripcion de producto" in col_norm or "desc de producto" in col_norm:
            columna_desc_prod_real = col

    if not columna_desc_prod_real and len(df_productos.columns) >= 3:
        columna_desc_prod_real = df_productos.columns[2]

    renombrar_dict = {}
    if columna_num_fam_real:
        renombrar_dict[columna_num_fam_real] = "Numero de familia"
    if columna_desc_prod_real:
        renombrar_dict[columna_desc_prod_real] = "Descripcion de producto"
        
    if renombrar_dict:
        df_productos = df_productos.rename(columns=renombrar_dict)

    if "columnas_seleccionadas" not in st.session_state:
        columnas_base = ["Numero de familia", "Descripcion de producto"]
        st.session_state.columnas_seleccionadas = [c for c in columnas_base if c in df_productos.columns]

# ==========================================
# PANTALLA 1: LOGIN
# ==========================================
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

# ==========================================
# PANTALLA DE CONFIGURACIÓN / ALTA Y EDICIÓN DE CLIENTES
# ==========================================
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
        st.markdown("#### ➕ Registrar Nuevo Cliente / Registro")
        with st.form("form_alta_cliente", clear_on_submit=True):
            n_cli = st.text_input("Número / Código de Cliente:")
            nom_cli = st.text_input("Nombre / Razón Social del Cliente:")
            btn_guardar = st.form_submit_button("💾 Guardar Registro", use_container_width=True, type="primary")

            if btn_guardar:
                if n_cli and nom_cli:
                    guardar_cliente_directorio(n_cli, nom_cli)
                    st.success(f"✅ ¡Registro '{nom_cli}' ({n_cli}) agregado con éxito!")
                    st.rerun()
                else:
                    st.error("⚠️ Debes completar tanto el número como el nombre del cliente.")

    with col_alta2:
        st.markdown("#### 📁 Directorio de Clientes")
        df_dir = cargar_catalogo_clientes()
        
        if df_dir.empty:
            st.info("ℹ️ Aún no hay clientes registrados en el directorio.")
        else:
            tab_ver, tab_editar, tab_eliminar = st.tabs(["👁️ Ver Directorio", "✏️ Editar Registro", "🗑️ Eliminar (Requiere Supervisor)"])
            
            with tab_ver:
                st.dataframe(df_dir, use_container_width=True, hide_index=True, height=280)

            with tab_editar:
                opciones_clientes_edit = [f"{idx} - {row['Nombre Cliente']} {row['Numero Cliente']}" for idx, row in df_dir.iterrows()]
                sel_edit = st.selectbox("Selecciona el cliente a modificar:", options=["-- Seleccionar --"] + opciones_clientes_edit)
                
                if sel_edit != "-- Seleccionar --":
                    idx_m = int(sel_edit.split(" - ")[0])
                    cliente_actual_row = df_dir.iloc[idx_m]
                    
                    with st.form("form_editar_cliente"):
                        nuevo_num = st.text_input("Modificar Número de Cliente:", value=str(cliente_actual_row["Numero Cliente"]))
                        nuevo_nom = st.text_input("Modificar Nombre de Cliente:", value=str(cliente_actual_row["Nombre Cliente"]))
                        btn_aplicar_edit = st.form_submit_button("💾 Guardar Cambios", use_container_width=True, type="primary")
                        
                        if btn_aplicar_edit:
                            if nuevo_num and nuevo_nom:
                                df_dir.at[idx_m, "Numero Cliente"] = str(nuevo_num).strip()
                                df_dir.at[idx_m, "Nombre Cliente"] = str(nuevo_nom).strip()
                                guardar_catalogo_clientes_completo(df_dir)
                                st.success("✅ ¡Registro actualizado exitosamente!")
                                st.rerun()
                            else:
                                st.error("⚠️ Los campos no pueden quedar vacíos.")

            with tab_eliminar:
                opciones_clientes_del = [f"{idx} - {row['Nombre Cliente']} {row['Numero Cliente']}" for idx, row in df_dir.iterrows()]
                sel_del = st.selectbox("Selecciona el cliente a eliminar:", options=["-- Seleccionar --"] + opciones_clientes_del)
                
                if sel_del != "-- Seleccionar --":
                    idx_d = int(sel_del.split(" - ")[0])
                    cliente_del_row = df_dir.iloc[idx_d]
                    
                    st.warning(f"⚠️ Estás por eliminar el registro: **{cliente_del_row['Nombre Cliente']}** ({cliente_del_row['Numero Cliente']})")
                    
                    clave_sup = st.text_input("🔒 Ingresa la Clave de Supervisor para autorizar:", type="password", key="pass_sup_del")
                    
                    if st.button("🚨 Autorizar y Eliminar Registro", type="primary", use_container_width=True):
                        if clave_sup == CLAVE_SUPERVISOR:
                            df_dir = df_dir.drop(index=idx_d).reset_index(drop=True)
                            guardar_catalogo_clientes_completo(df_dir)
                            st.success("✅ Registro eliminado correctamente por el supervisor.")
                            st.rerun()
                        else:
                            st.error("❌ Clave de supervisor incorrecta. Operación no autorizada.")

# ==========================================
# PANTALLA 2: REPORTE DE LA VISITA ACTUAL
# ==========================================
elif st.session_state.pantalla == "reporte_auditoria":
    col_nav1, col_nav2 = st.columns([7, 3])
    with col_nav1:
        st.markdown("<h3 style='color: #000000; margin:0;'>📋 Reporte de Visita Actual</h3>", unsafe_allow_html=True)
    with col_nav2:
        if st.button("← Volver a Búsqueda", use_container_width=True, type="primary"):
            st.session_state.pantalla = "resultados"
            st.rerun()

    st.markdown("---")

    total_elementos = len(st.session_state.productos_seleccionados) + len(st.session_state.marcas_seleccionadas)

    if total_elementos == 0:
        st.info("ℹ️ Aún no has seleccionado productos ni marcas para este cliente.")
    else:
        st.markdown("#### 👤 Datos del Cliente / Revisión")
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            nombre_cliente = st.text_input("Nombre del Cliente:", value=st.session_state.cliente_nombre if st.session_state.cliente_nombre else "Cliente General")
        with col_c2:
            num_cliente = st.text_input("Número de Cliente:", value=st.session_state.cliente_numero if st.session_state.cliente_numero else "1001")
        with col_c3:
            fecha_rev = st.date_input("Fecha de Revisión:", datetime.date.today())
        with col_c4:
            esquema_rev = st.text_input("Esquema:", value="Esquema Comercial 2017")

        st.markdown("---")

        filas_consolidadas = []
        fecha_hora_actual = datetime.datetime.now().strftime("%d de %B a las %I:%M %p").lower()
        fecha_std = fecha_rev.strftime("%Y-%m-%d")

        for k, v in st.session_state.productos_seleccionados.items():
            item = {
                "Fecha": fecha_std,
                "Fecha_Hora": fecha_hora_actual,
                "Numero Cliente": num_cliente,
                "Nombre Cliente": nombre_cliente,
                "Esquema": esquema_rev,
                "Tipo Registro": "PRODUCTO",
                "Identificador / Código": k,
                "Descripción / Detalle": v["datos"].get("Descripcion de producto", str(v["datos"])),
                "Ubicación": v["ubicacion"]
            }
            filas_consolidadas.append(item)

        for k, v in st.session_state.marcas_seleccionadas.items():
            item = {
                "Fecha": fecha_std,
                "Fecha_Hora": fecha_hora_actual,
                "Numero Cliente": num_cliente,
                "Nombre Cliente": nombre_cliente,
                "Esquema": esquema_rev,
                "Tipo Registro": "MARCA",
                "Identificador / Código": k,
                "Descripción / Detalle": f"Exhibidor / Marca: {k}",
                "Ubicación": v["ubicacion"]
            }
            filas_consolidadas.append(item)

        df_reporte_actual = pd.DataFrame(filas_consolidadas)
        st.dataframe(df_reporte_actual.drop(columns=["Fecha_Hora"], errors="ignore"), use_container_width=True, hide_index=True, height=300)

        st.markdown("---")
        col_acc1, col_acc2, col_acc3 = st.columns(3)
        
        with col_acc1:
            if st.button("💾 Guardar y Finalizar Visita", use_container_width=True, type="primary"):
                guardar_en_historial_maestro(df_reporte_actual)
                if nombre_cliente and num_cliente:
                    guardar_cliente_directorio(num_cliente, nombre_cliente)
                
                limpiar_casillas_y_seleccion()
                st.session_state.tipo_cliente_seleccion = "Uso libre / Consulta"
                st.session_state.cliente_nombre = ""
                st.session_state.cliente_numero = ""
                st.success(f"✅ ¡Visita del cliente '{nombre_cliente}' guardada exitosamente!")
                st.session_state.pantalla = "resultados"
                st.rerun()

        with col_acc2:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_reporte_actual.drop(columns=["Fecha_Hora"], errors="ignore").to_excel(writer, index=False, sheet_name='Visita_Actual')
            
            st.download_button(
                label="📥 Descargar Excel de esta Visita",
                data=output.getvalue(),
                file_name=f"Visita_{num_cliente}_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with col_acc3:
            if st.button("🗑️ Descartar Selección Actual", use_container_width=True):
                limpiar_casillas_y_seleccion()
                st.rerun()

# ==========================================
# PANTALLA 3: HISTORIAL GENERAL DE REVISIONES
# ==========================================
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
            clientes_unicos = [opcion_default] + sorted(df_historial["Nombre Cliente"].dropna().unique().tolist())
            cliente_sel = st.selectbox("Filtrar por Cliente:", options=clientes_unicos)
            
        with col_f2:
            fechas_unicas = [opcion_default] + sorted(df_historial["Fecha"].dropna().unique().tolist(), reverse=True)
            fecha_sel = st.selectbox("Filtrar por Fecha:", options=fechas_unicas)

        filtro_cliente_activo = (cliente_sel != opcion_default)
        filtro_fecha_activo = (fecha_sel != opcion_default)

        if filtro_cliente_activo or filtro_fecha_activo:
            df_h_filtrado = df_historial.copy()

            if filtro_cliente_activo:
                df_h_filtrado = df_h_filtrado[df_h_filtrado["Nombre Cliente"] == cliente_sel]

            if filtro_fecha_activo:
                df_h_filtrado = df_h_filtrado[df_h_filtrado["Fecha"] == fecha_sel]

            st.markdown("---")
            st.markdown(f"**Registros encontrados:** `{len(df_h_filtrado)}` filas")
            
            if not df_h_filtrado.empty:
                st.dataframe(df_h_filtrado.drop(columns=["Fecha_Hora"], errors="ignore"), use_container_width=True, hide_index=True, height=350)

                output_h = BytesIO()
                with pd.ExcelWriter(output_h, engine='openpyxl') as writer:
                    df_h_filtrado.drop(columns=["Fecha_Hora"], errors="ignore").to_excel(writer, index=False, sheet_name='Historial_Filtrado')

                st.download_button(
                    label="📥 Descargar Reporte de Consulta (Excel)",
                    data=output_h.getvalue(),
                    file_name=f"Reporte_Consulta_{datetime.date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )
            else:
                st.warning("⚠️ No se encontraron registros con la combinación de filtros seleccionada.")
        else:
            st.info("💡 **Vista Limpia:** Selecciona una opción en 'Filtrar por Cliente' o 'Filtrar por Fecha' para mostrar los resultados.")

# ==========================================
# PANTALLA PRINCIPAL: BÚSQUEDA Y SELECCIÓN
# ==========================================
elif st.session_state.pantalla == "resultados":
    
    total_sel = len(st.session_state.productos_seleccionados) + len(st.session_state.marcas_seleccionadas)
    
    col_sup1, col_sup2 = st.columns([4, 6])
    with col_sup1:
        st.markdown("<h3 style='margin:0;'>Esquema comercial 2017</h3>", unsafe_allow_html=True)
    with col_sup2:
        col_b1, col_b2, col_b3, col_b4 = st.columns([3, 2.5, 1.5, 2])
        with col_b1:
            lbl_rep = f"📋 Ver Visita ({total_sel})" if total_sel > 0 else "📋 Ver Visita"
            if st.button(lbl_rep, use_container_width=True, type="primary" if total_sel > 0 else "secondary"):
                st.session_state.pantalla = "reporte_auditoria"
                st.rerun()
        with col_b2:
            if st.button("📊 Historial", use_container_width=True):
                st.session_state.pantalla = "historial"
                st.rerun()
        with col_b3:
            if st.button("⋮", use_container_width=True, help="Menú de Opciones / Alta de Clientes"):
                st.session_state.pantalla = "gestion_clientes"
                st.rerun()
        with col_b4:
            if st.button("← Salir", use_container_width=True):
                st.session_state.pantalla = "login"
                st.rerun()

    st.markdown("---")
    
    col_panel_filtros, col_panel_resultados = st.columns([3, 7])
    
    with col_panel_filtros:
        st.markdown("<div class='sombra-tenue'><h4 class='titulo-negro'>👤 Selección de Cliente</h4></div>", unsafe_allow_html=True)
        
        opciones_modo_cliente = ["Cliente Preexistente", "Cliente Nuevo", "Uso libre / Consulta"]
        idx_modo_cli = opciones_modo_cliente.index(st.session_state.tipo_cliente_seleccion) if st.session_state.tipo_cliente_seleccion in opciones_modo_cliente else 2
        
        tipo_cli_sel = st.radio(
            "Modo de atención:",
            options=opciones_modo_cliente,
            index=idx_modo_cli,
            key="radio_tipo_cliente"
        )
        
        if tipo_cli_sel != st.session_state.tipo_cliente_seleccion:
            st.session_state.tipo_cliente_seleccion = tipo_cli_sel

        df_dir_clientes = cargar_catalogo_clientes()

        if tipo_cli_sel == "Cliente Preexistente":
            if df_dir_clientes.empty:
                st.caption("⚠️ No hay clientes registrados en el directorio. Presiona **'⋮'** para dar de alta o usa 'Cliente Nuevo'.")
            else:
                dict_clientes = {}
                opciones_combo = ["-- Seleccionar --"]
                
                for _, row in df_dir_clientes.iterrows():
                    nom = str(row['Nombre Cliente']).strip()
                    num = str(row['Numero Cliente']).strip()
                    etiqueta_limpia = f"{nom} {num}".strip()
                    opciones_combo.append(etiqueta_limpia)
                    dict_clientes[etiqueta_limpia] = (nom, num)
                
                cli_seleccionado_str = st.selectbox("Selecciona el cliente:", options=opciones_combo)
                
                if cli_seleccionado_str != "-- Seleccionar --":
                    nom_sel, num_sel = dict_clientes[cli_seleccionado_str]
                    
                    if st.session_state.cliente_nombre != nom_sel or st.session_state.cliente_numero != num_sel:
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
            st.caption("ℹ️ Navegación libre sin asignación de cliente.")

        # BOTONES DE FINALIZACIÓN Y LIMPIEZA
        if total_sel > 0:
            st.markdown("---")
            if st.button("💾 Finalizar y Guardar Visita", use_container_width=True, type="primary"):
                exito = consolidar_y_guardar_visita_actual()
                if exito:
                    st.success("✅ ¡Visita guardada e historial actualizado con éxito!")
                limpiar_casillas_y_seleccion()
                st.session_state.cliente_nombre = ""
                st.session_state.cliente_numero = ""
                st.rerun()

            if st.button("🧹 Limpiar Casillas del Cliente", use_container_width=True):
                limpiar_casillas_y_seleccion()
                st.toast("🧹 Casillas y selecciones restablecidas.")
                st.rerun()

        st.markdown("---")

        st.markdown("<div class='sombra-tenue'><h4 class='titulo-negro'>Modo de Consulta</h4></div>", unsafe_allow_html=True)
        
        modo_seleccionado = st.radio(
            "Elige la vista deseada:",
            options=["🔎 Catálogo de Productos", "🏷️ Listado de Marcas"],
            index=0 if st.session_state.vista_catalogo == "productos" else 1,
            label_visibility="collapsed"
        )
        
        nuevo_modo = "productos" if "Productos" in modo_seleccionado else "marcas"
        if nuevo_modo != st.session_state.vista_catalogo:
            st.session_state.vista_catalogo = nuevo_modo
            st.rerun()

        st.markdown("---")

        if st.session_state.vista_catalogo == "productos":
            st.markdown("<div class='sombra-tenue'><h4 class='titulo-negro'>Segmentación por esquema</h4></div>", unsafe_allow_html=True)
            
            if columna_familia_real and df_productos is not None:
                opcion_default = "-- Selecciona una familia --"
                familias_unicas = sorted(df_productos[columna_familia_real].dropna().unique().tolist())
                lista_familias = [opcion_default] + familias_unicas
                
                idx_actual = lista_familias.index(st.session_state.filtro_familia) if st.session_state.filtro_familia in lista_familias else 0
                
                seleccion_actual = st.selectbox(
                    "Selecciona una familia:",
                    options=lista_familias,
                    index=idx_actual,
                    label_visibility="collapsed"
                )
                
                if seleccion_actual != st.session_state.filtro_familia:
                    st.session_state.filtro_familia = seleccion_actual
                    st.rerun()

            if st.session_state.filtro_familia != "-- Selecciona una familia --" or st.session_state.busqueda_rapida != "":
                if st.button("🔄 Limpiar todos los filtros", use_container_width=True):
                    st.session_state.filtro_familia = "-- Selecciona una familia --"
                    st.session_state.busqueda_rapida = ""
                    st.rerun()

    with col_panel_resultados:
        
        # MODO 1: PRODUCTOS
        if st.session_state.vista_catalogo == "productos":
            if df_productos is None:
                st.error("⚠️ Crítico: No se pudo leer el archivo 'productos.csv'.")
            else:
                total_catalogo = len(df_productos)
                df_filtrado = df_productos.copy()
                
                busqueda = st.text_input(
                    "🔤 Búsqueda rápida por palabra clave (Descripción / Código / Clave):", 
                    value=st.session_state.busqueda_rapida,
                    placeholder="Escribe para buscar en todo el catálogo (ej. desarmador, pinza...)"
                )

                if busqueda != st.session_state.busqueda_rapida:
                    st.session_state.busqueda_rapida = busqueda
                    st.rerun()

                familia_seleccionada = st.session_state.filtro_familia != "-- Selecciona una familia --"
                if familia_seleccionada and columna_familia_real:
                    df_filtrado = df_filtrado[df_filtrado[columna_familia_real] == st.session_state.filtro_familia]

                busqueda_activa = bool(st.session_state.busqueda_rapida.strip())
                if busqueda_activa:
                    condicion = pd.Series(False, index=df_filtrado.index)
                    for c in ["Descripcion de producto", columna_codigo_real, columna_clave_real]:
                        if c and c in df_filtrado.columns:
                            condicion = condicion | df_filtrado[c].astype(str).str.contains(st.session_state.busqueda_rapida, case=False, na=False)
                    df_filtrado = df_filtrado[condicion]

                if familia_seleccionada or busqueda_activa:
                    total_filas = len(df_filtrado)
                    
                    col_inf1, col_inf2, col_inf3 = st.columns(3)
                    with col_inf1:
                        fam_texto = st.session_state.filtro_familia if familia_seleccionada else "Todas"
                        st.markdown(f"<div class='sombra-tenue'><span style='color: #6B7280; font-size: 11px;'>Familia Activa</span><br><strong style='color: #000000; font-size: 14px;'>{fam_texto}</strong></div>", unsafe_allow_html=True)
                    with col_inf2:
                        st.markdown(f"<div class='sombra-tenue'><span style='color: #6B7280; font-size: 11px;'>Coincidencias</span><br><strong style='color: #2563EB; font-size: 14px;'>{total_filas} productos</strong></div>", unsafe_allow_html=True)
                    with col_inf3:
                        st.markdown(f"<div class='sombra-tenue'><span style='color: #6B7280; font-size: 11px;'>Total Catálogo</span><br><strong style='color: #000000; font-size: 14px;'>{total_catalogo} productos</strong></div>", unsafe_allow_html=True)
                    
                    with st.expander("👁️ Configurar columnas visibles en la tabla", expanded=False):
                        st.session_state.columnas_seleccionadas = st.multiselect(
                            "Añade o quita columnas del catálogo para mostrar:",
                            options=list(df_productos.columns),
                            default=st.session_state.columnas_seleccionadas
                        )

                    cols_disponibles = st.session_state.columnas_seleccionadas
                    
                    if total_filas > 0:
                        if len(cols_disponibles) > 0:
                            st.dataframe(df_filtrado[cols_disponibles], use_container_width=True, hide_index=True, height=300)
                            
                            texto_compartir = f"Esquema Comercial 2017 - Consulta rápida\n\n"
                            for index, fila in df_filtrado[cols_disponibles].head(3).iterrows():
                                datos = [f"{col}: {fila[col]}" for col in cols_disponibles]
                                texto_compartir += " | ".join(datos) + "\n"
                            st.text_area("📋 Copiar resumen para compartir:", value=texto_compartir, height=70)

                            st.markdown("---")
                            st.markdown("#### 📌 Marca los productos encontrados para tu reporte:")
                            
                            df_muestra = df_filtrado.head(30)
                            for idx, row in df_muestra.iterrows():
                                col_id_ref = columna_codigo_real if columna_codigo_real else df_muestra.columns[0]
                                prod_id = str(row[col_id_ref]) if pd.notnull(row[col_id_ref]) else f"PROD_{idx}"
                                
                                esta_marcado = prod_id in st.session_state.productos_seleccionados
                                ubic_actual = st.session_state.productos_seleccionados[prod_id]["ubicacion"] if esta_marcado else "Piso de Venta"

                                col_det, col_ubi, col_chk = st.columns([6, 3, 1])
                                
                                with col_det:
                                    desc_txt = row.get("Descripcion de producto", str(row.iloc[1] if len(row)>1 else ""))
                                    st.write(f"**{prod_id}** - {desc_txt}")
                                
                                with col_ubi:
                                    ubicacion_sel = st.selectbox("Ubicación", ["Piso de Venta", "Almacén", "Ambos"], index=["Piso de Venta", "Almacén", "Ambos"].index(ubic_actual), key=f"sel_ubic_{prod_id}_{idx}", label_visibility="collapsed")

                                with col_chk:
                                    marcado = st.checkbox("", value=esta_marcado, key=f"chk_p_{prod_id}_{idx}")

                                if marcado:
                                    st.session_state.productos_seleccionados[prod_id] = {"datos": row.to_dict(), "ubicacion": ubicacion_sel}
                                else:
                                    if prod_id in st.session_state.productos_seleccionados:
                                        del st.session_state.productos_seleccionados[prod_id]

                                st.markdown("<hr style='margin:2px 0; border:0; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
                        else:
                            st.warning("⚠️ Selecciona al menos una columna para mostrar.")
                    else:
                        st.warning("⚠️ No se encontraron productos.")
                else:
                    st.info("💡 **Para comenzar:** Escribe en la **Búsqueda rápida** o selecciona una **Familia** en la izquierda.")

        # MODO 2: MARCAS
        else:
            st.markdown("<h4 style='color: #000000;'>🏷️ Listado de Marcas</h4>", unsafe_allow_html=True)
            st.markdown("---")

            if df_marcas is None:
                st.warning("⚠️ No se encontró el archivo 'marcas.csv' o 'marcas.xlsx'.")
            else:
                col_nombre_marca = df_marcas.columns[0]
                
                for idx, row in df_marcas.iterrows():
                    nombre_marca = str(row[col_nombre_marca]).strip()
                    if not nombre_marca or nombre_marca.lower() == "nan":
                        continue

                    esta_sel_m = nombre_marca in st.session_state.marcas_seleccionadas
                    ubic_m_def = st.session_state.marcas_seleccionadas[nombre_marca]["ubicacion"] if esta_sel_m else "Piso de Venta"

                    col_nom, col_ubi, col_chk = st.columns([6, 3, 1])

                    with col_nom:
                        st.markdown(f"🏷️ **{nombre_marca}**")

                    with col_ubi:
                        ubicacion_m_sel = st.selectbox("Ubicación Marca", ["Piso de Venta", "Almacén", "Ambos"], index=["Piso de Venta", "Almacén", "Ambos"].index(ubic_m_def), key=f"sel_ubi_m_{nombre_marca}_{idx}", label_visibility="collapsed")

                    with col_chk:
                        marcado_m = st.checkbox("", value=esta_sel_m, key=f"chk_m_{nombre_marca}_{idx}")

                    if marcado_m:
                        st.session_state.marcas_seleccionadas[nombre_marca] = {"ubicacion": ubicacion_m_sel}
                    else:
                        if nombre_marca in st.session_state.marcas_seleccionadas:
                            del st.session_state.marcas_seleccionadas[nombre_marca]

                    st.markdown("<hr style='margin:2px 0; border:0; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

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
    nombres = ["marcas.csv", "Marcas.csv", "marcas.xlsx", "Marcas.xlsx"]
    for n in nombres:
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

def guardar_cliente_directorio(num_cliente, nombre_cliente):
    num = str(num_cliente).strip()
    nom = str(nombre_cliente).strip()
    if not num or not nom:
        return
    df_existente = cargar_catalogo_clientes()
    if not df_existente.empty:
        if not df_existente[(df_existente["Numero Cliente"].str.lower() == num.lower()) & (df_existente["Nombre Cliente"].str.lower() == nom.lower())].empty:
            return
    nuevo_df = pd.DataFrame([{"Numero Cliente": num, "Nombre Cliente": nom}])
    df_final = pd.concat([df_existente, nuevo_df], ignore_index=True)
    df_final.to_csv("clientes_directorio.csv", index=False, encoding='utf-8')

def consolidar_y_guardar_visita_actual():
    nombre_c = st.session_state.cliente_nombre if st.session_state.cliente_nombre else "Cliente General"
    num_c = st.session_state.cliente_numero if st.session_state.cliente_numero else "1001"
    
    filas = []
    fecha_std = datetime.date.today().strftime("%Y-%m-%d")
    fecha_hora_actual = datetime.datetime.now().strftime("%d/%m/%Y %I:%M %p")
    
    # 1. Guardar productos seleccionados
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

    # 2. Guardar marcas seleccionadas
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

    if filas:
        df_rep = pd.DataFrame(filas)
        guardar_en_historial_maestro(df_rep)
        if st.session_state.cliente_nombre and st.session_state.cliente_numero:
            guardar_cliente_directorio(st.session_state.cliente_numero, st.session_state.cliente_nombre)
        return True
    return False

df_productos = cargar_productos()
df_marcas = cargar_marcas()

# Normalización de columnas de productos
columna_familia_real = None
columna_codigo_real = None
if df_productos is not None:
    df_productos.columns = df_productos.columns.str.strip()
    for col in df_productos.columns:
        col_norm = normalizar_texto(col)
        if col_norm == "familia":
            columna_familia_real = col
        elif col_norm == "codigo":
            columna_codigo_real = col

    if "columnas_seleccionadas" not in st.session_state:
        st.session_state.columnas_seleccionadas = list(df_productos.columns[:3])

# ==========================================
# PANTALLA 1: LOGIN
# ==========================================
if st.session_state.pantalla == "login":
    st.markdown("<h2 style='text-align: center; color: #000;'>Visualizador de Catálogo & Auditoría</h2>", unsafe_allow_html=True)
    st.markdown("---")
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        usuario = st.text_input("Usuario", key="input_user")
        contrasena = st.text_input("Contraseña", type="password", key="input_pass")
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if usuario == "admin" and contrasena == "1234":
                st.session_state.pantalla = "resultados"
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

# ==========================================
# PANTALLA 2: REPORTE DE VISITA ACTUAL
# ==========================================
elif st.session_state.pantalla == "reporte_auditoria":
    col_n1, col_n2 = st.columns([7, 3])
    with col_n1:
        st.markdown("<h3 style='margin:0;'>📋 Reporte de Visita Actual</h3>", unsafe_allow_html=True)
    with col_n2:
        if st.button("← Volver a Búsqueda", use_container_width=True, type="primary"):
            st.session_state.pantalla = "resultados"
            st.rerun()

    st.markdown("---")
    total_elementos = len(st.session_state.productos_seleccionados) + len(st.session_state.marcas_seleccionadas)

    if total_elementos == 0:
        st.info("ℹ️ No hay productos ni marcas seleccionadas actualmente.")
    else:
        st.markdown(f"**Cliente:** `{st.session_state.cliente_nombre or 'General'}` | **Número:** `{st.session_state.cliente_numero or '1001'}`")
        
        if st.button("💾 Guardar y Finalizar Visita", use_container_width=True, type="primary"):
            if consolidar_y_guardar_visita_actual():
                st.success("✅ ¡Visita guardada en el historial con éxito!")
                limpiar_casillas_y_seleccion()
                st.session_state.pantalla = "historial"
                st.rerun()
            else:
                st.error("⚠️ Ocurrió un problema al guardar la visita.")

# ==========================================
# PANTALLA 3: HISTORIAL GENERAL (PUNTO 2)
# ==========================================
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
        st.markdown(f"**Total de Registros Encontrados:** `{len(df_historial)}` filas")
        st.dataframe(df_historial, use_container_width=True, hide_index=True)
        
        output_h = BytesIO()
        with pd.ExcelWriter(output_h, engine='openpyxl') as writer:
            df_historial.to_excel(writer, index=False, sheet_name='Historial')

        st.download_button(
            label="📥 Descargar Reporte Completo (Excel)",
            data=output_h.getvalue(),
            file_name=f"Reporte_Historial_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )

# ==========================================
# PANTALLA PRINCIPAL: BÚSQUEDA Y SELECCIÓN
# ==========================================
elif st.session_state.pantalla == "resultados":
    total_sel = len(st.session_state.productos_seleccionados) + len(st.session_state.marcas_seleccionadas)
    
    col_s1, col_s2 = st.columns([5, 5])
    with col_s1:
        st.markdown("<h3 style='margin:0;'>Esquema Comercial</h3>", unsafe_allow_html=True)
    with col_s2:
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button(f"📋 Ver Visita ({total_sel})", use_container_width=True, type="primary" if total_sel > 0 else "secondary"):
                st.session_state.pantalla = "reporte_auditoria"
                st.rerun()
        with col_b2:
            if st.button("📊 Historial", use_container_width=True):
                st.session_state.pantalla = "historial"
                st.rerun()

    st.markdown("---")
    col_panel_filtros, col_panel_resultados = st.columns([3, 7])
    
    with col_panel_filtros:
        st.markdown("#### 👤 Datos del Cliente")
        st.session_state.cliente_nombre = st.text_input("Nombre del Cliente:", value=st.session_state.cliente_nombre)
        st.session_state.cliente_numero = st.text_input("Número de Cliente:", value=st.session_state.cliente_numero)

        if total_sel > 0:
            st.markdown("---")
            if st.button("💾 Finalizar y Guardar Visita", use_container_width=True, type="primary"):
                if consolidar_y_guardar_visita_actual():
                    limpiar_casillas_y_seleccion()
                    st.success("✅ ¡Visita guardada exitosamente!")
                    st.session_state.pantalla = "historial"
                    st.rerun()

        st.markdown("---")
        modo_seleccionado = st.radio("Modo de Consulta:", options=["🔎 Catálogo de Productos", "🏷️ Listado de Marcas"])
        st.session_state.vista_catalogo = "productos" if "Productos" in modo_seleccionado else "marcas"

    with col_panel_resultados:
        if st.session_state.vista_catalogo == "productos":
            if df_productos is not None:
                busqueda = st.text_input("🔤 Búsqueda rápida:", value=st.session_state.busqueda_rapida)
                st.session_state.busqueda_rapida = busqueda

                df_filtrado = df_productos.copy()
                if busqueda.strip():
                    condicion = pd.Series(False, index=df_filtrado.index)
                    for c in df_filtrado.columns:
                        condicion = condicion | df_filtrado[c].astype(str).str.contains(busqueda, case=False, na=False)
                    df_filtrado = df_filtrado[condicion]

                v = st.session_state.version_reset
                for idx, row in df_filtrado.head(20).iterrows():
                    col_id = columna_codigo_real if columna_codigo_real else df_filtrado.columns[0]
                    prod_id = str(row[col_id])
                    
                    col_det, col_ubi, col_chk = st.columns([6, 3, 1])
                    with col_det:
                        st.write(f"**{prod_id}** - {row.iloc[1] if len(row)>1 else ''}")
                    with col_ubi:
                        u_sel = st.selectbox("Ubicación", ["Piso de Venta", "Almacén"], key=f"sel_u_{prod_id}_{v}", label_visibility="collapsed")
                    with col_chk:
                        chk = st.checkbox("", value=prod_id in st.session_state.productos_seleccionados, key=f"chk_p_{prod_id}_{v}")
                        
                        # Actualización directa e inmediata del diccionario al marcar/desmarcar
                        if chk:
                            st.session_state.productos_seleccionados[prod_id] = {"datos": row.to_dict(), "ubicacion": u_sel}
                        else:
                            st.session_state.productos_seleccionados.pop(prod_id, None)

        else:
            if df_marcas is not None:
                v = st.session_state.version_reset
                col_m = df_marcas.columns[0]
                for idx, row in df_marcas.iterrows():
                    nombre_marca = str(row[col_m]).strip()
                    if not nombre_marca or nombre_marca.lower() == "nan":
                        continue

                    col_nom, col_ubi, col_chk = st.columns([6, 3, 1])
                    with col_nom:
                        st.write(f"🏷️ **{nombre_marca}**")
                    with col_ubi:
                        u_m_sel = st.selectbox("Ubicación Marca", ["Piso de Venta", "Almacén"], key=f"sel_um_{idx}_{v}", label_visibility="collapsed")
                    with col_chk:
                        chk_m = st.checkbox("", value=nombre_marca in st.session_state.marcas_seleccionadas, key=f"chk_m_{idx}_{v}")
                        
                        if chk_m:
                            st.session_state.marcas_seleccionadas[nombre_marca] = {"ubicacion": u_m_sel}
                        else:
                            st.session_state.marcas_seleccionadas.pop(nombre_marca, None)
