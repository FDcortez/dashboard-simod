import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import warnings

# Silenciar las advertencias de validación de datos del Excel
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# Configuración principal de la página
st.set_page_config(page_title="Dashboard Control MOD - Las Majaguas", layout="wide")

# 1. LECTURA Y LIMPIEZA DE DATOS
# @st.cache_data # Mantener comentado si el Excel se actualiza constantemente
def cargar_datos(ruta_excel='plantilla.xlsx'):
    try:
        df = pd.read_excel(ruta_excel)
        
        # LIMPIEZA CRÍTICA
        df.columns = df.columns.str.strip()
        df['ESTATUS'] = df['ESTATUS'].astype(str).str.strip().str.upper()
        df['TIPO_ACTIVIDAD'] = df['TIPO_ACTIVIDAD'].astype(str).str.strip().str.upper()
        df['DEPARTAMENTO'] = df['DEPARTAMENTO'].astype(str).str.strip().str.upper()
        
        df['JORNADA_EFECTIVA'] = pd.to_numeric(df['JORNADA_EFECTIVA'], errors='coerce').fillna(0)
        df['HH_PLANIFICADAS'] = pd.to_numeric(df['HH_PLANIFICADAS'], errors='coerce').fillna(0)
        df['CUADRILLA'] = pd.to_numeric(df['CUADRILLA'], errors='coerce').fillna(0)

        # MAPEO DE GERENCIAS
        mapeo_gerencias = {
            'ENVASE': 'Gerencia de Operaciones', 'FABRICACION': 'Gerencia de Operaciones',
            'GENERACION DE VAPOR': 'Gerencia de Operaciones', 'PREPARACION Y MOLIENDA': 'Gerencia de Operaciones',
            'AUTOMATIZACION Y CONTROL': 'Gerencia de Mantenimiento', 'ELECTRICIDAD': 'Gerencia de Mantenimiento',
            'MANTENIMIENTO BASADO EN CONDICION': 'Gerencia de Mantenimiento', 'MANTENIMIENTO MECANICO': 'Gerencia de Mantenimiento',
            'MONTAJE Y SOLDADURA': 'Gerencia de Mantenimiento', 'TALLER INDUSTRIAL': 'Gerencia de Mantenimiento'
        }
        df['GERENCIA'] = df['DEPARTAMENTO'].map(mapeo_gerencias).fillna('Otras Áreas')
        
        return df
    
    except FileNotFoundError:
        st.error(f"Error: No se encontró el archivo '{ruta_excel}'. Asegúrate de que esté en la misma carpeta.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Ocurrió un error al procesar los datos: {e}")
        return pd.DataFrame()

# Cargar el DataFrame
df = cargar_datos()

if df.empty:
    st.stop() # Detiene la ejecución visual si el archivo no carga

# --- ENCABEZADO ---
st.title("Control y Seguimiento")
st.markdown("### Prueba Piloto - Mano de Obra Directa (MOD)")

# --- FILTROS DINÁMICOS EN CASCADA ---
col1, col2 = st.columns(2)

with col1:
    opciones_gerencia = ['GLOBAL (Las Majaguas)', 'Gerencia de Operaciones', 'Gerencia de Mantenimiento']
    gerencia_seleccionada = st.selectbox("Seleccione Nivel / Gerencia:", opciones_gerencia)

with col2:
    if gerencia_seleccionada == 'GLOBAL (Las Majaguas)':
        depto_seleccionado = 'TODOS'
        st.write("") # Mantiene el layout alineado
    else:
        deptos_disponibles = ['TODOS'] + df[df['GERENCIA'] == gerencia_seleccionada]['DEPARTAMENTO'].unique().tolist()
        depto_seleccionado = st.selectbox("Seleccione Departamento:", deptos_disponibles)

# --- APLICACIÓN DEL FILTRO AL DATAFRAME ---
if gerencia_seleccionada == 'GLOBAL (Las Majaguas)':
    df_f = df.copy()
    titulo_vista = "Global (Todas las Áreas)"
elif depto_seleccionado == 'TODOS':
    df_f = df[df['GERENCIA'] == gerencia_seleccionada].copy()
    titulo_vista = f"{gerencia_seleccionada} (General)"
else:
    df_f = df[(df['GERENCIA'] == gerencia_seleccionada) & (df['DEPARTAMENTO'] == depto_seleccionado)].copy()
    titulo_vista = f"Departamento: {depto_seleccionado}"

st.subheader(f"Vista Actual: {titulo_vista}")

# Protección contra data vacía en el nivel seleccionado
if df_f.empty:
    st.warning(f"Aún no hay trabajos reportados en: {titulo_vista}.")
    st.stop()

