from io import BytesIO
import datetime
import pandas as pd
import streamlit as st
import unicodedata

# Configuración de la página en modo ancho
st.set_page_config(page_title="Catálogo & Auditoría", page_icon="📱", layout="wide")

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

# --- CONTROL DE ESTADOS DE LA SESIÓN ---
if "pantalla" not in st.session_state:
    st.session_state.pantalla = "login"
if "vista_catalogo" not in st.session_state:
    st.session_state.vista_catalogo = "productos"  # 'productos' o 'marcas'
if "filtro_familia" not in st.session_state:
    st.session_state.filtro_familia = "-- Selecciona una familia --"
if "busqueda_rapida" not in st.session_state:
    st.session_state.busqueda_rapida = ""

# REGISTROS SELECCIONADOS (PRODUCTOS Y MARCAS)
if "productos_seleccionados" not in st.session_state:
    st.session_state.productos_seleccionados = {}
if "marcas_seleccionadas" not in st.session_state:
    st.session_state.marcas_seleccionadas = {}

# Función auxiliar para normalizar texto
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.strip().lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto

# --- CARGA DE DATOS ---
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
    # Intenta leer diferentes variaciones de nombre y formato (CSV o Excel)
    nombres_posibles = ["marcas.csv", "Marcas.csv", "marcas.xlsx", "Marcas.xlsx"]
    
    for nombre in nombres_posibles:
        # Intento de lectura si es CSV
        if nombre.endswith(".csv"):
            for enc in ["utf-8", "latin1"]:
                try:
                    df = pd.read_csv(nombre, encoding=enc)
                    if df is not None and not df.empty:
                        return df
                except Exception:
                    continue
        # Intento de lectura si es Excel
        elif nombre.endswith(".xlsx"):
            try:
                df = pd.read_excel(nombre)
                if df is not None and not df.empty:
                    return df
            except Exception:
                continue
    return None

df_productos = cargar_productos()
df_marcas = cargar_marcas()

