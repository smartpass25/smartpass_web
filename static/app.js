document.addEventListener("DOMContentLoaded", function () {
    const cursos = {
        "estudiantes 4to": "tabla_4to",
        "estudiantes 5to": "tabla_5to",
        "estudiantes 6to": "tabla_6to"
    };

    let estudiantesGuardados = {
        "estudiantes 4to": [],
        "estudiantes 5to": [],
        "estudiantes 6to": []
    };

    // Cargar estudiantes al inicio
    function cargarEstudiantes() {
        for (let curso in cursos) {
            fetch(`/get_estudiantes/${encodeURIComponent(curso)}?filtro=all&valor=`)
                .then(response => response.json())
                .then(data => {
                    estudiantesGuardados[curso] = data;
                    actualizarTabla(curso, data);  // Actualiza la tabla con los datos cargados
                })
                .catch(error => console.error(`Error al cargar estudiantes de ${curso}:`, error));
        }
    }

    // Actualizar la tabla con los estudiantes
    function actualizarTabla(curso, estudiantes) {
        const tableId = cursos[curso];
        const tbody = document.querySelector(`#${tableId} tbody`);
        if (!tbody) return;

        tbody.innerHTML = ''; // Limpiar la tabla antes de agregar los nuevos estudiantes

        estudiantes.forEach(est => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${est.name}</td>
                <td>${est.numero}</td>
                <td>${est.curso}</td>
                <td>${est.last_access}</td>
            `;
            tbody.appendChild(row);
        });
    }

    // Filtrar estudiantes basado en la búsqueda
    function filtrarEstudiantes(index, curso) {
        const searchInput = document.getElementById('search' + index);
        const filterOption = document.getElementById('filterOption' + index);

        if (!searchInput || !filterOption) return;  // Si los elementos no existen, no hacer nada

        const searchValue = searchInput.value.toLowerCase().trim();
        const filterValue = filterOption.value;

        console.log('Filtro de búsqueda:', searchValue);
        console.log('Filtro de opción:', filterValue);

        let estudiantesFiltrados = estudiantesGuardados[curso];

        if (searchValue !== '') {
            estudiantesFiltrados = estudiantesFiltrados.filter(est => {
                let mostrar = false;

                if (filterValue === 'all') {
                    mostrar = est.name.toLowerCase().includes(searchValue) || est.numero.toLowerCase().includes(searchValue);
                } else if (filterValue === 'name') {
                    mostrar = est.name.toLowerCase().includes(searchValue);
                } else if (filterValue === 'numero') {
                    mostrar = est.numero.toLowerCase().includes(searchValue);
                }

                return mostrar;
            });
        }

        // Filtrar alfabéticamente si se selecciona esa opción
        if (filterValue === 'alfabetico') {
            estudiantesFiltrados.sort((a, b) => a.name.localeCompare(b.name));
        }

        console.log('Estudiantes filtrados:', estudiantesFiltrados);

        // Actualizar la tabla con los estudiantes filtrados
        actualizarTabla(curso, estudiantesFiltrados);
    }

    // Agregar eventos de filtrado
    function agregarEventosFiltrado() {
        ['0', '1', '2'].forEach(index => {
            const searchInput = document.getElementById('search' + index);
            const filterOption = document.getElementById('filterOption' + index);

            // Comprobar si los elementos existen antes de añadir el eventListener
            if (searchInput) {
                searchInput.addEventListener('input', () => filtrarEstudiantes(index, `estudiantes ${['4to', '5to', '6to'][index]}`));
            }
            if (filterOption) {
                filterOption.addEventListener('change', () => filtrarEstudiantes(index, `estudiantes ${['4to', '5to', '6to'][index]}`));
            }
        });
    }

    // Inicializar carga de estudiantes cuando la página se carga
    cargarEstudiantes();
    agregarEventosFiltrado();
});
