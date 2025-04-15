import firebase_admin
from firebase_admin import credentials, db
import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
from pyfingerprint.pyfingerprint import PyFingerprint
from datetime import datetime
import socket
import threading

# --- Pines GPIO ---
GPIO.setmode(GPIO.BOARD)
PUSH_BUTTON = 13
LED_VERDE_PIN = 11  # LED verde
LED_ROJO_PIN = 15   # LED rojo
BUZZER_PIN = 16     # Buzzer

GPIO.setup(PUSH_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(LED_VERDE_PIN, GPIO.OUT)
GPIO.setup(LED_ROJO_PIN, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# --- Función para registrar en logs ---
def registrar_acceso_en_logs(uid, name, curso, numero):
    from firebase_admin import db
    from datetime import datetime

    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    hora_actual = datetime.now().strftime("%H:%M:%S")
    log_ref = db.reference(f'logs/{fecha_actual}')

    logs_dia = log_ref.get()
    log_existente = None

    if logs_dia:
        if isinstance(logs_dia, dict):
            for key, log in logs_dia.items():
                if log.get('name') == name:
                    log_existente = key
                    break
        elif isinstance(logs_dia, list):
            for idx, log in enumerate(logs_dia):
                if log and log.get('name') == name:
                    log_existente = idx
                    break

    # 👇 Mover este bloque FUERA del if/elif
    if log_existente is not None:
        print(f"🔍 Log encontrado: {log_existente}")
        print(f"⏰ Actualizando hora de acceso a {hora_actual}")
        try:
            log_ref.child(str(log_existente)).update({
                'last_access': hora_actual
            })
            print(f"🕒 Log actualizado para {name} ({uid}) a las {hora_actual}")
        except Exception as e:
            print(f"❌ Error actualizando log: {e}")
    else:
        nuevo_indice = 0
        if isinstance(logs_dia, dict):
            indices_numericos = [int(k) for k in logs_dia.keys() if str(k).isdigit()]
            if indices_numericos:
                nuevo_indice = max(indices_numericos) + 1
        elif isinstance(logs_dia, list):
            nuevo_indice = len(logs_dia)

        try:
            log_ref.child(str(nuevo_indice)).set({
                'uid': uid,
                'name': name,
                'curso': curso,
                'numero': numero,
                'last_access': hora_actual
            })
            print(f"📝 Nuevo log creado para {name} ({uid}) en posición {nuevo_indice} a las {hora_actual}")
        except Exception as e:
            print(f"❌ Error creando log: {e}")

GPIO.setwarnings(False)

# --- Configuración Firebase ---
cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://samartpasss-default-rtdb.firebaseio.com/'
})

