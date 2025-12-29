import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import numpy as np
from os import path
import os 

# --- CONFIGURACIÓN DE ARCHIVOS Y GRUPO ---
# Nombre del archivo de datos
FILE_NAME_DATA = 'ListadoDeEstudiantesGrupo_051.xlsx - Hoja1.csv' 
GRUPO_INFO = 'Grupo 051 (001, 050, 051)'
# ¡INTEGRANTES DEL GRUPO ACTUALIZADOS!
INTEGRANTES = ['Yalen Camilo Aguirre', 'Ronald Briceño', 'Samuel Alzate', 'Maria Camila Rojas', 'Juan Jose Rivera']
REQUIRED_COLS = ['Codigo', 'Fecha_Nacimiento', 'Estatura', 'Peso', 'Nombre_Estudiante', 'Apellido_Estudiante']

# --- FUNCIÓN DE CLASIFICACIÓN DE IMC ---
def clasificar_imc(imc):
    """Clasifica el IMC según los rangos estándar (Punto 1.d)."""
    if pd.isna(imc):
        return 'Sin Datos'
    elif 18.5 <= imc < 25:
        return 'Peso Normal'
    elif 25 <= imc < 30:
        return 'Sobrepeso'
    elif imc < 18.5:
        return 'Bajo peso'
    else: # imc >= 30
        return 'Obesidad'

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Dashboard Estudiantil",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Variable para el modo debug global (inicialmente False)
show_debug_data = False

