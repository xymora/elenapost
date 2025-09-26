# app/streamlit_app.py
import os
import json
import time
import hashlib
from datetime import datetime, date, timezone, timedelta
from typing import Optional, Tuple, Dict, Any, List

import streamlit as st

# Firebase Admin (Firestore + Storage)
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.storage.bucket import Bucket  # tipo correcto

APP_TITLE = "Elenapost"
BUCKET_ENV_KEY = "FIREBASE_STORAGE_BUCKET"
DEFAULT_POSTS_COLLECTION = "posts"
DEFAULT_LEADS_COLLECTION = "leads"


# ====================== Helpers ======================

def _load_firebase_credentials_from_secrets() -> Optional[dict]:
    try:
        return dict(st.secrets["firebase_service_account"])
    except Exception:
        return None


def _load_firebase_credentials_from_file() -> Optional[dict]:
    local_path = os.path.join("secrets", "firebase_service_account.json")
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


@st.cache_resource(show_spinner=False)
def init_firebase() -> Tuple[firestore.Client, Bucket]:
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

    bucket_name = None
    if hasattr(st, "secrets"):
        bucket_name = st.secrets.get(BUCKET_ENV_KEY)
    if not bucket_name:
        bucket_name = os.getenv(BUCKET_ENV_KEY)
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


def _guess_mime(ext: str) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")


def upload_image(bucket: Bucket, file_bytes: bytes, filename_hint: str) -> str:
    ext = os.path.splitext(filename_hint)[1].lower() or ".bin"
    obj_name = f"images/{int(time.time())}_{hash_bytes(file_bytes)}{ext}"
    blob = bucket.blob(obj_name)
    blob.upload_from_string(file_bytes, content_type=_guess_mime(ext))
    try:
        blob.make_public()
        return blob.public_url
    except Exception:
        return blob.generate_signed_url(expiration=timedelta(days=365))


def to_csv(rows: List[Dict[str, Any]]) -> bytes:
    import pandas as pd
    if not rows:
        return b""
    df = pd.DataFrame(rows)
    return df.to_csv(index=False).encode("utf-8")


def _rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


# ---- Helpers específicos para Leads ----
def norm_si_no(val: str) -> Optional[bool]:
    if val is None:
        return None
    v = str(val).strip().lower()
    if v in ("si", "sí", "1", "true", "verdadero", "y", "yes"):
        return True
    if v in ("no", "0", "false", "falso", "n"):
        return False
    return None

def as_si_no(val: Optional[bool]) -> str:
    if val is True:
        return "SI"
    if val is False:
        return "NO"
    return ""

def norm_phone(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit() or c == "+")


# ====================== UI ======================

st.set_page_config(page_title=APP_TITLE, page_icon="📝", layout="wide")
st.title("📝 Elenapost")

with st.sidebar:
    st.header("⚙️ Configuración")
    st.caption("Credenciales desde `st.secrets['firebase_service_account']` o `secrets/firebase_service_account.json`.")
    st.markdown("---")
    posts_collection = st.text_input("Colección de posts", value=DEFAULT_POSTS_COLLECTION)
    leads_collection = st.text_input("Colección de leads", value=DEFAULT_LEADS_COLLECTION)

db, bucket = init_firebase()

# ------------------ Pestañas ------------------
tab_posts, tab_leads = st.tabs(["📚 Posts", "📇 Registro manual (Leads)"])

