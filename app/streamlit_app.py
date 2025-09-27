import streamlit as st
import json
from google.oauth2 import service_account
from google.cloud import firestore

# 🔐 JSON embebido sin modificar
FIREBASE_JSON = r"""
{
  "type": "service_account",
  "project_id": "elena-36be5",
  "private_key_id": "e5bac82a9d9034efeab75d1e8c550398b33f3512",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkq...<TRUNCADO>\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@elena-36be5.iam.gserviceaccount.com",
  "client_id": "117586238746856040628",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc@elena-36be5.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
""".strip()

# 1. Conectar a Firestore
try:
    sa_info = json.loads(FIREBASE_JSON)
    creds = service_account.Credentials.from_service_account_info(sa_info)
    db = firestore.Client(project=sa_info["project_id"], credentials=creds)
    st.success("✅ Conectado a Firestore.")
except Exception as e:
    st.error(f"❌ Error al conectar: {e}")
    st.stop()

# 2. Formulario Streamlit
st.title("Registrar datos en Firestore")

with st.form("registro"):
    nombre = st.text_input("Nombre")
    correo = st.text_input("Correo")
    telefono = st.text_input("Teléfono")
    folio = st.text_input("Folio")
    fecha = st.date_input("Fecha")
    maquina = st.number_input("Máquina", step=1, min_value=0)
    contactado = st.selectbox("¿Contactado?", ["", "SI", "NO"])
    posible = st.selectbox("¿Posible?", ["", "SI", "NO"])
    enviar = st.form_submit_button("Guardar")

    if enviar:
        try:
            datos = {
                "NOMBRE": nombre,
                "CORREO": correo,
                "TELEFONO": telefono,
                "FOLIO": folio,
                "FECHA": str(fecha),
                "MAQUINA": int(maquina),
                "CONTACTADO": contactado,
                "POSIBLE": posible
            }
            doc_ref = db.collection("leads").add(datos)
            st.success(f"✅ Documento guardado con ID: {doc_ref[1].id}")
            st.write(datos)
        except Exception as e:
            st.error(f"❌ Error al guardar en Firestore: {e}")
