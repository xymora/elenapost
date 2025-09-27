def iniciar_firebase():
    import json
    if not firebase_admin._apps:
        cred_data = st.secrets["firebase_service_account"]

        if isinstance(cred_data, str):
            # Si es un string, lo intentamos convertir a JSON (para evitar que venga como string plano desde Streamlit Cloud)
            try:
                cred_dict = json.loads(cred_data)
            except json.JSONDecodeError:
                raise ValueError("Las credenciales no son un JSON válido.")
        else:
            # Si ya es un dict (como debería ser cuando usas st.secrets en local o como dict en cloud)
            cred_dict = dict(cred_data)

        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)

    return firestore.client()
