# app/streamlit_app.py
import os
import io
import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List

import streamlit as st

# --------- Firebase Admin (Firestore + Storage) ----------
# Requiere: firebase-admin (en requirements.txt)
import firebase_admin
from firebase_admin import credentials, firestore, storage

APP_TITLE = "Elenapost"
BUCKET_ENV_KEY = "FIREBASE_STORAGE_BUCKET"   # puedes setearlo en secrets o env
DEFAULT_COLLECTION = "posts"                 # colección de Firestore


# ====================== Helpers ======================

def _load_firebase_credentials_from_secrets() -> Optional[dict]:
    """Intenta leer el JSON de servicio desde st.secrets['firebase_service_account']."""
    try:
        return dict(st.secrets["firebase_service_account"])
    except Exception:
        return None


def _load_firebase_credentials_from_file() -> Optional[dict]:
    """Intenta leer el JSON desde secrets/firebase_service_account.json (ruta local)."""
    local_path = os.path.join("secrets", "firebase_service_account.json")
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


@st.cache_resource(show_spinner=False)
def init_firebase() -> Tuple[firestore.Client, storage.bucket.Bucket]:
    """
    Inicializa Firebase Admin:
    1) Primero busca credenciales en st.secrets['firebase_service_account'].
    2) Si no existen, intenta cargar secrets/firebase_service_account.json.
    3) Si ya hay app inicializada, la reutiliza.
    Retorna (firestore_client, storage_bucket).
    """
    creds_dict = _load_firebase_credentials_from_secrets()
    if not creds_dict:
        creds_dict = _load_firebase_credentials_from_file()

    if not creds_dict:
        st.error(
            "No se encontraron credenciales de Firebase.\n\n"
            "Agrega tu JSON a **.streamlit/secrets.toml** (clave `firebase_service_account`), "
            "o coloca el archivo en `secrets/firebase_service_account.json`."
        )
        st.stop()

    # Determinar el bucket de Storage
    bucket_name = None
    # 1) secrets/env explícito
    bucket_name = st.secrets.get(BUCKET_ENV_KEY) if hasattr(st, "secrets") else None
    if not bucket_name:
        bucket_name = os.getenv(BUCKET_ENV_KEY)
    # 2) inferir de project_id si no lo definiste
    if not bucket_name and "project_id" in creds_dict:
        bucket_name = f"{creds_dict['project_id']}.appspot.com"

    cred = credentials.Certificate(creds_dict)
    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})

    db = firestore.client(app=app)
    bucket = storage.bucket(app=app)
    return db, bucket


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(s: str) -> str:
    base = "".join(c.lower() if c.isalnum() else "-" for c in s).strip("-")
    base = "-".join([p for p in base.split("-") if p])
    return base[:64] if base else hashlib.sha1(s.encode()).hexdigest()[:16]


def hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def upload_image(bucket, file_bytes: bytes, filename_hint: str) -> str:
    """Sube imagen a Storage y retorna URL pública firmada por tiempo largo."""
    ext = os.path.splitext(filename_hint)[1].lower() or ".bin"
    obj_name = f"images/{int(time.time())}_{hash_bytes(file_bytes)}{ext}"
    blob = bucket.blob(obj_name)
    blob.upload_from_string(file_bytes, content_type=_guess_mime(ext))
    # Hacer el objeto público (opcional) o generar URL firmada
    try:
        blob.make_public()
        return blob.public_url
    except Exception:
        # como fallback, URL firmada (1 año ~ 31536000 s)
        return blob.generate_signed_url(expiration=31536000)


def _guess_mime(ext: str) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")


def to_csv(rows: List[Dict[str, Any]]) -> bytes:
    import pandas as pd
    if not rows:
        return b""
    df = pd.DataFrame(rows)
    return df.to_csv(index=False).encode("utf-8")


# ====================== UI ======================

st.set_page_config(page_title=APP_TITLE, page_icon="📝", layout="wide")
st.title("📝 Elenapost")

with st.sidebar:
    st.header("⚙️ Configuración")
    st.caption("Credenciales desde `st.secrets['firebase_service_account']` o `secrets/firebase_service_account.json`.")
    st.markdown("---")
    st.write("Colección de Firestore:")
    collection_name = st.text_input("Nombre de colección", value=DEFAULT_COLLECTION)

db, bucket = init_firebase()
colL, colR = st.columns([1, 1])

