from flask import Flask, render_template, request, redirect, url_for, jsonify  # Asegúrate de importar jsonify
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
from collections import defaultdict

cred = credentials.Certificate('key.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://samartpasss-default-rtdb.firebaseio.com/'
})

app = Flask(__name__)

def obtener_registros_por_fecha(fecha):
    log_ref = db.reference(f'logs/{fecha}')
    registros = log_ref.get()

    # Verificamos si los registros son una lista
    if isinstance(registros, list):
        # Si los registros son una lista, simplemente los retornamos
        return registros
    elif isinstance(registros, dict):
        # Si los registros son un diccionario, los convertimos a lista de valores
        return list(registros.values())
    else:
        # Si los registros no son ni lista ni diccionario, retornamos vacío
        return []

        
def obtener_estudiantes(curso, filtro=None, valor=None, page=1, limit=15):
    ref = db.reference(f'users/{curso}')
    data = ref.get()

    if isinstance(data, dict):
        estudiantes = [est for est in data.values() if est]
    elif isinstance(data, list):
        estudiantes = [est for est in data if est]
    else:
        estudiantes = []

    if filtro == 'alfabetico':
        estudiantes.sort(key=lambda est: est.get('name', '').lower())


    # Ordenar los estudiantes por 'numero' numéricamente
    try:
        estudiantes.sort(key=lambda est: int(est.get('numero', 0)))
    except ValueError:
        estudiantes.sort(key=lambda est: est.get('numero', ''))

    # Formatear los números a 2 dígitos
    for est in estudiantes:
        est['numero'] = f"{int(est['numero']):02d}"

    start = (page - 1) * limit
    return estudiantes[start:start + limit]


@app.route('/')
def index():
    filtro = request.args.get('filtro', '')
    valor = request.args.get('valor', '')
    page_4to = int(request.args.get('page_4to', 1))
    page_5to = int(request.args.get('page_5to', 1))
    page_6to = int(request.args.get('page_6to', 1))
    limit = 40  # seguimos usando 40 estudiantes por página

    estudiantes_por_curso = {
        "estudiantes 4to": obtener_estudiantes('estudiantes 4to', filtro, valor, page_4to, limit),
        "estudiantes 5to": obtener_estudiantes('estudiantes 5to', filtro, valor, page_5to, limit),
        "estudiantes 6to": obtener_estudiantes('estudiantes 6to', filtro, valor, page_6to, limit),
    }

    # Ordenar los cursos en el orden correcto: 4to, 5to, 6to
    estudiantes_por_curso = {
        "estudiantes 4to": estudiantes_por_curso["estudiantes 4to"],
        "estudiantes 5to": estudiantes_por_curso["estudiantes 5to"],
        "estudiantes 6to": estudiantes_por_curso["estudiantes 6to"]
    }

    fecha_actual = datetime.now().strftime('%Y-%m-%d')

    total_estudiantes_4to = len(obtener_estudiantes('estudiantes 4to', filtro, valor))
    total_estudiantes_5to = len(obtener_estudiantes('estudiantes 5to', filtro, valor))
    total_estudiantes_6to = len(obtener_estudiantes('estudiantes 6to', filtro, valor))

    # Calculamos páginas pero limitamos a 15
    paginas_4to = min((total_estudiantes_4to + limit - 1) // limit, 15)
    paginas_5to = min((total_estudiantes_5to + limit - 1) // limit, 15)
    paginas_6to = min((total_estudiantes_6to + limit - 1) // limit, 15)

    return render_template('index.html', 
                       estudiantes_por_curso=estudiantes_por_curso,
                       fecha_actual=fecha_actual,
                       filtro=filtro,
                       valor=valor,
                       page_4to=page_4to,
                       page_5to=page_5to,
                       page_6to=page_6to,
                       paginas_4to=paginas_4to,
                       paginas_5to=paginas_5to,
                       paginas_6to=paginas_6to)


@app.route('/get_estudiantes/<curso>', methods=["GET"])
def obtener_estudiantes_api(curso):
    filtro = request.args.get('filtro', '')
    valor = request.args.get('valor', '')

    estudiantes = obtener_estudiantes(curso, filtro=filtro, valor=valor)
    return jsonify(estudiantes)

@app.route('/logs/<fecha>', methods=['GET'])
def ver_logs(fecha):
    page = request.args.get('page', 1, type=int)

    # Usar la función para obtener los logs según la fecha y la página
    logs = obtener_logs(fecha, page)

    # Calcular el número total de páginas (esto depende de cuántos logs tienes en total)
    total_logs = sum(len(curso['logs']) for curso in logs)  # Total de logs por curso
    logs_por_pagina = 10  # Por ejemplo, mostramos 10 logs por página
    total_paginas = (total_logs + logs_por_pagina - 1) // logs_por_pagina  # Redondear hacia arriba

    return render_template('logs.html',
                           logs=logs,
                           fecha_actual=fecha,
                           page=page,
                           total_paginas=total_paginas)

def obtener_logs(fecha, page, logs_por_pagina=10):
    log_ref = db.reference(f'logs/{fecha}')
    registros = log_ref.get()

    if isinstance(registros, list):
        logs = registros
    elif isinstance(registros, dict):
        logs = list(registros.values())
    else:
        logs = []

    # Agrupar los logs por curso
    logs_por_curso = defaultdict(list)
    for log in logs:
        curso = log.get('curso', 'Desconocido')  # Si no tiene curso, lo marcamos como "Desconocido"
        log['presente'] = 'Sí'  # Añadimos la columna "Presente" y lo marcamos como 'Sí'
        logs_por_curso[curso].append(log)

    # Ordenar los cursos en el orden correcto: 4to, 5to, 6to
    cursos_ordenados = ['4to', '5to', '6to']
    logs_ordenados = []
    
    def safe_int(numero):
        try:
            return int(numero)
        except:
            return 9999  # Por si hay algún valor inválido o vacío

    for curso in cursos_ordenados:
        if curso in logs_por_curso:
            logs_ordenados.append({
                'curso': curso,
                'logs': sorted(logs_por_curso[curso], key=lambda x: safe_int(x.get('numero', '0')))
            })

    # Paginación de los logs agrupados por curso
    start = (page - 1) * logs_por_pagina
    end = start + logs_por_pagina

    # Crear una lista con los logs para cada curso según la página
    logs_paginados = []
    for curso_data in logs_ordenados:
        logs_paginados.append({
            'curso': curso_data['curso'],
            'logs': curso_data['logs'][start:end]
        })

    return logs_paginados



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
