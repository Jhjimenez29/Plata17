import pandas as pd
import streamlit as st
import unicodedata

# Configuración de la página en modo ancho para vista tipo catálogo/Excel
st.set_page_config(page_title="Catálogo App", page_icon="📱", layout="wide")

# Estilos CSS personalizados para sombreados tenues
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

# --- CONTROL DE PANTALLAS Y FILTROS (ESTADOS) ---
if "pantalla" not in st.session_state:
    st.session_state.pantalla = "login"
if "filtro_familia" not in st.session_state:
    st.session_state.filtro_familia = "-- Selecciona una familia --"
if "busqueda_rapida" not in st.session_state:
    st.session_state.busqueda_rapida = ""
if "busqueda_codigo_tmp" not in st.session_state:
    st.session_state.busqueda_codigo_tmp = ""
if "busqueda_clave_tmp" not in st.session_state:
    st.session_state.busqueda_clave_tmp = ""

# Función auxiliar para normalizar texto
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.strip().lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_csv("productos.csv", encoding="utf-8")
        return df
    except Exception:
        try:
            df = pd.read_csv("productos.csv", encoding="latin1")
            return df
        except Exception:
            return None

df_productos = cargar_datos()

# IDENTIFICACIÓN Y ESTANDARIZACIÓN BASE DE COLUMNAS
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

    # Definir columnas visibles predeterminadas si no existen en session_state
    if "columnas_seleccionadas" not in st.session_state:
        columnas_base = ["Numero de familia", "Descripcion de producto"]
        st.session_state.columnas_seleccionadas = [c for c in columnas_base if c in df_productos.columns]

# ==========================================
# PANTALLA 1: LOGIN
# ==========================================
if st.session_state.pantalla == "login":
    st.markdown("<h1 style='text-align: center;'>🖼️</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #000000;'>Visualizador de Catálogo</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6B7280;'>Filtra y consulta tus productos de forma rápida.</p>", unsafe_allow_html=True)
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
            elif usuario == "" or contrasena == "":
                st.warning("Por favor, llena todos los campos.")
            else:
                st.error("Usuario o contraseña incorrectos.")

# ==========================================
# PANTALLA 2: BÚSQUEDA MANUAL DIRECTA
# ==========================================
elif st.session_state.pantalla == "busqueda_manual":
    col_nav1, col_nav2 = st.columns([8, 2])
    with col_nav1:
        st.markdown("<h3 style='color: #000000; margin:0;'>Búsqueda Manual Directa</h3>", unsafe_allow_html=True)
    with col_nav2:
        if st.button("← Volver a Esquemas", use_container_width=True):
            st.session_state.pantalla = "resultados"
            st.rerun()
            
    st.markdown("---")
    
    st.markdown("🔎 **Introduce los criterios de búsqueda:**")
    
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        txt_codigo = st.text_input("Buscar por Código:", value=st.session_state.busqueda_codigo_tmp)
    with col_in2:
        txt_clave = st.text_input("Buscar por Clave:", value=st.session_state.busqueda_clave_tmp)
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("⚡ Aplicar Filtro", use_container_width=True, type="primary"):
            st.session_state.busqueda_codigo_tmp = txt_codigo
            st.session_state.busqueda_clave_tmp = txt_clave
            st.rerun()
    with col_btn2:
        if st.button("🧹 Limpiar Búsqueda", use_container_width=True):
            st.session_state.busqueda_codigo_tmp = ""
            st.session_state.busqueda_clave_tmp = ""
            st.rerun()

    st.markdown("---")

    if df_productos is None:
        st.error("⚠️ Crítico: No se pudo leer el archivo 'productos.csv'.")
    else:
        with st.expander("👁️ Configurar columnas visibles en la tabla", expanded=False):
            st.session_state.columnas_seleccionadas = st.multiselect(
                "Selecciona las columnas que deseas visualizar:",
                options=list(df_productos.columns),
                default=st.session_state.columnas_seleccionadas
            )

        df_manual = df_productos.copy()
        aplicó_filtro = False

        if st.session_state.busqueda_codigo_tmp:
            col_cod = columna_codigo_real if columna_codigo_real else df_manual.columns[0]
            df_manual = df_manual[df_manual[col_cod].astype(str).str.contains(st.session_state.busqueda_codigo_tmp, case=False, na=False)]
            aplicó_filtro = True
            
        if st.session_state.busqueda_clave_tmp:
            col_clav = columna_clave_real if columna_clave_real else df_manual.columns[0]
            df_manual = df_manual[df_manual[col_clav].astype(str).str.contains(st.session_state.busqueda_clave_tmp, case=False, na=False)]
            aplicó_filtro = True

        if aplicó_filtro:
            total_filas = len(df_manual)
            st.markdown(f"**Coincidencias encontradas:** `{total_filas}` productos")
            
            cols_disponibles = st.session_state.columnas_seleccionadas
            
            if total_filas > 0:
                if len(cols_disponibles) > 0:
                    st.dataframe(
                        df_manual[cols_disponibles], 
                        use_container_width=True, 
                        hide_index=True,
                        height=450
                    )
                else:
                    st.warning("⚠️ Selecciona al menos una columna en el selector de arriba para visualizar los datos.")
            else:
                st.warning("⚠️ No se encontraron productos que coincidan con la búsqueda.")
        else:
            st.info("Escribe un código o clave arriba y haz clic en **Aplicar Filtro** para visualizar los resultados aquí.")

