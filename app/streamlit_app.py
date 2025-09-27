import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

# ---------------------------
# Inicialización de Firebase
# ---------------------------
def iniciar_firebase():
    if not firebase_admin._apps:
        cred_json = st.secrets["firebase_service_account"]

        # Corregido: asegurar que es un diccionario
        if isinstance(cred_json, str):
            cred_json = json.loads(cred_json)

        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred)
    return firestore.client()

# ---------------------------
# Guardar en Firestore
# ---------------------------
def guardar_datos(db, datos):
    try:
        doc_ref = db.collection("registros_enarm").document(datos["folio"])
        doc_ref.set(datos)
        return True, "Datos guardados correctamente ✅"
    except Exception as e:
        return False, f"Error al guardar datos: {e}"

# ---------------------------
# Interfaz gráfica Streamlit
# ---------------------------
def main():
    st.set_page_config(page_title="Registro ENARM", layout="centered")
    st.title("🩺 Registro ENARM")
    st.markdown("Por favor ingresa los siguientes datos para registrar tu información:")

    with st.form("registro_formulario"):
        folio = st.text_input("📄 Folio")
        curp = st.text_input("🆔 CURP")
        nombre = st.text_input("👤 Nombre completo")
        fecha_examen = st.text_input("📅 Fecha del examen")
        sede = st.text_input("📍 Sede")
        turno = st.selectbox("🕐 Turno", ["MATUTINO", "VESPERTINO"])
        puntaje = st.text_input("📊 Puntaje")

        submit_btn = st.form_submit_button("Registrar")

        if submit_btn:
            campos = [folio, curp, nombre, fecha_examen, sede, turno, puntaje]
            if any(c.strip() == "" for c in campos):
                st.warning("⚠️ Todos los campos son obligatorios.")
            else:
                try:
                    puntaje_float = round(float(puntaje), 4)
                    datos = {
                        "folio": folio,
                        "curp": curp,
                        "nombre": nombre,
                        "fecha_examen": fecha_examen,
                        "sede": sede,
                        "turno": turno,
                        "puntaje": puntaje_float
                    }
                    db = iniciar_firebase()
                    exito, mensaje = guardar_datos(db, datos)
                    if exito:
                        st.success(mensaje)
                    else:
                        st.error(mensaje)
                except ValueError:
                    st.error("❌ El puntaje debe ser un número decimal válido.")

if __name__ == "__main__":
    main()
