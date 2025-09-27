import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

# 🔐 JSON embebido con clave correcta
firebase_credentials = {
  "type": "service_account",
  "project_id": "elena-36be5",
  "private_key_id": "e782907d3427bc1d8d1655fdda70a79ec6973cba",
  "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDC/JzY0DNqUYUq
/ROJOc+9KwWMJNEmECKxMsOM+0bXbdfMDSJ3bOcMapLujmWdmXUAWkGreHf7RqfB
B9yUhibhYooYVXmdptQWJTR5Ly1J71cdzyoyI5moMhGMvfnahHfU1epkocEgmrcl
BYyI05RudLfRhIYfEzp8syAjwaHXzjMybufy4stryLuwLcwjPjG1ROHhD4C9IE5K
nuijVIbwtt3+Y8mll+rUrNZS7d1z6Y8J9S7jNFWnxTEHZIoJsEXTJiQ49/pmImXv
tvQXKEPAxri7M6M5vxqProVqZ8J7gpKgcxbMqLdY3OtnuXVKsoA2YBy6gIiXUyP/
WO+4/9z9AgMBAAECggEAH+zxl3RbfsRzO+stCDJth6kkIuKiVgudSosnxo0b98j1
5OSfqJMtr3RBs4qgK7JFHHYqu3MhngRfEjWB0dW3Rv714m8YVw5KOogD8/WcAjeM
eYaCf6whjA8KnZM7diJrZm9SDgEIGJkMdKTYckzGSGGW+VisBymEUYeYsxIQuD8y
xxFR3i1UZ1d60mq2MkSIJXBPIn6gBb63HVT5Dj5EUyFq/qdVT//BElTSrZyIDGB7
nR+ZmwkAJIkSh9nHHKOcuBJmsc/8dCnRIxwMnJPMI/wgCG0yVyQZ3APWyzDs8byU
dMZ92u8Oit52a4Cvtn/pA7nnvAFqEZjVlOMkX90GxwKBgQD32axHVbrwzBDBglzf
Q4E+wFvkvk5GXL9z2ooWYgpjiomtFJRbYCMIySrzWOfE99NE5yKiUQl9WEuorSnv
NKrsHI18ryrvO2amQWA3dwNr1wsa4sv3YJFOiLTlZxqvsOvfjVeQcbnlMh8zbcao
0prH4nCjv8pU5NQPAGrHDereKwKBgQDJZfNz58/qET7+S/uXW7TsUzgDniBSkiB9
ZLwxwyYTkoJn9lDJE3A0jZp1l8NHl8706lv2Fpin0dx9p4HOv1dc8Qge+XLPKZTw
E8BfEQCxy1s1h0LUUGgjy5PqEKTaVFDdY44q6YeXW2HHJn/QSzPMtetDQUciAcCg
IDrLQVNFdwKBgGz1YZpeovc3DuqzL7brC0eV8xAFZY3jOjtpSKl8YkrOXaYcVPgy
tFQpc9tVK1bZCCTTY9Ntwrk69s/piHTjd3yjNMQqkbpoJ8FRHkZj6Log6H3iVH6l
ElwvFy9+eynfomI91c/nXyzWMwc97EbNh0P2VUR3jTBzBJKvwUFO6gDPAoGAIF/i
JcSi2IaTML+4HtmgGMk73OEDYyKYVG/oDLvJGCZaDio7TEdypxAIP1T5ED4oB5jQ
1ZtGSNvkbNKLfFenzIn2ezwwJ3sQtRMHvoB2Mx50eANZS9XtF6v3CA5K4cniAeSq
Ct3lbQBElIXsz+f22LZ5riMFM0NC2rqzmM7UevsCgYEAyJ/gL0QFfeu5KqrDb7/C
6Q58QBEQbZr6Eb08Oy45yqfh4U7TSOYrUyRx6u90yYdDpcTaZzBsRiqDxQfMaSJz
gHsxmTeokXlir1vn9zT8IOF6892wuE88iJrYgJ/xFEaA7i0fU9tLyDwWxh3iD89Q
qGOkwKW7asgFvQXW3RKkQOE=
-----END PRIVATE KEY-----""",
  "client_email": "firebase-adminsdk-fbsvc@elena-36be5.iam.gserviceaccount.com",
  "client_id": "117586238746856040628",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc@elena-36be5.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# 🔌 Conexión a Firestore
creds = service_account.Credentials.from_service_account_info(firebase_credentials)
db = firestore.Client(credentials=creds, project=firebase_credentials["project_id"])

# 🌐 Interfaz
st.title("📋 Gestión de Clientes")

# Navegación
opcion = st.sidebar.radio("Selecciona una acción", ["Registrar nuevo", "Ver registros"])

if opcion == "Registrar nuevo":
    st.subheader("Agregar nuevo cliente")
    with st.form("registro"):
        nombre = st.text_input("Nombre")
        correo = st.text_input("Correo")
        telefono = st.text_input("Teléfono")
        folio = st.text_input("Folio")
        fecha = st.date_input("Fecha")
        maquina = st.number_input("Máquina", step=1, min_value=0)
        contactado = st.selectbox("¿Contactado?", ["", "SI", "NO"])
        posible = st.selectbox("¿Posible?", ["", "SI", "NO"])
        enviar = st.form_submit_button("Guardar")

        if enviar:
            datos = {
                "NOMBRE": nombre,
                "CORREO": correo,
                "TELEFONO": telefono,
                "FOLIO": folio,
                "FECHA": str(fecha),
                "MAQUINA": int(maquina),
                "CONTACTADO": contactado,
                "POSIBLE": posible
            }
            try:
                ref = db.collection("leads").add(datos)
                st.success(f"✅ Guardado correctamente con ID: {ref[1].id}")
            except Exception as e:
                st.error(f"❌ Error al guardar: {e}")

elif opcion == "Ver registros":
    st.subheader("📑 Lista de registros existentes")
    try:
        registros = db.collection("leads").stream()
        lista = []
        for doc in registros:
            dato = doc.to_dict()
            dato["ID"] = doc.id
            lista.append(dato)

        if lista:
            st.write(f"🔍 Se encontraron {len(lista)} registros en Firestore.")
            st.dataframe(lista)
        else:
            st.info("No hay registros todavía.")
    except Exception as e:
        st.error(f"❌ Error al consultar Firestore: {e}")
