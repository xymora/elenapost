# app/streamlit_app.py
import os
import json
import hashlib
from datetime import datetime, date, timezone
from typing import Optional, Tuple, List, Dict, Any

import streamlit as st

# Firebase Admin
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.storage.bucket import Bucket  # solo para type hints

APP_TITLE = "Elenapost • Leads"
LEADS_COLLECTION = "leads"
BUCKET_ENV_KEY = "FIREBASE_STORAGE_BUCKET"

# ========= Credenciales / Firebase =========
def _load_creds() -> Optional[dict]:
    """Carga el service account desde st.secrets o secrets/firebase_service_account.json"""
    try:
        # .streamlit/secrets.toml con la sección [firebase_service_account]
        return dict(st.secrets["firebase_service_account"])
    except Exception:
        pass
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
            "Faltan credenciales de Firebase.\n\n"
            "• Coloca tu JSON en `.streamlit/secrets.toml` bajo la clave `[firebase_service_account]`,\n"
            "  o en `secrets/firebase_service_account.json`.\n\n"
            "Revisa la documentación del proyecto para ver un ejemplo."
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

# ========= Utils =========
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def day_start_iso(d: date) -> str:
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc).isoformat()

def day_end_iso(d: date) -> str:
    return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc).isoformat()

def norm_phone(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit() or c == "+")

def norm_bool_from_si_no(x: str):
    v = str(x or "").strip().lower()
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
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()

def getf(d: dict, low: str, up: str):
    """Obtiene d[low] o d[up] (minúscula/mayúscula) si existe."""
    return d.get(low, d.get(up, None))

def to_bool_any(x):
    """Convierte 'SI'/'NO'/True/False/None a bool|None."""
    if isinstance(x, bool): return x
    if x is None: return None
    s = str(x).strip().lower()
    if s in ("si","sí","true","1","y","yes"): return True
    if s in ("no","false","0","n"): return False
    return None

# ========= UI =========
st.set_page_config(page_title=APP_TITLE, page_icon="📇", layout="wide")
st.title("📇 Leads")

db, _bucket = init_firebase()

# Estado inicial para filtros / último guardado
for k, v in {
    "f_texto": "", "f_maquina": "", "f_fecha_desde": None, "f_fecha_hasta": None,
    "f_contactado": "(todos)", "f_posible": "(todos)", "f_limite": 200,
    "just_saved_id": None
}.items():
    st.session_state.setdefault(k, v)

left, right = st.columns([1, 2.3], gap="large")