# --- CARGA Y PROCESAMIENTO DE DATOS ---
@st.cache_data
def load_and_process_data(debug_mode):
    """Carga y procesa el archivo de datos, intentando leer como Excel o CSV."""
    
    file_to_load = FILE_NAME_DATA
    df = None 
    
    # 1. VERIFICACIÓN DE EXISTENCIA DEL ARCHIVO
    if not path.exists(file_to_load):
        current_dir = os.getcwd()
        st.error(f"❌ ERROR CRÍTICO DE RUTA: No se encontró el archivo '{file_to_load}'.")
        st.error(f"El script lo está buscando en la carpeta: `{current_dir}`")
        st.warning(f"👉 **Asegúrese de que '{file_to_load}' esté *directamente* en esa carpeta.**")
        return None
        
    # 2. INTENTAR CARGAR COMO EXCEL (PRIORIDAD: Esto manejará tu archivo .xlsx renombrado a .csv)
    try:
        df = pd.read_excel(file_to_load)
        st.info(f"✅ Archivo '{file_to_load}' cargado exitosamente como formato Excel (XLSX).")
    except ImportError:
        st.error("❌ Error de dependencia: Instala 'openpyxl' (`pip install openpyxl`) para leer Excels.")
        return None
    except Exception as e_excel:
        # 3. SI EXCEL FALLA, INTENTAR CARGAR COMO CSV (SEGUNDA OPCIÓN)
        st.warning(f"La lectura como Excel falló. Intentando cargar como CSV...")
        
        load_options = [(';', 'latin-1'), (',', 'latin-1'), (';', 'utf-8'), (',', 'utf-8')]
        
        for sep, encoding in load_options:
            try:
                # La lectura con inferencia de encabezados ayuda con CSV
                df_temp = pd.read_csv(file_to_load, sep=sep, encoding=encoding, header='infer')
                if not df_temp.empty and df_temp.shape[1] > 2:
                    df = df_temp
                    st.info(f"✅ Archivo cargado exitosamente como CSV con separador '{sep}' y encoding '{encoding}'.")
                    break
            except Exception:
                pass

        if df is None: 
            st.error(f"❌ Error crítico de FORMATO: No se pudo leer el archivo '{file_to_load}'. Revise el contenido y encabezados.")
            return None

    if df.empty:
        st.error("❌ Error: El archivo se encontró, pero está vacío.")
        return None

    # 4. Validar y limpiar columnas esenciales
    try:
        # CORRECCIÓN DE NORMALIZACIÓN: Usar un patrón más seguro que preserve los guiones bajos
        df.columns = df.columns.str.strip().str.replace(' ', '_').str.replace('[^a-zA-Z0-9_]', '', regex=True)
        
        missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]
        if missing_cols:
            st.error(f"❌ Error de ENCABEZADO: Faltan las columnas esenciales: {', '.join(missing_cols)}")
            st.warning("Los encabezados *deben* ser: Codigo, Fecha_Nacimiento, Estatura, Peso, Nombre_Estudiante, Apellido_Estudiante")
            return None
            
        df.dropna(subset=['Codigo'], inplace=True) 
        
        # Cálculo de Edad (Punto 1.a)
        today = date.today()
        # Intentar convertir la fecha usando varios formatos si el primero falla
        df['Fecha_Nacimiento'] = pd.to_datetime(df['Fecha_Nacimiento'], errors='coerce', dayfirst=True)
        df['Edad'] = df['Fecha_Nacimiento'].apply(lambda x: today.year - x.year - ((today.month, today.day) < (x.month, x.day)) if pd.notna(x) else np.nan)

        # Normalización de Estatura y Peso (Punto 2: Estatura a Centímetros)
        def normalize_numeric_column(value, is_estatura=False):
            try:
                if isinstance(value, str):
                    value = value.replace(',', '.') 
                val = float(value)
                # Conversión de metros a centímetros si el valor está entre 1 y 3 
                if is_estatura and val > 1 and val < 3:
                    return val * 100 
                return val
            except:
                return np.nan
                
        df['Estatura_cm'] = df['Estatura'].apply(lambda x: normalize_numeric_column(x, is_estatura=True))
        # La columna 'Peso' ya existe, pero se recalcula con la limpieza (Punto 1.b)
        df['Peso'] = df['Peso'].apply(normalize_numeric_column) 

        # Cálculo de IMC y Clasificación (Punto 1.c y 1.d)
        df['Estatura_m'] = df['Estatura_cm'] / 100
        df['IMC'] = df['Peso'] / (df['Estatura_m'] ** 2)
        df['Clasificación IMC'] = df['IMC'].apply(clasificar_imc)
        
        # Limpieza y estandarización de categóricos (RH, Color_Cabello, etc.)
        for col in ['Barrio_Residencia', 'Color_Cabello', 'RH', 'Talla_Zapato']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.split(',').str[0].str.strip().replace('nan', np.nan)
        
        # Renombrar columna de estatura final
        df = df.rename(columns={'Estatura': 'Estatura_Original', 'Estatura_cm': 'Estatura'})
        
        # Crear la columna de Nombre Completo para el filtro de Integrantes
        df['Nombre_Completo'] = df['Nombre_Estudiante'].astype(str).str.strip() + ' ' + df['Apellido_Estudiante'].astype(str).str.strip()
        
        # Eliminar columnas intermedias
        df = df.drop(columns=['Estatura_Original', 'Estatura_m'], errors='ignore')
        
        # MOSTRAR DEBUG COMPLETO SI EL CHECKBOX ESTÁ MARCADO (NUEVO)
        if debug_mode:
            st.sidebar.markdown("---")
            st.sidebar.markdown(f"**DEBUG COMPLETO:** `{df.shape[0]}` filas cargadas y procesadas.")
            # Mostrar el DataFrame completo en la barra lateral
            st.sidebar.dataframe(df, use_container_width=True)
            st.sidebar.markdown("---")
        
        return df.copy()
    
    except Exception as e_proc:
        st.error(f"❌ Error durante el procesamiento de datos (cálculos/limpieza): {type(e_proc).__name__}: {e_proc}") 
        return None

# --- APLICACIÓN DE FILTROS Y CONTROLES DE LA BARRA LATERAL (PRIMERA PARTE) ---
with st.sidebar:
    st.header("⚙️ Opciones y Filtros")

    # Checkbox de Debug (Controla si se muestra el DataFrame completo)
    show_debug_data = st.checkbox('Mostrar datos de Debug (DataFrame completo)', value=False)
    
    # Cargar datos con el estado del checkbox
    df_original = load_and_process_data(show_debug_data)
    
# Control de error FINAL: Si df_original es None, la aplicación se detiene.
if df_original is None:
    st.stop()
    
# Si llegamos aquí, df_original tiene datos.
df = df_original.copy() 
df_base_kpi = df.dropna(subset=['Edad', 'Estatura', 'Peso', 'IMC'])

if df_base_kpi.empty:
    st.error("No quedan datos válidos para las métricas clave después de limpiar filas incompletas.")
    st.stop()


