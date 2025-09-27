import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# ---------- Autenticación con Firebase ----------
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")  # Asegúrate que este archivo esté en tu repo
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------- Formulario ----------
st.title("Registro de Resultados ENARM")

folio = st.text_input("Folio")
curp = st.text_input("CURP")
nombre = st.text_input("Nombre completo")
fecha_examen = st.text_input("Fecha examen (ej. 23 de Septiembre de 2025)")
sede = st.text_input("Sede")
turno = st.selectbox("Turno", ["MATUTINO", "VESPERTINO"])
puntaje = st.text_input("Puntaje")

if st.button("Guardar registro"):
    if folio and curp and nombre and fecha_examen and sede and turno and puntaje:
        try:
            doc_ref = db.collection("resultados_enarm").document(folio)
            doc_ref.set({
                "folio": folio,
                "curp": curp,
                "nombre": nombre,
                "fecha_examen": fecha_examen,
                "sede": sede,
                "turno": turno,
                "puntaje": float(puntaje),
                "timestamp": datetime.now()
            })
            st.success("✅ Registro guardado exitosamente.")
        except Exception as e:
            st.error(f"❌ Error al guardar: {e}")
    else:
        st.warning("⚠️ Por favor completa todos los campos.")
