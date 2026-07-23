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

# ACUMULADORES PERSISTENTES DE AUDITORÍA
if "productos_seleccionados" not in st.session_state:
    st.session_state.productos_seleccionados = {}  # {codigo_id: dict_datos_completos}
if "marcas_seleccionadas" not in st.session_state:
    st.session_state.marcas_seleccionadas = {}     # {marca_id: dict_datos_completos}

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

def guardar_en_historial_maestro(df_nuevas_filas):
    archivo_historial = "historial_revisiones.csv"
    if os.path.exists(archivo_historial):
        df_nuevas_filas.to_csv(archivo_historial, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        df_nuevas_filas.to_csv(archivo_historial, mode='w', header=True, index=False, encoding='utf-8-sig')

def cargar_historial_maestro():
    archivo_historial = "historial_revisiones.csv"
    if os.path.exists(archivo_historial):
        try:
            return pd.read_csv(archivo_historial, encoding='utf-8-sig')
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

# Carga de datos
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
# PANTALLA: REPORTE DE LA VISITA ACTUAL
# ==========================================
if st.session_state.pantalla == "reporte_auditoria":
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
        st.info("ℹ️ Aún no has marcado productos ni marcas durante el recorrido.")
    else:
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
        fecha_std = fecha_rev.strftime("%Y-%m-%d")

        # Integrar productos seleccionados conservando sus columnas
        for k, v in st.session_state.productos_seleccionados.items():
            item = {
                "Fecha": fecha_std,
                "Numero Cliente": num_cliente,
                "Nombre Cliente": nombre_cliente,
                "Esquema": esquema_rev,
                "Tipo Registro": "PRODUCTO"
            }
            item.update(v)
            filas_consolidadas.append(item)

        # Integrar marcas seleccionadas conservando sus columnas
        for k, v in st.session_state.marcas_seleccionadas.items():
            item = {
                "Fecha": fecha_std,
                "Numero Cliente": num_cliente,
                "Nombre Cliente": nombre_cliente,
                "Esquema": esquema_rev,
                "Tipo Registro": "MARCA"
            }
            item.update(v)
            filas_consolidadas.append(item)

        df_reporte_actual = pd.DataFrame(filas_consolidadas)
        st.markdown(f"**Total de ítems registrados en el recorrido:** `{len(df_reporte_actual)}`")
        st.dataframe(df_reporte_actual, use_container_width=True, hide_index=True, height=350)

        st.markdown("---")
        col_acc1, col_acc2, col_acc3 = st.columns(3)

        with col_acc1:
            if st.button("💾 Guardar y Finalizar Visita", use_container_width=True, type="primary"):
                guardar_en_historial_maestro(df_reporte_actual)
                limpiar_casillas_y_seleccion()
                st.session_state.cliente_nombre = ""
                st.session_state.cliente_numero = ""
                st.success("✅ ¡Visita guardada en el historial exitosamente!")
                st.session_state.pantalla = "resultados"
                st.rerun()

        with col_acc2:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_reporte_actual.to_excel(writer, index=False, sheet_name='Visita_Actual')

            st.download_button(
                label="📥 Descargar Reporte (Excel)",
                data=output.getvalue(),
                file_name=f"Visita_{num_cliente}_{fecha_std}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with col_acc3:
            if st.button("🗑️ Descartar Selección", use_container_width=True):
                limpiar_casillas_y_seleccion()
                st.rerun()

# ==========================================
# PANTALLA: HISTORIAL DE REVISIONES
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
            clientes_unicos = [opcion_default] + sorted(df_historial["Nombre Cliente"].dropna().astype(str).unique().tolist())
            cliente_sel = st.selectbox("Filtrar por Cliente:", options=clientes_unicos)

        with col_f2:
            fechas_unicas = [opcion_default] + sorted(df_historial["Fecha"].dropna().astype(str).unique().tolist(), reverse=True)
            fecha_sel = st.selectbox("Filtrar por Fecha:", options=fechas_unicas)

        df_h_filtrado = df_historial.copy()
        if cliente_sel != opcion_default:
            df_h_filtrado = df_h_filtrado[df_h_filtrado["Nombre Cliente"].astype(str) == cliente_sel]
        if fecha_sel != opcion_default:
            df_h_filtrado = df_h_filtrado[df_h_filtrado["Fecha"].astype(str) == fecha_sel]

        st.markdown(f"**Registros encontrados:** `{len(df_h_filtrado)}` filas")
        st.dataframe(df_h_filtrado, use_container_width=True, hide_index=True, height=350)

        output_h = BytesIO()
        with pd.ExcelWriter(output_h, engine='openpyxl') as writer:
            df_h_filtrado.to_excel(writer, index=False, sheet_name='Historial')

        st.download_button(
            label="📥 Descargar Consulta Histórica (Excel)",
            data=output_h.getvalue(),
            file_name=f"Historial_Consulta_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )

# ==========================================
# PANTALLA PRINCIPAL: BÚSQUEDA Y SELECCIÓN
# ==========================================
elif st.session_state.pantalla == "resultados":

    total_sel = len(st.session_state.productos_seleccionados) + len(st.session_state.marcas_seleccionadas)

    col_sup1, col_sup2 = st.columns([5, 5])
    with col_sup1:
        st.markdown("<h3 style='margin:0;'>Esquema comercial 2017</h3>", unsafe_allow_html=True)
    with col_sup2:
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            lbl_rep = f"📋 Ver Visita ({total_sel})" if total_sel > 0 else "📋 Ver Visita"
            if st.button(lbl_rep, use_container_width=True, type="primary" if total_sel > 0 else "secondary"):
                st.session_state.pantalla = "reporte_auditoria"
                st.rerun()
        with col_b2:
            if st.button("📊 Historial", use_container_width=True):
                st.session_state.pantalla = "historial"
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

        st.markdown("---")
        st.markdown("<div class='sombra-tenue'><h4 class='titulo-negro'>Modo de Consulta</h4></div>", unsafe_allow_html=True)

        modo_seleccionado = st.radio(
            "Selecciona qué deseas revisar:",
            options=["🔎 Catálogo de Productos", "🏷️ Listado de Marcas"],
            index=0 if st.session_state.vista_catalogo == "productos" else 1
        )

        nuevo_modo = "productos" if "Productos" in modo_seleccionado else "marcas"
        if nuevo_modo != st.session_state.vista_catalogo:
            st.session_state.vista_catalogo = nuevo_modo
            st.rerun()

        st.markdown("---")

        if st.session_state.vista_catalogo == "productos" and columna_familia_real:
            st.markdown("<div class='sombra-tenue'><h4 class='titulo-negro'>Segmentación por esquema</h4></div>", unsafe_allow_html=True)
            opcion_default = "-- Selecciona una familia --"
            familias = [opcion_default] + sorted(df_productos[columna_familia_real].dropna().unique().tolist())
            idx_act = familias.index(st.session_state.filtro_familia) if st.session_state.filtro_familia in familias else 0

            sel_fam = st.selectbox("Familia:", options=familias, index=idx_act)
            if sel_fam != st.session_state.filtro_familia:
                st.session_state.filtro_familia = sel_fam
                st.rerun()

            if st.session_state.filtro_familia != "-- Selecciona una familia --" or st.session_state.busqueda_rapida != "":
                if st.button("🔄 Limpiar filtros", use_container_width=True):
                    st.session_state.filtro_familia = "-- Selecciona una familia --"
                    st.session_state.busqueda_rapida = ""
                    st.rerun()

    with col_panel_resultados:

        # MODO 1: PRODUCTOS
        if st.session_state.vista_catalogo == "productos":
            if df_productos is None:
                st.error("⚠️ Crítico: No se pudo leer el archivo 'productos.csv'.")
            else:
                df_filtrado = df_productos.copy()

                busqueda = st.text_input(
                    "🔤 Búsqueda rápida por palabra clave:",
                    key="busqueda_rapida",
                    placeholder="Escribe para buscar..."
                )

                familia_seleccionada = (st.session_state.filtro_familia != "-- Selecciona una familia --")
                busqueda_activa = bool(busqueda.strip())

                if not familia_seleccionada and not busqueda_activa:
                    st.info("💡 **Vista limpia:** Selecciona una **familia** o escribe en el buscador para ver productos y seleccionarlos.")
                else:
                    if columna_familia_real and familia_seleccionada:
                        df_filtrado = df_filtrado[df_filtrado[columna_familia_real] == st.session_state.filtro_familia]

                    if busqueda_activa:
                        busq_norm = normalizar_texto(busqueda)
                        df_filtrado = df_filtrado[df_filtrado.apply(lambda r: any(busq_norm in normalizar_texto(str(c)) for c in r), axis=1)]

                    # Identificador único de fila (usando primera columna / código)
                    col_id = df_filtrado.columns[0]

                    # Insertar casilla de selección "Seleccionar"
                    df_editor = df_filtrado.copy()
                    df_editor.insert(0, "Seleccionar", df_editor[col_id].apply(lambda x: str(x) in st.session_state.productos_seleccionados))

                    # Definir visualización predeterminada (3 columnas + casilla)
                    cols_defecto = ["Seleccionar"]
                    if "Descripcion de producto" in df_editor.columns: cols_defecto.append("Descripcion de producto")
                    if "Numero de familia" in df_editor.columns: cols_defecto.append("Numero de familia")
                    if columna_familia_real and columna_familia_real in df_editor.columns: cols_defecto.append(columna_familia_real)

                    st.markdown(f"**Productos encontrados:** `{len(df_filtrado)}` | **Seleccionados acumulados:** `{len(st.session_state.productos_seleccionados)}`")

                    edited_df = st.data_editor(
                        df_editor,
                        column_order=cols_defecto,
                        column_config={
                            "Seleccionar": st.column_config.CheckboxColumn("Seleccionar", default=False)
                        },
                        disabled=[c for c in df_editor.columns if c != "Seleccionar"],
                        use_container_width=True,
                        hide_index=True,
                        height=450,
                        key=f"editor_prod_{st.session_state.filtro_familia}_{busqueda}"
                    )

                    # Guardar automáticamente la selección en la sesión
                    for idx, row in edited_df.iterrows():
                        key_item = str(row[col_id])
                        if row["Seleccionar"]:
                            st.session_state.productos_seleccionados[key_item] = row.drop("Seleccionar").to_dict()
                        else:
                            st.session_state.productos_seleccionados.pop(key_item, None)

        # MODO 2: MARCAS
        else:
            if df_marcas is None:
                st.error("⚠️ Crítico: No se pudo leer el archivo de marcas.")
            else:
                df_editor_m = df_marcas.copy()
                col_id_m = df_editor_m.columns[0]

                df_editor_m.insert(0, "Seleccionar", df_editor_m[col_id_m].apply(lambda x: str(x) in st.session_state.marcas_seleccionadas))

                st.markdown(f"**Marcas/Exhibidores registrados:** `{len(df_marcas)}` | **Marcas acumuladas:** `{len(st.session_state.marcas_seleccionadas)}`")

                edited_df_m = st.data_editor(
                    df_editor_m,
                    column_config={
                        "Seleccionar": st.column_config.CheckboxColumn("Seleccionar", default=False)
                    },
                    disabled=[c for c in df_editor_m.columns if c != "Seleccionar"],
                    use_container_width=True,
                    hide_index=True,
                    height=450,
                    key="editor_marcas"
                )

                # Guardar automáticamente la selección de marcas en la sesión
                for idx, row in edited_df_m.iterrows():
                    key_item_m = str(row[col_id_m])
                    if row["Seleccionar"]:
                        st.session_state.marcas_seleccionadas[key_item_m] = row.drop("Seleccionar").to_dict()
                    else:
                        st.session_state.marcas_seleccionadas.pop(key_item_m, None)
