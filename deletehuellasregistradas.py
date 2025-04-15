import firebase_admin
from firebase_admin import credentials, db
from pyfingerprint.pyfingerprint import PyFingerprint

# Inicializar Firebase
cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://samartpasss-default-rtdb.firebaseio.com/'
})

# Conectar con el sensor de huellas
try:
    f = PyFingerprint('/dev/ttyS0', 57600, 0xFFFFFFFF, 0x00000000)
    if f.verifyPassword():
        print("✅ Sensor de huella conectado correctamente.")
    else:
        print("❌ Contraseña del sensor incorrecta.")
        exit(1)
except Exception as e:
    print("🚫 No se pudo conectar con el sensor de huellas.")
    print("Error:", str(e))
    exit(1)

# Confirmación del usuario
confirm = input("⚠️ ¿Estás seguro de que quieres borrar TODAS las huellas y datos? (sí/no): ").strip().lower()

if confirm.lower() in ["sí", "si", "s"]:
    
    # Borrar todas las huellas del sensor
    try:
        f.clearDatabase()
        print("🧼 Huellas borradas del sensor con éxito.")
    except Exception as e:
        print("❌ Error al borrar las huellas del sensor.")
        print("Error:", str(e))

    # Borrar nodos en Firebase
    try:
        db.reference('fingerprints').delete()
        db.reference('users').delete()
        print("🧹 Base de datos de Firebase reiniciada.")
    except Exception as e:
        print("❌ Error al borrar datos de Firebase.")
        print("Error:", str(e))
else:
    print("❎ Operación cancelada por el usuario.")