# ======================= TAB POSTS =======================
with tab_posts:
    colL, colR = st.columns([1, 1])

    # ---- Crear/Editar Post ----
    with colL:
        st.subheader("✍️ Crear / Editar post")
        edit_mode = st.checkbox("Editar un post existente", key="edit_post_mode")
        post_to_edit_id = None

        if edit_mode:
            docs = (
                db.collection(posts_collection)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(50).stream()
            )
            options = []
            for d in docs:
                data = d.to_dict() or {}
                title = data.get("title", "(sin título)")
                options.append((f"{title} — {d.id}", d.id, data))
            if options:
                label, post_to_edit_id, _ = st.selectbox(
                    "Selecciona post",
                    options=options,
                    format_func=lambda x: x[0] if isinstance(x, tuple) else x,
                    index=0, key="post_select"
                )
            else:
                st.info("No hay posts recientes para editar.")

        default_title = default_body = default_tags = default_image = ""
        if post_to_edit_id:
            doc = db.collection(posts_collection).document(post_to_edit_id).get()
            if doc.exists:
                d = doc.to_dict() or {}
                default_title = d.get("title", "")
                default_body = d.get("body", "")
                default_tags = ",".join(d.get("tags", []))
                default_image = d.get("image_url", "")

        with st.form("post_form", clear_on_submit=not edit_mode):
            title = st.text_input("Título", value=default_title)
            body = st.text_area("Contenido", value=default_body, height=220)
            tags_text = st.text_input("Etiquetas (coma)", value=default_tags)
            image_file = st.file_uploader("Imagen (opcional)", type=["png", "jpg", "jpeg", "gif", "webp"], key="post_image")
            image_url_manual = st.text_input("o URL de imagen (opcional)", value=default_image, key="post_image_url")

            c1, c2 = st.columns([1, 1])
            submitted = c1.form_submit_button("Guardar")
            delete_clicked = c2.form_submit_button("Eliminar", disabled=not bool(post_to_edit_id))

        if submitted:
            if not title.strip():
                st.error("El título es obligatorio.")
            else:
                doc_id = post_to_edit_id or (slugify(title) + "-" + datetime.now().strftime("%Y%m%d%H%M%S"))
                ref = db.collection(posts_collection).document(doc_id)

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
                if not post_to_edit_id:
                    payload["created_at"] = utc_now_iso()

                ref.set(payload, merge=True)
                st.success(f"Post {'actualizado' if post_to_edit_id else 'creado'}: {doc_id}")
                _rerun()

        if delete_clicked and post_to_edit_id:
            db.collection(posts_collection).document(post_to_edit_id).delete()
            st.warning(f"Post eliminado: {post_to_edit_id}")
            _rerun()

    # ---- Listado Posts ----
    with colR:
        st.subheader("📚 Posts")
        q_text = st.text_input("Buscar por título o etiqueta", key="post_search")
        tag_filter = st.text_input("Filtrar por etiqueta exacta", key="post_tag_filter")
        limit = st.slider("Límite", 5, 100, 20, 5, key="post_limit")

        q = (
            db.collection(posts_collection)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(250)
        )
        docs = [d for d in q.stream()]
        rows = []
        for d in docs:
            data = d.to_dict() or {}
            title = data.get("title", "")
            tags = data.get("tags", [])
            if q_text:
                q_lc = q_text.lower()
                if q_lc not in title.lower() and not any(q_lc in t.lower() for t in tags):
                    continue
            if tag_filter and tag_filter not in tags:
                continue

            body_preview = data.get("body", "")
            if len(body_preview) > 120:
                body_preview = body_preview[:120] + "…"

            rows.append({
                "id": d.id,
                "title": title,
                "tags": ", ".join(tags),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
                "image_url": data.get("image_url", ""),
                "body": body_preview
            })

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
                        if st.button("Editar", key=f"edit_post_{row['id']}"):
                            st.session_state["_force_edit_post_id"] = row["id"]
                            _rerun()

            st.download_button(
                "⬇️ Exportar CSV",
                data=to_csv(rows),
                file_name="elenapost_posts.csv",
                mime="text/csv",
                help="Exporta el listado actual a CSV"
            )

    if "_force_edit_post_id" in st.session_state:
        st.toast("Cargando post para edición…", icon="✍️")
        del st.session_state["_force_edit_post_id"]
        _rerun()

