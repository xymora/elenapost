import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# ---------- INICIAR FIREBASE -----------
@st.cache_resource
def iniciar_firebase():
    try:
        # Reemplaza con tu archivo real
        cred = credentials.Certificate("elenapost/app/credenciales.json")
        firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Error iniciando Firebase: {e}")
        st.stop()

# ---------- FUNCIÓN PRINCIPAL ----------
def main():
    st.title("Registro ENARM - Streamlit")

    st.markdown("Por favor ingresa los siguientes datos para registrar tu información:")

    folio = st.text_input("📄 Folio")
    curp = st.text_input("🆔 CURP")
    nombre = st.text_input("👤 Nombre completo")
    fecha_examen = st.text_input("📅 Fecha del examen")
    sede = st.text_input("📍 Sede")
    turno = st.selectbox("🕓 Turno", ["MATUTINO", "VESPERTINO"])
    puntaje_input = st.text_input("📈 Puntaje")

    if st.button("Registrar"):
        # Validaciones
        try:
            puntaje = float(puntaje_input)
        except ValueError:
            st.error("❌ El puntaje debe ser un número decimal válido.")
            return

        if not (folio and curp and nombre and fecha_examen and sede):
            st.error("❌ Todos los campos deben estar completos.")
            return

        try:
            fecha_iso = datetime.strptime(fecha_examen.strip(), "%d de %B de %Y").date().isoformat()
        except ValueError:
            try:
                fecha_iso = datetime.strptime(fecha_examen.strip(), "%Y-%m-%d").date().isoformat()
            except:
                fecha_iso = None

        db = iniciar_firebase()

        data = {
            "folio": folio,
            "curp": curp,
            "nombre": nombre,
            "fecha_examen": fecha_examen,
            "fecha_iso": fecha_iso,
            "sede": sede,
            "turno": turno,
            "puntaje": puntaje
        }

        try:
            db.collection("leads").add(data)
            st.success("✅ Registro exitoso en Firebase.")
        except Exception as e:
            st.error(f"❌ Error al guardar en Firebase: {e}")

if __name__ == "__main__":
    main()