# --- APLICACIÓN DE FILTROS EN LA BARRA LATERAL (SEGUNDA PARTE) ---
with st.sidebar:
    st.markdown("---")
    
    # Punto 13: Filtro Opcional por Integrante
    st.subheader("Filtro por Integrante (Opcional)")
    parIntegrantes = st.selectbox('Integrantes del Grupo', ['TODOS'] + INTEGRANTES, index=0)
    
    st.subheader("Filtros Categóricos (Punto 4)")
    
    # Punto 4: Filtros Multiselect
    for label, col_name in [('Tipo de Sangre (RH)', 'RH'), ('Color de Cabello', 'Color_Cabello'), ('Barrio de Residencia', 'Barrio_Residencia')]:
        if col_name in df_base_kpi.columns:
            # Usamos df_original para la lista completa de valores únicos, mejor para multiselect
            unique_values = df_base_kpi[col_name].dropna().unique()
            globals()[f"par{col_name.replace('_', '')}"] = st.multiselect(label, sorted(unique_values))
        else:
            globals()[f"par{col_name.replace('_', '')}"] = [] 

    st.subheader("Filtros de Rango (Punto 5)")
    
    # Punto 5: Slider Rango de Edad
    try:
        min_edad, max_edad = int(df_base_kpi['Edad'].min()), int(df_base_kpi['Edad'].max())
        parRangoEdad = st.slider('Rango de Edad', min_edad, max_edad, (min_edad, max_edad), step=1)
    except: parRangoEdad = (0, 100)
    
    # Punto 5: Slider Rango de Estatura
    try:
        min_est, max_est = int(df_base_kpi['Estatura'].min()), int(df_base_kpi['Estatura'].max())
        parRangoEst = st.slider('Rango de Estatura (cm)', min_est, max_est, (min_est, max_est), step=1)
    except: parRangoEst = (100, 200)

# Aplicar filtros
df_filtrado = df_base_kpi.copy()

# APLICACIÓN DE FILTRO DE INTEGRANTES 
if parIntegrantes != 'TODOS':
    # Hacemos el filtro usando la columna Nombre_Completo generada.
    df_filtrado = df_filtrado[df_filtrado['Nombre_Completo'].str.contains(parIntegrantes, case=False, na=False)]


# Aplicar filtros categóricos
if 'parRH' in locals() and parRH: df_filtrado = df_filtrado[df_filtrado['RH'].isin(parRH)]
if 'parColorCabello' in locals() and parColorCabello: df_filtrado = df_filtrado[df_filtrado['Color_Cabello'].isin(parColorCabello)]
if 'parBarrioResidencia' in locals() and parBarrioResidencia: df_filtrado = df_filtrado[df_filtrado['Barrio_Residencia'].isin(parBarrioResidencia)]

# Aplicar filtros de rango
df_filtrado = df_filtrado[
    (df_filtrado['Edad'] >= parRangoEdad[0]) & (df_filtrado['Edad'] <= parRangoEdad[1]) &
    (df_filtrado['Estatura'] >= parRangoEst[0]) & (df_filtrado['Estatura'] <= parRangoEst[1])
]

if df_filtrado.empty:
    st.warning("No hay datos que coincidan con los filtros seleccionados.")
    st.stop()


# CUERPO DEL DASHBOARD
# Punto 6: Título
st.title(f'Dashboard Estudiantil – {GRUPO_INFO}')
st.markdown("---")


# Punto 3: Mostrar el Archivo De Excel (primeras 5 filas con columnas calculadas)
st.subheader('📋 Datos Originales y Columnas Calculadas (Primeras 5 Filas)')
# Mostrar las columnas calculadas Edad, Peso, IMC, Clasificación IMC
cols_display = [col for col in df_original.columns if col not in ['Estatura_Original', 'Estatura_m', 'Nombre_Completo']]
st.dataframe(df_original.head(5)[cols_display], use_container_width=True)
st.markdown("---")

# MOSTRAR FILA INDIVIDUAL SELECCIONADA 
if parIntegrantes != 'TODOS':
    st.subheader(f"👤 Información Individual: {parIntegrantes}")
    df_individual = df_filtrado[df_filtrado['Nombre_Completo'].str.contains(parIntegrantes, case=False, na=False)].head(1)
    if not df_individual.empty:
        # Seleccionar solo las columnas relevantes para la vista individual
        col_select = ['Nombre_Estudiante', 'Apellido_Estudiante', 'Codigo', 'Edad', 'Estatura', 'Peso', 'IMC', 'Clasificación IMC', 'RH', 'Color_Cabello', 'Talla_Zapato', 'Barrio_Residencia']
        
        # Reformatear para mejor vista vertical
        df_display = df_individual[col_select].T.reset_index()
        df_display.columns = ['Campo', 'Valor']
        # Usamos una función lambda para formatear números flotantes, dejando otros tipos como están
        st.table(df_display.style.format({'Valor': lambda x: f'{x:.1f}' if isinstance(x, (int, float)) and x > 10 else str(x)}))

    st.markdown("---")


