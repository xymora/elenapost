# app/streamlit_app.py
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, date, timezone
from typing import Optional, Tuple, List, Dict, Any

import streamlit as st

# Firebase Admin
import firebase_admin
from firebase_admin import credentials, firestore

APP_TITLE = "Elenapost • Leads"
LEADS_COLLECTION = "leads"

# === NOMBRE Y CARPETA DEL JSON LOCAL (fallback) ===
JSON_DIR = "Secrets"
JSON_FILENAME = "elena-36be5-firebase-adminsdk-fbsvc-3c1451f3d5.json"
JSON_CANDIDATES = [
    Path(JSON_DIR) / JSON_FILENAME,                    # Secrets/elena-36be5-...json
    Path(JSON_FILENAME),                               # raíz del repo
    Path(".streamlit") / "secrets.json",               # por si lo subes así
    Path("secrets") / JSON_FILENAME,                   # otra ruta común
]

# ========= Carga de credenciales DESDE SECRETS o JSON en /Secrets =========
def _load_creds() -> Optional[dict]:
    """
    1) Intenta leer credenciales desde st.secrets["firebase_service_account"] (streamlit.app).
    2) Si no existen, intenta leer un archivo JSON local en rutas candidatas (incluye Secrets/).
    """
    # 1) Secrets (recomendado en streamlit.app)
    try:
        return dict(st.secrets["firebase_service_account"])
    except Exception:
        pass

    # 2) Fallback a archivo JSON local (e.g., Secrets/elena-36be5-firebase-adminsdk-...json)
    for p in JSON_CANDIDATES:
        try:
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            continue

    return None

@st.cache_resource(show_spinner=False)
def init_firebase() -> Tuple[firestore.Client, dict]:
    """Inicializa Firebase Admin con Firestore usando credenciales."""
    creds = _load_creds()
    if not creds:
        # Mensaje claro indicando ambas opciones (Secrets o archivo)
        paths = "\n".join([f"- `{str(p)}`" for p in JSON_CANDIDATES])
        st.error(
            "No se encontraron credenciales de Firebase.\n\n"
            "Opciones válidas:\n"
            "1) En **Manage app → Settings → Secrets**, pega tu JSON bajo la sección `[firebase_service_account]`.\n"
            "2) Sube el archivo JSON con nombre **"
            f"{JSON_FILENAME}** dentro de la carpeta **{JSON_DIR}/** del repo.\n\n"
            "Rutas que se intentan localizar:\n" + paths
        )
        st.stop()

    cred = credentials.Certificate(creds)
    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app(cred)

    return firestore.client(app=app), creds

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

# ========= UI =========
st.set_page_config(page_title=APP_TITLE, page_icon="📇", layout="wide")
st.title("📇 Leads")

db, _creds = init_firebase()

# --- 🔧 Diagnóstico en sidebar ---
st.sidebar.markdown("### 🔧 Diagnóstico Firebase")
st.sidebar.info(
    f"**project_id:** `{_creds.get('project_id','?')}`\n\n"
    f"**service account:** `{_creds.get('client_email','?')}`\n\n"
    f"**origen:** `st.secrets[\"firebase_service_account\"]` *o* archivo en `{JSON_DIR}/`"
)

