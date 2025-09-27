import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import gaussian_kde
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import logging

# -----------------------------------
# Configuración de logging
# -----------------------------------
logging.basicConfig(
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# -----------------------------------
# Configurar Kaleido para exportar imágenes (para ZIP)
# -----------------------------------
import plotly.io as pio
try:
    pio.kaleido.scope.default_format = "png"
except Exception as e:
    logger.warning(f"No se pudo configurar Kaleido: {e}")

# -----------------------------------
# Configuración de la página
# -----------------------------------
st.set_page_config(
    page_title="Dashboard de Clientes Bancarios",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("🏦 Dashboard de Clientes Bancarios")

# ====================================
# Función de carga de datos con cache
# ====================================
DATA_URL = "https://covenantaegis.com/segmentation_data_recruitment.csv"

@st.cache_data(show_spinner=False)
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    for col in ['avg_amount_withdrawals', 'avg_purchases_per_week']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

# -----------------------------------
# Cargar datos y mostrar KPI iniciales
# -----------------------------------
try:
    df = load_data(DATA_URL)
    total_clients = len(df)
    avg_withdrawals = df['avg_amount_withdrawals'].mean()
    avg_purchases = df['avg_purchases_per_week'].mean()
    avg_age = df['age'].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Clientes", f"{total_clients:,}")
    c2.metric("Retiro Promedio", f"${avg_withdrawals:,.2f}")
    c3.metric("Compras/Semana Prom.", f"{avg_purchases:.2f}")
    c4.metric("Edad Promedio", f"{avg_age:.1f} años")

    logger.info(f"Datos cargados: {total_clients} registros")
except Exception as e:
    logger.error(f"Error al cargar datos: {e}")
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# ====================================
# Clasificación crediticia y binning
# ====================================
def classify_credit(df: pd.DataFrame) -> pd.DataFrame:
    conditions = [
        (df['avg_amount_withdrawals'] > 50000) & (df['avg_purchases_per_week'] == 0),
        (df['avg_amount_withdrawals'] > 20000) & (df['avg_purchases_per_week'] <= 1),
        (df['avg_amount_withdrawals'] > 10000)
    ]
    choices = ['🔵 Premium Credit', '🟢 Basic Credit', '🟡 Moderate Risk']
    df['credit_score'] = np.select(conditions, choices, default='🔴 High Risk')
    df['compras_binned'] = pd.cut(
        df['avg_purchases_per_week'], bins=[0,1,2,3,4,5,np.inf],
        labels=["0","1","2","3","4","5+"], right=False
    )
    return df

df = classify_credit(df)

# ====================================
# Sidebar: filtros y búsqueda de usuario
# ====================================
st.sidebar.header("🔍 Filtros y Búsqueda")

overall_order = ['🔵 Premium Credit','🟢 Basic Credit','🟡 Moderate Risk','🔴 High Risk']
avail_scores = [c for c in overall_order if c in df['credit_score'].unique()]
selected_scores = st.sidebar.multiselect(
    "Credit Score", avail_scores, default=avail_scores
)

if 'user_search' not in st.session_state:
    st.session_state['user_search'] = ''
if 'search_active' not in st.session_state:
    st.session_state['search_active'] = False
user_input = st.sidebar.text_input("👤 Usuario exacto", key='user_search')
btn1, btn2 = st.sidebar.columns(2)

def clear_search():
    st.session_state['user_search'] = ''
    st.session_state['search_active'] = False

search_clicked = btn1.button("Buscar", key='search_btn')
clear_clicked = btn2.button("Borrar", key='clear_btn', on_click=clear_search)
if search_clicked:
    st.session_state['search_active'] = True

# ====================================
# Filtrar DataFrame
# ====================================
df_filtered = df[df['credit_score'].isin(selected_scores)].copy()
if st.session_state['search_active'] and st.session_state['user_search']:
    df_filtered = df_filtered[df_filtered['user'] == st.session_state['user_search']]

st.markdown(f"Filtrados: **{len(df_filtered):,}** de **{len(df):,}** clientes")

# ====================================
# Vista de tabla de clientes
# ====================================
st.subheader("📋 Clientes mostrados")
if not df_filtered.empty:
    base_cols = ['user','age','index','credit_score','user_type','registration_channel','creation_flow','creation_date','avg_amount_withdrawals']
    dep_cols = [c for c in df_filtered.columns if 'deposit' in c.lower()]
    for dc in dep_cols:
        if dc not in base_cols:
            base_cols.append(dc)
    other_cols = sorted([c for c in df_filtered.columns if c not in base_cols])
    st.dataframe(df_filtered[base_cols+other_cols], use_container_width=True)
else:
    st.warning("No hay clientes para mostrar con los filtros actuales.")

# Botón de descarga CSV
csv = df_filtered.to_csv(index=False).encode('utf-8')
st.download_button("💾 Descargar CSV", data=csv, file_name='clientes_filtrados.csv')

# ====================================
# Gráficas de perfil al filtrar un usuario
# ====================================
if st.session_state['search_active'] and st.session_state['user_search'] and len(df_filtered) == 1:
    user_df = df_filtered.iloc[0]
    st.subheader(
        f"📈 Gráficas de crédito para `{st.session_state['user_search']}` "
        f"(Edad: {int(user_df['age'])} años | Index: {user_df['index']} | Score: {user_df['credit_score']})"
    )

    # Calcular percentiles del usuario
    pct_retiros = (df['avg_amount_withdrawals'] <= user_df['avg_amount_withdrawals']).mean() * 100
    pct_compras = (df['avg_purchases_per_week'] <= user_df['avg_purchases_per_week']).mean() * 100
    pct_edad = (df['age'] <= user_df['age']).mean() * 100

    # 1) Histograma de retiros
    fig1 = px.histogram(
        df, x='avg_amount_withdrawals', nbins=20,
        title='Distribución Retiros (tu posición)'
    )
    fig1.add_vline(
        x=user_df['avg_amount_withdrawals'],
        line_dash='dash', annotation_text='Tú', annotation_position='top right'
    )
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown(
        f"**Explicación:** El cliente retiró un promedio de **${user_df['avg_amount_withdrawals']:,.2f}**, "
        f"ubicándose en el percentil **{pct_retiros:.1f}%** de todos los clientes."
    )

    # 2) Histograma de compras/semana
    fig2 = px.histogram(
        df, x='avg_purchases_per_week', nbins=20,
        title='Distribución Compras/Semana (tu posición)'
    )
    fig2.add_vline(
        x=user_df['avg_purchases_per_week'],
        line_dash='dash', annotation_text='Tú', annotation_position='top right'
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown(
        f"**Explicación:** El cliente realiza en promedio **{user_df['avg_purchases_per_week']:.2f}** compras/semana, "
        f"situándose en el percentil **{pct_compras:.1f}%** frente a la base."
    )

    # 3) Radar chart
    radar_df = pd.DataFrame({
        'Feature': ['Retiros','Compras/Semana','Edad'],
        'Value': [user_df['avg_amount_withdrawals'], user_df['avg_purchases_per_week'], user_df['age']]
    })
    fig3 = px.line_polar(
        radar_df, r='Value', theta='Feature', line_close=True,
        title='Perfil Radar del Usuario'
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown(
        f"**Explicación:** Muestra simultáneamente retiros (${user_df['avg_amount_withdrawals']:,.2f}), "
        f"compras/semana ({user_df['avg_purchases_per_week']:.2f}) y edad ({int(user_df['age'])} años), "
        "para evaluar desequilibrios."
    )

    # 4) Comparativa vs mediana
    medians = df[['avg_amount_withdrawals','avg_purchases_per_week','age']].median()
    comp_df = pd.DataFrame({
        'Metric': ['Retiros','Compras/Semana','Edad'],
        'Usuario': [user_df['avg_amount_withdrawals'], user_df['avg_purchases_per_week'], user_df['age']],
        'Mediana': medians.values
    })
    fig4 = px.bar(
        comp_df, x='Metric', y=['Usuario','Mediana'], barmode='group',
        title='Usuario vs Mediana del Dataset'
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown(
        f"**Explicación:** Para retiros, compras/semana y edad, el cliente versus mediana: "
        f"{user_df['avg_amount_withdrawals']:,.0f} vs {medians['avg_amount_withdrawals']:,.0f}, "
        f"{user_df['avg_purchases_per_week']:.2f} vs {medians['avg_purchases_per_week']:.2f}, "
        f"{user_df['age']} vs {int(medians['age'])}."
    )

    # 5) Pie de Credit Scores global
    score_counts = df['credit_score'].value_counts().reindex(overall_order).reset_index()
    score_counts.columns = ['credit_score','count']
    fig5 = px.pie(
        score_counts, names='credit_score', values='count',
        title='Distribución Global de Credit Scores'
    )
    st.plotly_chart(fig5, use_container_width=True)
    pct_score = (score_counts.set_index('credit_score').loc[user_df['credit_score'],'count'] / len(df)) * 100
    st.markdown(
        f"**Explicación:** El cliente pertenece al {pct_score:.1f}% de usuarios con score `{user_df['credit_score']}` en la base."
    )

# ====================================
# Gráficas generales
# ====================================
if selected_scores:
    cnt = df_filtered['credit_score'].value_counts().reindex(overall_order, fill_value=0)
    fig = px.bar(
        x=cnt.index, y=cnt.values, color=cnt.index, text=cnt.values,
        title='Distribución por Credit Score'
    )
    fig.update_layout(showlegend=False)
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# ====================================
# Análisis Financiero por Credit Score
# ====================================
st.subheader("📊 Análisis Financiero por Credit Score")
for score in selected_scores:
    sub = df_filtered[df_filtered['credit_score'] == score]
    if len(sub) > 0:
        st.markdown(f"### {score}")
        a, b, c = st.columns(3)
        with a:
            f1 = px.line(sub.sort_values('avg_amount_withdrawals'),
                         y='avg_amount_withdrawals',
                         title='Retiros promedio', height=250)
            st.plotly_chart(f1, use_container_width=True)
        with b:
            vc = sub['compras_binned'].value_counts().sort_index()
            f2 = px.bar(x=vc.index.astype(str), y=vc.values,
                        text=vc.values,
                        labels={'x':'Compras','y':'Cantidad'},
                        title='Compras promedio/semana', height=250)
            f2.update_traces(textposition='outside')
            st.plotly_chart(f2, use_container_width=True)
        with c:
            if len(sub['age']) > 1:
                kde = gaussian_kde(sub['age'])
                xs = np.linspace(sub['age'].min(), sub['age'].max(), 100)
                ys = kde(xs)
                f3 = px.area(x=xs, y=ys, title='Distribución de edad', height=250)
                st.plotly_chart(f3, use_container_width=True)
            else:
                st.write('Distribución de edad: solo un valor')

# ====================================
# Clustering (K=4)
# ====================================
st.subheader("🤖 Clustering K-Means (K=4)")
features = ['avg_amount_withdrawals','avg_purchases_per_week','age']
scaled = StandardScaler().fit_transform(df[features])
km = KMeans(n_clusters=4, random_state=42).fit(scaled)
df['cluster'] = km.labels_
fig6 = px.scatter_3d(
    df, x='avg_amount_withdrawals', y='avg_purchases_per_week', z='age',
    color='cluster', title='Clustering 3D'
)
st.plotly_chart(fig6, use_container_width=True)

logger.info("Dashboard renderizado exitosamente.")
# ====================================
# Fin del Dashboard de Data Science
