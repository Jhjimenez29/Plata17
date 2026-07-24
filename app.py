import datetime
import pandas as pd
import streamlit as st

# =============================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# =============================================================
st.set_page_config(
    page_title="Catálogo y Auditoría", page_icon="📦", layout="wide"
)

# Estilos CSS personalizados
st.markdown(
    """
    <style>
    .sombra-tenue {
        background-color: #F9FAFB;
        border: 1px solid #E5E7EB;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# =============================================================
# INICIALIZACIÓN DE VARIABLES DE SESIÓN (SESSION STATE)
# =============================================================
if "pantalla" not in st.session_state:
    st.session_state.pantalla = "resultados"

if "vista_catalogo" not in st.session_state:
    st.session_state.vista_catalogo = "productos"

if "busqueda_rapida" not in st.session_state:
    st.session_state.busqueda_rapida = ""

if "filtro_familia" not in st.session_state:
    st.session_state.filtro_familia = "-- Selecciona una familia --"

if "productos_seleccionados" not in st.session_state:
    st.session_state.productos_seleccionados = {}

if "marcas_seleccionadas" not in st.session_state:
    st.session_state.marcas_seleccionadas = {}

if "cliente_nombre" not in st.session_state:
    st.session_state.cliente_nombre = ""

if "cliente_numero" not in st.session_state:
    st.session_state.cliente_numero = ""


# =============================================================
# FUNCIONES DE APOYO Y CARGA DE DATOS
# =============================================================
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    import unicodedata

    return "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    ).lower()


@st.cache_data
def cargar_archivos():
    df_prod, df_mar = None, None
    try:
        df_prod = pd.read_csv("productos.csv")
    except Exception:
        try:
            df_prod = pd.read_excel("productos.xlsx")
        except Exception:
            df_prod = None

    try:
        df_mar = pd.read_csv("marcas.csv")
    except Exception:
        try:
            df_mar = pd.read_excel("marcas.xlsx")
        except Exception:
            df_mar = None

    return df_prod, df_mar


df_productos, df_marcas = cargar_archivos()

# Detectar columna real de familia en el CSV
columna_familia_real = None
if df_productos is not None:
    for col in df_productos.columns:
        col_norm = normalizar_texto(col)
        if "familia" in col_norm and "2017" in col_norm:
            columna_familia_real = col
            break
    if not columna_familia_real:
        for col in df_productos.columns:
            if "familia" in normalizar_texto(col):
                columna_familia_real = col
                break


def consolidar_visita_actual():
    filas = []
    # Productos
    for p_id, info in st.session_state.productos_seleccionados.items():
        row_dict = info["datos"].copy() if "datos" in info else {}
        row_dict["Tipo"] = "Producto"
        row_dict["Identificador / Código"] = p_id
        row_dict["Ubicación"] = info.get("ubicacion", "Piso de Venta")
        filas.append(row_dict)

    # Marcas
    for m_nom, info in st.session_state.marcas_seleccionadas.items():
        filas.append({
            "Tipo": "Marca",
            "Identificador / Código": m_nom,
            "Descripcion de producto": f"Marca: {m_nom}",
            "Ubicación": info.get("ubicacion", "Piso de Venta"),
        })

    return pd.DataFrame(filas)


def guardar_en_historial_maestro(df_reporte, nombre_cli, num_cli):
    if df_reporte.empty:
        return
    df_guardar = df_reporte.copy()
    df_guardar["Nombre Cliente"] = nombre_cli or "Cliente General"
    df_guardar["Número Cliente"] = num_cli or "1001"
    df_guardar["Fecha"] = datetime.date.today().strftime("%Y-%m-%d")
    df_guardar["Fecha_Hora"] = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    try:
        df_existente = pd.read_csv("historial_maestro.csv")
        df_final = pd.concat([df_existente, df_guardar], ignore_index=True)
    except Exception:
        df_final = df_guardar

    df_final.to_csv("historial_maestro.csv", index=False)


def cargar_historial_maestro():
    try:
        return pd.read_csv("historial_maestro.csv")
    except Exception:
        return pd.DataFrame()


def generar_excel_profesional(df, titulo_reporte="REPORTE"):
    import io

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Reporte", index=False)
    return output.getvalue()


def limpiar_casillas_y_seleccion():
    st.session_state.productos_seleccionados = {}
    st.session_state.marcas_seleccionadas = {}
    st.session_state.busqueda_rapida = ""
    st.session_state.filtro_familia = "-- Selecciona una familia --"


# =============================================================
# CONTROLADOR DE PANTALLAS
# =============================================================

# -------------------------------------------------------------
# PANTALLA: REPORTE DE LA VISITA ACTUAL
# -------------------------------------------------------------
if st.session_state.pantalla == "reporte_auditoria":
    col_nav1, col_nav2 = st.columns([7, 3])
    with col_nav1:
        st.markdown(
            "<h3 style='color: #000000; margin:0;'>📋 Reporte de Visita"
            " Actual</h3>",
            unsafe_allow_html=True,
        )
    with col_nav2:
        if st.button(
            "← Volver a Búsqueda", use_container_width=True, type="primary"
        ):
            st.session_state.pantalla = "resultados"
            st.rerun()

    st.markdown("---")
    df_reporte_actual = consolidar_visita_actual()

    if df_reporte_actual.empty:
        st.info(
            "ℹ️ Aún no has seleccionado productos ni marcas para este"
            " cliente."
        )
    else:
        st.markdown("#### 👤 Datos del Cliente / Revisión")
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            st.session_state.cliente_nombre = st.text_input(
                "Nombre del Cliente:",
                value=st.session_state.cliente_nombre or "Cliente General",
            )
        with col_c2:
            st.session_state.cliente_numero = st.text_input(
                "Número de Cliente:",
                value=st.session_state.cliente_numero or "1001",
            )
        with col_c3:
            st.date_input("Fecha de Revisión:", datetime.date.today())
        with col_c4:
            st.text_input(
                "Esquema:", value="Esquema Comercial 2017", disabled=True
            )

        st.markdown("---")
        st.dataframe(
            df_reporte_actual.drop(columns=["Fecha_Hora"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
            height=300,
        )

        st.markdown("---")
        col_acc1, col_acc2, col_acc3 = st.columns(3)

        with col_acc1:
            if st.button(
                "💾 Finalizar y Guardar Visita",
                use_container_width=True,
                type="primary",
            ):
                # 1. Guardar en el Historial Maestro
                guardar_en_historial_maestro(
                    df_reporte_actual,
                    st.session_state.cliente_nombre,
                    st.session_state.cliente_numero,
                )

                # 2. Limpieza total de selecciones y memoria temporal
                st.session_state.busqueda_rapida = ""
                st.session_state.filtro_familia = (
                    "-- Selecciona una familia --"
                )
                st.session_state.productos_seleccionados = {}
                st.session_state.marcas_seleccionadas = {}
                st.session_state.cliente_nombre = ""
                st.session_state.cliente_numero = ""

                # 3. Regresar a la vista principal limpia
                st.session_state.pantalla = "resultados"
                st.toast(
                    "✅ ¡Visita guardada correctamente! La pantalla se ha"
                    " limpiado.",
                    icon="🎉",
                )
                st.rerun()

        with col_acc2:
            bytes_excel = generar_excel_profesional(
                df_reporte_actual, titulo_reporte="REPORTE DE VISITA Y AUDITORÍA"
            )
            st.download_button(
                label="📥 Descargar Reporte en Excel Pro",
                data=bytes_excel,
                file_name=(
                    f"Visita_{st.session_state.cliente_numero}_{datetime.date.today()}.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True,
            )

        with col_acc3:
            if st.button(
                "🗑️ Descartar Selección Actual", use_container_width=True
            ):
                limpiar_casillas_y_seleccion()
                st.rerun()

# -------------------------------------------------------------
# PANTALLA: HISTORIAL GENERAL
# -------------------------------------------------------------
elif st.session_state.pantalla == "historial":
    col_h1, col_h2 = st.columns([7, 3])
    with col_h1:
        st.markdown(
            "<h3 style='margin:0;'>📊 Historial de Revisiones"
            " Realizadas</h3>",
            unsafe_allow_html=True,
        )
    with col_h2:
        if st.button(
            "← Volver a Búsqueda", use_container_width=True, type="primary"
        ):
            st.session_state.pantalla = "resultados"
            st.rerun()

    st.markdown("---")

    # Carga protegida del historial maestro
    df_historial = pd.DataFrame()
    try:
        df_historial = cargar_historial_maestro()
    except Exception as e:
        st.error(f"⚠️ Ocurrió un detalle al cargar el historial: {e}")

    if df_historial is None or df_historial.empty:
        st.info("ℹ️ Aún no hay visitas guardadas en el historial.")
    else:
        st.markdown("#### 🔍 Filtros de Consulta")
        col_f1, col_f2 = st.columns(2)
        opcion_default = "-- Seleccionar --"

        cols_df = df_historial.columns.tolist()
        col_cliente = (
            "Nombre Cliente" if "Nombre Cliente" in cols_df else cols_df[0]
        )
        col_fecha = (
            "Fecha"
            if "Fecha" in cols_df
            else (cols_df[1] if len(cols_df) > 1 else cols_df[0])
        )

        with col_f1:
            opts_cli = [opcion_default] + sorted(
                df_historial[col_cliente].dropna().astype(str).unique().tolist()
            )
            cliente_sel = st.selectbox("Filtrar por Cliente:", options=opts_cli)
        with col_f2:
            opts_fec = [opcion_default] + sorted(
                df_historial[col_fecha].dropna().astype(str).unique().tolist(),
                reverse=True,
            )
            fecha_sel = st.selectbox("Filtrar por Fecha:", options=opts_fec)

        filtro_cli = cliente_sel != opcion_default
        filtro_fec = fecha_sel != opcion_default

        df_filtrado = df_historial.copy()
        if filtro_cli:
            df_filtrado = df_filtrado[
                df_filtrado[col_cliente].astype(str) == cliente_sel
            ]
        if filtro_fec:
            df_filtrado = df_filtrado[
                df_filtrado[col_fecha].astype(str) == fecha_sel
            ]

        st.markdown("---")
        st.markdown(
            f"**Registros encontrados:** `{len(df_filtrado)}` filas"
        )

        if not df_filtrado.empty:
            st.dataframe(
                df_filtrado.drop(columns=["Fecha_Hora"], errors="ignore"),
                use_container_width=True,
                hide_index=True,
                height=350,
            )

            try:
                bytes_excel_h = generar_excel_profesional(
                    df_filtrado,
                    titulo_reporte="HISTORIAL DE REVISIONES Y AUDITORÍAS",
                )
                st.download_button(
                    label="📥 Descargar Historial Filtrado (Excel Pro)",
                    data=bytes_excel_h,
                    file_name=(
                        f"Historial_Consulta_{datetime.date.today()}.xlsx"
                    ),
                    mime=(
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ),
                    use_container_width=True,
                    type="primary",
                )
            except Exception:
                st.warning(
                    "⚠️ No se pudo generar el archivo de descarga en Excel."
                )
        else:
            st.warning(
                "⚠️ No se encontraron registros para los filtros"
                " seleccionados."
            )

# -------------------------------------------------------------
# PANTALLA PRINCIPAL: BÚSQUEDA Y AUDITORÍA
# -------------------------------------------------------------
elif st.session_state.pantalla == "resultados":
    total_sel = len(st.session_state.productos_seleccionados) + len(
        st.session_state.marcas_seleccionadas
    )

    col_sup1, col_sup2 = st.columns([4, 6])
    with col_sup1:
        st.markdown(
            "<h3 style='margin:0;'>Esquema comercial 2017</h3>",
            unsafe_allow_html=True,
        )
    with col_sup2:
        col_b1, col_b2, col_b3, col_b4 = st.columns([3, 2.5, 1.5, 2])
        with col_b1:
            lbl = (
                f"📋 Ver Visita ({total_sel})"
                if total_sel > 0
                else "📋 Ver Visita"
            )
            if st.button(
                lbl,
                use_container_width=True,
                type="primary" if total_sel > 0 else "secondary",
            ):
                st.session_state.pantalla = "reporte_auditoria"
                st.rerun()
        with col_b2:
            if st.button("📊 Historial", use_container_width=True):
                st.session_state.pantalla = "historial"
                st.rerun()
        with col_b3:
            if st.button(
                "⋮", use_container_width=True, help="Menú Opciones / Clientes"
            ):
                st.session_state.pantalla = "gestion_clientes"
                st.rerun()
        with col_b4:
            if st.button("← Salir", use_container_width=True):
                st.session_state.pantalla = "login"
                st.rerun()

    st.markdown("---")
    col_panel_filtros, col_panel_resultados = st.columns([3, 7])

    # -------------------------------------------------------------
    # PANEL DE FILTROS Y CONTROLES (LADO IZQUIERDO)
    # -------------------------------------------------------------
    with col_panel_filtros:
        st.markdown("#### 📂 Navegación")

        # Botones de Vista: Productos vs Marcas
        c_v1, c_v2 = st.columns(2)
        with c_v1:
            if st.button(
                "📦 Productos",
                use_container_width=True,
                type=(
                    "primary"
                    if st.session_state.vista_catalogo == "productos"
                    else "secondary"
                ),
            ):
                st.session_state.vista_catalogo = "productos"
                st.rerun()
        with c_v2:
            if st.button(
                "🏷️ Marcas",
                use_container_width=True,
                type=(
                    "primary"
                    if st.session_state.vista_catalogo == "marcas"
                    else "secondary"
                ),
            ):
                st.session_state.vista_catalogo = "marcas"
                st.rerun()

        st.markdown("---")

        # Desplegable de Familias
        if (
            st.session_state.vista_catalogo == "productos"
            and df_productos is not None
            and columna_familia_real
        ):
            lista_familias = ["-- Selecciona una familia --"] + sorted(
                df_productos[columna_familia_real]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            idx_actual = 0
            if st.session_state.filtro_familia in lista_familias:
                idx_actual = lista_familias.index(
                    st.session_state.filtro_familia
                )

            fam_sel = st.selectbox(
                "Filtrar por Familia:", options=lista_familias, index=idx_actual
            )
            if fam_sel != st.session_state.filtro_familia:
                st.session_state.filtro_familia = fam_sel
                st.rerun()

    # -------------------------------------------------------------
    # PANEL DE RESULTADOS Y PRODUCTOS (LADO DERECHO)
    # -------------------------------------------------------------
    with col_panel_resultados:
        if st.session_state.vista_catalogo == "productos":
            if df_productos is None:
                st.error(
                    "⚠️ No se pudo cargar 'productos.csv'. Asegúrate de que"
                    " el archivo esté en la carpeta del proyecto."
                )
            else:
                df_filtrado = df_productos.copy()

                # Caja de Búsqueda Rápida
                busqueda = st.text_input(
                    "🔤 Búsqueda rápida:",
                    value=st.session_state.busqueda_rapida,
                    placeholder="Escribe código, clave o descripción...",
                )

                if busqueda != st.session_state.busqueda_rapida:
                    st.session_state.busqueda_rapida = busqueda
                    st.rerun()

                # Verificar si hay algún filtro activo por parte del usuario
                fam_activa = (
                    st.session_state.filtro_familia
                    != "-- Selecciona una familia --"
                )
                texto_activo = bool(st.session_state.busqueda_rapida.strip())
                filtro_aplicado = fam_activa or texto_activo

                if filtro_aplicado:
                    # Aplicar Filtro de Familia
                    if (
                        fam_activa
                        and columna_familia_real
                        and columna_familia_real in df_filtrado.columns
                    ):
                        df_filtrado = df_filtrado[
                            df_filtrado[columna_familia_real]
                            == st.session_state.filtro_familia
                        ]

                    # Aplicar Filtro de Texto
                    if texto_activo:
                        cond = pd.Series(False, index=df_filtrado.index)
                        for col_val in df_filtrado.columns:
                            cond |= (
                                df_filtrado[col_val]
                                .astype(str)
                                .str.contains(
                                    st.session_state.busqueda_rapida,
                                    case=False,
                                    na=False,
                                )
                            )
                        df_filtrado = df_filtrado[cond]

                    # Mostrar Tarjetas Informativas
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(
                            "<div class='sombra-tenue'><span"
                            " style='color:#6B7280;font-size:11px;'>Familia"
                            " Seleccionada</span><br><strong>"
                            f"{st.session_state.filtro_familia if fam_activa else 'Todas'}"
                            "</strong></div>",
                            unsafe_allow_html=True,
                        )
                    with c2:
                        st.markdown(
                            "<div class='sombra-tenue'><span"
                            " style='color:#6B7280;font-size:11px;'>Coincidencias</span><br><strong"
                            f" style='color:#2563EB;'>{len(df_filtrado)}</strong></div>",
                            unsafe_allow_html=True,
                        )
                    with c3:
                        st.markdown(
                            "<div class='sombra-tenue'><span"
                            " style='color:#6B7280;font-size:11px;'>Total"
                            " Catálogo</span><br><strong>"
                            f"{len(df_productos)}</strong></div>",
                            unsafe_allow_html=True,
                        )

                    # Mostrar Tabla de Resultados
                    if not df_filtrado.empty:
                        cols_deseadas = [
                            "Descripcion de producto",
                            "Numero de familia",
                            "Familia 2017",
                        ]
                        cols_a_mostrar = [
                            c for c in cols_deseadas if c in df_filtrado.columns
                        ]

                        if "Numero de familia" not in cols_a_mostrar:
                            var_num_fam = [
                                c
                                for c in df_filtrado.columns
                                if "numero de familia" in normalizar_texto(c)
                                or (
                                    "num" in normalizar_texto(c)
                                    and "familia" in normalizar_texto(c)
                                )
                            ]
                            if var_num_fam:
                                cols_a_mostrar.insert(1, var_num_fam[0])

                        st.dataframe(
                            df_filtrado[cols_a_mostrar],
                            use_container_width=True,
                            hide_index=True,
                            height=280,
                        )

                        # --- SECCIÓN DE CASILLAS DE SELECCIÓN ---
                        st.markdown("---")
                        st.markdown("#### 📌 Marcar productos de esta vista:")

                        for idx, row in df_filtrado.head(30).iterrows():
                            p_id = (
                                str(row.iloc[0])
                                if len(row) > 0
                                else f"PROD_{idx}"
                            )

                            marcado = (
                                p_id in st.session_state.productos_seleccionados
                            )
                            ubi_act = (
                                st.session_state.productos_seleccionados[p_id][
                                    "ubicacion"
                                ]
                                if marcado
                                else "Piso de Venta"
                            )

                            cdet, cubi, cchk = st.columns([6, 3, 1])
                            with cdet:
                                desc = row.get(
                                    "Descripcion de producto",
                                    str(
                                        row.iloc[1] if len(row) > 1 else p_id
                                    ),
                                )
                                st.write(f"**{p_id}** - {desc}")
                            with cubi:
                                u_sel = st.selectbox(
                                    "Ubicación",
                                    ["Piso de Venta", "Almacén", "Ambos"],
                                    index=[
                                        "Piso de Venta",
                                        "Almacén",
                                        "Ambos",
                                    ].index(ubi_act),
                                    key=f"sel_ubic_{p_id}_{idx}",
                                    label_visibility="collapsed",
                                )
                            with cchk:
                                chk = st.checkbox(
                                    "",
                                    value=marcado,
                                    key=f"chk_p_{p_id}_{idx}",
                                )

                            if chk:
                                st.session_state.productos_seleccionados[
                                    p_id
                                ] = {"datos": row.to_dict(), "ubicacion": u_sel}
                            elif p_id in st.session_state.productos_seleccionados:
                                del st.session_state.productos_seleccionados[
                                    p_id
                                ]

                            st.markdown(
                                "<hr style='margin:2px 0; border:0;"
                                " border-top: 1px solid #E2E8F0;'>",
                                unsafe_allow_html=True,
                            )
                    else:
                        st.warning(
                            "⚠️ No se encontraron productos con los filtros"
                            " seleccionados."
                        )
                else:
                    # Pantalla limpia por defecto
                    st.info(
                        "💡 Utiliza el buscador o selecciona una familia para"
                        " desplegar los productos."
                    )

        else:
            st.markdown(
                "<h4 style='color: #000000;'>🏷️ Listado de Marcas</h4>",
                unsafe_allow_html=True,
            )
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
                    ubi_m_act = (
                        st.session_state.marcas_seleccionadas[nom_m][
                            "ubicacion"
                        ]
                        if marcado_m
                        else "Piso de Venta"
                    )

                    cnom, cubi, cchk = st.columns([6, 3, 1])
                    with cnom:
                        st.markdown(f"🏷️ **{nom_m}**")
                    with cubi:
                        u_m_sel = st.selectbox(
                            "Ubicación Marca",
                            ["Piso de Venta", "Almacén", "Ambos"],
                            index=["Piso de Venta", "Almacén", "Ambos"].index(
                                ubi_m_act
                            ),
                            key=f"sel_ubi_m_{nom_m}_{idx}",
                            label_visibility="collapsed",
                        )
                    with cchk:
                        chk_m = st.checkbox(
                            "", value=marcado_m, key=f"chk_m_{nom_m}_{idx}"
                        )

                    if chk_m:
                        st.session_state.marcas_seleccionadas[nom_m] = {
                            "ubicacion": u_m_sel
                        }
                    elif nom_m in st.session_state.marcas_seleccionadas:
                        del st.session_state.marcas_seleccionadas[nom_m]

                    st.markdown(
                        "<hr style='margin:2px 0; border:0; border-top: 1px"
                        " solid #E2E8F0;'>",
                        unsafe_allow_html=True,
                    )


