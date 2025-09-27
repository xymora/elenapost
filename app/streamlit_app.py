import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
import json
import os
from datetime import datetime

# ---------------------------
# Inicializar Firebase desde credenciales.json
# ---------------------------
@st.cache_resource
def iniciar_firestore():
    try:
        ruta_json = os.path.join(os.path.dirname(__file__), "credenciales.json")
        with open(ruta_json, "r", encoding="utf-8") as f:
            sa_info = json.load(f)
        creds = service_account.Credentials.from_service_account_info(sa_info)
        project_id = sa_info["project_id"]
        client = firestore.Client(project=project_id, credentials=creds)
        return client
    except Exception as e:
        st.error(f"Error iniciando Firebase: {e}")
        return None

# ---------------------------
# Guardar en Firestore
# ---------------------------
def guardar_en_firestore(client, datos):
    try:
        doc_ref = client.collection("leads").document()  # Auto-ID
        doc_ref.set(datos)
        return True, doc_ref.id
    except Exception as e:
        return False, str(e)

# ---------------------------
# Interfaz Streamlit
# ---------------------------
def main():
    st.set_page_config(page_title="Registro ENARM", layout="centered")
    st.title("📋 Registro ENARM (Cloud Firestore)")

    with st.form("registro_formulario"):
        folio = st.text_input("📄 Folio")
        curp = st.text_input("🆔 CURP")
        nombre = st.text_input("👤 Nombre completo")
        fecha_examen = st.date_input("📅 Fecha del examen")
        sede = st.text_input("📍 Sede")
        turno = st.selectbox("🕐 Turno", ["MATUTINO", "VESPERTINO"])
        puntaje = st.text_input("📊 Puntaje")
        contacto = st.selectbox("📞 ¿Te contactamos?", ["SI", "NO"])
        correo = st.text_input("✉️ Correo electrónico")
        telefono = st.text_input("📱 Teléfono")
        posible = st.selectbox("📈 ¿Posible ingreso?", ["", "SI", "NO"])

        submit = st.form_submit_button("Registrar")

    if submit:
        if any(x.strip() == "" for x in [folio, curp, nombre, sede, puntaje, contacto, correo, telefono]):
            st.warning("⚠️ Todos los campos obligatorios deben estar completos.")
            return

        try:
            puntaje_valor = round(float(puntaje), 4)
        except ValueError:
            st.error("❌ El puntaje debe ser un número decimal válido.")
            return

        datos = {
            "MAQUINA": 1,
            "FECHA": fecha_examen.strftime("%Y-%m-%d"),
            "NOMBRE": nombre,
            "CORREO": correo,
            "TELEFONO": telefono,
            "FOLIO": folio,
            "CONTACTADO": contacto,
            "POSIBLE": posible,
            "CURP": curp,
            "SEDE": sede,
            "TURNO": turno,
            "PUNTAJE": puntaje_valor
        }

        db = iniciar_firestore()
        if db:
            ok, result = guardar_en_firestore(db, datos)
            if ok:
                st.success(f"✅ Guardado correctamente con ID: {result}")
            else:
                st.error(f"❌ Error al guardar en Firestore: {result}")

if __name__ == "__main__":
    main()
