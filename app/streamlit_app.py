import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

# Inicializar Firebase
@st.cache_resource
def iniciar_firebase():
    if not firebase_admin._apps:
        cred_json = st.secrets["firebase_service_account"]
        if isinstance(cred_json, str):
            cred_json = json.loads(cred_json)
        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred)
    return firestore.client()

# Guardar en Firestore
def guardar_datos(db, datos):
    try:
        doc_ref = db.collection("registros_enarm").document(str(datos["folio"]))
        doc_ref.set(datos)
        return True
    except Exception as e:
        st.error(f"Ocurrió un error al guardar los datos: {e}")
        return False

# App principal
def main():
    st.title("Registro ENARM 2025")
    st.write("Por favor ingresa los siguientes datos para registrar tu información:")

    db = iniciar_firebase()

    folio = st.text_input("📄 Folio")
    curp = st.text_input("🆔 CURP")
    nombre = st.text_input("👤 Nombre completo")
    fecha_examen = st.text_input("📅 Fecha del examen")
    sede = st.text_input("📍 Sede")
    turno = st.selectbox("⏰ Turno", ["MATUTINO", "VESPERTINO"])
    puntaje_str = st.text_input("📊 Puntaje")

    # Validación del puntaje
    try:
        puntaje = float(puntaje_str)
        puntaje_valido = True
    except ValueError:
        puntaje_valido = False
        st.error("❌ El puntaje debe ser un número decimal válido.")

    if st.button("Registrar") and puntaje_valido:
        datos = {
            "folio": folio,
            "curp": curp,
            "nombre_completo": nombre,
            "fecha_examen": fecha_examen,
            "sede": sede,
            "turno": turno,
            "puntaje": puntaje
        }
        exito = guardar_datos(db, datos)
        if exito:
            st.success("✅ Datos registrados correctamente en Firestore.")

if __name__ == "__main__":
    main()
