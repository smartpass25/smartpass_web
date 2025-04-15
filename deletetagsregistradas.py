import os
import json
import firebase_admin
from firebase_admin import credentials, db

# Configurar Firebase
cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://samartpasss-default-rtdb.firebaseio.com/'
})

# Archivo donde se guardarán los tags
TAG_FILE = "tags.json"

def delete_tags_from_firebase():
    # Eliminar todos los registros de tags en Firebase
    tags_ref = db.reference('tags')
    tags_ref.delete()  # Usar delete() en lugar de set(None)
    print("✅ Todos los tags eliminados de Firebase.")

def delete_tags_file():
    # Eliminar el archivo de tags
    if os.path.exists(TAG_FILE):
        os.remove(TAG_FILE)
        print("✅ Archivo de tags eliminado.")
    else:
        print("❌ El archivo de tags no existe.")

def confirm_deletion():
    confirmation = input("¿Estás seguro de que deseas borrar todos los tags guardados? (sí/no): ").strip().lower()
    if confirmation == "sí" or confirmation == "si":
        delete_tags_from_firebase()
        delete_tags_file()
    else:
        print("❌ Operación cancelada.")

# Llamar a la función de confirmación de eliminación
confirm_deletion()
