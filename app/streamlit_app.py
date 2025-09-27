import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from scipy.stats import gaussian_kde
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import concurrent.futures

# Firebase
import firebase_admin
from firebase_admin import credentials, firestore

# ================================
# 🔐 Inicializar Firebase desde st.secrets
# ================================
firestore_active = False
collection_name = st.secrets.get("collection_name", "clients")  # cámbialo en secrets si quieres

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    firestore_active = True
except Exception as e:
    st.warning(f"⚠️ Firebase no disponible: {e}")
    firestore_active = False

# ================================
# 🔄 Cargar datos desde Firestore (con timeout) o CSV
# ================================
def try_firestore_fetch():
    try:
        rows = []
        for doc in db.collection(collection_name).stream():
            d = doc.to_dict()
            d["id"] = doc.id
            rows.append(d)
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_data():
    # 1) Firestore con timeout
    if firestore_active:
        try:
            with concurrent.futures.ThreadPoolExecutor() as ex:
                fut = ex.submit(try_firestore_fetch)
                df = fut.result(timeout=6)
                if not df.empty:
                    return df
                st.warning("Firestore devolvió vacío. Usando CSV de respaldo.")
        except Exception:
            st.warning("⏱️ Firestore no respondió a tiempo. Usando CSV.")
    # 2) CSV local de respaldo
    for path in [
        "notebooks/segmentation_data_recruitment.csv",
        "segmentation_data_recruitment.csv",
        "data/segmentation_data_recruitment.csv",
    ]:
        try:
            return pd.read_csv(path)
        except Exception:
            pass
    st.error("❌ No se pudo cargar ni Firestore ni el CSV local.")
    return pd.DataFrame()

df = load_data()

# ====================================
# Normalizaciones mínimas
# ====================================
num_cols = ['avg_amount_withdrawals', 'avg_purchases_per_week', 'age']
for c in num_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

# Asegura columna 'user' (si no existe, crea una)
if "user" not in df.columns:
    df["user"] = df.index.astype(str)

# ====================================
# 🎬 INTERFAZ Streamlit
# ====================================
st.set_page_config(page_title="Dashboard de Clientes Bancarios", layout="wide")
st.title("🏦 Dashboard de Clientes Bancarios")

if df.empty:
    st.warning("No hay datos disponibles.")
    st.stop()

# KPIs (tolerantes a faltantes)
total_clients   = len(df)
avg_withdrawals = df.get('avg_amount_withdrawals', pd.Series([0]*len(df))).mean()
avg_purchases   = df.get('avg_purchases_per_week', pd.Series([0]*len(df))).mean()
avg_age         = df.get('age', pd.Series([0]*len(df))).mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Clientes", f"{total_clients:,}")
c2.metric("Retiro Promedio", f"${avg_withdrawals:,.2f}")
c3.metric("Compras/Semana Prom.", f"{avg_purchases:.2f}")
c4.metric("Edad Promedio", f"{avg_age:.1f} años")

# ====================================
# Clasificación crediticia y binning
# ====================================
def classify_credit(df: pd.DataFrame) -> pd.DataFrame:
    if not {'avg_amount_withdrawals','avg_purchases_per_week'}.issubset(df.columns):
        df['credit_score'] = 'N/A'
        df['compras_binned'] = 'N/A'
        return df
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
# Sidebar: filtros y búsqueda
# ====================================
with st.sidebar:
    st.header("🔍 Filtros personalizados")
    overall_order = ['🔵 Premium Credit','🟢 Basic Credit','🟡 Moderate Risk','🔴 High Risk']
    avail_scores = [c for c in overall_order if c in df['credit_score'].unique()]
    selected_scores = st.multiselect("Credit Score", avail_scores, default=avail_scores)

    if 'user_search' not in st.session_state:
        st.session_state['user_search'] = ''
    if 'search_active' not in st.session_state:
        st.session_state['search_active'] = False

    search_title = st.text_input("👤 Usuario exacto", key='user_search')
    b1, b2 = st.columns(2)
    if b1.button("Buscar"):
        st.session_state['search_active'] = True
    if b2.button("Borrar"):
        st.session_state['user_search'] = ''
        st.session_state['search_active'] = False