# --- KPIs DE MANO DE OBRA ---
st.markdown("#### Indicadores de Mano de Obra")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

total_hh_plan = df_f['HH_PLANIFICADAS'].sum()
total_hh_real = df_f['JORNADA_EFECTIVA'].sum()
hh_totales_impacto = (df_f['JORNADA_EFECTIVA'] * df_f['CUADRILLA']).sum()

count_manto = df_f[df_f['GERENCIA'] == 'Gerencia de Mantenimiento'].shape[0]
count_oper = df_f[df_f['GERENCIA'] == 'Gerencia de Operaciones'].shape[0]

kpi1.metric("HH Planificadas", f"{total_hh_plan:.1f}h")
kpi2.metric("HH Reales", f"{total_hh_real:.1f}h")
kpi3.metric("Esfuerzo Total (HH x Cuadrilla)", f"{hh_totales_impacto:.1f}h")
kpi4.metric("Volumen de Actividades", f"{count_manto + count_oper}", f"Manto: {count_manto} | Oper: {count_oper}")

st.divider()

# --- KPIs DE CONFIABILIDAD INDUSTRIAL ---
st.markdown("#### Indicadores de Confiabilidad Industrial")
ind1, ind2, ind3 = st.columns(3)

# Lógica MTTR: Tareas FINALIZADAS excluyendo el mantenimiento PREDICTIVO
df_mttr = df_f[(df_f['ESTATUS'] == 'FINALIZADO') & (df_f['TIPO_ACTIVIDAD'] != 'PREDICTIVO')]
mttr_real = df_mttr['JORNADA_EFECTIVA'].mean() if not df_mttr.empty else 0

ind1.metric("MTTR Actual", f"{mttr_real:.1f}h", "Tiempo Medio de Reparación")
ind2.metric("MTBF (Ref)", "124.5h", "Tiempo Entre Fallas")
ind3.metric("OEE Estimado", "76.8%", "Efectividad de Equipos")

st.divider()

# --- BLOQUE DE GRÁFICOS (1 al 4) ---
c1, c2 = st.columns(2)

with c1:
    # 1. Distribución de Horas por Estructura
    df_g1 = df_f[df_f['JORNADA_EFECTIVA'] > 0].groupby(['GERENCIA', 'DEPARTAMENTO']).agg(
        JORNADA_EFECTIVA=('JORNADA_EFECTIVA', 'sum'), CANTIDAD_TAREAS=('ID_TAREA', 'count')).reset_index()
    
    if not df_g1.empty:
        fig1 = px.sunburst(df_g1, path=['GERENCIA', 'DEPARTAMENTO'], values='JORNADA_EFECTIVA', custom_data=['CANTIDAD_TAREAS'],
                           title='1. Distribución de Horas por Estructura', 
                           color_discrete_sequence=['#1B5E20', '#0D47A1'])
        fig1.update_traces(hovertemplate='<b>%{label}</b><br>Horas: %{value:.1f}h<br>Actividades: %{customdata[0]}<extra></extra>')
        st.plotly_chart(fig1, use_container_width=True)

    # 3. Eficiencia de Planificación
    df_g3 = df_f.groupby(['GERENCIA', 'DEPARTAMENTO']).agg(
        HH_PLAN_SUM=('HH_PLANIFICADAS', 'sum'), HH_REAL_SUM=('JORNADA_EFECTIVA', 'sum'), CANT_TAREAS=('ID_TAREA', 'count')
    ).reset_index()
    
    df_g3['EFICIENCIA'] = df_g3.apply(lambda row: (row['HH_PLAN_SUM'] / row['HH_REAL_SUM'] * 100) if row['HH_REAL_SUM'] > 0 else 0, axis=1)
    
    fig3 = px.bar(df_g3, x='DEPARTAMENTO', y='EFICIENCIA', color='GERENCIA', custom_data=['CANT_TAREAS', 'HH_REAL_SUM'],
                  title='3. Eficiencia de Planificación (%)', 
                  color_discrete_map={'Gerencia de Operaciones': '#2E7D32', 'Gerencia de Mantenimiento': '#1565C0'})
    fig3.update_traces(hovertemplate='<b>%{x}</b><br>Eficiencia: %{y:.1f}%<br>Actividades: %{customdata[0]}<extra></extra>')
    fig3.add_hline(y=100, line_dash="dash", line_color="red")
    st.plotly_chart(fig3, use_container_width=True)

