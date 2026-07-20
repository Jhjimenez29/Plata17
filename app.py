import pandas as pd
import streamlit as st
import unicodedata

# Configuración de la página optimizada para visualización tipo catálogo
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

# --- CARGA DE DATOS (VERSIÓN CSV ULTRA RÁPIDA) ---
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

    # Contenedor centrado para el login de escritorio/móvil
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        usuario = st.text_input("Usuario", placeholder="Introduce tu usuario", key="input_user")
        contrasena = st.text_input("Contraseña", type="password", placeholder="Introduce tu contraseña", key="input_pass")
        st.write("")
        
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if usuario == "admin" and contrasena == "1234":
                st.session_state.pantalla = "filtros"
                st.slots = {}
                st.rerun()
            elif usuario == "" or contrasena == "":
                st.warning("Por favor, llena todos los campos.")
            else:
                st.error("Usuario o contraseña incorrectos.")

    st.markdown("<br><br><br><hr>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #9CA3AF; font-size: 12px;'>Versión 1.1.0 | Panel de Navegación Mejorado</p>", unsafe_allow_html=True)

# ==========================================
# PANTALLA 2 Y 3 COMBINADAS: NAVEGADOR PROFESIONAL
# ==========================================
elif st.session_state.pantalla in ["filtros", "resultados"]:
    
    # Barra Superior de Control
    col_sup1, col_sup2 = st.columns([2, 8])
    with col_sup1:
        if st.button("⬅️ Salir (Login)", use_container_width=True):
            st.session_state.pantalla = "login"
            st.rerun()
    with col_sup2:
        st.markdown("<h3 style='margin:0; color: #1E3A8A;'>Explorador de Esquemas e Inventario</h3>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    if df_productos is None:
        st.error("⚠️ Crítico: No se pudo leer el archivo 'productos.csv'.")
    else:
        # CREACIÓN DEL DISEÑO DE DOS COLUMNAS (Panel izquierdo: Filtros/Resultados | Panel derecho: Segmentación Vertical)
        col_izquierda, col_derecha = st.columns([7, 3])
        
        # ----------------------------------------------------
        # COLUMNA DERECHA: SELECCIÓN VERTICAL DE FAMILIAS
        # ----------------------------------------------------
        with col_derecha:
            st.markdown("#### 📁 Familias Esquema")
            
            if columna_familia_real:
                lista_familias = ["Todas"] + sorted(df_productos[columna_familia_real].dropna().unique().tolist())
                
                # Renderizado vertical estilizado de las familias mediante botones de opción continuos
                # Simulando el menú táctil gris de tu ejemplo de Excel
                seleccion_actual = st.radio(
                    "Selecciona una familia para filtrar:",
                    options=lista_familias,
                    index=lista_familias.index(st.session_state.filtro_familia),
                    label_visibility="collapsed"
                )
                
                # Si el usuario hace clic en una opción de la lista vertical, actualiza el filtro en tiempo real
                if seleccion_actual != st.session_state.filtro_familia:
                    st.session_state.filtro_familia = seleccion_actual
                    st.session_state.pagina_actual = 0
                    st.session_state.pantalla = "resultados"
                    st.rerun()
            else:
                st.error("No se encontró la columna 'Familia'")

        # ----------------------------------------------------
        # COLUMNA IZQUIERDA: BÚSQUEDA MANUAL Y TARJETAS EN VERTICAL
        # ----------------------------------------------------
        with col_izquierda:
            # Inputs rápidos de búsqueda manual superiores
            st.markdown("🔎 **Búsqueda por texto directo:**")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                busqueda_codigo = st.text_input("Código:", value=st.session_state.get("filtro_codigo", ""))
            with col_b2:
                busqueda_clave = st.text_input("Clave:", value=st.session_state.get("filtro_clave", ""))
                
            # Configuración Ocultable de Columnas visibles
            with st.expander("⚙️ Configuración de Columnas Visibles"):
                todas_columnas = df_productos.columns.tolist()
                columnas_defecto = todas_columnas[:6]
                columnas_elegidas = st.multiselect(
                    "Columnas a mostrar en los resultados:", 
                    options=todas_columnas, 
                    default=st.session_state.columnas_visibles if st.session_state.columnas_visibles else columnas_defecto
                )
                st.session_state.columnas_visibles = columnas_elegidas

            # Botón para procesar filtros de texto escritos
            if st.button("⚡ Aplicar Búsqueda Manual", use_container_width=True, type="primary"):
                st.session_state.filtro_codigo = busqueda_codigo
                st.session_state.filtro_clave = busqueda_clave
                st.session_state.pagina_actual = 0
                st.session_state.pantalla = "resultados"
                st.rerun()
                
            st.markdown("---")
            
            # --- PROCESAMIENTO Y PRESENTACIÓN VERTICAL DE RESULTADOS ---
            df_filtrado = df_productos.copy()
            
            # 1. Filtro por Selección Vertical de Familia
            if st.session_state.filtro_familia != "Todas" and columna_familia_real:
                df_filtrado = df_filtrado[df_filtrado[columna_familia_real] == st.session_state.filtro_familia]
                
            # 2. Filtro por campo de Código
            if st.session_state.get("filtro_codigo"):
                col_cod = columna_codigo_real if columna_codigo_real else df_filtrado.columns[0]
                df_filtrado = df_filtrado[df_filtrado[col_cod].astype(str).str.contains(st.session_state.filtro_codigo, case=False, na=False)]
                
            # 3. Filtro por campo de Clave
            if st.session_state.get("filtro_clave"):
                col_clav = columna_clave_real if columna_clave_real else df_filtrado.columns[0]
                df_filtrado = df_filtrado[df_filtrado[col_clav].astype(str).str.contains(st.session_state.filtro_clave, case=False, na=False)]

            total_filas = len(df_filtrado)
            st.subheader(f"📦 Productos de la familia: {st.session_state.filtro_familia}")
            st.caption(f"Se encontraron {total_filas} registros coincidentes.")
            
            if total_filas > 0:
                cols_a_mostrar = st.session_state.columnas_visibles
                
                # Paginador compacto
                filas_por_pagina = 20
                if "pagina_actual" not in st.session_state:
                    st.session_state.pagina_actual = 0
                max_paginas = max(1, (total_filas - 1) // filas_por_pagina + 1)
                
                col_ant, col_pag, col_sig = st.columns([1, 2, 1])
                with col_ant:
                    if st.button("◀️ Ant") and st.session_state.pagina_actual > 0:
                        st.session_state.pagina_actual -= 1
                        st.rerun()
                with col_pag:
                    st.write(f"<p style='text-align: center; font-weight: bold;'>Página {st.session_state.pagina_actual + 1} de {max_paginas}</p>", unsafe_allow_html=True)
                with col_sig:
                    if st.button("Sig ▶️") and st.session_state.pagina_actual < max_paginas - 1:
                        st.session_state.pagina_actual += 1
                        st.rerun()
                
                inicio = st.session_state.pagina_actual * filas_por_pagina
                fin = inicio + filas_por_pagina
                df_pagina = df_filtrado[cols_a_mostrar].iloc[inicio:fin]
                
                # Muestra los resultados en formato puramente vertical e individual
                for index, fila in df_pagina.iterrows():
                    with st.container():
                        # Caja de diseño vertical optimizada
                        st.markdown(
                            f"""
                            <div style='background-color: #F8FAFC; padding: 14px; border-radius: 8px; 
                                        margin-bottom: 12px; border-left: 5px solid #10B981; 
                                        box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>
                            """, 
                            unsafe_allow_html=True
                        )
                        # Imprime los campos uno abajo del otro de forma vertical
                        for col in cols_a_mostrar:
                            st.markdown(f"🔹 **{col}:** {fila[col]}")
                        st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Caja de texto listo para compartir en WhatsApp
                texto_compartir = f"Resultados del Catálogo - Familia: {st.session_state.filtro_familia}\n\n"
                for index, fila in df_pagina.head(5).iterrows():
                    datos_fila = [f"{c}: {fila[c]}" for c in cols_a_mostrar[:3]]
                    texto_compartir += "\n".join(datos_fila) + "\n" + "─"*20 + "\n"
                    
                st.text_area("📋 Copiar datos estructurados en vertical para WhatsApp:", value=texto_compartir, height=130)
            else:
                st.warning("⚠️ Selecciona una familia a la derecha o ajusta los criterios de búsqueda manual para desplegar productos.")