# Filtrado
df_filtered = df[df['credit_score'].isin(selected_scores)].copy()
if st.session_state['search_active'] and st.session_state['user_search']:
    df_filtered = df_filtered[df_filtered['user'] == st.session_state['user_search']]

st.markdown(f"Filtrados: **{len(df_filtered):,}** de **{len(df):,}** clientes")

# Tabla
st.subheader("📋 Clientes mostrados")
if not df_filtered.empty:
    base_cols = [
        'user','age','credit_score','avg_amount_withdrawals',
        'avg_purchases_per_week','compras_binned'
    ]
    other_cols = [c for c in df_filtered.columns if c not in base_cols]
    show_cols = [c for c in base_cols + other_cols if c in df_filtered.columns]
    st.dataframe(df_filtered[show_cols], use_container_width=True)
else:
    st.warning("No hay clientes para mostrar con los filtros actuales.")

# Descargar CSV
csv = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button("💾 Descargar CSV", data=csv, file_name="clientes_filtrados.csv", use_container_width=True)

# ====================================
# Gráficas de perfil para 1 usuario
# ====================================
if st.session_state['search_active'] and st.session_state['user_search'] and len(df_filtered) == 1:
    user_df = df_filtered.iloc[0]
    st.subheader(
        f"📈 Gráficas para `{st.session_state['user_search']}` "
        f"(Edad: {int(user_df.get('age',0))} | Score: {user_df.get('credit_score','?')})"
    )

    if {'avg_amount_withdrawals','avg_purchases_per_week','age'}.issubset(df.columns):
        pct_retiros = (df['avg_amount_withdrawals'] <= user_df['avg_amount_withdrawals']).mean() * 100
        pct_compras = (df['avg_purchases_per_week'] <= user_df['avg_purchases_per_week']).mean() * 100

        fig1 = px.histogram(df, x='avg_amount_withdrawals', nbins=20,
                            title='Distribución Retiros (tu posición)')
        fig1.add_vline(x=user_df['avg_amount_withdrawals'], line_dash='dash',
                       annotation_text='Tú', annotation_position='top right')
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.histogram(df, x='avg_purchases_per_week', nbins=20,
                            title='Distribución Compras/Semana (tu posición)')
        fig2.add_vline(x=user_df['avg_purchases_per_week'], line_dash='dash',
                       annotation_text='Tú', annotation_position='top right')
        st.plotly_chart(fig2, use_container_width=True)

        radar_df = pd.DataFrame({
            'Feature': ['Retiros','Compras/Semana','Edad'],
            'Value': [user_df['avg_amount_withdrawals'],
                      user_df['avg_purchases_per_week'],
                      user_df.get('age',0)]
        })
        fig3 = px.line_polar(radar_df, r='Value', theta='Feature', line_close=True,
                             title='Perfil Radar del Usuario')
        st.plotly_chart(fig3, use_container_width=True)

# ====================================
# Gráficas generales
# ====================================
overall_order = ['🔵 Premium Credit','🟢 Basic Credit','🟡 Moderate Risk','🔴 High Risk']
cnt = df_filtered['credit_score'].value_counts().reindex(overall_order, fill_value=0)
fig = px.bar(x=cnt.index, y=cnt.values, color=cnt.index, text=cnt.values,
             title='Distribución por Credit Score')
fig.update_layout(showlegend=False)
fig.update_traces(textposition='outside')
st.plotly_chart(fig, use_container_width=True)

# ====================================
# Clustering (K=4) — si están las 3 columnas
# ====================================
st.subheader("🤖 Clustering K-Means (K=4)")
need = ['avg_amount_withdrawals','avg_purchases_per_week','age']
if all(c in df.columns for c in need):
    scaled = StandardScaler().fit_transform(df[need])
    km = KMeans(n_clusters=4, random_state=42).fit(scaled)
    df['cluster'] = km.labels_
    fig3d = px.scatter_3d(df, x='avg_amount_withdrawals', y='avg_purchases_per_week', z='age',
                          color='cluster', title='Clustering 3D')
    st.plotly_chart(fig3d, use_container_width=True)
else:
    st.info("Para clustering se requieren: avg_amount_withdrawals, avg_purchases_per_week y age.")