# --- Funciones para controlar los LEDs y el buzzer ---
def blink_led(led_pin, times=1, duration=0.3):
    for _ in range(times):
        GPIO.output(led_pin, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(led_pin, GPIO.LOW)
        time.sleep(duration)

def buzzer_beep(duration=0.5):
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

# Mantener LED verde encendido permanentemente
GPIO.output(LED_VERDE_PIN, GPIO.HIGH)

def error_led_red():
    print("❌ Error detectado.")
    buzzer_beep()
    blink_led(LED_ROJO_PIN, times=2, duration=0.5)
    
# --- Inicializar RFID ---
reader = SimpleMFRC522()

# --- Inicializar huella ---
try:
    f = PyFingerprint('/dev/ttyS0', 57600, 0xFFFFFFFF, 0x00000000)

    if f.verifyPassword():
        print("✅ Sensor de huella listo.")
except Exception as e:
    error_led_red()
    print("❌ Error al conectar el sensor de huella:", e)
    exit(1)

    
def get_next_free_position(f):
    template_index = f.getTemplateIndex(0)
    for i in range(f.getStorageCapacity()):
        if not template_index[i]:
            return i
    raise Exception("🛑 Sensor lleno.")

def register_fingerprint(f):
    print("🆕 Registro de huella mejorado (6 toques requeridos)")

    name = input("name: ")
    curso = input("Curso (4to, 5to, 6to): ").strip().lower()
    numero = input("Número: ").strip()[:2]
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if curso not in ['4to', '5to', '6to']:
        error_led_red()
        print("❌ Curso inválido.")
        return

    print("👉 Coloca el dedo para verificar si ya está registrado...")
    while not f.readImage():
        pass

    f.convertImage(0x01)
    result = f.searchTemplate()
    if result[0] >= 0:
        error_led_red()  # Si no se detecta el UID, parpadea el LED rojo
        print("❗ Huella ya registrada.")
        return

    print("📸 Comenzando registro con 6 toques del mismo dedo...")

    try:
        print("➡️ Toca el sensor (1/6)")
        while not f.readImage():
            pass
        f.convertImage(0x01)

        print("➡️ Retira el dedo...")
        while f.readImage():
            pass
        print("➡️ Toca de nuevo el sensor (2/6)")
        while not f.readImage():
            pass
        f.convertImage(0x02)

        f.createTemplate()

        print("➡️ Retira el dedo...")
        while f.readImage():
            pass
        print("➡️ Toca de nuevo el sensor (3/6)")
        while not f.readImage():
            pass
        f.convertImage(0x01)
        f.createTemplate()
        blink_led(LED_VERDE_PIN, times=1, duration=0.5)  # LED verde parpadea por 3 segundos
        buzzer_beep()
        print("📦 Plantilla creada con precisión mejorada.")

        pos = get_next_free_position(f)
        f.storeTemplate(pos)

        for i in range(4, 7):
            print("➡️ Retira el dedo...")
            while f.readImage():
                pass
            print(f"➡️ Toca el sensor nuevamente ({i}/6)")
            while not f.readImage():
                pass
            f.convertImage(0x01)
            score = f.compareCharacteristics()
            print(f"📊 Coincidencia con plantilla: {score}/100")
            if score < 100:
                error_led_red()  # Si no se detecta el UID, parpadea el LED rojo
                print("⚠️ Coincidencia baja. Intenta mejor posición.")

        user_data = {
            'name': name,
            'curso': curso,
            'numero': numero,
            'registration_time': now,
            'last_access': now
        }

        db.reference(f'users/estudiantes {curso}/{pos}').set(user_data)
        registrar_acceso_en_logs(pos, name, curso, numero)


        blink_led(LED_VERDE_PIN, times=1, duration=0.5)  # LED verde parpadea por 3 segundos
        buzzer_beep()
        print(f"✅ Huella registrada correctamente en posición {pos} para {name} ({curso})")

    except Exception as e:
        error_led_red()  # Si no se detecta el UID, parpadea el LED rojo
        print(f"❌ Error durante el registro de huella: {e}")

def assign_rfid(uid):
    print("🎫 Leyendo tarjeta...")

    # 1. Verificar si la tarjeta RFID ya está asignada a otro usuario
    for curso in ['4to', '5to', '6to']:
        estudiantes_ref = db.reference(f'users/estudiantes {curso}')
        estudiantes = estudiantes_ref.get()

        if estudiantes:
            if isinstance(estudiantes, dict):
                iterable = estudiantes.items()
            elif isinstance(estudiantes, list):
                iterable = enumerate(estudiantes)
            else:
                continue

            for key, datos in iterable:
                if not isinstance(datos, dict):
                    continue
                if datos.get('uid') == uid:
                    error_led_red()  # Si no se detecta el UID, parpadea el LED rojo
                    print(f"⚠️ Esta tarjeta ya está asignada a: {datos['name']} ({curso}, N°{datos['numero']})")
                    return
                    
    blink_led(LED_VERDE_PIN, times=1, duration=0.5)  # LED verde parpadea por 3 segundos
    buzzer_beep()
    print("✅ Tarjeta disponible. Coloca el dedo del usuario.")

    # 2. Verificar si el usuario ya tiene una tarjeta asignada
    while not f.readImage():
        pass
    f.convertImage(0x01)
    result = f.searchTemplate()
    if result[0] == -1:
        error_led_red()  # Si no se detecta el UID, parpadea el LED rojo
        print("❌ Huella no registrada.")
        return

    id_encontrado = str(result[0])

    for curso in ['4to', '5to', '6to']:
        estudiantes_ref = db.reference(f'users/estudiantes {curso}')
        estudiantes = estudiantes_ref.get()

        if estudiantes:
            if isinstance(estudiantes, dict):
                datos_usuario = estudiantes.get(id_encontrado)
            elif isinstance(estudiantes, list):
                idx = int(id_encontrado)
                datos_usuario = estudiantes[idx] if 0 <= idx < len(estudiantes) else None
            else:
                datos_usuario = None

            if isinstance(datos_usuario, dict):
                # Verificar si el usuario ya tiene una tarjeta asignada
                if 'uid' in datos_usuario and datos_usuario['uid'] != "":
                    error_led_red()  # Si no se detecta el UID, parpadea el LED rojo
                    print(f"⚠️ {datos_usuario['name']} ya tiene una tarjeta asignada.")
                    return

                # Asignar la tarjeta RFID al usuario
                db.reference(f'users/estudiantes {curso}/{id_encontrado}').update({'uid': uid})
                blink_led(LED_VERDE_PIN, times=1, duration=0.5)  # LED verde parpadea por 3 segundos
                buzzer_beep()
                print(f"✅ Tarjeta asignada a {datos_usuario['name']} ({curso}, N°{datos_usuario['numero']})")
                return
                
    error_led_red()  # Si no se detecta el UID, parpadea el LED rojo
    print("❌ Usuario no encontrado para esta huella.")
    
def check_rfid(uid):
    # Buscar en los cursos para ver si el UID está asignado a algún usuario
    for curso in ['4to', '5to', '6to']:
        estudiantes_ref = db.reference(f'users/estudiantes {curso}')
        estudiantes = estudiantes_ref.get()

        if estudiantes:
            if isinstance(estudiantes, dict):
                iterable = estudiantes.items()
            elif isinstance(estudiantes, list):
                iterable = enumerate(estudiantes)
            else:
                continue

            for key, datos in iterable:
                if not isinstance(datos, dict):
                    continue
                if datos.get('uid') == uid:
                    # Si el UID de la tarjeta coincide con el UID en la base de datos
                    name = datos.get('name', 'Desconocido')
                    numero = datos.get('numero', '??')

                    # Actualizar el last_access en la base de datos
                    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    db.reference(f'users/estudiantes {curso}/{key}').update({'last_access': ahora})
                    
                    blink_led(LED_VERDE_PIN, times=1, duration=0.5)  # LED verde parpadea por 3 segundos
                    buzzer_beep()
                    print(f"✅ Tarjeta detectada: {uid} está asignada a {name} ({curso}, N°{numero})")
                    registrar_acceso_en_logs(uid, name, curso, numero)


                    return True
    error_led_red()  # Si no se detecta el UID, parpadea el LED rojo
    print(f"❌ La tarjeta con UID {uid} no está registrada en el sistema.")
    return False
    
def check_fingerprint(f):
    try:
        if f.readImage():
            f.convertImage(0x01)
            result = f.searchTemplate()
            pos = result[0]
            if pos >= 0:
                for curso in ['4to', '5to', '6to']:
                    ref = db.reference(f'users/estudiantes {curso}/{pos}')
                    user = ref.get()

                    if user:
                        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ref.update({'last_access': now})
                        blink_led(LED_VERDE_PIN, times=1, duration=0.5)  # LED verde parpadea por 3 segundos
                        buzzer_beep()
                        print(f"🔓 Acceso permitido a {user['name']} ({user['numero']})")
                        registrar_acceso_en_logs(str(pos), user['name'], curso, user['numero'])
                        return True
                error_led_red()  # Si no se detecta el UID, parpadea el LED rojo
                print("⚠️ Huella reconocida pero sin datos.")
            else:
                error_led_red()  # Si no se detecta el UID, parpadea el LED rojo
                print("🛑 Huella no registrada.")
    except Exception as e:
        print(f"[Error Huella]: {e}")
    return False


print("🟢 Sistema listo. Escaneando huella o tarjeta...")

try:
    while True:
        if GPIO.input(PUSH_BUTTON) == GPIO.HIGH:
            print("\n🔧 MODO REGISTRO ACTIVADO")
            time.sleep(0.5)
            while GPIO.input(PUSH_BUTTON) == GPIO.HIGH:
                time.sleep(0.1)

            while True:
                print("\n1. Registrar huella")
                print("2. Asignar tarjeta")
                print("3. Salir del modo registro")
                opcion = input("Elige opción: ")

                if opcion == '1':
                    register_fingerprint(f)
                elif opcion == '2':
                    print("👉 Acerca una tarjeta para asignarla...")
                    uid = reader.read_id()
                    assign_rfid(uid)
                    blink_led(LED_VERDE_PIN, times=1, duration=0.5)  # LED verde parpadea por 3 segundos
                    buzzer_beep()
                    
                elif opcion == '3':
                    print("🚪 Saliendo del modo registro...")
                    break
                else:
                    error_led_red()  # Si no se detecta el UID, parpadea el LED rojo
                    print("❌ Opción inválida.")

                print("📌 Pulsa el botón para salir o presiona ENTER para continuar...")
                for _ in range(50):
                    if GPIO.input(PUSH_BUTTON) == GPIO.HIGH:
                        print("🚪 Salida activada por botón.")
                        while GPIO.input(PUSH_BUTTON) == GPIO.HIGH:
                            time.sleep(0.1)
                        break
                    time.sleep(0.1)

        print("Leyendo huella o tarjeta...")
        if check_fingerprint(f):
            pass
        else:
            try:
                uid = reader.read_id_no_block()
                if uid:
                    print(f"✅ Tarjeta detectada: {uid}")
                    check_rfid(uid)
            except:
                pass

        time.sleep(0.5)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("🚪 Programa terminado.")  
