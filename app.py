from io import BytesIO
import datetime
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
    </style>
""", unsafe_allow_html=True)

# --- CONTROL DE ESTADOS DE LA SESIÓN ---
if "pantalla" not in st.session_state:
    st.session_state.pantalla = "login"
if "vista_catalogo" not in st.session_state:
    st.session_state.vista_catalogo = "productos"  # 'productos' o 'marcas'
if "filtro_familia" not in st.session_state:
    st.session_state.filtro_familia = "-- Todas las familias --"
if "busqueda_rapida" not in st.session_state:
    st.session_state.busqueda_rapida = ""
if "busqueda_marca_rapida" not in st.session_state:
    st.session_state.busqueda_marca_rapida = ""

# REGISTROS SELECCIONADOS (PRODUCTOS Y MARCAS SE GUARDAN AQUÍ)
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

# --- CARGA DE ARCHIVOS ---
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
    for enc in ["utf-8", "latin1"]:
        try:
            return pd.read_csv("marcas.csv", encoding=enc)
        except Exception:
            continue
    return None

df_productos = cargar_productos()
df_marcas = cargar_marcas()

# PROCESAMIENTO COLUMNAS PRODUCTOS
columna_familia_real = None
columna_codigo_real = None
columna_clave_real = None

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

    if "columnas_seleccionadas" not in st.session_state:
        st.session_state.columnas_seleccionadas = list(df_productos.columns[:3])

# ==========================================
# PANTALLA 1: LOGIN
# ==========================================
if st.session_state.pantalla == "login":
    st.markdown("<h1 style='text-align: center;'>🖼️</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>Visualizador de Catálogo & Auditoría</h2>", unsafe_allow_html=True)
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
                st.error("Credenciales incorrectas.")

# ==========================================
# PANTALLA 2: REPORTE INTEGRADO (PRODUCTOS + MARCAS)
# ==========================================
elif st.session_state.pantalla == "reporte_auditoria":
    col_nav1, col_nav2 = st.columns([7, 3])
    with col_nav1:
        st.markdown("<h3 style='margin:0;'>📋 Reporte de Levantamiento en Campo</h3>", unsafe_allow_html=True)
    with col_nav2:
        if st.button("← Volver a Búsqueda", use_container_width=True, type="primary"):
            st.session_state.pantalla = "resultados"
            st.rerun()

    st.markdown("---")

    total_elementos = len(st.session_state.productos_seleccionados) + len(st.session_state.marcas_seleccionadas)

    if total_elementos == 0:
        st.info("ℹ️ No has seleccionado productos ni marcas aún.")
    else:
        st.markdown("#### 👤 Datos de Encabezado")
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            nombre_cliente = st.text_input("Nombre del Cliente:", value="Cliente General")
        with col_c2:
            num_cliente = st.text_input("Número de Cliente:", value="1001")
        with col_c3:
            fecha_rev = st.date_input("Fecha de Revisión:", datetime.date.today())
        with col_c4:
            esquema_rev = st.text_input("Esquema:", value="Esquema Comercial 2017")

        st.markdown("---")

        filas_consolidadas = []

        # 1. Agregar Productos
        for k, v in st.session_state.productos_seleccionados.items():
            item = {
                "Tipo": "PRODUCTO",
                "Identificador / Nombre": k,
                "Detalle / Descripción": v["datos"].get("Descripcion de producto", str(v["datos"])),
                "Ubicación": v["ubicacion"],
                "Cliente": nombre_cliente,
                "Num Cliente": num_cliente,
                "Fecha": fecha_rev.strftime("%d/%m/%Y"),
                "Esquema": esquema_rev
            }
            filas_consolidadas.append(item)

        # 2. Agregar Marcas
        for k, v in st.session_state.marcas_seleccionadas.items():
            item = {
                "Tipo": "MARCA / EXHIBIDOR",
                "Identificador / Nombre": k,
                "Detalle / Descripción": f"Marca: {k}",
                "Ubicación": v["ubicacion"],
                "Cliente": nombre_cliente,
                "Num Cliente": num_cliente,
                "Fecha": fecha_rev.strftime("%d/%m/%Y"),
                "Esquema": esquema_rev
            }
            filas_consolidadas.append(item)

        df_reporte = pd.DataFrame(filas_consolidadas)
        st.dataframe(df_reporte, use_container_width=True, hide_index=True)

        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_reporte.to_excel(writer, index=False, sheet_name='Auditoria_Campo')
            
            st.download_button(
                label="📥 Descargar Reporte Completo (Excel)",
                data=output.getvalue(),
                file_name=f"Reporte_Campo_{num_cliente}_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
        with col_ex2:
            if st.button("🗑️ Vaciar Todas las Selecciones", use_container_width=True):
                st.session_state.productos_seleccionados = {}
                st.session_state.marcas_seleccionadas = {}
                st.rerun()

# ==========================================
# PANTALLA PRINCIPAL: NAVEGACIÓN Y SELECCIÓN
# ==========================================
elif st.session_state.pantalla == "resultados":
    
    total_sel = len(st.session_state.productos_seleccionados) + len(st.session_state.marcas_seleccionadas)
    
    col_sup1, col_sup2 = st.columns([6, 4])
    with col_sup1:
        st.markdown("<h3 style='margin:0;'>Esquema Comercial & Auditoría</h3>", unsafe_allow_html=True)
    with col_sup2:
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            lbl_rep = f"📋 Ver Reporte ({total_sel})" if total_sel > 0 else "📋 Ver Reporte"
            if st.button(lbl_rep, use_container_width=True, type="primary" if total_sel > 0 else "secondary"):
                st.session_state.pantalla = "reporte_auditoria"
                st.rerun()
        with col_b2:
            if st.button("← Salir", use_container_width=True):
                st.session_state.pantalla = "login"
                st.rerun()

    st.markdown("---")

    # PANEL IZQUIERDO: SWITCHER DE VISTA Y FILTROS
    col_pan_izq, col_pan_der = st.columns([3, 7])

    with col_pan_izq:
        st.markdown("<div class='sombra-tenue'><b>Modo de Consulta</b></div>", unsafe_allow_html=True)
        
        # Conmutador entre consultar Productos o Marcas
        modo = st.radio(
            "Selecciona qué deseas consultar/marcar:",
            options=["🔎 Catálogo de Productos", "🏷️ Listado de Marcas"],
            index=0 if st.session_state.vista_catalogo == "productos" else 1
        )
        
        nuevo_modo = "productos" if "Productos" in modo else "marcas"
        if nuevo_modo != st.session_state.vista_catalogo:
            st.session_state.vista_catalogo = nuevo_modo
            st.rerun()

        st.markdown("---")

        if st.session_state.vista_catalogo == "productos":
            st.markdown("<b>Filtros de Productos</b>", unsafe_allow_html=True)
            if columna_familia_real and df_productos is not None:
                fams = ["-- Todas las familias --"] + sorted(df_productos[columna_familia_real].dropna().unique().tolist())
                idx_fam = fams.index(st.session_state.filtro_familia) if st.session_state.filtro_familia in fams else 0
                sel_fam = st.selectbox("Familia:", options=fams, index=idx_fam)
                if sel_fam != st.session_state.filtro_familia:
                    st.session_state.filtro_familia = sel_fam
                    st.rerun()

    # PANEL DERECHO: VISTA Y SELECCIÓN ACTIVA
    with col_pan_der:
        
        # -------------------------------------------------------------
        # VISTA 1: CATÁLOGO DE PRODUCTOS
        # -------------------------------------------------------------
        if st.session_state.vista_catalogo == "productos":
            st.markdown("#### 📦 Consulta y Marca de Productos")
            
            busq = st.text_input("🔤 Búsqueda rápida de productos:", value=st.session_state.busqueda_rapida, placeholder="Buscar por código, clave o descripción...")
            if busq != st.session_state.busqueda_rapida:
                st.session_state.busqueda_rapida = busq
                st.rerun()

            if df_productos is not None:
                df_f = df_productos.copy()
                
                # Filtrar Familia
                if st.session_state.filtro_familia != "-- Todas las familias --" and columna_familia_real:
                    df_f = df_f[df_f[columna_familia_real] == st.session_state.filtro_familia]
                
                # Filtrar Texto
                if st.session_state.busqueda_rapida.strip():
                    cond = pd.Series(False, index=df_f.index)
                    for col_t in df_f.columns:
                        cond = cond | df_f[col_t].astype(str).str.contains(st.session_state.busqueda_rapida, case=False, na=False)
                    df_f = df_f[cond]

                if st.session_state.filtro_familia != "-- Todas las familias --" or st.session_state.busqueda_rapida.strip():
                    df_muestra = df_f.head(30)
                    st.caption(f"Mostrando {len(df_muestra)} de {len(df_f)} coincidencias")
                    
                    for idx, row in df_muestra.iterrows():
                        prod_id = str(row[columna_codigo_real]) if columna_codigo_real and pd.notnull(row[columna_codigo_real]) else f"PROD_{idx}"
                        esta_sel = prod_id in st.session_state.productos_seleccionados
                        ubic_def = st.session_state.productos_seleccionados[prod_id]["ubicacion"] if esta_sel else "Piso de Venta"

                        c_chk, c_txt, c_ubi = st.columns([1, 6, 3])
                        with c_chk:
                            chk = st.checkbox("", value=esta_sel, key=f"chk_p_{prod_id}_{idx}")
                        with c_txt:
                            desc = row.get("Descripcion de producto", str(row.iloc[0]))
                            st.write(f"**{prod_id}** - {desc}")
                        with c_ubi:
                            ubi = st.selectbox("Ubicación", ["Piso de Venta", "Almacén", "Ambos"], index=["Piso de Venta", "Almacén", "Ambos"].index(ubic_def), key=f"ubi_p_{prod_id}_{idx}", label_visibility="collapsed")

                        if chk:
                            st.session_state.productos_seleccionados[prod_id] = {"datos": row.to_dict(), "ubicacion": ubi}
                        elif prod_id in st.session_state.productos_seleccionados:
                            del st.session_state.productos_seleccionados[prod_id]

                        st.markdown("<hr style='margin:2px 0; border-top:1px solid #EEE;'>", unsafe_allow_html=True)
                else:
                    st.info("💡 Utiliza el filtro de **Familia** a la izquierda o escribe en la **Búsqueda rápida** para ver productos.")

        # -------------------------------------------------------------
        # VISTA 2: LISTADO INDEPENDIENTE DE MARCAS
        # -------------------------------------------------------------
        else:
            st.markdown("#### 🏷️ Listado de Marcas (~50 Marcas)")
            
            busq_m = st.text_input("🔍 Buscar marca:", value=st.session_state.busqueda_marca_rapida, placeholder="Escribe el nombre de la marca...")
            if busq_m != st.session_state.busqueda_marca_rapida:
                st.session_state.busqueda_marca_rapida = busq_m
                st.rerun()

            if df_marcas is None:
                st.warning("⚠️ No se encontró el archivo 'marcas.csv'. Por favor agrégalo a la raíz del proyecto con la lista de marcas.")
            else:
                col_marca_nombre = df_marcas.columns[0]
                df_m_filtrado = df_marcas.copy()

                if st.session_state.busqueda_marca_rapida.strip():
                    df_m_filtrado = df_m_filtrado[df_m_filtrado[col_marca_nombre].astype(str).str.contains(st.session_state.busqueda_marca_rapida, case=False, na=False)]

                st.caption(f"Total de marcas encontradas: {len(df_m_filtrado)}")

                for idx, row in df_m_filtrado.iterrows():
                    nombre_marca = str(row[col_marca_nombre]).strip()
                    esta_sel_m = nombre_marca in st.session_state.marcas_seleccionadas
                    ubic_m_def = st.session_state.marcas_seleccionadas[nombre_marca]["ubicacion"] if esta_sel_m else "Piso de Venta"

                    c_chk, c_txt, c_ubi = st.columns([1, 6, 3])
                    with c_chk:
                        chk_m = st.checkbox("", value=esta_sel_m, key=f"chk_m_{nombre_marca}_{idx}")
                    with c_txt:
                        st.markdown(f"🏷️ **{nombre_marca}**")
                    with c_ubi:
                        ubi_m = st.selectbox("Ubicación", ["Piso de Venta", "Almacén", "Ambos"], index=["Piso de Venta", "Almacén", "Ambos"].index(ubic_m_def), key=f"ubi_m_{nombre_marca}_{idx}", label_visibility="collapsed")

                    if chk_m:
                        st.session_state.marcas_seleccionadas[nombre_marca] = {"ubicacion": ubi_m}
                    elif nombre_marca in st.session_state.marcas_seleccionadas:
                        del st.session_state.marcas_seleccionadas[nombre_marca]

                    st.markdown("<hr style='margin:2px 0; border-top:1px solid #EEE;'>", unsafe_allow_html=True)
