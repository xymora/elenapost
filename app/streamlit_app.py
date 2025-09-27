# Requisitos previos: instalar librería
!pip install -q google-cloud-firestore

import json
from google.oauth2 import service_account
from google.cloud import firestore

# JSON de la cuenta de servicio (sin modificar, incluido aquí directamente)
FIREBASE_JSON = r"""{
  "type": "service_account",
  "project_id": "elena-36be5",
  "private_key_id": "e5bac82a9d9034efeab75d1e8c550398b33f3512",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkq...<TRUNCADO>\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@elena-36be5.iam.gserviceaccount.com",
  "client_id": "117586238746856040628",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40elena-36be5.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}"""

# Cargar credenciales
try:
    sa_info = json.loads(FIREBASE_JSON)
    creds = service_account.Credentials.from_service_account_info(sa_info)
    project_id = sa_info["project_id"]
    print("✅ Autenticado con éxito. project_id:", project_id)
except Exception as e:
    raise SystemExit(f"❌ Error en el JSON de la clave. Detalles: {e}")

# Inicializar cliente Firestore
client = firestore.Client(project=project_id, credentials=creds)
print("🔥 Conexión a Firestore lista.")

# ======= REGISTRO MANUAL DE DATOS =======
registro = {
    "CONTACTADO": "SI",
    "CORREO":     "alomarcosss@hotmail.com",
    "FECHA":      "2025-09-26",
    "FOLIO":      "2483",
    "MAQUINA":    1,
    "NOMBRE":     "marco reyes",
    "POSIBLE":    "",
    "TELEFONO":   "4622100885"
}

# Guardar documento con ID automático en colección 'leads'
doc_ref = client.collection("leads").add(registro)[1]
print("📥 Documento guardado con ID:", doc_ref.id)

# Leer el documento para validar
doc_data = doc_ref.get().to_dict()
print("📄 Contenido guardado:", doc_data)
