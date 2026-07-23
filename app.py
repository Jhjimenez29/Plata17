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
ARCHIVO_HISTORIAL = "historial_revisiones.csv"
COLUMNAS_HISTORIAL = ["Fecha", "Fecha_Hora", "Numero Cliente", "Nombre Cliente", "Esquema", "Tipo Registro", "Identificador / Código", "Descripción / Detalle", "Ubicación"]

# --- CONTROL DE ESTADOS DE LA SESIÓN ---
if "pantalla" not in st.session_state:
    st.session_state.pantalla = "login"
if "vista_catalogo" not in st.session_state:
    st.session_state.vista_catalogo = "productos"
if "filtro_familia" not in st.session_state:
    st.session_state.filtro_familia = "-- Selecciona una familia --"
if "busqueda_rapida" not in st.session_state:
    st.session_state.busqueda_rapida = ""
if "version_reset" not in st.session_state:
    st.session_state.version_reset = 0

# CONFIGURACIÓN DEL CLIENTE ACTUAL
if "tipo_cliente_seleccion" not in st.session_state:
    st.session_state.tipo_cliente_seleccion = "Uso libre / Consulta"
if "cliente_nombre" not in st.session_state:
    st.session_state.cliente_nombre = ""
if "cliente_numero" not in st.session_state:
    st.session_state.cliente_numero = ""

# SELECCIONES TEMPORALES
if "productos_seleccionados" not in st.session_state:
    st.session_state.productos_seleccionados = {}
if "marcas_seleccionadas" not in st.session_state:
    st.session_state.marcas_seleccionadas = {}

def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def limpiar_casillas_y_seleccion():
    """Limpia la memoria de selección para la siguiente visita"""
    for key in list(st.session_state.keys()):
        if key.startswith("chk_") or key.startswith("sel_"):
            del st.session_state[key]
            
    st.session_state.productos_seleccionados = {}
    st.session_state.marcas_seleccionadas = {}
    st.session_state.version_reset += 1

# --- FUNCIONES DE HISTORIAL Y DATOS ---
def cargar_historial_maestro():
    if os.path.exists(ARCHIVO_HISTORIAL):
        try:
            df = pd.read_csv(ARCHIVO_HISTORIAL, encoding='utf-8', dtype=str)
            if not df.empty:
                return df
        except Exception:
            pass
    return pd.DataFrame(columns=COLUMNAS_HISTORIAL)

def guardar_en_historial_maestro(df_nuevas_filas):
    if df_nuevas_filas.empty:
        return False
    header = not os.path.exists(ARCHIVO_HISTORIAL)
    df_nuevas_filas.to_csv(ARCHIVO_HISTORIAL, mode='a', header=header, index=False, encoding='utf-8')
    return True

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
