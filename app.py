import pandas as pd
import streamlit as st
import unicodedata

# Configuración de la página en modo ancho para simular la experiencia de Excel
st.set_page_config(page_title="Catálogo App", page_icon="📱", layout="wide")

# --- CONTROL DE PANTALLAS Y FILTROS (ESTADOS) ---
if "pantalla" not in st.session_state:
    st.session_state.pantalla = "login"
if "columnas_visibles" not in st.session_state:
    st.session_state.columnas_visibles = []
if "filtro_familia" not in st.session_state:
    st.session_state.filtro_familia = "Todas"

# Función auxiliar para normalizar texto (quita acentos y espacios extra)
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
    except Exception as e:
        try:
            df = pd.read_csv("productos.csv", encoding="latin1")
            return df
        except Exception as e2:
            return None

df_productos = cargar_datos()

# Mapeo inteligente de columnas
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

# ==========================================
# PANTALLA 1: LOGIN
# ==========================================
if st.session_state.pantalla == "login":
    st.markdown("<h1 style='text-align: center;'>🖼️</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>Visualizador de Catálogo</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6B7280;'>Filtra y consulta tus 15,000 productos de forma rápida.</p>", unsafe_allow_html=True)
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
# NAVEGADOR AVANZADO (PANTALLA PRINCIPAL)
# ==========================================
elif st.session_state.pantalla == "resultados":
    
    # Barra Superior de Control
    col_sup1, col_sup2 = st.columns([2, 8])
    with col_sup1:
        if st.button("Exit ⬅️", use_container_width=True):
            st.session_state.pantalla = "login"
            st.rerun()
    with col_sup2:
        st.markdown("<h3 style='margin:0; color: #1E3A8A; font-weight: bold;'>Plataforma Corporativa de Inventario</h3>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    if df_productos is None:
        st.error("⚠️ Crítico: No se pudo leer el archivo 'productos.csv'.")
    else:
        # CAMBIO 2: Inversión de columnas para Celular Primero (Tope) / PC (Izquierda)
        # Reservamos el primer bloque para el panel de selección/búsqueda
        col_panel_filtros, col_panel_resultados = st.columns([3, 7])
        
        # ----------------------------------------------------
        # COLUMNA FILTROS: LO PRIMERO EN CELULAR / IZQUIERDA EN PC
        # ----------------------------------------------------
        with col_panel_filtros:
            st.markdown("#### 📁 Segmentación por Esquema")
            
            if columna_familia_real:
                lista_familias = ["Todas"] + sorted(df_productos[columna_familia_real].dropna().unique().tolist())
                
                # CAMBIO 1: Buscador predictivo combinado con opción deslizable/scrolleable de familias
                # Reducimos drásticamente el espacio vertical usando un st.selectbox nativo optimizado
                # que en iPhone abre el selector táctil nativo y en PC permite buscar escribiendo.
                seleccion_actual = st.selectbox(
                    "Filtrar por nombre de familia:",
                    options=lista_familias,
                    index=lista_familias.index(st.session_state.filtro_familia),
                    help="Escribe el nombre o desliza para seleccionar"
                )
                
                if seleccion_actual != st.session_state.filtro_familia:
                    st.session_state.filtro_familia = seleccion_actual
                    st.session_state.pagina_actual = 0
                    st.rerun()
            else:
                st.error("Columna 'Familia' no detectada.")

            st.markdown("---")
            st.markdown("🔎 **Búsqueda Manual Directa:**")
            busqueda_codigo = st.text_input("Por Código:", value=st.session_state.get("filtro_codigo", ""))
            busqueda_clave = st.text_input("Por Clave:", value=st.session_state.get("filtro_clave", ""))
            
            if st.button("⚡ Aplicar Código/Clave", use_container_width=True, type="primary"):
                st.session_state.filtro_codigo = busqueda_codigo
                st.session_state.filtro_clave = busqueda_clave
                st.session_state.pagina_actual = 0
                st.rerun()

        # ----------------------------------------------------
        # COLUMNA RESULTADOS: ABAJO EN CELULAR / DERECHA EN PC
        # ----------------------------------------------------
        with col_panel_resultados:
            # Filtrado de Datos
            df_filtrado = df_productos.copy()
            
            if st.session_state.filtro_familia != "Todas" and columna_familia_real:
                df_filtrado = df_filtrado[df_filtrado[columna_familia_real] == st.session_state.filtro_familia]
                
            if st.session_state.get("filtro_codigo"):
                col_cod = columna_codigo_real if columna_codigo_real else df_filtrado.columns[0]
                df_filtrado = df_filtrado[df_filtrado[col_cod].astype(str).str.contains(st.session_state.filtro_codigo, case=False, na=False)]
                
            if st.session_state.get("filtro_clave"):
                col_clav = columna_clave_real if columna_clave_real else df_filtrado.columns[0]
                df_filtrado = df_filtrado[df_filtrado[col_clav].astype(str).str.contains(st.session_state.filtro_clave, case=False, na=False)]

            total_filas = len(df_filtrado)
            st.markdown(f"##### 📦 Familia activa: `{st.session_state.filtro_familia}` | Coincidencias: **{total_filas}**")
            
            if total_filas > 0:
                # Configuración automática de columnas para evitar saturación visual en la vista horizontal
                todas_cols = df_filtrado.columns.tolist()
                cols_vista_excel = todas_cols[:7] # Mostramos las columnas principales en modo tabla
                
                # Paginación compacta
                filas_por_pagina = 30
                if "pagina_actual" not in st.session_state:
                    st.session_state.pagina_actual = 0
                max_paginas = max(1, (total_filas - 1) // filas_por_pagina + 1)
                
                col_ant, col_pag, col_sig = st.columns([1, 2, 1])
                with col_ant:
                    if st.button("◀️ Ant") and st.session_state.pagina_actual > 0:
                        st.session_state.pagina_actual -= 1
                        st.rerun()
                with col_pag:
                    st.write(f"<p style='text-align: center; font-size:13px;'>Pág. {st.session_state.pagina_actual + 1} de {max_paginas}</p>", unsafe_allow_html=True)
                with col_sig:
                    if st.button("Sig ▶️") and st.session_state.pagina_actual < max_paginas - 1:
                        st.session_state.pagina_actual += 1
                        st.rerun()
                
                inicio = st.session_state.pagina_actual * filas_por_pagina
                fin = inicio + filas_por_pagina
                df_pagina = df_filtrado[cols_vista_excel].iloc[inicio:fin]
                
                # CAMBIO 3: Despliegue de resultados en formato horizontal estilo hoja de cálculo de Excel
                # st.dataframe renderiza una tabla nativa e interactiva con scroll horizontal y vertical,
                # permitiendo seleccionar celdas y ajustar anchos igual que en un Excel corporativo.
                st.dataframe(
                    df_pagina, 
                    use_container_width=True, 
                    hide_index=True
                )
                
                st.markdown("---")
                
                # Caja compacta de copiado para WhatsApp
                texto_compartir = f"Catálogo Express - Familia: {st.session_state.filtro_familia}\n\n"
                for index, fila in df_pagina.head(3).iterrows():
                    texto_compartir += f"▪️ {cols_vista_excel[0]}: {fila[cols_vista_excel[0]]} | {cols_vista_excel[1]}: {fila[cols_vista_excel[1]]} | {cols_vista_excel[2]}: {fila[cols_vista_excel[2]]}\n"
                st.text_area("📋 Formato rápido para WhatsApp:", value=texto_compartir, height=90)
                
            else:
                st.warning("⚠️ Sin resultados. Cambia de familia o limpia las búsquedas manuales.")