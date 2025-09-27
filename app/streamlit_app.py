import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import date

# Inicializar conexión con Firebase
@st.cache_resource
def init_firestore():
    cred = credentials.Certificate("app/serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firestore()

# Nombre de la colección en Firestore
COLLECTION = "leads"

# Título de la app
st.title("📋 Registro manual de contactos")

# Formulario manual
with st.form("registro_form"):
    st.subheader("Ingresa los datos del nuevo contacto")

    nombre = st.text_input("Nombre completo")
    correo = st.text_input("Correo electrónico")
    telefono = st.text_input("Teléfono")
    fecha = st.date_input("Fecha de contacto", value=date.today())
    turno = st.selectbox("Turno", ["MATUTINO", "VESPERTINO"])
    maquina = st.text_input("Número de máquina")
    folio = st.text_input("Folio asignado")
    codigo_postal = st.text_input("Código Postal")

    submit = st.form_submit_button("Guardar en Firestore")

# Guardar datos al hacer submit
if submit:
    if not nombre or not correo or not folio:
        st.warning("❗ Los campos nombre, correo y folio son obligatorios.")
    else:
        doc_ref = db.collection(COLLECTION).document()
        doc_ref.set({
            "nombre": nombre,
            "correo": correo,
            "telefono": telefono,
            "fecha": str(fecha),
            "turno": turno,
            "maquina": maquina,
            "folio": folio,
            "codigo_postal": codigo_postal,
        })
        st.success("✅ ¡Contacto guardado en Firestore!")
