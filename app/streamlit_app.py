# app/streamlit_app.py
import os
import json
import time
import hashlib
from datetime import datetime, date, timezone, timedelta
from typing import Optional, Tuple

import streamlit as st

# Firebase Admin
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.storage.bucket import Bucket  # requerido por type hints

APP_TITLE = "Elenapost - Registro de Leads"
LEADS_COLLECTION = "leads"
BUCKET_ENV_KEY = "FIREBASE_STORAGE_BUCKET"  # opcional si quieres usar Storage


# ---------------- Credenciales ----------------
def _load_creds() -> Optional[dict]:
    try:
        return dict(st.secrets["firebase_service_account"])
    except Exception:
        pass
    local_path = os.path.join("secrets", "firebase_service_account.json")
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


@st.cache_resource(show_spinner=False)
def init_firebase() -> Tuple[firestore.Client, Bucket]:
    creds = _load_creds()
    if not creds:
        st.error(
            "Faltan credenciales de Firebase.\n"
            "Coloca tu JSON en `.streamlit/secrets.toml` (clave `firebase_service_account`) "
            "o en `secrets/firebase_service_account.json`."
        )
        st.stop()

    bucket_name = st.secrets.get(BUCKET_ENV_KEY) if hasattr(st, "secrets") else None
    bucket_name = bucket_name or os.getenv(BUCKET_ENV_KEY) or f"{creds['project_id']}.appspot.com"

    cred = credentials.Certificate(creds)
    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})

    return firestore.client(app=app), storage.bucket(app=app)


# ---------------- Utilidades ----------------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def norm_phone(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit() or c == "+")

def norm_bool_from_si_no(x: str):
    v = str(x).strip().lower()
    if v in ("si", "sí", "1", "true", "y", "yes"):
        return True
    if v in ("no", "0", "false", "n"):
        return False
    return None

def as_si_no(b) -> str:
    return "SI" if b is True else ("NO" if b is False else "")


# ---------------- UI ----------------
st.set_page_config(page_title=APP_TITLE, page_icon="📝", layout="centered")
st.title("📝 Registro de Leads (1 por vez)")

db, _bucket = init_firebase()

with st.form("lead_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        maquina  = st.number_input("MAQUINA", min_value=0, step=1, value=1)
        nombre   = st.text_input("NOMBRE")
        telefono = st.text_input("TELEFONO")
        contactado = st.radio("CONTACTADO", options=["", "SI", "NO"], horizontal=True, index=0)

    with c2:
        fecha    = st.date_input("FECHA", value=date.today())
        correo   = st.text_input("CORREO")
        folio    = st.text_input("FOLIO")
        posible  = st.radio("POSIBLE", options=["", "SI", "NO"], horizontal=True, index=0)

    guardar = st.form_submit_button("💾 Guardar y capturar otro")

if guardar:
    # Validaciones mínimas
    if not nombre.strip():
        st.error("El campo **NOMBRE** es obligatorio.")
        st.stop()
    # Construir payload
    fecha_iso = datetime(fecha.year, fecha.month, fecha.day, tzinfo=timezone.utc).isoformat()
    payload = {
        "maquina": int(maquina),
        "fecha": fecha_iso,
        "nombre": nombre.strip(),
        "correo": correo.strip(),
        "telefono": norm_phone(telefono),
        "folio": str(folio).strip(),
        "contactado": norm_bool_from_si_no(contactado),
        "posible": norm_bool_from_si_no(posible),
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }
    # ID único (estable) por nombre+folio+telefono para evitar duplicados accidentales
    base = f"{payload['nombre']}|{payload['folio']}|{payload['telefono']}"
    lead_id = hashlib.md5(base.encode("utf-8")).hexdigest()[:16]

    db.collection(LEADS_COLLECTION).document(lead_id).set(payload, merge=True)
    st.success("✅ Registro guardado.")

st.markdown("---")
st.subheader("Últimos registros")

q = (
    db.collection(LEADS_COLLECTION)
    .order_by("created_at", direction=firestore.Query.DESCENDING)
    .limit(50)
)
docs = [d for d in q.stream()]

rows = []
for d in docs:
    data = d.to_dict() or {}
    rows.append({
        "MAQUINA": data.get("maquina", ""),
        "FECHA": data.get("fecha", ""),
        "NOMBRE": data.get("nombre", ""),
        "CORREO": data.get("correo", ""),
        "TELEFONO": data.get("telefono", ""),
        "FOLIO": data.get("folio", ""),
        "CONTACTADO": as_si_no(data.get("contactado")),
        "POSIBLE": as_si_no(data.get("posible")),
    })

if rows:
    import pandas as pd
    st.dataframe(pd.DataFrame(rows))
else:
    st.info("Aún no hay registros.")