# -------- Crear / Editar Post --------
with colL:
    st.subheader("✍️ Crear / Editar post")

    # Modo edición
    edit_mode = st.checkbox("Editar un post existente")
    doc_to_edit_id = None
    if edit_mode:
        # cargar ids para seleccionar
        docs = db.collection(collection_name).order_by("created_at", direction=firestore.Query.DESCENDING).limit(50).stream()
        options = []
        for d in docs:
            data = d.to_dict()
            title = data.get("title", "(sin título)")
            options.append((f"{title} — {d.id}", d.id, data))
        if options:
            label, doc_to_edit_id, data_sel = st.selectbox("Selecciona post", options=options, format_func=lambda x: x[0] if isinstance(x, tuple) else x, index=0)
        else:
            st.info("No hay posts recientes para editar.")

    # Cargar datos si se edita
    default_title = default_body = default_tags = default_image = ""
    if doc_to_edit_id:
        doc = db.collection(collection_name).document(doc_to_edit_id).get()
        if doc.exists:
            d = doc.to_dict()
            default_title = d.get("title", "")
            default_body = d.get("body", "")
            default_tags = ",".join(d.get("tags", []))
            default_image = d.get("image_url", "")

    with st.form("post_form", clear_on_submit=not edit_mode):
        title = st.text_input("Título", value=default_title, placeholder="Ej. Lanzamiento Q4")
        body = st.text_area("Contenido", value=default_body, height=220)
        tags_text = st.text_input("Etiquetas (separadas por coma)", value=default_tags, placeholder="news, product, release")
        image_file = st.file_uploader("Imagen (opcional)", type=["png", "jpg", "jpeg", "gif", "webp"])
        image_url_manual = st.text_input("o URL de imagen (opcional)", value=default_image)

        submit_col1, submit_col2 = st.columns([1, 1])
        submitted = submit_col1.form_submit_button("Guardar")
        delete_clicked = submit_col2.form_submit_button("Eliminar", disabled=not bool(doc_to_edit_id))

    if submitted:
        if not title.strip():
            st.error("El título es obligatorio.")
        else:
            doc_id = doc_to_edit_id or slugify(title) + "-" + datetime.now().strftime("%Y%m%d%H%M%S")
            ref = db.collection(collection_name).document(doc_id)

            final_image_url = image_url_manual.strip()
            if image_file is not None:
                bytes_data = image_file.read()
                final_image_url = upload_image(bucket, bytes_data, image_file.name)

            payload = {
                "title": title.strip(),
                "body": body.strip(),
                "tags": [t.strip() for t in tags_text.split(",") if t.strip()],
                "image_url": final_image_url or None,
                "updated_at": utc_now_iso(),
            }
            if not doc_to_edit_id:
                payload["created_at"] = utc_now_iso()

            ref.set(payload, merge=True)
            st.success(f"Post {'actualizado' if doc_to_edit_id else 'creado'}: {doc_id}")
            st.experimental_rerun()

    if delete_clicked and doc_to_edit_id:
        db.collection(collection_name).document(doc_to_edit_id).delete()
        st.warning(f"Post eliminado: {doc_to_edit_id}")
        st.experimental_rerun()

# -------- Listado / Búsqueda --------
with colR:
    st.subheader("📚 Posts")
    q_text = st.text_input("Buscar por título o etiqueta")
    tag_filter = st.text_input("Filtrar por etiqueta exacta (opcional)")
    limit = st.slider("Límite", 5, 100, 20, 5)

    # Consulta básica y filtrado en cliente (para demo)
    q = db.collection(collection_name).order_by("created_at", direction=firestore.Query.DESCENDING).limit(250)
    docs = [d for d in q.stream()]
    rows = []
    for d in docs:
        data = d.to_dict()
        if not data:
            continue
        title = data.get("title", "")
        tags = data.get("tags", [])
        if q_text:
            q_lc = q_text.lower()
            if q_lc not in title.lower() and not any(q_lc in t.lower() for t in tags):
                continue
        if tag_filter and tag_filter not in tags:
            continue

        rows.append({
            "id": d.id,
            "title": title,
            "tags": ", ".join(tags),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "image_url": data.get("image_url", ""),
            "body": (data.get("body", "")[:120] + "…") if len(data.get("body", "")) > 120 else data.get("body", "")
        })

    # Mostrar tarjetas
    if not rows:
        st.info("No hay posts que coincidan.")
    else:
        for row in rows[:limit]:
            with st.container(border=True):
                left, right = st.columns([3, 1])
                with left:
                    st.markdown(f"**{row['title']}**")
                    st.caption(f"ID: `{row['id']}` | tags: {row['tags'] or '—'}")
                    st.write(row["body"])
                    st.caption(f"Creado: {row['created_at']} | Actualizado: {row['updated_at']}")
                with right:
                    if row["image_url"]:
                        st.image(row["image_url"], use_container_width=True)
                    if st.button("Editar", key=f"edit_{row['id']}"):
                        st.session_state["_force_edit_id"] = row["id"]
                        st.experimental_rerun()

        # Export CSV
        st.download_button(
            "⬇️ Exportar CSV",
            data=to_csv(rows),
            file_name="elenapost_posts.csv",
            mime="text/csv",
            help="Exporta el listado actual a CSV"
        )

# Forzar edición (si se pulsó botón en tarjeta)
if "_force_edit_id" in st.session_state:
    st.toast("Cargando post para edición…", icon="✍️")
    # Reinicia con el checkbox en True y seleccionado ese ID
    # (Técnicamente necesitaríamos un estado más complejo; para esta demo basta relanzar)
    del st.session_state["_force_edit_id"]
    st.experimental_rerun()