# -------- IZQUIERDA: Filtros + Nuevo lead --------
with left:
    st.markdown("### Filtros")

    st.session_state.f_texto   = st.text_input("Buscar por NOMBRE / CORREO / FOLIO", value=st.session_state.f_texto)
    st.session_state.f_maquina = st.text_input("Máquina (igual a)", value=st.session_state.f_maquina, placeholder="ej. 1")

    c_fecha1, c_fecha2 = st.columns(2)
    with c_fecha1:
        st.session_state.f_fecha_desde = st.date_input("Desde (fecha)", value=st.session_state.f_fecha_desde, format="YYYY-MM-DD")
    with c_fecha2:
        st.session_state.f_fecha_hasta = st.date_input("Hasta (fecha)", value=st.session_state.f_fecha_hasta, format="YYYY-MM-DD")

    c_bool1, c_bool2 = st.columns(2)
    with c_bool1:
        st.session_state.f_contactado = st.selectbox("Contactado", ["(todos)", "SI", "NO", "(vacío)"], index=["(todos)","SI","NO","(vacío)"].index(st.session_state.f_contactado))
    with c_bool2:
        st.session_state.f_posible = st.selectbox("Posible", ["(todos)", "SI", "NO", "(vacío)"], index=["(todos)","SI","NO","(vacío)"].index(st.session_state.f_posible))

    st.session_state.f_limite = st.slider("Límite", 10, 1000, st.session_state.f_limite, 10)

    if st.button("🧹 Limpiar filtros", use_container_width=True):
        st.session_state.update({
            "f_texto": "", "f_maquina": "", "f_fecha_desde": None, "f_fecha_hasta": None,
            "f_contactado": "(todos)", "f_posible": "(todos)", "f_limite": 200
        })
        _rerun()

    st.markdown("---")
    st.markdown("### Nuevo lead")
    with st.form("lead_form_left", clear_on_submit=True):
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
        guardar = st.form_submit_button("Guardar lead", use_container_width=True)

    if guardar:
        if not nombre.strip():
            st.error("El campo NOMBRE es obligatorio.")
            st.stop()

        payload_low = {
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
        # Duplicamos en MAYÚSCULAS para compatibilidad con lo ya guardado desde Colab
        payload_up = {
            "MAQUINA": payload_low["maquina"],
            "FECHA": payload_low["fecha"],
            "NOMBRE": payload_low["nombre"],
            "CORREO": payload_low["correo"],
            "TELEFONO": payload_low["telefono"],
            "FOLIO": payload_low["folio"],
            "CONTACTADO": "SI" if payload_low["contactado"] else ("NO" if payload_low["contactado"] is False else ""),
            "POSIBLE": "SI" if payload_low["posible"] else ("NO" if payload_low["posible"] is False else ""),
        }
        payload = {**payload_low, **payload_up}

        base = f"{payload_low['nombre']}|{payload_low['folio']}|{payload_low['telefono']}"
        lead_id = hashlib.md5(base.encode("utf-8")).hexdigest()[:16]

        db.collection(LEADS_COLLECTION).document(lead_id).set(payload, merge=True)

        # limpiar filtros para que nada lo oculte y recordar el último id
        st.session_state.update({
            "f_texto": "", "f_maquina": "", "f_fecha_desde": None, "f_fecha_hasta": None,
            "f_contactado": "(todos)", "f_posible": "(todos)", "f_limite": 200,
            "just_saved_id": lead_id
        })
        st.success("Lead guardado.")
        _rerun()

# -------- DERECHA: Últimos registros (agnóstico a mayúsculas/minúsculas) --------
with right:
    st.markdown("### Últimos registros")

    # Traemos últimos N sin filtros del servidor (evita perder docs por esquema distinto)
    try:
        try:
            docs = list(
                db.collection(LEADS_COLLECTION)
                  .order_by("updated_at", direction=firestore.Query.DESCENDING)
                  .limit(st.session_state.f_limite)
                  .stream()
            )
        except Exception:
            # Si no existe updated_at en algunos docs, ordenamos por id
            docs = list(
                db.collection(LEADS_COLLECTION)
                  .order_by("__name__", direction=firestore.Query.DESCENDING)
                  .limit(st.session_state.f_limite)
                  .stream()
            )
    except Exception as e:
        st.error(f"Error consultando Firestore: {e}")
        st.stop()

    rows: List[Dict[str, Any]] = []
    from_date = st.session_state.f_fecha_desde
    to_date   = st.session_state.f_fecha_hasta
    texto     = st.session_state.f_texto.lower().strip()
    fmaq      = st.session_state.f_maquina.strip()
    fcont     = st.session_state.f_contactado
    fpos      = st.session_state.f_posible

    for d in docs:
        data = d.to_dict() or {}

        # Leer ambos esquemas
        v_maquina   = getf(data, "maquina", "MAQUINA")
        v_fecha     = getf(data, "fecha", "FECHA")
        v_nombre    = getf(data, "nombre", "NOMBRE")
        v_correo    = getf(data, "correo", "CORREO")
        v_telefono  = getf(data, "telefono", "TELEFONO")
        v_folio     = getf(data, "folio", "FOLIO")
        v_contact   = getf(data, "contactado", "CONTACTADO")
        v_posible   = getf(data, "posible", "POSIBLE")

        b_contact = to_bool_any(v_contact)
        b_posible = to_bool_any(v_posible)

        # ===== Filtros en cliente =====
        if fmaq.isdigit() and str(v_maquina) != fmaq:
            continue

        if isinstance(from_date, date):
            if not v_fecha or v_fecha < day_start_iso(from_date):
                continue
        if isinstance(to_date, date):
            if not v_fecha or v_fecha > day_end_iso(to_date):
                continue

        if fcont == "SI" and b_contact is not True:   continue
        if fcont == "NO" and b_contact is not False:  continue
        if fcont == "(vacío)" and b_contact is not None: continue

        if fpos == "SI" and b_posible is not True:    continue
        if fpos == "NO" and b_posible is not False:   continue
        if fpos == "(vacío)" and b_posible is not None: continue

        if texto:
            blob = " ".join([str(x or "") for x in (v_nombre, v_correo, v_folio)]).lower()
            if texto not in blob:
                continue

        rows.append({
            "ID":        d.id,
            "MAQUINA":   v_maquina or "",
            "FECHA":     v_fecha or "",
            "NOMBRE":    v_nombre or "",
            "CORREO":    v_correo or "",
            "TELEFONO":  v_telefono or "",
            "FOLIO":     v_folio or "",
            "CONTACTADO":as_si_no(b_contact),
            "POSIBLE":   as_si_no(b_posible),
        })

    total = len(rows)
    st.caption(f"Total encontradas: {total}")

    if total == 0:
        if st.session_state.just_saved_id:
            st.warning("Acabas de guardar un lead, pero algún filtro lo está ocultando. Pulsa **🧹 Limpiar filtros**.")
        else:
            st.info("No hay registros para los filtros seleccionados.")
    else:
        import pandas as pd
        df = pd.DataFrame(rows)

        # Resaltar el último guardado (si existe)
        if st.session_state.just_saved_id:
            df["__is_last__"] = (df["ID"] == st.session_state.just_saved_id)
            df = pd.concat([df[df["__is_last__"]], df[~df["__is_last__"]]]).drop(columns="__is_last__")

        st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)

        st.download_button(
            "Exportar CSV",
            data=to_csv(df.drop(columns=["ID"]).to_dict(orient="records")),
            file_name="leads_filtrados.csv",
            mime="text/csv",
            use_container_width=True
        )