# IDENTIFICACIÓN Y ESTANDARIZACIÓN BASE DE COLUMNAS DE PRODUCTOS
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
    st.markdown("<p style='text-align: center; color: #6B7280;'>Filtra, consulta y realiza levantamientos en piso de venta.</p>", unsafe_allow_html=True)
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
# PANTALLA 2: REPORTE DE AUDITORÍA INTEGRADO
# ==========================================
elif st.session_state.pantalla == "reporte_auditoria":
    col_nav1, col_nav2 = st.columns([7, 3])
    with col_nav1:
        st.markdown("<h3 style='color: #000000; margin:0;'>📋 Reporte: Productos y Marcas en Piso de Venta / Almacén</h3>", unsafe_allow_html=True)
    with col_nav2:
        if st.button("← Volver a Búsqueda", use_container_width=True, type="primary"):
            st.session_state.pantalla = "resultados"
            st.rerun()

    st.markdown("---")

    total_elementos = len(st.session_state.productos_seleccionados) + len(st.session_state.marcas_seleccionadas)

    if total_elementos == 0:
        st.info("ℹ️ Aún no has seleccionado productos ni marcas. Regresa al catálogo para realizar tu levantamiento.")
    else:
        st.markdown("#### 👤 Datos de Encabezado de la Revisión")
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

        # 1. Agregar Productos Seleccionados
        for k, v in st.session_state.productos_seleccionados.items():
            item = {
                "Tipo Registro": "PRODUCTO",
                "Identificador / Código": k,
                "Descripción / Detalle": v["datos"].get("Descripcion de producto", str(v["datos"])),
                "Ubicación Encontrada": v["ubicacion"],
                "Nombre del Cliente": nombre_cliente,
                "Numero de Cliente": num_cliente,
                "Fecha de Revision": fecha_rev.strftime("%d/%m/%Y"),
                "Esquema": esquema_rev
            }
            filas_consolidadas.append(item)

        # 2. Agregar Marcas Seleccionadas
        for k, v in st.session_state.marcas_seleccionadas.items():
            item = {
                "Tipo Registro": "MARCA",
                "Identificador / Código": k,
                "Descripción / Detalle": f"Exhibidor / Marca: {k}",
                "Ubicación Encontrada": v["ubicacion"],
                "Nombre del Cliente": nombre_cliente,
                "Numero de Cliente": num_cliente,
                "Fecha de Revision": fecha_rev.strftime("%d/%m/%Y"),
                "Esquema": esquema_rev
            }
            filas_consolidadas.append(item)

        df_reporte = pd.DataFrame(filas_consolidadas)
        st.dataframe(df_reporte, use_container_width=True, hide_index=True, height=350)

        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_reporte.to_excel(writer, index=False, sheet_name='Reporte_Levantamiento')
            
            st.download_button(
                label="📥 Descargar Reporte Completo (Excel)",
                data=output.getvalue(),
                file_name=f"Reporte_PisoVenta_{num_cliente}_{datetime.date.today()}.xlsx",
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
# PANTALLA PRINCIPAL: ESQUEMA COMERCIAL
# ==========================================
elif st.session_state.pantalla == "resultados":
    
    total_sel = len(st.session_state.productos_seleccionados) + len(st.session_state.marcas_seleccionadas)
    
    # BARRA SUPERIOR
    col_sup_izq, col_sup_der = st.columns([6, 4])
    
    with col_sup_izq:
        st.markdown("<h3 style='color: #000000; font-weight: bold; margin:0;'>Esquema comercial 2017</h3>", unsafe_allow_html=True)

    with col_sup_der:
        btn_reporte = f"📋 Ver Reporte ({total_sel})" if total_sel > 0 else "📋 Ver Reporte Auditoría"
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button(btn_reporte, use_container_width=True, type="secondary" if total_sel == 0 else "primary"):
                st.session_state.pantalla = "reporte_auditoria"
                st.rerun()
        with col_b2:
            if st.button("← Salir", use_container_width=True):
                st.session_state.pantalla = "login"
                st.rerun()

    st.markdown("---")
    
    col_panel_filtros, col_panel_resultados = st.columns([3, 7])
    
    # PANEL IZQUIERDO: SELECCIÓN DE MODO Y FILTRO DE FAMILIA
    with col_panel_filtros:
        st.markdown(
            """
            <div class='sombra-tenue'>
                <h4 class='titulo-negro'>Modo de Consulta</h4>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
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
            st.markdown(
                """
                <div class='sombra-tenue'>
                    <h4 class='titulo-negro'>Segmentación por esquema</h4>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
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

    # PANEL DERECHO: CONTENIDO SEGÚN MODO SELECCIONADO
    with col_panel_resultados:
        
        # =============================================================
        # MODO 1: CATÁLOGO DE PRODUCTOS (ESTRUCTURA EXACTA ANTERIOR)
        # =============================================================
        if st.session_state.vista_catalogo == "productos":
            
            if df_productos is None:
                st.error("⚠️ Crítico: No se pudo leer el archivo 'productos.csv'.")
            else:
                total_catalogo = len(df_productos)
                df_filtrado = df_productos.copy()
                
                # BUSCADOR GLOBAL RÁPIDO
                busqueda = st.text_input(
                    "🔤 Búsqueda rápida por palabra clave (Descripción / Código / Clave):", 
                    value=st.session_state.busqueda_rapida,
                    placeholder="Escribe para buscar en todo el catálogo (ej. desarmador, pinza...)"
                )

                if busqueda != st.session_state.busqueda_rapida:
                    st.session_state.busqueda_rapida = busqueda
                    st.rerun()

                # FILTRADO
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

                # MOSTRAR RESULTADOS
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
                    
                    # CONFIGURADOR DE COLUMNAS
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
                                height=300
                            )
                            
                            # RESUMEN PARA COMPARTIR
                            texto_compartir = f"Esquema Comercial 2017 - Consulta rápida\n\n"
                            for index, fila in df_filtrado[cols_disponibles].head(3).iterrows():
                                datos = [f"{col}: {fila[col]}" for col in cols_disponibles]
                                texto_compartir += " | ".join(datos) + "\n"
                            st.text_area("📋 Copiar resumen para compartir:", value=texto_compartir, height=70)

                            # SECCIÓN INTERACTIVA DE SELECCIÓN PARA AUDITORÍA
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
                                    ubicacion_sel = st.selectbox(
                                        "Ubicación",
                                        options=["Piso de Venta", "Almacén", "Ambos"],
                                        index=["Piso de Venta", "Almacén", "Ambos"].index(ubic_actual),
                                        key=f"sel_ubic_{prod_id}_{idx}",
                                        label_visibility="collapsed"
                                    )

                                with col_chk:
                                    marcado = st.checkbox("", value=esta_marcado, key=f"chk_p_{prod_id}_{idx}")

                                if marcado:
                                    st.session_state.productos_seleccionados[prod_id] = {
                                        "datos": row.to_dict(),
                                        "ubicacion": ubicacion_sel
                                    }
                                else:
                                    if prod_id in st.session_state.productos_seleccionados:
                                        del st.session_state.productos_seleccionados[prod_id]

                                st.markdown("<hr style='margin:2px 0; border:0; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
                        else:
                            st.warning("⚠️ Selecciona al menos una columna para mostrar en el selector desplegable.")
                    else:
                        st.warning("⚠️ No se encontraron productos con los criterios ingresados.")

                else:
                    st.info("💡 **Para comenzar:** Puedes escribir una palabra en la **Búsqueda rápida** de arriba para buscar en todo el catálogo, o seleccionar una **Familia** en el menú de la izquierda.")

        # =============================================================
        # MODO 2: LISTADO DE MARCAS (TODAS VISIBLES + CASILLA A LA DERECHA)
        # =============================================================
        else:
            st.markdown("<h4 style='color: #000000;'>🏷️ Listado de Marcas</h4>", unsafe_allow_html=True)
            st.markdown("<p style='color: #6B7280; font-size: 13px;'>Marca las firmas encontradas durante tu recorrido para agregarlas al reporte.</p>", unsafe_allow_html=True)
            st.markdown("---")

            if df_marcas is None:
                st.warning("⚠️ No se encontró el archivo 'marcas.csv'. Asegúrate de agregarlo a la raíz de GitHub.")
            else:
                col_nombre_marca = df_marcas.columns[0]
                
                # MOSTRAR TODAS LAS MARCAS DEL LISTADO SIN BUSCADOR
                for idx, row in df_marcas.iterrows():
                    nombre_marca = str(row[col_nombre_marca]).strip()
                    if not nombre_marca or nombre_marca.lower() == "nan":
                        continue

                    esta_sel_m = nombre_marca in st.session_state.marcas_seleccionadas
                    ubic_m_def = st.session_state.marcas_seleccionadas[nombre_marca]["ubicacion"] if esta_sel_m else "Piso de Venta"

                    # Estructura: Nombre Marca (Izq) | Ubicación (Centro) | Casilla de Selección (A la Derecha)
                    col_nom, col_ubi, col_chk = st.columns([6, 3, 1])

                    with col_nom:
                        st.markdown(f"🏷️ **{nombre_marca}**")

                    with col_ubi:
                        ubicacion_m_sel = st.selectbox(
                            "Ubicación Marca",
                            options=["Piso de Venta", "Almacén", "Ambos"],
                            index=["Piso de Venta", "Almacén", "Ambos"].index(ubic_m_def),
                            key=f"sel_ubi_m_{nombre_marca}_{idx}",
                            label_visibility="collapsed"
                        )

                    with col_chk:
                        marcado_m = st.checkbox("", value=esta_sel_m, key=f"chk_m_{nombre_marca}_{idx}")

                    if marcado_m:
                        st.session_state.marcas_seleccionadas[nombre_marca] = {
                            "ubicacion": ubicacion_m_sel
                        }
                    else:
                        if nombre_marca in st.session_state.marcas_seleccionadas:
                            del st.session_state.marcas_seleccionadas[nombre_marca]

                    st.markdown("<hr style='margin:2px 0; border:0; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
