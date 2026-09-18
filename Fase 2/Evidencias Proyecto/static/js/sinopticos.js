document.addEventListener('DOMContentLoaded', function () {

    const NOMBRES_DIAS = { 1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado' };

    const selectCarrera = document.getElementById('carrera');
    const selectSemestre = document.getElementById('semestre');
    const selectExistente = document.getElementById('sinopticoExistente');
    const btnCrearSinoptico = document.getElementById('btnCrearSinoptico');
    const mensaje = document.getElementById('mensaje');

    const bloqueAgregarClase = document.getElementById('bloqueAgregarClase');
    const selectAsignatura = document.getElementById('asignatura');
    const selectProfesor = document.getElementById('profesor');
    const selectSala = document.getElementById('sala');
    const selectBloqueHorario = document.getElementById('bloqueHorario');
    const btnAgregarClase = document.getElementById('btnAgregarClase');

    // Sinóptico que se está editando actualmente (recién creado o elegido de la lista)
    let sinopticoActualId = null;

    // --- Calendario ---
    const calendarEl = document.getElementById('calendar');
    const calendar = new FullCalendar.Calendar(calendarEl, {
        locale: 'es',
        initialView: 'timeGridWeek',
        headerToolbar: { left: '', center: 'title', right: '' },
        allDaySlot: false,
        slotMinTime: '08:00:00',
        slotMaxTime: '22:00:00',
        hiddenDays: [0],
        height: 'auto',
        events: [],
        eventContent: function (arg) {
            const props = arg.event.extendedProps;
            const div = document.createElement('div');
            div.innerHTML = `
                <b>${arg.event.title}</b>
                <div class="fc-event-detalle">${props.profesor || ''}</div>
                <div class="fc-event-detalle">Sala: ${props.sala || ''}</div>
            `;
            return { domNodes: [div] };
        }
    });
    calendar.render();

    function mostrarMensaje(texto, tipo) {
        mensaje.textContent = texto;
        mensaje.className = tipo;
    }

    function cargarEventos(sinopticoId) {
        fetch(`/sinopticos/${sinopticoId}/eventos`)
            .then(res => {
                if (!res.ok) {
                    // Un sinóptico recién creado y sin clases todavía da 404: no es un error real.
                    calendar.removeAllEvents();
                    return [];
                }
                return res.json();
            })
            .then(eventos => {
                calendar.removeAllEvents();
                calendar.addEventSource(eventos);
            });
    }

    // --- Combos que dependen de la carrera elegida ---
    function cargarAsignaturas(carreraId) {
        fetch(`/asignaturas?carrera_id=${carreraId}`)
            .then(res => res.json())
            .then(datos => {
                selectAsignatura.innerHTML = '';
                datos.forEach(a => {
                    const opt = document.createElement('option');
                    opt.value = a.id;
                    opt.textContent = `${a.nombre} (${a.codigo})`;
                    selectAsignatura.appendChild(opt);
                });
            });
    }

    // --- Combos generales (no dependen de la carrera) ---
    function cargarCarreras() {
        fetch('/carreras')
            .then(res => res.json())
            .then(datos => {
                selectCarrera.innerHTML = '';
                datos.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.id;
                    opt.textContent = `${c.nombre} (${c.codigo})`;
                    selectCarrera.appendChild(opt);
                });
                if (datos.length > 0) cargarAsignaturas(datos[0].id);
            });
    }

    function cargarSemestres() {
        fetch('/semestres')
            .then(res => res.json())
            .then(datos => {
                selectSemestre.innerHTML = '';
                datos.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.id;
                    opt.textContent = `${s.anio} - Semestre ${s.numero}`;
                    selectSemestre.appendChild(opt);
                });
            });
    }

    function cargarProfesores() {
        fetch('/profesores')
            .then(res => res.json())
            .then(datos => {
                selectProfesor.innerHTML = '';
                datos.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.id;
                    opt.textContent = `${p.nombre} ${p.apellido}`;
                    selectProfesor.appendChild(opt);
                });
            });
    }

    function cargarSalas() {
        fetch('/salas')
            .then(res => res.json())
            .then(datos => {
                selectSala.innerHTML = '';
                datos.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.id;
                    opt.textContent = `${s.nombre} (${s.cantidad_sillas} sillas)`;
                    selectSala.appendChild(opt);
                });
            });
    }

    function cargarBloquesHorario() {
        fetch('/bloques-horario')
            .then(res => res.json())
            .then(datos => {
                selectBloqueHorario.innerHTML = '';
                datos.forEach(b => {
                    const opt = document.createElement('option');
                    opt.value = b.id;
                    const dia = NOMBRES_DIAS[b.dia_semana] || `Día ${b.dia_semana}`;
                    opt.textContent = `${dia} ${b.hora_inicio.slice(0, 5)} - ${b.hora_fin.slice(0, 5)} (${b.jornada})`;
                    selectBloqueHorario.appendChild(opt);
                });
            });
    }

    function cargarSinopticosExistentes() {
        fetch('/sinopticos')
            .then(res => res.json())
            .then(datos => {
                selectExistente.innerHTML = '<option value="">-- Seleccione --</option>';
                datos.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.id;
                    opt.textContent = `#${s.id} - ${s.carrera} (${s.semestre})`;
                    selectExistente.appendChild(opt);
                });
            });
    }

    function activarSinoptico(sinopticoId) {
        sinopticoActualId = sinopticoId;
        bloqueAgregarClase.style.display = 'block';
        cargarEventos(sinopticoId);
    }

    // --- Eventos de la interfaz ---
    selectCarrera.addEventListener('change', function () {
        if (this.value) cargarAsignaturas(this.value);
    });

    selectExistente.addEventListener('change', function () {
        if (this.value) {
            mostrarMensaje(`Editando sinóptico #${this.value}`, 'info');
            activarSinoptico(this.value);
        }
    });

    btnCrearSinoptico.addEventListener('click', function () {
        if (!selectCarrera.value || !selectSemestre.value) {
            mostrarMensaje('Selecciona una carrera y un semestre.', 'error');
            return;
        }

        fetch('/sinopticos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                carrera_id: parseInt(selectCarrera.value),
                semestre_id: parseInt(selectSemestre.value)
            })
        })
            .then(async res => {
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'No se pudo crear el sinóptico.');
                return data;
            })
            .then(data => {
                mostrarMensaje(`Sinóptico #${data.id} creado. Ahora agrega las clases una por una.`, 'ok');
                activarSinoptico(data.id);
                cargarSinopticosExistentes();
            })
            .catch(err => mostrarMensaje(err.message, 'error'));
    });

    btnAgregarClase.addEventListener('click', function () {
        if (!sinopticoActualId) {
            mostrarMensaje('Primero crea o elige un sinóptico.', 'error');
            return;
        }
        if (!selectAsignatura.value || !selectBloqueHorario.value) {
            mostrarMensaje('Selecciona al menos la asignatura y el horario.', 'error');
            return;
        }

        fetch('/sinopticos/items', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sinoptico_id: sinopticoActualId,
                asignatura_id: parseInt(selectAsignatura.value),
                profesor_id: selectProfesor.value ? parseInt(selectProfesor.value) : null,
                sala_id: selectSala.value ? parseInt(selectSala.value) : null,
                bloque_horario_id: parseInt(selectBloqueHorario.value),
            })
        })
            .then(async res => {
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'No se pudo agregar la clase.');
                return data;
            })
            .then(() => {
                mostrarMensaje('Clase agregada correctamente.', 'ok');
                cargarEventos(sinopticoActualId);
            })
            .catch(err => mostrarMensaje(err.message, 'error'));
    });

    // --- Carga inicial ---
    cargarCarreras();
    cargarSemestres();
    cargarProfesores();
    cargarSalas();
    cargarBloquesHorario();
    cargarSinopticosExistentes();
});