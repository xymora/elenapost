import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path

# ---------- Ruta del archivo JSON de credenciales ----------
credenciales_path = Path(__file__).parent / "app" / "credenciales.json"

# ---------- Inicialización de Firebase ----------
@st.cache_resource
def iniciar_firebase():
    if not firebase_admin._apps:
        if not credenciales_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {credenciales_path}")
        credenciales = credentials.Certificate(str(credenciales_path))
        firebase_admin.initialize_app(credenciales)
    return firestore.client()

# ---------- Interfaz principal ----------
def main():
    st.set_page_config(page_title="Demo Firebase ElenaPost", layout="centered")
    st.title("📄 Registro de Mensajes")
    st.markdown("Ingresa tu nombre y mensaje para guardarlo en Firebase Firestore.")

    db = None
    try:
        db = iniciar_firebase()
    except Exception as e:
        st.error(f"Error iniciando Firebase: {e}")
        st.stop()

    with st.form("formulario_mensaje"):
        nombre = st.text_input("👤 Nombre")
        mensaje = st.text_area("💬 Mensaje")
        enviar = st.form_submit_button("Guardar")

    if enviar:
        if nombre.strip() == "" or mensaje.strip() == "":
            st.warning("⚠️ Por favor completa todos los campos.")
        else:
            try:
                doc_ref = db.collection("mensajes").document()
                doc_ref.set({
                    "nombre": nombre.strip(),
                    "mensaje": mensaje.strip()
                })
                st.success("✅ Mensaje guardado correctamente.")
            except Exception as e:
                st.error(f"❌ Error al guardar mensaje: {e}")

    st.subheader("📋 Mensajes guardados")
    try:
        docs = db.collection("mensajes").stream()
        for doc in docs:
            data = doc.to_dict()
            st.write(f"**{data.get('nombre')}**: {data.get('mensaje')}")
    except Exception as e:
        st.warning(f"No se pudieron cargar los mensajes: {e}")

if __name__ == "__main__":
    main()