if st.sidebar.button("Probar escritura ahora"):
    try:
        ping_id = datetime.now(timezone.utc).strftime("debug_%Y%m%d_%H%M%S")
        db.collection(LEADS_COLLECTION).document(ping_id).set(
            {
                "ping": True,
                "at": utc_now_iso(),
                "source": "streamlit_debug",
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        st.sidebar.success(f"Escritura OK en `{_creds.get('project_id')}` (doc: {ping_id})")
    except Exception as e:
        st.sidebar.error(f"Fallo escribiendo: {e}")

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
    st.markdown("### Filtros personalizados")

    st.session_state.f_texto   = st.text_input("Buscar por NOMBRE / CORREO / FOLIO", value=st.session_state.f_texto)
    st.session_state.f_maquina = st.text_input("Máquina (igual a)", value=st.session_state.f_maquina, placeholder="ej. 1")

    c_fecha1, c_fecha2 = st.columns(2)
    with c_fecha1:
        st.session_state.f_fecha_desde = st.date_input("Desde (fecha)", value=st.session_state.f_fecha_desde, format="YYYY-MM-DD")
    with c_fecha2:
        st.session_state.f_fecha_hasta = st.date_input("Hasta (fecha)", value=st.session_state.f_fecha_hasta, format="YYYY-MM-DD")

    c_bool1, c_bool2 = st.columns(2)
    with c_bool1:
        st.session_state.f_contactado = st.selectbox("Contactado", ["(todos)", "SI", "NO", "(vacío)"],
                                                     index=["(todos)","SI","NO","(vacío)"].index(st.session_state.f_contactado))
    with c_bool2:
        st.session_state.f_posible = st.selectbox("Posible", ["(todos)", "SI", "NO", "(vacío)"],
                                                  index=["(todos)","SI","NO","(vacío)"].index(st.session_state.f_posible))

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
            default_date = date.today()
            fecha    = st.date_input("FECHA", value=default_date)
            correo   = st.text_input("CORREO")
            folio    = st.text_input("FOLIO")
            posible  = st.radio("POSIBLE", options=["", "SI", "NO"], horizontal=True, index=0)
        guardar = st.form_submit_button("Guardar lead", use_container_width=True)

    if guardar:
        if not nombre.strip():
            st.error("El campo NOMBRE es obligatorio.")
            st.stop()

        payload = {
            "maquina": int(maquina),
            # guardamos fecha en ISO (inicio del día UTC)
            "fecha": datetime(fecha.year, fecha.month, fecha.day, tzinfo=timezone.utc).isoformat(),
            "nombre": nombre.strip(),
            "correo": correo.strip(),
            "telefono": norm_phone(telefono),
            "folio": str(folio).strip(),
            "contactado": norm_bool_from_si_no(contactado),
            "posible": norm_bool_from_si_no(posible),
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        # ID estable para evitar duplicados
        base = f"{payload['nombre']}|{payload['folio']}|{payload['telefono']}"
        lead_id = hashlib.md5(base.encode("utf-8")).hexdigest()[:16]

        db.collection(LEADS_COLLECTION).document(lead_id).set(payload, merge=True)

        # limpiar filtros/recordar último id
        st.session_state.update({
            "f_texto": "", "f_maquina": "", "f_fecha_desde": None, "f_fecha_hasta": None,
            "f_contactado": "(todos)", "f_posible": "(todos)", "f_limite": 200,
            "just_saved_id": lead_id
        })
        st.success("Lead guardado.")
        _rerun()

# -------- DERECHA: Últimos registros (filtrados) --------
with right:
    st.markdown("### Últimos registros")

    q = db.collection(LEADS_COLLECTION)

    if st.session_state.f_maquina.strip().isdigit():
        q = q.where("maquina", "==", int(st.session_state.f_maquina.strip()))

    if isinstance(st.session_state.f_fecha_desde, date):
        q = q.where("fecha", ">=", day_start_iso(st.session_state.f_fecha_desde))
    if isinstance(st.session_state.f_fecha_hasta, date):
        q = q.where("fecha", "<=", day_end_iso(st.session_state.f_fecha_hasta))

    def where_bool(sel: str, field: str, query):
        if sel == "SI": return query.where(field, "==", True)
        if sel == "NO": return query.where(field, "==", False)
        return query

    q = where_bool(st.session_state.f_contactado, "contactado", q)
    q = where_bool(st.session_state.f_posible,    "posible",    q)

    # Si combinas filtros por fecha y order_by en otro campo,
    # Firestore podría pedir un índice compuesto.
    q = q.order_by("updated_at", direction=firestore.Query.DESCENDING).limit(st.session_state.f_limite)

    docs = list(q.stream())

    rows: List[Dict[str, Any]] = []
    for d in docs:
        data = d.to_dict() or {}

        # Acepta documentos antiguos con claves en MAYÚSCULAS
        maquina_val = data.get("maquina", data.get("MAQUINA", ""))
        fecha_val   = data.get("fecha",   data.get("FECHA",   ""))
        nombre_val  = data.get("nombre",  data.get("NOMBRE",  ""))
        correo_val  = data.get("correo",  data.get("CORREO",  ""))
        tel_val     = data.get("telefono",data.get("TELEFONO",""))
        folio_val   = data.get("folio",   data.get("FOLIO",   ""))
        contactado_val = data.get("contactado", data.get("CONTACTADO", None))
        posible_val    = data.get("posible",    data.get("POSIBLE",    None))

        # Normaliza "SI/NO" string a boolean si viniera en mayúsculas
        if isinstance(contactado_val, str): contactado_val = norm_bool_from_si_no(contactado_val)
        if isinstance(posible_val, str):    posible_val    = norm_bool_from_si_no(posible_val)

        # Filtros de cliente extra (vacíos)
        if st.session_state.f_contactado == "(vacío)" and contactado_val is not None:
            continue
        if st.session_state.f_posible == "(vacío)" and posible_val is not None:
            continue

        if st.session_state.f_texto.strip():
            t = st.session_state.f_texto.lower().strip()
            if not (
                t in str(nombre_val).lower()
                or t in str(correo_val).lower()
                or t in str(folio_val).lower()
            ):
                continue

        rows.append({
            "ID":        d.id,
            "MAQUINA":   maquina_val,
            "FECHA":     fecha_val,
            "NOMBRE":    nombre_val,
            "CORREO":    correo_val,
            "TELEFONO":  tel_val,
            "FOLIO":     folio_val,
            "CONTACTADO":as_si_no(contactado_val),
            "POSIBLE":   as_si_no(posible_val),
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
