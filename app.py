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

CLAVE_SUPERVISOR = st.secrets.get("CLAVE_SUPERVISOR", "super123")

# --- CONTROL DE ESTADOS DE LA SESIÓN ---
if "pantalla" not in st.session_state:
    st.session_state.pantalla = "resultados"
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

# REGISTROS SELECCIONADOS EN LA VISITA (DICCIONARIOS DE SELECCIÓN)
if "productos_seleccionados" not in st.session_state:
    st.session_state.productos_seleccionados = {}  # {codigo_o_clave: {row_data, ubicacion}}
if "marcas_seleccionadas" not in st.session_state:
    st.session_state.marcas_seleccionadas = {}

def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.strip().lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto

def limpiar_casillas_y_seleccion():
    st.session_state.productos_seleccionados = {}
    st.session_state.marcas_seleccionadas = {}

@st.cache_data
def cargar_productos():
    for enc in ["utf-8", "latin1"]:
        try:
            df = pd.read_csv("productos.csv", encoding=enc)
            if df is not None:
                df.columns = df.columns.str.strip()
                return df
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
                        df.columns = df.columns.str.strip()
                        return df
                except Exception:
                    continue
        elif n.endswith(".xlsx"):
            try:
                df = pd.read_excel(n)
                if df is not None and not df.empty:
                    df.columns = df.columns.str.strip()
                    return df
            except Exception:
                continue
    return None

# Carga de catálogos
raw_prod = cargar_productos()
df_productos = raw_prod.copy() if raw_prod is not None else None

raw_marcas = cargar_marcas()
df_marcas = raw_marcas.copy() if raw_marcas is not None else None

columna_familia_real = None
if df_productos is not None:
    for col in df_productos.columns:
        if normalizar_texto(col) == "familia":
            columna_familia_real = col
            break