with c2:
    # 2. Impacto HH por Tipo de Actividad
    df_g2 = df_f[df_f['JORNADA_EFECTIVA'] > 0].groupby(['GERENCIA', 'TIPO_ACTIVIDAD']).agg(
        JORNADA_EFECTIVA=('JORNADA_EFECTIVA', 'sum'), CANTIDAD_TAREAS=('ID_TAREA', 'count')).reset_index()
    
    if not df_g2.empty:
        fig2 = px.treemap(df_g2, path=['GERENCIA', 'TIPO_ACTIVIDAD'], values='JORNADA_EFECTIVA', custom_data=['CANTIDAD_TAREAS'],
                          title='2. Impacto HH por Tipo de Actividad', color_discrete_sequence=px.colors.qualitative.Safe)
        fig2.update_traces(hovertemplate='<b>%{label}</b><br>Horas: %{value:.1f}h<br>Actividades: %{customdata[0]}<extra></extra>')
        st.plotly_chart(fig2, use_container_width=True)

    # 4. Salud del Backlog (Estatus)
    df_g4 = df_f.groupby('ESTATUS').agg(CANT_TAREAS=('ID_TAREA', 'count'), HH_SUM=('JORNADA_EFECTIVA', 'sum')).reset_index()
    
    fig4 = px.pie(df_g4, names='ESTATUS', values='CANT_TAREAS', custom_data=['HH_SUM'], hole=0.5, title='4. Salud del Backlog (Estatus)')
    fig4.update_traces(textinfo='percent+value', hovertemplate='<b>%{label}</b><br>Actividades: %{value}<br>Horas: %{customdata[0]:.1f}h<extra></extra>')
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# --- BLOQUE DE GRÁFICOS (5 al 8) ---
c3, c4 = st.columns(2)

with c3:
    # 5. Esfuerzo Físico por Área
    df_g5 = df_f.groupby('AREA_ORIGEN').agg(HH_SUM=('JORNADA_EFECTIVA', 'sum'), CANT_TAREAS=('ID_TAREA', 'count')).reset_index().sort_values(by='HH_SUM', ascending=True)
    df_g5['TEXTO'] = df_g5.apply(lambda x: f"{x['HH_SUM']:.1f}h ({x['CANT_TAREAS']} act)", axis=1)
    
    fig5 = px.bar(df_g5, x='HH_SUM', y='AREA_ORIGEN', orientation='h', custom_data=['CANT_TAREAS'], title='5. Esfuerzo Físico por Área', text='TEXTO')
    fig5.update_traces(hovertemplate='<b>%{y}</b><br>Horas: %{x:.1f}h<br>Actividades: %{customdata[0]}<extra></extra>')
    st.plotly_chart(fig5, use_container_width=True)

    # 7. Horas Perdidas por Causa
    df_g7 = df_f[df_f['CAUSA_RETRASO'] != 'NINGUNO'].groupby('CAUSA_RETRASO').agg(HH_SUM=('JORNADA_EFECTIVA', 'sum'), CANT_TAREAS=('ID_TAREA', 'count')).reset_index()
    
    if not df_g7.empty and df_g7['HH_SUM'].sum() > 0:
        fig7 = px.pie(df_g7, names='CAUSA_RETRASO', values='HH_SUM', custom_data=['CANT_TAREAS'], hole=0.4, title='7. Horas Perdidas por Causa')
        fig7.update_traces(textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Horas: %{value:.1f}h<extra></extra>')
        st.plotly_chart(fig7, use_container_width=True)
    else:
        st.info("Gráfico 7: Sin horas de retraso reportadas en el departamento o gerencia seleccionada.")

with c4:
    # 6. Top 8 Equipos Críticos
    df_g6 = df_f.groupby('TAG_EQUIPO').agg(HH_SUM=('JORNADA_EFECTIVA', 'sum'), CANT_TAREAS=('ID_TAREA', 'count')).reset_index().sort_values(by='HH_SUM', ascending=False).head(8)
    
    fig6 = px.bar(df_g6, x='TAG_EQUIPO', y='HH_SUM', text='HH_SUM', custom_data=['CANT_TAREAS'], title='6. Top 8 Equipos Críticos', color='HH_SUM', color_continuous_scale='Reds')
    fig6.update_traces(hovertemplate='<b>Equipo: %{x}</b><br>Horas: %{y:.1f}h<br>Intervenciones: %{customdata[0]}<extra></extra>')
    st.plotly_chart(fig6, use_container_width=True)

    # 8. Impacto Económico por Turno
    df_g8 = df_f.groupby('HORARIO_TRABAJO').agg(HH_SUM=('JORNADA_EFECTIVA', 'sum'), CANT_TAREAS=('ID_TAREA', 'count')).reset_index()
    
    fig8 = px.pie(df_g8, names='HORARIO_TRABAJO', values='HH_SUM', custom_data=['CANT_TAREAS'], hole=0.4, title='8. Impacto Económico por Turno')
    fig8.update_traces(textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Horas: %{value:.1f}h<extra></extra>')
    st.plotly_chart(fig8, use_container_width=True)