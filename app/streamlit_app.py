import json
from google.oauth2 import service_account
from google.cloud import firestore

# ============ OPCIÓN A: JSON embebido (sin comentarios) ============
FIREBASE_JSON = r"""
{
  "type": "service_account",
  "project_id": "elena-36be5",
  "private_key_id": "e5bac82a9d9034efeab75d1e8c550398b33f3512",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCu8X87z8D5yXM8\ncO3EStMTJVB5y/2iYxq56WgssSbzFkPnvNVq5vXX+Ft1WkI1n+IPYoOidGyh6tv5\nzhrcmJVUjWmrfSTqHJA2C1UkH3Ta0RPDO7qlEkMt7o7aIEsDOOZUKuVEHGdPpG05\nJDyzJOLiQn0FKUPRhqE6jXz5saMXwboIrx0tgbgNB6390rOY8b1o1c2GZ981xXea\nOvJFBO10aSPqWApmqq2kcCUyf8i/3C6AHNq5DJqEEPNZhPb8k/4uM0/dd3zmkaDe\nJBUm+X8woTDnXJp5fJfHoPSXQJbz3YGiDp9iwyKOhrK9IM7ahMGRlJnrrPAJP962\n8Sr/xd8DAgMBAAECggEAAqBtoKBF7Xow2L95UnEtKiRtSObfMAj85b2zarheNVgo\nPNqA+dHt7wgzl1d7lwKHimOYRmApIWU9WErX7Gf+Ff7pj0GZxEoZgDY7WQd/4akx\n+sRy0PetOotSacQCXFIGY00hlBw5EOEPIsSAhNAQ+AS3i9RKyGKVGSP2tGkOYdTo\nX9zspCBBaIWls/XEGHBTIgd66FDmv3zWg2kfGiXaJliMDTtmzqTIdaUmDZjF52V1\nZm/581nbJuUj9bttoNW5+FameWh31ZJLtwwq6vKbEOdx93dQVrzRzp8HV0gXi7ux\ng9raQ6b7ClqlawP4LNrQcrRvUG3bfe4cw1ZXlWVegQKBgQD286FpMz0u5ZtsRD/t\ndTs+lUf1C8PcG8i6OCHnYd4uoRZ7YEh+ErnLEEmCPO9TEC0JyebNwSCUI6Dx79aB\nTyR36YMY8LKHnaj3rLj8p8U0l5Qv3hO7KAWPbje0CJbFYWrzpXangEofGYHMP1tT\nZTHRM5uyEBdr6iXFt1gV9x4TmQKBgQC1WnBvBXtKgz7uDgERiIvwr339/tpek9ng\ns10SXKi/0Io6zuLKPBzTYL2cAEa0FMsIpCl2P8bzcxfZHunxcklU0g4ulaFAuL6z\nQASZxIgPaIcNzqzTVl3qUN5Vz1TKVT887vgyjNDEq7wdNqVuwY3qxMRZEFo4NZQx\nmM5vo3bo+wKBgGSZAHLDXbQh8ntbHhOUQusOkr5+6W1boBxDy4PfOUwTcP4XTdCV\nvju7ScaVHgTfPQmUxsGgX64ZCXIk+mO4oql6ZV4ehwt5rSAfq0e47DutV79cHvuJ\npSI1itl6+jgzpAbWq4w2VXtvv5E9ae2B9pY7CLyzk2bxfiuZsXdZMFZZAoGBAKWz\nufGnF4zwuMo4n39OvVawcrVmbE5oV3Z5THwfj8yblgG/0Pap0EjPJtBobDHUoeMG\nZB/4jCcbLVokZetH2nsW5wBnlYwWgaA0yT9alFtHzcau5bjAPFWBiHTtWPL6yyo4\nyy0c/xAEPoCO0r+NOMee/CzIxTaAtiRPE6hrupWLAoGAB5QMLmy/T2LFnUibWwEv\nC4sSfWJTQ2mf3mCBpcYTEFmFdqE2vliOlO1jae1lrE/aCckx3pOlBntXAhUqPwH/\nhbDP8pvPN6pbcezYZ0j0iC6FptBUna8U2vXOc6kC1nGOnp31JKX/62BLG2wFQfGp\npKnBzGhoxIXlRj+9yOoXjh4=\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@elena-36be5.iam.gserviceaccount.com",
  "client_id": "117586238746856040628",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40elena-36be5.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
""".strip()
# ============================================================================

creds = None
project_id = None

try:
    sa_info = json.loads(FIREBASE_JSON)
    creds = service_account.Credentials.from_service_account_info(sa_info)
    project_id = sa_info["project_id"]
    print("✅ JSON embebido válido. project_id:", project_id)
except Exception as e:
    raise SystemExit(f"❌ JSON inválido. Detalle: {e}")

# Crear cliente de Firestore
client = firestore.Client(project=project_id, credentials=creds)
print("🔥 Firestore conectado correctamente.")

# Documento de prueba
data = {
    "MAQUINA":    1,
    "FECHA":      "2025-09-26",  # También puede ser datetime con timestamp
    "NOMBRE":     "marco reyes",
    "CORREO":     "alomarcosss@hotmail.com",
    "TELEFONO":   "4622100885",
    "FOLIO":      "2483",
    "CONTACTADO": "SI",          # "SI" / "NO"
    "POSIBLE":    ""             # "SI" / "NO" / vacío
}

# Guardar en colección 'leads'
try:
    doc_ref = client.collection("leads").add(data)[1]
    print("✅ Documento guardado en 'leads' con ID:", doc_ref.id)

    # Leer para comprobar
    result = doc_ref.get().to_dict()
    print("📄 Documento leído:", result)

except Exception as e:
    print("❌ Error guardando o leyendo en Firestore:", e)