# ==========================================
# PANTALLA: REPORTE "PRODUCTOS EN PISO DE VENTA O ALMACÉN"
# ==========================================
if st.session_state.pantalla == "reporte_auditoria":
    col_nav1, col_nav2 = st.columns([7, 3])
    with col_nav1:
        st.markdown("<h3 style='color: #000000; margin:0;'>📋 Reporte: Productos en Piso de Venta o Almacén</h3>", unsafe_allow_html=True)
    with col_nav2:
        if st.button("← Volver al Catálogo", use_container_width=True, type="primary"):
            st.session_state.pantalla = "resultados"
            st.rerun()

    st.markdown("---")

    total_elementos = len(st.session_state.productos_seleccionados) + len(st.session_state.marcas_seleccionadas)

    if total_elementos == 0:
        st.info("ℹ️ Aún no has marcado ningún producto o marca en el catálogo.")
    else:
        st.markdown("#### 👤 Encabezado de la Auditoría")
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            nombre_cliente = st.text_input("Nombre del Cliente:", value=st.session_state.cliente_nombre if st.session_state.cliente_nombre else "Cliente General")
        with col_c2:
            num_cliente = st.text_input("Número de Cliente:", value=st.session_state.cliente_numero if st.session_state.cliente_numero else "S/N")
        with col_c3:
            fecha_rev = st.date_input("Fecha de Revisión:", datetime.date.today())
        with col_c4:
            esquema_rev = st.text_input("Esquema:", value="Esquema Comercial 2017")

        st.markdown("---")

        # Construcción del DataFrame consolidado conservando TODAS las columnas
        filas_consolidadas = []
        fecha_std = fecha_rev.strftime("%Y-%m-%d")

        for k, item_data in st.session_state.productos_seleccionados.items():
            registro = {
                "Nombre del Cliente": nombre_cliente,
                "Número de Cliente": num_cliente,
                "Fecha de Revisión": fecha_std,
                "Esquema": esquema_rev,
                "Ubicación": item_data["ubicacion"],
                "Tipo Registro": "PRODUCTO"
            }
            # Agregamos todas las columnas originales del producto
            registro.update(item_data["datos"])
            filas_consolidadas.append(registro)

        for k, item_data in st.session_state.marcas_seleccionadas.items():
            registro = {
                "Nombre del Cliente": nombre_cliente,
                "Número de Cliente": num_cliente,
                "Fecha de Revisión": fecha_std,
                "Esquema": esquema_rev,
                "Ubicación": item_data["ubicacion"],
                "Tipo Registro": "MARCA"
            }
            registro.update(item_data["datos"])
            filas_consolidadas.append(registro)

        df_reporte = pd.DataFrame(filas_consolidadas)

        st.markdown(f"**Total de ítems auditados:** `{len(df_reporte)}`")
        st.dataframe(df_reporte, use_container_width=True, hide_index=True, height=350)

        st.markdown("---")
        col_acc1, col_acc2, col_acc3 = st.columns(3)

        with col_acc1:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_reporte.to_excel(writer, index=False, sheet_name='Productos_Piso_Almacen')
            
            st.download_button(
                label="📥 Descargar Reporte (Excel)",
                data=output.getvalue(),
                file_name=f"Reporte_Piso_Almacen_{num_cliente}_{fecha_std}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )

        with col_acc2:
            if st.button("🧹 Limpiar Selección Actual", use_container_width=True):
                limpiar_casillas_y_seleccion()
                st.rerun()

# ==========================================
# PANTALLA PRINCIPAL: BÚSQUEDA Y SELECCIÓN
# ==========================================
elif st.session_state.pantalla == "resultados":
    
    total_sel = len(st.session_state.productos_seleccionados) + len(st.session_state.marcas_seleccionadas)
    
    col_sup1, col_sup2 = st.columns([5, 5])
    with col_sup1:
        st.markdown("<h3 style='margin:0;'>Esquema comercial 2017</h3>", unsafe_allow_html=True)
    with col_sup2:
        lbl_rep = f"📋 Ver Reporte Auditoría ({total_sel})" if total_sel > 0 else "📋 Ver Reporte Auditoría"
        if st.button(lbl_rep, use_container_width=True, type="primary" if total_sel > 0 else "secondary"):
            st.session_state.pantalla = "reporte_auditoria"
            st.rerun()

    st.markdown("---")
    
    col_panel_filtros, col_panel_resultados = st.columns([3, 7])
    
    with col_panel_filtros:
        st.markdown("<div class='sombra-tenue'><h4 class='titulo-negro'>👤 Selección de Cliente</h4></div>", unsafe_allow_html=True)
        
        tipo_cli_sel = st.radio(
            "Modo de atención:",
            options=["Cliente Preexistente", "Cliente Nuevo", "Uso libre / Consulta"],
            key="radio_tipo_cliente"
        )
        
        if tipo_cli_sel == "Cliente Nuevo":
            st.session_state.cliente_nombre = st.text_input("Nombre del Cliente:", value=st.session_state.cliente_nombre)
            st.session_state.cliente_numero = st.text_input("Número de Cliente:", value=st.session_state.cliente_numero)
        elif tipo_cli_sel == "Uso libre / Consulta":
            st.session_state.cliente_nombre = ""
            st.session_state.cliente_numero = ""

        # Selector global de Ubicación predeterminada para marcar
        st.markdown("<div class='sombra-tenue'><h4 class='titulo-negro'>📍 Ubicación del Marcado</h4></div>", unsafe_allow_html=True)
        ubicacion_actual = st.radio("Marcar ítems como encontrados en:", ["Piso de Venta", "Almacén"], horizontal=True)

        st.markdown("---")
        modo_seleccionado = st.radio(
            "Vista:",
            options=["🔎 Catálogo de Productos", "🏷️ Listado de Marcas"],
            index=0 if st.session_state.vista_catalogo == "productos" else 1
        )
        st.session_state.vista_catalogo = "productos" if "Productos" in modo_seleccionado else "marcas"

        if st.session_state.vista_catalogo == "productos" and columna_familia_real:
            st.markdown("<div class='sombra-tenue'><h4 class='titulo-negro'>Segmentación por esquema</h4></div>", unsafe_allow_html=True)
            opcion_default = "-- Selecciona una familia --"
            familias = [opcion_default] + sorted(df_productos[columna_familia_real].dropna().unique().tolist())
            idx_act = familias.index(st.session_state.filtro_familia) if st.session_state.filtro_familia in familias else 0
            
            sel_fam = st.selectbox("Familia:", options=familias, index=idx_act)
            if sel_fam != st.session_state.filtro_familia:
                st.session_state.filtro_familia = sel_fam
                st.rerun()

    with col_panel_resultados:
        
        # MODO 1: PRODUCTOS
        if st.session_state.vista_catalogo == "productos":
            if df_productos is None:
                st.error("⚠️ No se pudo cargar el archivo 'productos.csv'.")
            else:
                df_filtrado = df_productos.copy()
                
                busqueda = st.text_input(
                    "🔤 Búsqueda rápida:", 
                    key="busqueda_rapida",
                    placeholder="Escribe para buscar..."
                )

                familia_seleccionada = (st.session_state.filtro_familia != "-- Selecciona una familia --")
                busqueda_activa = bool(busqueda.strip())

                if not familia_seleccionada and not busqueda_activa:
                    st.info("💡 **Vista limpia:** Selecciona una **familia** o escribe en el buscador para ver productos y marcar la ubicación.")
                else:
                    if columna_familia_real and familia_seleccionada:
                        df_filtrado = df_filtrado[df_filtrado[columna_familia_real] == st.session_state.filtro_familia]

                    if busqueda_activa:
                        busq_norm = normalizar_texto(busqueda)
                        df_filtrado = df_filtrado[df_filtrado.apply(lambda r: any(busq_norm in normalizar_texto(str(c)) for c in r), axis=1)]

                    # Incorporamos columna interactiva de marcado (Marcar)
                    # Colocamos una clave única como identificador (por ejemplo, primer columna o Código)
                    col_id = df_filtrado.columns[0]
                    
                    df_editor = df_filtrado.copy()
                    df_editor.insert(0, "Marcar", df_editor[col_id].apply(lambda x: str(x) in st.session_state.productos_seleccionados))

                    cols_defecto = ["Marcar"]
                    if "Descripcion de producto" in df_editor.columns: cols_defecto.append("Descripcion de producto")
                    if "Numero de familia" in df_editor.columns: cols_defecto.append("Numero de familia")
                    if columna_familia_real: cols_defecto.append(columna_familia_real)

                    st.markdown(f"**Productos encontrados:** `{len(df_filtrado)}` | **Marcados en esta vista:** `{sum(df_editor['Marcar'])}`")
                    
                    # Interfaz de edición interactiva (Checkbox)
                    edited_df = st.data_editor(
                        df_editor,
                        column_order=cols_defecto,
                        column_config={
                            "Marcar": st.column_config.CheckboxColumn("Marcar", default=False)
                        },
                        disabled=[c for c in df_editor.columns if c != "Marcar"],
                        use_container_width=True,
                        hide_index=True,
                        height=450,
                        key="editor_productos"
                    )

                    # Sincronización con session_state al marcar/desmarcar
                    for idx, row in edited_df.iterrows():
                        key_item = str(row[col_id])
                        is_checked = row["Marcar"]
                        
                        if is_checked:
                            row_dict = row.drop("Marcar").to_dict()
                            st.session_state.productos_seleccionados[key_item] = {
                                "datos": row_dict,
                                "ubicacion": ubicacion_actual
                            }
                        else:
                            st.session_state.productos_seleccionados.pop(key_item, None)