# ======================= TAB LEADS =======================
with tab_leads:
    st.subheader("🧾 Captura manual de contactos (leads)")

    lead_colL, lead_colR = st.columns([1, 1])

    # ---------- Formulario alta/edición ----------
    with lead_colL:
        st.markdown("### ✍️ Alta / Edición")

        edit_lead_mode = st.checkbox("Editar un lead existente", key="edit_lead_mode")
        lead_to_edit_id = None
        existing_data = {}

        if edit_lead_mode:
            docs = (
                db.collection(leads_collection)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(100).stream()
            )
            options = []
            for d in docs:
                data = d.to_dict() or {}
                nombre = data.get("nombre", "(sin nombre)")
                folio = data.get("folio", "")
                options.append((f"{nombre} — {folio} — {d.id}", d.id, data))
            if options:
                label, lead_to_edit_id, existing_data = st.selectbox(
                    "Selecciona lead",
                    options=options,
                    format_func=lambda x: x[0] if isinstance(x, tuple) else x,
                    index=0, key="lead_select"
                )
            else:
                st.info("No hay leads recientes para editar.")

        def_val = lambda k, default="": existing_data.get(k, default) if existing_data else default
        def_bool = lambda k: existing_data.get(k, None) if existing_data else None

        with st.form("lead_form", clear_on_submit=not edit_lead_mode):
            maquina = st.number_input("MAQUINA", min_value=0, step=1,
                                      value=int(def_val("maquina", 1)) if str(def_val("maquina", "")).isdigit() else 1)
            fecha_val = def_val("fecha") or ""
            try:
                fecha_default = datetime.fromisoformat(fecha_val).date() if fecha_val else date.today()
            except Exception:
                fecha_default = date.today()
            fecha = st.date_input("FECHA", value=fecha_default)

            nombre = st.text_input("NOMBRE", value=def_val("nombre", ""))
            correo = st.text_input("CORREO", value=def_val("correo", ""))
            telefono = st.text_input("TELEFONO", value=def_val("telefono", ""))
            folio = st.text_input("FOLIO", value=str(def_val("folio", "")))

            contactado_opt = st.selectbox("CONTACTADO", options=["", "SI", "NO"],
                                          index=["","SI","NO"].index(as_si_no(def_bool("contactado"))))
            posible_opt    = st.selectbox("POSIBLE", options=["", "SI", "NO"],
                                          index=["","SI","NO"].index(as_si_no(def_bool("posible"))))

            c1, c2 = st.columns([1,1])
            save_lead = c1.form_submit_button("Guardar lead")
            delete_lead = c2.form_submit_button("Eliminar lead", disabled=not bool(lead_to_edit_id))

        if save_lead:
            if not nombre.strip():
                st.error("El campo NOMBRE es obligatorio.")
            else:
                lead_id = lead_to_edit_id or (f"{int(time.time())}_{hashlib.md5((nombre+str(folio)).encode()).hexdigest()[:8]}")
                ref = db.collection(leads_collection).document(lead_id)
                payload = {
                    "maquina": int(maquina) if maquina is not None else None,
                    "fecha": datetime(fecha.year, fecha.month, fecha.day, tzinfo=timezone.utc).isoformat(),
                    "nombre": nombre.strip(),
                    "correo": correo.strip(),
                    "telefono": norm_phone(telefono),
                    "folio": str(folio).strip(),
                    "contactado": norm_si_no(contactado_opt),
                    "posible": norm_si_no(posible_opt),
                    "updated_at": utc_now_iso()
                }
                if not lead_to_edit_id:
                    payload["created_at"] = utc_now_iso()

                ref.set(payload, merge=True)
                st.success(f"Lead {'actualizado' if lead_to_edit_id else 'creado'}: {lead_id}")
                _rerun()

        if delete_lead and lead_to_edit_id:
            db.collection(leads_collection).document(lead_to_edit_id).delete()
            st.warning(f"Lead eliminado: {lead_to_edit_id}")
            _rerun()

    # ---------- Listado / Filtros / Export ----------
    with lead_colR:
        st.markdown("### 📋 Listado y filtros")

        q_nombre = st.text_input("Buscar por NOMBRE", key="lead_q_nombre")
        q_folio  = st.text_input("Buscar por FOLIO", key="lead_q_folio")
        q_contactado = st.selectbox("Filtrar CONTACTADO", options=["(todos)", "SI", "NO", "(vacío)"], key="lead_q_contactado")
        q_posible    = st.selectbox("Filtrar POSIBLE", options=["(todos)", "SI", "NO", "(vacío)"], key="lead_q_posible")
        limit_leads  = st.slider("Límite", 5, 200, 50, 5, key="lead_limit")

        q = (
            db.collection(leads_collection)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(500)
        )
        docs = [d for d in q.stream()]
        rows = []
        for d in docs:
            data = d.to_dict() or {}

            if q_nombre and q_nombre.lower() not in (data.get("nombre","").lower()):
                continue
            if q_folio and q_folio.lower() not in str(data.get("folio","")).lower():
                continue

            def match_bool_filter(field_val: Optional[bool], sel: str) -> bool:
                if sel == "(todos)":
                    return True
                if sel == "(vacío)":
                    return field_val is None
                if sel == "SI":
                    return field_val is True
                if sel == "NO":
                    return field_val is False
                return True

            if not match_bool_filter(data.get("contactado"), q_contactado):
                continue
            if not match_bool_filter(data.get("posible"), q_posible):
                continue

            rows.append({
                "id": d.id,
                "MAQUINA": data.get("maquina", ""),
                "FECHA": data.get("fecha", ""),
                "NOMBRE": data.get("nombre", ""),
                "CORREO": data.get("correo", ""),
                "TELEFONO": data.get("telefono", ""),
                "FOLIO": data.get("folio", ""),
                "CONTACTADO": as_si_no(data.get("contactado")),
                "POSIBLE": as_si_no(data.get("posible")),
                "created_at": data.get("created_at",""),
                "updated_at": data.get("updated_at",""),
            })

        if not rows:
            st.info("No hay leads que coincidan con los filtros.")
        else:
            for row in rows[:limit_leads]:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2,2,1])
                    with c1:
                        st.markdown(f"**{row['NOMBRE']}**")
                        st.caption(f"ID: `{row['id']}` | FECHA: {row['FECHA']} | MAQUINA: {row['MAQUINA']}")
                        st.write(f"Correo: {row['CORREO'] or '—'}")
                        st.write(f"Teléfono: {row['TELEFONO'] or '—'}")
                        st.write(f"Folio: {row['FOLIO'] or '—'}")
                    with c2:
                        st.write(f"Contactado: {row['CONTACTADO'] or '—'}")
                        st.write(f"Posible: {row['POSIBLE'] or '—'}")
                        st.caption(f"Creado: {row['created_at']} | Actualizado: {row['updated_at']}")
                    with c3:
                        if st.button("Editar", key=f"edit_lead_{row['id']}"):
                            st.session_state["_force_edit_lead_id"] = row["id"]
                            _rerun()

            st.download_button(
                "⬇️ Exportar CSV (leads)",
                data=to_csv(rows),
                file_name="elenapost_leads.csv",
                mime="text/csv",
                help="Exporta el listado de leads a CSV"
            )

    if "_force_edit_lead_id" in st.session_state:
        st.toast("Cargando lead para edición…", icon="✍️")
        del st.session_state["_force_edit_lead_id"]
        _rerun()

    # ---------- Importación masiva (pegar o CSV) ----------
    st.markdown("---")
    with st.expander("📥 Importación masiva (pegar tabla o subir CSV)", expanded=False):
        st.write(
            "Pega las filas con encabezados o sube un CSV. Columnas esperadas: "
            "`MAQUINA, FECHA, NOMBRE, CORREO, TELEFONO, FOLIO, CONTACTADO, POSIBLE`."
        )
        raw_text = st.text_area(
            "Pega aquí tus filas (con encabezados)",
            height=180,
            placeholder=(
                "MAQUINA\tFECHA\tNOMBRE\tCORREO\tTELEFONO\tFOLIO\tCONTACTADO\tPOSIBLE\n"
                "1\t\tmarco reyes\talomarcosss@hotmail.com\t4622100885\t2483\tSI\t\n"
                "1\t\tandrea bernal\tandybg.1406@gmail.com\t4431691117\t41\tSI\tSI\n"
                "1\t\tKevin Christofer Navejas Rodriguez\t\t33 4855 9221\t2981\tSI\t\n"
                "1\t\tAlan Sanchez\tsan3alan@gmail.com\t8148059342\t6826\tSI\t\n"
                "1\t\tVictor Miramontes\tvimin12.vm@gmail.com\t3333222489\t10937\tSI\tSI\n"
                "1\t\tsalvador cano arredondo\thectorsalvador19@hotmail.com\t6671014514\t23870\tSI\t\n"
                "1\t\tRafael López\trafaelopez.arteche@gmail.com\t3343309233\t371\tSI\t\n"
                "1\t\tCarmen Ochoa\tCarmenOchoa19091997@hotmail.com\t6941081247\t9619\tSI\t\n"
                "1\t\tGuadalupe de Jesús Bojorquez armenta\tjebza2794@gmail.com\t6682663876\t33221\tSI\t\n"
            ),
        )
        csv_file = st.file_uploader("O sube CSV", type=["csv"])

        def _load_dataframe():
            import pandas as pd
            from io import StringIO
            if csv_file is not None:
                return pd.read_csv(csv_file)
            if raw_text.strip():
                try:
                    return pd.read_csv(StringIO(raw_text), sep=None, engine="python")
                except Exception:
                    return pd.read_csv(StringIO(raw_text), sep=r"\s{2,}|\t|,", engine="python")
            return None

        if st.button("📄 Previsualizar"):
            import pandas as pd
            df = _load_dataframe()
            if df is None or df.empty:
                st.error("No se pudo leer ninguna fila. Verifica que pegaste la tabla con encabezados.")
            else:
                df.rename(columns={c: c.strip().upper() for c in df.columns}, inplace=True)
                required = ["MAQUINA","FECHA","NOMBRE","CORREO","TELEFONO","FOLIO","CONTACTADO","POSIBLE"]
                for r in required:
                    if r not in df.columns:
                        df[r] = ""

                def _norm_bool(x):
                    x = str(x).strip().lower()
                    if x in ("si","sí","true","1","y","yes"): return "SI"
                    if x in ("no","false","0","n"): return "NO"
                    return ""
                def _norm_phone(x):
                    return "".join(ch for ch in str(x) if ch.isdigit() or ch=="+")
                def _norm_date(x):
                    x = str(x).strip()
                    if not x or x.lower() in ("nan","none"):
                        d = date.today()
                        return d.isoformat()
                    try:
                        return pd.to_datetime(x, dayfirst=True, errors="coerce").date().isoformat()
                    except Exception:
                        return x

                df["CONTACTADO"] = df["CONTACTADO"].apply(_norm_bool)
                df["POSIBLE"]    = df["POSIBLE"].apply(_norm_bool)
                df["TELEFONO"]   = df["TELEFONO"].apply(_norm_phone)
                df["FECHA"]      = df["FECHA"].apply(_norm_date)

                st.write("**Previsualización (primeras 20 filas):**")
                st.dataframe(df.head(20))
                st.session_state["_import_df_cache"] = df

        if "_import_df_cache" in st.session_state:
            if st.button("✅ Importar a Firestore (leads)"):
                df = st.session_state["_import_df_cache"]
                ok, fail = 0, 0
                for _, row in df.iterrows():
                    try:
                        fecha_iso = str(row["FECHA"])
                        if len(fecha_iso) == 10:
                            yyyy, mm, dd = fecha_iso.split("-")
                            fecha_iso = datetime(int(yyyy), int(mm), int(dd), tzinfo=timezone.utc).isoformat()

                        payload = {
                            "maquina": int(row["MAQUINA"]) if str(row["MAQUINA"]).strip().isdigit() else None,
                            "fecha": fecha_iso,
                            "nombre": str(row["NOMBRE"]).strip(),
                            "correo": str(row["CORREO"]).strip(),
                            "telefono": norm_phone(str(row["TELEFONO"])),
                            "folio": str(row["FOLIO"]).strip(),
                            "contactado": True if str(row["CONTACTADO"]).strip().upper()=="SI" else (False if str(row["CONTACTADO"]).strip().upper()=="NO" else None),
                            "posible":    True if str(row["POSIBLE"]).strip().upper()=="SI" else (False if str(row["POSIBLE"]).strip().upper()=="NO" else None),
                            "created_at": utc_now_iso(),
                            "updated_at": utc_now_iso(),
                        }
                        base = f"{payload['nombre']}|{payload['folio']}|{payload['telefono']}"
                        lead_id = hashlib.md5(base.encode("utf-8")).hexdigest()[:16]
                        db.collection(leads_collection).document(lead_id).set(payload, merge=True)
                        ok += 1
                    except Exception:
                        fail += 1
                st.success(f"Importación completada. Éxitos: {ok} | Fallos: {fail}")
                del st.session_state["_import_df_cache"]
                _rerun()
