# --- PRUEBA FIRESTORE (modo cliente nativo, no Firebase Admin) ---
# Pega este bloque en tu streamlit_app.py (por ejemplo, en la zona de Diagnóstico)

import json
import streamlit as st
from google.oauth2 import service_account
from google.cloud import firestore as gfs

def probar_firestore_cliente(creds_dict: dict):
    """
    Crea un cliente nativo de Firestore usando google.oauth2.service_account
    y guarda/lee un documento de prueba en la colección 'leads'.
    """
    # 1) Construir credenciales y cliente nativo
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    project_id = creds_dict.get("project_id")
    client = gfs.Client(project=project_id, credentials=credentials)

    # 2) Documento de prueba (puedes cambiar los campos si quieres)
    data = {
        "MAQUINA":   2,
        "FECHA":     "2025-09-26",
        "NOMBRE":    "marca reyes",
        "CORREO":    "omarcosss@hotmail.com",
        "TELEFONO":  "5522100885",
        "FOLIO":     "1183",
        "CONTACTADO":"SI",
        "POSIBLE":   ""
    }

    # 3) Guardar con auto-ID
    doc_ref = client.collection("leads").add(data)[1]
    saved_id = doc_ref.id

    # 4) Leer para comprobar
    got = doc_ref.get().to_dict()
    return project_id, saved_id, got

# ====== Botón en el sidebar para ejecutar la prueba ======
with st.sidebar:
    st.markdown("#### 🔌 Prueba Firestore (cliente nativo)")
    if st.button("Probar (cliente nativo)"):
        try:
            # Prioriza st.secrets["firebase"]; si no, usa el .streamlit/secrets.toml ya cargado por tu app
            try:
                creds_dict = dict(st.secrets["firebase"])
            except Exception:
                # Si ya tienes _creds en tu app (del init_firebase), úsalo:
                #   db, _creds, _source, _tried = init_firebase()
                # Si no, vuelve a lanzar un error claro:
                if "_creds" in globals() and isinstance(_creds, dict):
                    creds_dict = _creds
                else:
                    raise RuntimeError(
                        "No encuentro credenciales. Asegúrate de tener [firebase] en st.secrets "
                        "o reutiliza _creds del init_firebase()."
                    )

            project_id, saved_id, got = probar_firestore_cliente(creds_dict)
            st.success(f"OK proyecto: {project_id} • Doc ID: {saved_id}")
            st.code(json.dumps(got, indent=2, ensure_ascii=False))
        except Exception as e:
            st.error(f"❌ Error en prueba cliente nativo: {e}")
