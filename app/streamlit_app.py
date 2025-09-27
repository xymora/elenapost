# --- Diagnóstico rápido en sidebar ---
creds_info = _load_creds() or {}
proj = creds_info.get("project_id", "¿desconocido?")
svc  = creds_info.get("client_email", "¿desconocido?")
st.sidebar.markdown("### 🔧 Diagnóstico Firebase")
st.sidebar.info(f"**project_id:** `{proj}`\n\n**service account:** `{svc}`")

if st.sidebar.button("Probar escritura ahora"):
    try:
        ping_id = datetime.now(timezone.utc).strftime("debug_%Y%m%d_%H%M%S")
        db.collection(LEADS_COLLECTION).document(ping_id).set({
            "ping": True,
            "at": datetime.now(timezone.utc).isoformat(),
            "source": "streamlit_debug",
        }, merge=True)
        st.sidebar.success(f"Escritura OK en `{proj}` (doc: {ping_id})")
    except Exception as e:
        st.sidebar.error(f"Fallo escribiendo: {e}")
