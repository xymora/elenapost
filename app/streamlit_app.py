import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

# --------------------------
# Autenticación con Firebase
# --------------------------
if not firebase_admin._apps:
    firebase_info = json.loads(st.secrets["firebase_service_account"])
    cred = credentials.Certificate(firebase_info)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --------------------------
# Interfaz de Streamlit
# --------------------------
st.set_page_config(page_title="Registro de folio", layout="centered")

st.title("📋 Registro de datos ENARM")

with st.form("registro_form"):
    folio = st.text_input("Folio")
    curp = st.text_input("CURP")
    nombre = st.text_input("Nombre completo")
    fecha = st.text_input("Fecha de examen")
    sede = st.text_input("Sede")
    turno = st.selectbox("Turno", ["MATUTINO", "VESPERTINO"])
    puntaje = st.text_input("Puntaje")

    enviar = st.form_submit_button("Guardar en Firebase")

if enviar:
    if not all([folio, curp, nombre, fecha, sede, turno, puntaje]):
        st.warning("Todos los campos son obligatorios.")
    else:
        try:
            doc_ref = db.collection("registros").document(folio)
            doc_ref.set({
                "folio": folio,
                "curp": curp,
                "nombre": nombre,
                "fecha": fecha,
                "sede": sede,
                "turno": turno,
                "puntaje": float(puntaje)
            })
            st.success("✅ Datos guardados correctamente en Firebase.")
        except Exception as e:
            st.error(f"❌ Error al guardar los datos: {e}")
