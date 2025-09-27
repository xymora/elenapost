# app/streamlit_app.py
import os
import json
import hashlib
from datetime import datetime, date, timezone, timedelta
from typing import Optional, Tuple, List, Dict, Any

import streamlit as st

# Firebase Admin
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.storage.bucket import Bucket  # solo para type hints

APP_TITLE = "Elenapost • Leads Dashboard"
LEADS_COLLECTION = "leads"
BUCKET_ENV_KEY = "FIREBASE_STORAGE_BUCKET"   # opcional si usaras Storage


# ================= Credenciales / Firebase =================
def _load_creds() -> Optional[dict]:
    # 1) st.secrets["firebase_service_account"]
    try:
        return dict(st.secrets["firebase_service_account"])
    except Exception:
        pass
    # 2) archivo local
    p = os.path.join("secrets", "firebase_service_account.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
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

    bucket_name = (st.secrets.get(BUCKET_ENV_KEY) if hasattr(st, "secrets") else None) \
                  or os.getenv(BUCKET_ENV_KEY) \
                  or f"{creds['project_id']}.appspot.com"

    cred = credentials.Certificate(creds)
    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})

    return firestore.client(app=app), storage.bucket(app=app)


# ================= Utilidades =================
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def day_start_iso(d: date) -> str:
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc).isoformat()

def day_end_iso(d: date) -> str:
    return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc).isoformat()

def norm_phone(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit() or c == "+")

def norm_bool_from_si_no(x: str):
    v = str(x).strip().lower()
    if v in ("si", "sí", "1", "true", "y", "yes"): return True
    if v in ("no", "0", "false", "n"): return False
    return None

def as_si_no(b) -> str:
    return "SI" if b is True else ("NO" if b is False else "")

def to_csv(rows: List[Dict[str, Any]]) -> bytes:
    import pandas as pd
    if not rows: return b""
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")

def _rerun():
    try: st.rerun()
    except Exception: st.experimental_rerun()


# ================= UI (layout estilo dashboard) =================
st.set_page_config(page_title=APP_TITLE, page_icon="🎯", layout="wide")
st.title("🎯 Leads Dashboard")

db, _bucket = init_firebase()

left, right = st.columns([1, 2.2])

# --------- Barra lateral (filtros + nuevo lead) ---------
with left:
    st.markdown("### 🧭 Filtros personalizados")

    # Filtros
    filtro_texto = st.text_input("Buscar por nombre, correo o folio")
    filtro_maquina = st.text_input("Máquina (igual a)", placeholder="ej. 1")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_desde = st.date_input("Desde (fecha)", value=None, format="YYYY-MM-DD")
    with col_f2:
        fecha_hasta = st.date_input("Hasta (fecha)", value=None, format="YYYY-MM-DD")

    col_f3, col_f4 = st.columns(2)
    with col_f3:
        filtro_contactado = st.selectbox("Contactado", ["(todos)", "SI", "NO", "(vacío)"])
    with col_f4:
        filtro_posible = st.selectbox("Posible", ["(todos)", "SI", "NO", "(vacío)"])

    limite = st.slider("Límite", 10, 1000, 100, 10)
    st.button("🔄 Aplicar filtros", use_container_width=True)

    st.markdown("---")
    st.markdown("### ✍️ Nuevo lead")

    # Formulario de una fila (registro en línea)
    with st.form("lead_form", clear_on_submit=True):
        m1, m2 = st.columns(2)
        with m1:
            maquina  = st.number_input("MAQUINA", min_value=0, step=1, value=1)
            nombre   = st.text_input("NOMBRE")
            telefono = st.text_input("TELEFONO")
            contactado = st.radio("CONTACTADO", options=["", "SI", "NO"], horizontal=True, index=0)
        with m2:
            fecha    = st.date_input("FECHA", value=date.today())
            correo   = st.text_input("CORREO")
            folio    = st.text_input("FOLIO")
            posible  = st.radio("POSIBLE", options=["", "SI", "NO"], horizontal=True, index=0)
        guardar = st.form_submit_button("💾 Guardar lead", use_container_width=True)

    if guardar:
        if not nombre.strip():
            st.error("El campo **NOMBRE** es obligatorio.")
            st.stop()

        payload = {
            "maquina": int(maquina),
            "fecha": datetime(fecha.year, fecha.month, fecha.day, tzinfo=timezone.utc).isoformat(),
            "nombre": nombre.strip(),
            "correo": correo.strip(),
            "telefono": norm_phone(telefono),
            "folio": str(folio).strip(),
            "contactado": norm_bool_from_si_no(contactado),
            "posible": norm_bool_from_si_no(posible),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        # ID estable para evitar duplicados accidentales
        base = f"{payload['nombre']}|{payload['folio']}|{payload['telefono']}"
        lead_id = hashlib.md5(base.encode("utf-8")).hexdigest()[:16]
        db.collection(LEADS_COLLECTION).document(lead_id).set(payload, merge=True)
        st.success("✅ Lead guardado.")
        _rerun()

# --------- Panel derecho (tabla de resultados) ---------
with right:
    st.markdown("### 🗂️ Registros filtrados")

    # Construir query: aplicamos en servidor lo que sea posible
    q = db.collection(LEADS_COLLECTION)

    # Igualdad por máquina
    if filtro_maquina.strip().isdigit():
        q = q.where("maquina", "==", int(filtro_maquina.strip()))

    # Rango de fechas (como guardamos ISO string, funciona lexicográficamente)
    if isinstance(fecha_desde, date):
        q = q.where("fecha", ">=", day_start_iso(fecha_desde))
    if isinstance(fecha_hasta, date):
        q = q.where("fecha", "<=", day_end_iso(fecha_hasta))

    # Filtros booleanos (excepto "(vacío)" que lo haremos en cliente)
    def where_bool(sel: str, field: str, query):
        if sel == "SI": return query.where(field, "==", True)
        if sel == "NO": return query.where(field, "==", False)
        return query

    q = where_bool(filtro_contactado, "contactado", q)
    q = where_bool(filtro_posible,    "posible",    q)

    # Ordenar y limitar
    q = q.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limite)

    docs = [d for d in q.stream()]
    rows: List[Dict[str, Any]] = []
    for d in docs:
        data = d.to_dict() or {}

        # Filtros que hacemos en cliente:
        if filtro_contactado == "(vacío)" and data.get("contactado") is not None:
            continue
        if filtro_posible == "(vacío)" and data.get("posible") is not None:
            continue

        if filtro_texto.strip():
            t = filtro_texto.lower().strip()
            if not (
                t in str(data.get("nombre","")).lower()
                or t in str(data.get("correo","")).lower()
                or t in str(data.get("folio","")).lower()
            ):
                continue

        rows.append({
            "MAQUINA":   data.get("maquina", ""),
            "FECHA":     data.get("fecha", ""),
            "NOMBRE":    data.get("nombre", ""),
            "CORREO":    data.get("correo", ""),
            "TELEFONO":  data.get("telefono", ""),
            "FOLIO":     data.get("folio", ""),
            "CONTACTADO":as_si_no(data.get("contactado")),
            "POSIBLE":   as_si_no(data.get("posible")),
        })

    total = len(rows)
    st.caption(f"🔢 Total encontradas: **{total}**")

    if total == 0:
        st.info("No hay registros para los filtros seleccionados.")
    else:
        import pandas as pd
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ Exportar CSV",
            data=to_csv(rows),
            file_name="leads_filtrados.csv",
            mime="text/csv",
            use_container_width=True
        )