# Punto 7: KPIs (Métricas clave)
total_estudiantes = len(df_filtrado)
edad_promedio = df_filtrado['Edad'].mean()
estatura_promedio = df_filtrado['Estatura'].mean()
peso_promedio = df_filtrado['Peso'].mean()
imc_promedio = df_filtrado['IMC'].mean()

col1, col2, col3, col4, col5 = st.columns(5)

# CORRECCIÓN DE FORMATO: Asegurar que los valores KPI estén en negrita
with col1: st.metric("Total Estudiantes", f"**{total_estudiantes}**")
with col2: st.metric("Edad Promedio", f"**{edad_promedio:.1f}** años")
with col3: st.metric("Estatura Promedio", f"**{estatura_promedio:.1f}** cm")
with col4: st.metric("Peso Promedio", f"**{peso_promedio:.1f}** kg")
with col5: st.metric("IMC Promedio", f"**{imc_promedio:.1f}**")

st.markdown("---")

# 1era Fila de gráficos (Punto 8)
st.subheader('📈 Análisis de Distribución Poblacional')
col1, col2 = st.columns(2)

with col1:
    st.markdown("##### Distribución de Estudiantes por Edad (Barras)")
    df_edad = df_filtrado.groupby('Edad').size().reset_index(name='Conteo')
    fig_edad = px.bar(df_edad, x='Edad', y='Conteo', 
                    title='Conteo de Estudiantes por Edad', 
                    labels={'Conteo': 'Número de Estudiantes', 'Edad': 'Edad (años)'},
                    color_discrete_sequence=px.colors.qualitative.Plotly)
    st.plotly_chart(fig_edad, use_container_width=True)

with col2:
    if 'RH' in df_filtrado.columns:
        st.markdown("##### Distribución por Tipo de Sangre (RH) (Torta)")
        df_rh = df_filtrado.groupby('RH').size().reset_index(name='Conteo')
        fig_rh = px.pie(df_rh, names='RH', values='Conteo', 
                        title='Distribución por RH', 
                        hole=.3,
                        color_discrete_sequence=px.colors.qualitative.D3)
        st.plotly_chart(fig_rh, use_container_width=True)
    else:
        st.info("La columna 'RH' no está disponible.")

st.markdown("---")

# 2da Fila de gráficos (Punto 9)
st.subheader('🏋️ Análisis Biométrico y Estilístico')
col1, col2 = st.columns(2)

with col1:
    st.markdown("##### Relación Estatura vs Peso (Dispersión/Scatter)")
    order_imc = ['Bajo peso', 'Peso Normal', 'Sobrepeso', 'Obesidad', 'Sin Datos']
    
    fig_scatter = px.scatter(df_filtrado, 
                            x='Estatura', 
                            y='Peso', 
                            color='Clasificación IMC', 
                            title='Estatura vs. Peso',
                            labels={'Estatura': 'Estatura (cm)', 'Peso': 'Peso (kg)'},
                            category_orders={"Clasificación IMC": order_imc},
                            hover_data=['Nombre_Estudiante', 'Apellido_Estudiante', 'IMC'])
    st.plotly_chart(fig_scatter, use_container_width=True)

with col2:
    if 'Color_Cabello' in df_filtrado.columns:
        st.markdown("##### Distribución por Color de Cabello (Barras)")
        df_cabello = df_filtrado.groupby('Color_Cabello').size().reset_index(name='Conteo').sort_values(by='Conteo', ascending=False).head(10) 
        fig_cabello = px.bar(df_cabello, 
                            x='Color_Cabello', 
                            y='Conteo', 
                            title='Conteo por Color de Cabello (Top 10)',
                            color='Color_Cabello',
                            color_discrete_sequence=px.colors.qualitative.Vivid)
        st.plotly_chart(fig_cabello, use_container_width=True)
    else:
        st.info("La columna 'Color_Cabello' no está disponible.")
        
st.markdown("---")

# 3ra Fila de gráficos (Punto 10)
st.subheader('📍 Análisis de Tendencias y Residencia')
col1, col2 = st.columns(2)