# ==========================================
# PANTALLA PRINCIPAL: ESQUEMA COMERCIAL 2017
# ==========================================
elif st.session_state.pantalla == "resultados":
    
    # BARRA SUPERIOR
    col_sup_izq, col_sup_der = st.columns([7, 3])
    
    with col_sup_izq:
        st.markdown("<h3 style='color: #000000; font-weight: bold; margin:0;'>Esquema comercial 2017</h3>", unsafe_allow_html=True)

    with col_sup_der:
        if st.button("← Salir", use_container_width=True):
            st.session_state.pantalla = "login"
            st.rerun()
        
        if st.button("🔍 Búsqueda Manual Directa", use_container_width=True):
            st.session_state.pantalla = "busqueda_manual"
            st.rerun()

    st.markdown("---")
    
    if df_productos is None:
        st.error("⚠️ Crítico: No se pudo leer el archivo 'productos.csv'.")
    else:
        col_panel_filtros, col_panel_resultados = st.columns([3, 7])
        
        # COLUMNA IZQUIERDA: SEGMENTACIÓN POR ESQUEMA
        with col_panel_filtros:
            st.markdown(
                """
                <div class='sombra-tenue'>
                    <h4 class='titulo-negro'>Segmentación por esquema</h4>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            if columna_familia_real:
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
            else:
                st.error("Columna 'Familia' no detectada en el archivo CSV.")

            # Botón para reiniciar todos los filtros de este panel
            if st.session_state.filtro_familia != "-- Selecciona una familia --" or st.session_state.busqueda_rapida != "":
                if st.button("🔄 Limpiar todos los filtros", use_container_width=True):
                    st.session_state.filtro_familia = "-- Selecciona una familia --"
                    st.session_state.busqueda_rapida = ""
                    st.rerun()

        # COLUMNA DERECHA: RESULTADOS Y BUSCADOR GLOBAL
        with col_panel_resultados:
            total_catalogo = len(df_productos)
            df_filtrado = df_productos.copy()
            
            # 1. BUSCADOR GLOBAL RÁPIDO EN TODO EL ARCHIVO
            col_busq1, col_busq2 = st.columns([8, 2])
            with col_busq1:
                busqueda = st.text_input(
                    "🔤 Búsqueda rápida por palabra clave (Descripción / Código / Clave):", 
                    value=st.session_state.busqueda_rapida,
                    placeholder="Escribe para buscar en todo el catálogo (ej. desarmador, pinza...)"
                )
            with col_busq2:
                st.write("") # Espaciador para alinear botón
                if st.button("❌ Limpiar", use_container_width=True):
                    st.session_state.busqueda_rapida = ""
                    st.rerun()

            if busqueda != st.session_state.busqueda_rapida:
                st.session_state.busqueda_rapida = busqueda
                st.rerun()

            # Aplicar filtro de familia si seleccionó alguna
            familia_seleccionada = st.session_state.filtro_familia != "-- Selecciona una familia --"
            if familia_seleccionada and columna_familia_real:
                df_filtrado = df_filtrado[df_filtrado[columna_familia_real] == st.session_state.filtro_familia]

            # Aplicar filtro de palabra clave si escribió algo
            busqueda_activa = bool(st.session_state.busqueda_rapida.strip())
            if busqueda_activa:
                condicion = pd.Series(False, index=df_filtrado.index)
                for c in ["Descripcion de producto", columna_codigo_real, columna_clave_real]:
                    if c and c in df_filtrado.columns:
                        condicion = condicion | df_filtrado[c].astype(str).str.contains(st.session_state.busqueda_rapida, case=False, na=False)
                df_filtrado = df_filtrado[condicion]

            # EVALUAR SI DEBEMOS MOSTRAR RESULTADOS (Si hay búsqueda activa O familia seleccionada)
            if familia_seleccionada or busqueda_activa:
                total_filas = len(df_filtrado)
                
                # TARJETAS / MÉTRICAS
                col_inf1, col_inf2, col_inf3 = st.columns(3)
                with col_inf1:
                    fam_texto = st.session_state.filtro_familia if familia_seleccionada else "Todas"
                    st.markdown(
                        f"""
                        <div class='sombra-tenue'>
                            <span style='color: #6B7280; font-size: 11px;'>Familia Activa</span><br>
                            <strong style='color: #000000; font-size: 14px;'>{fam_texto}</strong>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                with col_inf2:
                    st.markdown(
                        f"""
                        <div class='sombra-tenue'>
                            <span style='color: #6B7280; font-size: 11px;'>Coincidencias</span><br>
                            <strong style='color: #2563EB; font-size: 14px;'>{total_filas} productos</strong>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                with col_inf3:
                    st.markdown(
                        f"""
                        <div class='sombra-tenue'>
                            <span style='color: #6B7280; font-size: 11px;'>Total Catálogo</span><br>
                            <strong style='color: #000000; font-size: 14px;'>{total_catalogo} productos</strong>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                # CONTROL DE COLUMNAS A MOSTRAR (SHOW/HIDE)
                with st.expander("👁️ Configurar columnas visibles en la tabla", expanded=False):
                    st.session_state.columnas_seleccionadas = st.multiselect(
                        "Añade o quita columnas del catálogo para mostrar:",
                        options=list(df_productos.columns),
                        default=st.session_state.columnas_seleccionadas
                    )

                cols_disponibles = st.session_state.columnas_seleccionadas
                
                if total_filas > 0:
                    if len(cols_disponibles) > 0:
                        st.dataframe(
                            df_filtrado[cols_disponibles], 
                            use_container_width=True, 
                            hide_index=True,
                            height=450
                        )
                        
                        texto_compartir = f"Esquema Comercial 2017 - Consulta rápida\n\n"
                        for index, fila in df_filtrado[cols_disponibles].head(3).iterrows():
                            datos = [f"{col}: {fila[col]}" for col in cols_disponibles]
                            texto_compartir += " | ".join(datos) + "\n"
                        st.text_area("📋 Copiar resumen para compartir:", value=texto_compartir, height=80)
                    else:
                        st.warning("⚠️ Selecciona al menos una columna para mostrar en el selector desplegable.")
                else:
                    st.warning("⚠️ No se encontraron productos con los criterios ingresados.")

            else:
                # PANTALLA INICIAL CUANDO NO HAY BÚSQUEDA NI FAMILIA SELECCIONADA
                st.info("💡 **Para comenzar:** Puedes escribir una palabra en la **Búsqueda rápida** de arriba para buscar en todo el catálogo, o seleccionar una **Familia** en el menú de la izquierda.")