with col1:
    if 'Talla_Zapato' in df_filtrado.columns:
        st.markdown("##### Distribución de Tallas de Zapatos (Línea)")
        df_zapatos = df_filtrado.dropna(subset=['Talla_Zapato']).copy()
        df_zapatos['Talla_Zapato'] = pd.to_numeric(df_zapatos['Talla_Zapato'], errors='coerce')
        df_zapatos.dropna(subset=['Talla_Zapato'], inplace=True)
        
        df_zapatos = df_zapatos.groupby('Talla_Zapato').size().reset_index(name='Conteo').sort_values(by='Talla_Zapato')
        
        fig_zapatos = px.line(df_zapatos, 
                            x='Talla_Zapato', 
                            y='Conteo', 
                            title='Distribución de Tallas de Zapatos', 
                            markers=True, 
                            line_shape='spline',
                            labels={'Talla_Zapato': 'Talla de Zapato', 'Conteo': 'Número de Estudiantes'})
        st.plotly_chart(fig_zapatos, use_container_width=True)
    else:
        st.info("La columna 'Talla_Zapato' no está disponible para el gráfico.")

with col2:
    if 'Barrio_Residencia' in df_filtrado.columns:
        st.markdown("##### Top 10 Barrios de Residencia (Barras)")
        df_barrios = df_filtrado.groupby('Barrio_Residencia').size().reset_index(name='Conteo').sort_values(by='Conteo', ascending=False).head(10)
        fig_barrios = px.bar(df_barrios, 
                            x='Barrio_Residencia', 
                            y='Conteo', 
                            title='Top 10 Barrios',
                            color='Conteo',
                            color_continuous_scale=px.colors.sequential.Sunset)
        st.plotly_chart(fig_barrios, use_container_width=True)
    else:
        st.info("La columna 'Barrio_Residencia' no está disponible para el gráfico.")

st.markdown("---")

# Tablas Top 5 y Resumen Estadístico (Puntos 11 y 12)
st.subheader('🏆 Tablas y Resumen Estadístico')
col_top1, col_top2, col_desc = st.columns([1, 1, 1.5]) 

def format_describe_df(series, name):
    """Función auxiliar para formatear la salida del .describe()"""
    df_desc = series.describe().reset_index().rename(columns={'index': 'Métrica', series.name: 'Valor'})
    df_desc['Valor'] = df_desc.apply(
        lambda row: f"{int(row['Valor'])}" if row['Métrica'] == 'count' else f"{row['Valor']:.1f}", 
        axis=1
    )
    df_desc.insert(1, 'Unidad', name)
    return df_desc

with col_top1:
    # Punto 11: Top 5 Mayor Estatura
    st.markdown("##### Top 5 Mayor Estatura (cm)")
    top_estatura = df_filtrado.sort_values(by='Estatura', ascending=False).head(5)[
        ['Nombre_Estudiante', 'Apellido_Estudiante', 'Estatura', 'Edad']
    ].reset_index(drop=True)
    top_estatura.index = top_estatura.index + 1 
    st.table(top_estatura.style.format({'Estatura': '{:.1f}'}))

with col_top2:
    # Punto 11: Top 5 Mayor Peso
    st.markdown("##### Top 5 Mayor Peso (kg)")
    top_peso = df_filtrado.sort_values(by='Peso', ascending=False).head(5)[
        ['Nombre_Estudiante', 'Apellido_Estudiante', 'Peso', 'Estatura', 'IMC']
    ].reset_index(drop=True)
    top_peso.index = top_peso.index + 1
    st.table(top_peso.style.format({'Peso': '{:.1f}', 'Estatura': '{:.1f}', 'IMC': '{:.1f}'}))

with col_desc:
    # Punto 12: Resumen Estadístico de Estatura, Peso, IMC
    st.markdown("##### Resumen Biométrico (Estatura, Peso, IMC)")
    if 'Estatura' in df_filtrado.columns and 'Peso' in df_filtrado.columns and 'IMC' in df_filtrado.columns:
        
        desc_est = format_describe_df(df_filtrado['Estatura'], 'cm').set_index('Métrica')
        desc_peso = format_describe_df(df_filtrado['Peso'], 'kg').set_index('Métrica')
        desc_imc = format_describe_df(df_filtrado['IMC'], '').set_index('Métrica')
        
        combined_desc = pd.concat([desc_est, desc_peso, desc_imc], axis=1)
        # Reordenar las columnas para mostrar (Valor, Unidad)
        combined_desc.columns = pd.MultiIndex.from_product([['Estatura', 'Peso', 'IMC'], ['Unidad', 'Valor']])
        combined_desc = combined_desc.loc[['count', 'mean', 'std', 'min', 'max', '25%', '50%', '75%']] 
        
        # Muestra la tabla de resumen
        st.dataframe(combined_desc.iloc[:, [1, 0, 3, 2, 5, 4]], use_container_width=True)
    else:
        st.warning("Faltan datos para el resumen estadístico.")