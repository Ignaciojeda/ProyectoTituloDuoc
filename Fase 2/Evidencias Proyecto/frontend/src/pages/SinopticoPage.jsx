import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import Navbar from '../components/Navbar'
import api from '../api/client'
import SelectorColor from '../components/SelectorColor'
import { COLOR_DEFAULT, colorValido, colorTextoSobre } from '../utils/color'
import { descargarPdfSinoptico, descargarExcelSinoptico } from '../utils/pdf'
import '../duoc.css'

const MODULOS_DUOC = [
  { id: 1, label: '08:31 A 09:10' },
  { id: 2, label: '09:11 A 09:50' },
  { id: 3, label: '10:01 A 10:40' },
  { id: 4, label: '10:41 A 11:20' },
  { id: 5, label: '11:31 A 12:10' },
  { id: 6, label: '12:11 A 12:50' },
  { id: 7, label: '13:01 A 13:40' },
  { id: 8, label: '13:41 A 14:20' },
  { id: 9, label: '14:31 A 15:10' },
  { id: 10, label: '15:11 A 15:50' },
  { id: 11, label: '16:01 A 16:40' },
  { id: 12, label: '16:41 A 17:20' },
  { id: 13, label: '17:31 A 18:10' },
]

const DIAS_SEMANA = [
  { key: 1, nombre: 'Lunes' },
  { key: 2, nombre: 'Martes' },
  { key: 3, nombre: 'Miércoles' },
  { key: 4, nombre: 'Jueves' },
  { key: 5, nombre: 'Viernes' },
  { key: 6, nombre: 'Sábado' },
]

export default function SinopticoPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [panelAbierto, setPanelAbierto] = useState(true)

  const [carreras, setCarreras] = useState([])
  const [semestres, setSemestres] = useState([])
  const [planes, setPlanes] = useState([])
  const [planSel, setPlanSel] = useState('')
  const [sinopticosExistentes, setSinopticosExistentes] = useState([])
  const [jornadas, setJornadas] = useState([])

  // Listas para llenar los combos del panel de edición
  const [asignaturas, setAsignaturas] = useState([])
  const [profesores, setProfesores] = useState([])
  const [profesoresDisponibles, setProfesoresDisponibles] = useState([])
  const [cargandoProfesores, setCargandoProfesores] = useState(false)
  const [salas, setSalas] = useState([])
  const [bloquesHorario, setBloquesHorario] = useState([])

  const [areasCarrera, setAreasCarrera] = useState([]) // áreas docentes propias de la carrera elegida, para resaltar profesores afines
  const [carreraSel, setCarreraSel] = useState('')
  const [semestreSel, setSemestreSel] = useState('')
  const [nivelSel, setNivelSel] = useState('') // Nivel de la malla (1°, 2°, 3°...), filtra qué ramos se muestran
  const [jornadaSel, setJornadaSel] = useState('diurno')
  const [sinopticoSel, setSinopticoSel] = useState('')

  const [eventos, setEventos] = useState([])
  const [mensaje, setMensaje] = useState('')

  // Estado "finalizado" del sinóptico abierto y horas requeridas/programadas por asignatura
  const [finalizadoSel, setFinalizadoSel] = useState(false)
  const [horasPorAsignatura, setHorasPorAsignatura] = useState([])
  const [finalizando, setFinalizando] = useState(false)

  // Panel de edición de una clase (null = cerrado)
  const [itemEditando, setItemEditando] = useState(null)

  // Modal para agregar nuevo ramo manualmente
  const [agregandoNuevo, setAgregandoNuevo] = useState(false)
  const [nuevoItem, setNuevoItem] = useState({
    asignatura_id: '',
    profesor_id: '',
    sala_id: '',
    bloque_horario_id: '',
    capacidad_inicial: '',
    tipo: '',
    color: COLOR_DEFAULT,
  })
  const [bloqueFijo, setBloqueFijo] = useState(false)

  useEffect(() => {
    api.get('/carreras').then(res => setCarreras(res.data)).catch(err => console.error('Error carreras:', err))
    api.get('/semestres').then(res => setSemestres(res.data)).catch(err => console.error('Error semestres:', err))
    api.get('/sinopticos').then(res => setSinopticosExistentes(res.data)).catch(err => console.error('Error sinopticos:', err))
    api.get('/asignaturas').then(res => setAsignaturas(res.data)).catch(err => console.error('Error asignaturas:', err))
    api.get('/profesores').then(res => {
      setProfesores(res.data)
      setProfesoresDisponibles(res.data)
    }).catch(err => console.error('Error profesores:', err))
    api.get('/salas').then(res => setSalas(res.data)).catch(err => console.error('Error salas:', err))
    api.get('/bloques-horario').then(res => setBloquesHorario(res.data)).catch(err => console.error('Error bloques horario:', err))
    api.get('/jornadas').then(res => setJornadas(res.data)).catch(err => console.error('Error jornadas:', err))
    api.get('/planes-estudio').then(res => setPlanes(res.data)).catch(err => console.error('Error planes:', err))
  }, [])

  // Cuando cambia la carrera seleccionada, traer qué áreas docentes le son propias
  useEffect(() => {
    if (!carreraSel) {
      setAreasCarrera([])
      return
    }
    api.get(`/carreras/${carreraSel}/areas-docentes`)
      .then(res => setAreasCarrera(res.data.areas || []))
      .catch(err => { console.error('Error areas-docentes:', err); setAreasCarrera([]) })
  }, [carreraSel])

  const profesorEsDeLaCarrera = (p) => {
    if (!areasCarrera.length || !p.area_docente) return false
    const area = p.area_docente.value ?? p.area_docente
    return areasCarrera.includes(area)
  }

  const ETIQUETAS_AREA = {
    informatica: 'Informática',
    redes: 'Redes',
    contabilidad: 'Contabilidad',
    administracion: 'Administración',
    prevencion_riesgos: 'Prevención de Riesgos',
    trabajo_social: 'Trabajo Social',
    diseno_grafico: 'Diseño Gráfico',
    turismo: 'Turismo',
    gastronomia: 'Gastronomía',
    enfermeria: 'Enfermería',
    matematica: 'Matemática',
    lenguaje: 'Lenguaje',
    ingles: 'Inglés',
  }

  const etiquetaAreaProfesor = (p) => {
    if (!p.area_docente) return ''
    const area = p.area_docente.value ?? p.area_docente
    return ETIQUETAS_AREA[area] || area
  }

  // Niveles disponibles, derivados de las asignaturas cargadas (1°, 2°, 3°...)
  const niveles = useMemo(() => {
    return [...new Set(asignaturas.map(a => a.nivel_semestral).filter(n => n !== null && n !== undefined))]
      .sort((a, b) => a - b)
  }, [asignaturas])

  // Asignaturas que se muestran en los selects de "agregar"/"editar", filtradas por el nivel elegido (si hay uno)
  const asignaturasFiltradas = useMemo(() => {
    if (!nivelSel) return asignaturas
    return asignaturas.filter(a => String(a.nivel_semestral) === String(nivelSel))
  }, [asignaturas, nivelSel])

  // Ids de las asignaturas que pertenecen a la carrera elegida (para mostrarlas primero)
  const [idsAsignaturasCarrera, setIdsAsignaturasCarrera] = useState(new Set())
  useEffect(() => {
    if (!carreraSel) {
      setIdsAsignaturasCarrera(new Set())
      return
    }
    api.get(`/asignaturas?carrera_id=${carreraSel}`)
      .then(res => setIdsAsignaturasCarrera(new Set(res.data.map(a => a.id))))
      .catch(() => setIdsAsignaturasCarrera(new Set()))
  }, [carreraSel])

  // Opciones del select de asignaturas: primero las de la carrera, luego las demás
  const opcionesAsignaturas = () => {
    const delaCarrera = asignaturasFiltradas.filter(a => idsAsignaturasCarrera.has(a.id))
    const otras = asignaturasFiltradas.filter(a => !idsAsignaturasCarrera.has(a.id))
    const opcion = a => <option key={a.id} value={a.id}>{a.nombre} ({a.codigo})</option>
    if (!delaCarrera.length) return asignaturasFiltradas.map(opcion)
    return (
      <>
        <optgroup label="★ De la carrera">{delaCarrera.map(opcion)}</optgroup>
        {otras.length > 0 && <optgroup label="Otras carreras">{otras.map(opcion)}</optgroup>}
      </>
    )
  }

  // Cargar profesores por disponibilidad cuando cambia el bloque seleccionado en "Agregar"
  useEffect(() => {
    if (agregandoNuevo && nuevoItem.bloque_horario_id) {
      cargarProfesoresPorDisponibilidad(nuevoItem.bloque_horario_id)
    }
  }, [agregandoNuevo, nuevoItem.bloque_horario_id])

  // Cargar profesores por disponibilidad cuando cambia el bloque seleccionado en "Editar"
  useEffect(() => {
    if (itemEditando && itemEditando.bloque_horario_id) {
      cargarProfesoresPorDisponibilidad(itemEditando.bloque_horario_id, itemEditando.id)
    }
  }, [itemEditando?.bloque_horario_id])

  const cargarProfesoresPorDisponibilidad = async (bloqueHorarioId, excluirItemId = null) => {
    if (!bloqueHorarioId) {
      setProfesoresDisponibles(profesores)
      return
    }
    setCargandoProfesores(true)
    try {
      const extra = excluirItemId ? `&excluir_item_id=${excluirItemId}` : ''
      const { data } = await api.get(`/profesores?bloque_horario_id=${bloqueHorarioId}${extra}`)
      setProfesoresDisponibles(data)
    } catch (err) {
      console.error('Error al filtrar profesores por disponibilidad:', err)
      setProfesoresDisponibles(profesores)
    } finally {
      setCargandoProfesores(false)
    }
  }

  // Al abrir/seleccionar un sinóptico existente se rellenan los filtros de la izquierda
  // (plan de estudio, semestre, nivel y jornada) con los datos de ese sinóptico.
  useEffect(() => {
    if (!sinopticoSel) return
    api.get(`/sinopticos/${sinopticoSel}/filtros`)
      .then(({ data }) => {
        if (data.carrera_id) setCarreraSel(String(data.carrera_id))
        if (data.plan_estudio_id) setPlanSel(String(data.plan_estudio_id))
        if (data.semestre_id) setSemestreSel(String(data.semestre_id))
        if (data.jornada) setJornadaSel(data.jornada)
        // nivel: número = ese nivel; 0 = varios niveles ("Todos"); null = sinóptico vacío (no se toca)
        if (data.nivel_semestral === 0) setNivelSel('')
        else if (data.nivel_semestral) setNivelSel(String(data.nivel_semestral))
        setFinalizadoSel(Boolean(data.finalizado))
      })
      .catch(err => console.error('No se pudieron rellenar los filtros del sinóptico:', err))
  }, [sinopticoSel])

  useEffect(() => {
    const idDesdeUrl = searchParams.get('id')
    if (idDesdeUrl) {
      setSinopticoSel(idDesdeUrl)
      cargarEventosSinoptico(idDesdeUrl)
    }
  }, [searchParams])

  const cargarEventosSinoptico = async (id) => {
    try {
      const { data } = await api.get(`/sinopticos/${id}/eventos`)
      setEventos(data)
    } catch (err) {
      console.error('Error al cargar eventos:', err)
      setEventos([])
    }
    cargarHorasSinoptico(id)
  }

  // Horas requeridas vs. programadas (18 semanas, 1 hora por bloque) de cada
  // asignatura que ya tiene clases en este sinóptico.
  const cargarHorasSinoptico = async (id) => {
    try {
      const { data } = await api.get(`/sinopticos/${id}/horas`)
      setHorasPorAsignatura(data)
    } catch (err) {
      console.error('Error al cargar las horas del sinóptico:', err)
      setHorasPorAsignatura([])
    }
  }

  // Info de horas (requeridas/programadas) para la asignatura seleccionada en un
  // formulario. "Requeridas" es la columna 'horas' de la asignatura TAL CUAL
  // (ya es el total del ramo, no se multiplica por nada). Si la asignatura
  // todavía no tiene clases en este sinóptico, las programadas parten en 0.
  const infoHorasAsignatura = (asignaturaId) => {
    if (!asignaturaId) return null
    const existente = horasPorAsignatura.find(h => String(h.asignatura_id) === String(asignaturaId))
    if (existente) return existente
    const asig = asignaturas.find(a => String(a.id) === String(asignaturaId))
    if (!asig) return null
    const requeridas = asig.horas || 0
    return {
      horas_requeridas: requeridas,
      horas_programadas: 0,
      cumple: requeridas === 0,
      diferencia: requeridas,
    }
  }

  // Caja con el resumen de horas (requeridas/programadas) de la asignatura
  // elegida en un formulario. null si todavía no hay asignatura seleccionada.
  // Las "programadas" sí son bloques del sinóptico x semanas en que se dictan.
  const renderInfoHoras = (asignaturaId) => {
    const info = infoHorasAsignatura(asignaturaId)
    if (!info) return null
    const colorFondo = info.cumple ? '#dcfce7' : '#fef3c7'
    const colorTexto = info.cumple ? '#15803d' : '#92400e'
    return (
      <div style={{
        marginTop: '-4px', marginBottom: '10px', padding: '6px 8px', fontSize: '11px',
        borderRadius: 'var(--radius-sm)', backgroundColor: colorFondo, color: colorTexto,
      }}>
        Horas: {info.horas_programadas} de {info.horas_requeridas} requeridas (programado según los bloques del sinóptico × semanas en que se dictan)
        {info.cumple
          ? ' — Completo'
          : info.diferencia > 0
            ? ` — Faltan ${info.diferencia} hrs`
            : ` — Sobran ${Math.abs(info.diferencia)} hrs`}
      </div>
    )
  }

  // Mensaje estándar cuando se intenta editar un sinóptico finalizado sin
  // haberlo desbloqueado primero.
  const avisarFinalizado = () => {
    window.alert('Este sinóptico está finalizado y quedó bloqueado para edición. Usa el botón "Desbloquear para editar" y confirma para poder modificarlo de nuevo.')
  }

  const handleFinalizarSinoptico = async () => {
    if (!sinopticoSel) {
      setMensaje('Primero seleccione un sinóptico de la lista.')
      return
    }
    const nuevoValor = !finalizadoSel
    const confirmado = window.confirm(
      nuevoValor
        ? `¿Finalizar el sinóptico #${sinopticoSel}? Se validará que todas sus asignaturas cumplan las horas requeridas y, mientras esté finalizado, quedará bloqueado para edición.`
        : `¿Desbloquear el sinóptico #${sinopticoSel} para editarlo? Dejará de estar marcado como finalizado hasta que lo vuelvas a finalizar.`
    )
    if (!confirmado) return
    setFinalizando(true)
    try {
      const { data } = await api.patch(`/sinopticos/${sinopticoSel}/finalizado`, { finalizado: nuevoValor })
      setFinalizadoSel(data.finalizado)
      setMensaje(data.finalizado ? `Sinóptico #${sinopticoSel} finalizado.` : `Sinóptico #${sinopticoSel} reabierto.`)
      const { data: lista } = await api.get('/sinopticos')
      setSinopticosExistentes(lista)
    } catch (err) {
      window.alert(err.response?.data?.detail || 'No se pudo cambiar el estado de finalizado.')
    } finally {
      setFinalizando(false)
    }
  }

  const handleGenerarAuto = async () => {
    if (!planSel || !semestreSel) {
      setMensaje('Debe seleccionar plan de estudio y semestre.')
      return
    }
    if (sinopticoSel && finalizadoSel) { avisarFinalizado(); return }
    // Si hay un sinóptico seleccionado, se ofrece generar DENTRO de él en vez de crear otro
    let rellenarId = null
    if (sinopticoSel) {
      const dentro = window.confirm(
        `Tienes seleccionado el sinóptico #${sinopticoSel}.\n\n` +
        `Aceptar: generar las asignaturas que le faltan DENTRO de ese sinóptico.\n` +
        `Cancelar: crear un sinóptico nuevo.`
      )
      if (dentro) rellenarId = parseInt(sinopticoSel)
    }
    try {
      const { data } = await api.post('/sinopticos/generar', {
        carrera_id: parseInt(carreraSel),
        plan_estudio_id: parseInt(planSel),
        semestre_id: parseInt(semestreSel),
        jornada: jornadaSel,
        nivel_semestral: nivelSel ? parseInt(nivelSel) : null,
        sinoptico_id: rellenarId,
      })
      setMensaje(rellenarId
        ? `Sinóptico #${data.sinoptico_id} completado correctamente.`
        : `Sinóptico #${data.sinoptico_id} generado correctamente.`)
      setSinopticoSel(data.sinoptico_id)
      cargarEventosSinoptico(data.sinoptico_id)

      const res = await api.get('/sinopticos')
      setSinopticosExistentes(res.data)
    } catch (err) {
      setMensaje(err.response?.data?.detail || 'Error al generar sinóptico.')
    }
  }

  // Crea un sinóptico vacío (sin asignar ramos automáticamente) para armarlo a mano con el '+' de la grilla
  const handleCrearVacio = async () => {
    if (!planSel || !semestreSel) {
      setMensaje('Debe seleccionar plan de estudio y semestre.')
      return
    }
    try {
      const { data } = await api.post('/sinopticos', {
        carrera_id: parseInt(carreraSel),
        plan_estudio_id: parseInt(planSel),
        semestre_id: parseInt(semestreSel),
        jornada: jornadaSel,
        nivel_semestral: nivelSel ? parseInt(nivelSel) : null,
      })
      setMensaje(`Sinóptico #${data.sinoptico_id} creado vacío. Use el "+" de la grilla para agregar ramos.`)
      setSinopticoSel(data.sinoptico_id)
      cargarEventosSinoptico(data.sinoptico_id)

      const res = await api.get('/sinopticos')
      setSinopticosExistentes(res.data)
    } catch (err) {
      setMensaje(err.response?.data?.detail || 'Error al crear el sinóptico.')
    }
  }

  // Salas con sillas suficientes para la capacidad indicada (la sala ya elegida siempre se mantiene)
  const salasParaCapacidad = (capacidad, salaActual) => {
    const cap = parseInt(capacidad)
    const sinCapacidad = isNaN(cap) || cap <= 0
    return salas
      .filter(s => (sinCapacidad ? false : s.cantidad_sillas >= cap) || String(s.id) === String(salaActual))
      .sort((a, b) => a.cantidad_sillas - b.cantidad_sillas || String(a.nombre).localeCompare(String(b.nombre)))
  }
  const capacidadValida = (c) => !isNaN(parseInt(c)) && parseInt(c) > 0

  // Al cambiar la sala de un bloque: ids de OTROS bloques de la misma asignatura (otros días) a los que también se aplica
  const [salaExtra, setSalaExtra] = useState([])

  // Ocupación de TODAS las salas (todos los sinópticos), para avisar al instante si una sala está ocupada
  const [ocupacionSalas, setOcupacionSalas] = useState({})
  const [cargandoOcupacion, setCargandoOcupacion] = useState(false)

  const cargarOcupacionSalas = async () => {
    setCargandoOcupacion(true)
    try {
      const { data } = await api.get('/salas/eventos')
      setOcupacionSalas(data || {})
    } catch (err) {
      console.error('No se pudo cargar la ocupación de salas:', err)
    } finally {
      setCargandoOcupacion(false)
    }
  }

  // Devuelve la clase que ocupa la sala en ese día/hora (o undefined si está libre)
  const ocupanteSala = (salaId, dia, horaInicio, ignorarItemId) => {
    if (!salaId) return undefined
    const lista = ocupacionSalas[String(salaId)] || []
    return lista.find(e =>
      String(e.id) !== String(ignorarItemId) &&
      (Array.isArray(e.daysOfWeek) ? e.daysOfWeek[0] : e.daysOfWeek) === dia &&
      String(e.startTime).slice(0, 5) === String(horaInicio).slice(0, 5)
    )
  }
  const textoOcupante = (e) => `${e.title}${e.extendedProps?.carrera ? ` (${e.extendedProps.carrera})` : ''}`

  // Bloque horario que se está editando (puede haber cambiado dentro del mismo formulario)
  const ocupanteDelBloqueEditado = () => {
    if (!itemEditando?.sala_id) return undefined
    const b = bloquesHorario.find(x => String(x.id) === String(itemEditando.bloque_horario_id))
    if (!b) return undefined
    return ocupanteSala(itemEditando.sala_id, b.dia_semana, b.hora_inicio, itemEditando.id)
  }

  useEffect(() => { setSalaExtra([]) }, [itemEditando?.sala_id])

  const hermanosDelBloque = (item) => {
    if (!item) return []
    return eventos
      .filter(e => String(e.extendedProps?.asignatura_id) === String(item.asignatura_id) && String(e.id) !== String(item.id))
      .sort((a, b) => (a.daysOfWeek?.[0] ?? 0) - (b.daysOfWeek?.[0] ?? 0) || String(a.startTime).localeCompare(String(b.startTime)))
  }
  const etiquetaDiaHora = (e) => {
    const dia = DIAS_SEMANA.find(d => d.key === (Array.isArray(e.daysOfWeek) ? e.daysOfWeek[0] : e.daysOfWeek))?.nombre || ''
    return `${dia} ${String(e.startTime || '').slice(0, 5)}`
  }

  const [verHistorial, setVerHistorial] = useState(false)
  const [historial, setHistorial] = useState([])
  const [cargandoHistorial, setCargandoHistorial] = useState(false)

  const abrirHistorial = async () => {
    if (!sinopticoSel) return
    setVerHistorial(true)
    setCargandoHistorial(true)
    try {
      const { data } = await api.get(`/sinopticos/${sinopticoSel}/historial`)
      setHistorial(data)
    } catch (err) {
      console.error('No se pudo cargar el historial:', err)
      setHistorial([])
    } finally {
      setCargandoHistorial(false)
    }
  }

  const handleExportarExcel = async () => {
    if (!sinopticoSel) {
      setMensaje('Primero seleccione un sinóptico de la lista.')
      return
    }
    try {
      await descargarExcelSinoptico(sinopticoSel)
    } catch (err) {
      console.error('Error al exportar Excel:', err)
      setMensaje('No se pudo generar el Excel.')
    }
  }

  const handleExportarPdf = async () => {
    if (!sinopticoSel) {
      setMensaje('Primero seleccione un sinóptico de la lista.')
      return
    }
    try {
      await descargarPdfSinoptico(sinopticoSel)
    } catch (err) {
      setMensaje('No se pudo generar el PDF del sinóptico.')
    }
  }

  const handleEliminarSinoptico = async () => {
    if (!sinopticoSel) {
      setMensaje('Primero seleccione un sinóptico de la lista.')
      return
    }
    const confirmado = window.confirm(
      `¿Está seguro de que desea eliminar el sinóptico #${sinopticoSel} completo? Esta acción no se puede deshacer y borrará todas sus clases.`
    )
    if (!confirmado) return

    try {
      await api.delete(`/sinopticos/${sinopticoSel}`)
      setMensaje(`Sinóptico #${sinopticoSel} eliminado.`)
      setSinopticoSel('')
      setEventos([])
      const { data } = await api.get('/sinopticos')
      setSinopticosExistentes(data)
    } catch (err) {
      setMensaje(err.response?.data?.detail || 'Error al eliminar el sinóptico.')
    }
  }

  const handleEliminarBloque = async (clase) => {
    if (finalizadoSel) { avisarFinalizado(); return }
    const confirmado = window.confirm(
      `¿Está seguro de que desea eliminar el bloque "${clase.title}"? Esta acción no se puede deshacer.`
    )
    if (!confirmado) return

    try {
      await api.delete(`/sinopticos/items/${clase.id}`)
      setEventos(prev => prev.filter(e => e.id !== clase.id))
      setMensaje('Bloque de horario eliminado.')
      if (sinopticoSel) cargarHorasSinoptico(sinopticoSel)
    } catch (err) {
      setMensaje(err.response?.data?.detail || 'Error al eliminar el bloque.')
    }
  }

  // --- Semanas en que se dicta la asignatura (1..18) ---
  const TOTAL_SEMANAS = 18
  const TODAS_LAS_SEMANAS = Array.from({ length: TOTAL_SEMANAS }, (_, i) => i + 1)
  const PRESETS_SEMANAS = [
    { nombre: 'Todas las semanas', semanas: TODAS_LAS_SEMANAS },
    { nombre: 'Semana por medio (impares)', semanas: TODAS_LAS_SEMANAS.filter(w => w % 2 === 1) },
    { nombre: 'Semana por medio (pares)', semanas: TODAS_LAS_SEMANAS.filter(w => w % 2 === 0) },
    { nombre: 'Una vez al mes', semanas: [1, 5, 9, 13, 17] },
  ]

  const alternarSemana = (w) => {
    setItemEditando(prev => {
      const actual = new Set(prev.semanas)
      actual.has(w) ? actual.delete(w) : actual.add(w)
      return { ...prev, semanas: [...actual].sort((a, b) => a - b) }
    })
  }

  const textoSemanas = (semanas) => {
    if (!semanas || semanas.length === TOTAL_SEMANAS) return 'Todas las semanas'
    return `Semanas: ${semanas.join(', ')}`
  }

  const abrirEditorBloque = (clase) => {
    const bloqueId = clase.extendedProps?.bloque_horario_id ?? ''
    setItemEditando({
      id: clase.id,
      asignatura_id: clase.extendedProps?.asignatura_id ?? '',
      profesor_id: clase.extendedProps?.profesor_id ?? '',
      sala_id: clase.extendedProps?.sala_id ?? '',
      salaOriginal: clase.extendedProps?.sala_id ?? '',
      bloque_horario_id: bloqueId,
      seccion: clase.extendedProps?.seccion ?? '',
      id_seccion: clase.extendedProps?.id_seccion ?? '',
      capacidad_inicial: clase.extendedProps?.capacidad_inicial ?? '',
      tipo: clase.extendedProps?.tipo ?? '',
      color: colorValido(clase.extendedProps?.color),
      semanas: clase.extendedProps?.semanas || TODAS_LAS_SEMANAS,
      semanasOriginales: clase.extendedProps?.semanas || TODAS_LAS_SEMANAS,
    })
    setSalaExtra([])
    cargarOcupacionSalas()
    if (bloqueId) {
      cargarProfesoresPorDisponibilidad(bloqueId, clase.id)
    }
  }

  const cerrarEditorBloque = () => setItemEditando(null)

  const guardarEdicionBloque = async () => {
    if (finalizadoSel) { avisarFinalizado(); return }
    if (!itemEditando.asignatura_id || !itemEditando.bloque_horario_id) {
      window.alert('Debe seleccionar al menos la asignatura y el bloque horario.')
      return
    }

    const choque = ocupanteDelBloqueEditado()
    if (choque) {
      window.alert(`Esa sala ya está ocupada en este horario por: ${textoOcupante(choque)}.`)
      return
    }

    try {
      await api.put(`/sinopticos/items/${itemEditando.id}`, {
        asignatura_id: parseInt(itemEditando.asignatura_id),
        profesor_id: itemEditando.profesor_id ? parseInt(itemEditando.profesor_id) : null,
        sala_id: itemEditando.sala_id ? parseInt(itemEditando.sala_id) : null,
        bloque_horario_id: parseInt(itemEditando.bloque_horario_id),
        capacidad_inicial: itemEditando.capacidad_inicial !== '' ? parseInt(itemEditando.capacidad_inicial) : null,
        tipo: itemEditando.tipo || null,
        color: itemEditando.color,
      })

      // Si se cambió la sala y el usuario eligió otros días, se aplica también a esos bloques
      const fallosSala = []
      for (const otroId of salaExtra) {
        const otro = eventos.find(e => String(e.id) === String(otroId))
        if (!otro) continue
        try {
          await api.put(`/sinopticos/items/${otro.id}`, {
            asignatura_id: otro.extendedProps.asignatura_id,
            profesor_id: otro.extendedProps.profesor_id ?? null,
            sala_id: itemEditando.sala_id ? parseInt(itemEditando.sala_id) : null,
            bloque_horario_id: otro.extendedProps.bloque_horario_id,
            capacidad_inicial: otro.extendedProps.capacidad_inicial ?? null,
            tipo: otro.extendedProps.tipo || null,
            color: itemEditando.color,
          })
        } catch (errOtro) {
          fallosSala.push(`${etiquetaDiaHora(otro)}: ${errOtro.response?.data?.detail || 'no se pudo cambiar la sala'}`)
        }
      }
      if (fallosSala.length) {
        window.alert('La sala no se pudo cambiar en estos días:\n\n' + fallosSala.join('\n'))
      }

      // Propaga el color a todos los bloques de esta misma asignatura dentro
      // de este mismo sinóptico (para que toda la asignatura luzca igual).
      try {
        await api.patch(`/sinopticos/${sinopticoSel}/asignaturas/${itemEditando.asignatura_id}/color`, {
          color: itemEditando.color,
        })
      } catch (errColor) {
        console.error('No se pudo propagar el color a la asignatura:', errColor)
      }

      // Semanas en que se dicta: se aplican a todos los bloques de la asignatura
      const cambioSemanas = JSON.stringify(itemEditando.semanas) !== JSON.stringify(itemEditando.semanasOriginales)
      if (cambioSemanas) {
        if (!itemEditando.semanas.length) {
          window.alert('Debes marcar al menos una semana.')
          return
        }
        await api.patch(`/sinopticos/${sinopticoSel}/asignaturas/${itemEditando.asignatura_id}/semanas`, {
          semanas: itemEditando.semanas,
        })
      }

      setMensaje('Bloque actualizado correctamente.')
      cerrarEditorBloque()
      if (sinopticoSel) cargarEventosSinoptico(sinopticoSel)
    } catch (err) {
      const detalle = err.response?.data?.detail || 'No se pudo guardar la edición.'
      window.alert(detalle)
    }
  }

  const abrirFormularioNuevo = () => {
    if (!sinopticoSel) {
      setMensaje('Primero seleccione un sinóptico existente.')
      return
    }
    if (finalizadoSel) { avisarFinalizado(); return }
    setNuevoItem({
      asignatura_id: '',
      profesor_id: '',
      sala_id: '',
      bloque_horario_id: '',
      capacidad_inicial: '',
      tipo: '',
      color: COLOR_DEFAULT,
    })
    setProfesoresDisponibles(profesores)
    setBloqueFijo(false)
    setAgregandoNuevo(true)
  }

  const cerrarFormularioNuevo = () => {
    setAgregandoNuevo(false)
    setBloqueFijo(false)
  }

  const abrirNuevoEnCelda = (diaKey, moduloLabel) => {
    if (!sinopticoSel) {
      setMensaje('Primero seleccione un sinóptico existente.')
      return
    }
    if (finalizadoSel) { avisarFinalizado(); return }

    const horaIni = moduloLabel.split(' A ')[0]
    const candidatos = bloquesHorario.filter(
      b => b.dia_semana === diaKey && b.hora_inicio.slice(0, 5) === horaIni
    )
    // Si el sinóptico es "mixto" se acepta cualquier jornada de bloque para esa celda;
    // si no, se prioriza el bloque de la jornada seleccionada en el panel.
    const bloque = candidatos.find(b => b.jornada === jornadaSel) || candidatos[0]
    if (!bloque) {
      setMensaje('No existe un bloque horario para esa celda.')
      return
    }

    setNuevoItem({
      asignatura_id: '',
      profesor_id: '',
      sala_id: '',
      bloque_horario_id: String(bloque.id),
      capacidad_inicial: '',
      tipo: '',
      color: COLOR_DEFAULT,
    })

    cargarProfesoresPorDisponibilidad(bloque.id)
    setBloqueFijo(true)
    setAgregandoNuevo(true)
  }

  const guardarNuevoItem = async () => {
    if (finalizadoSel) { avisarFinalizado(); return }
    if (!nuevoItem.asignatura_id || !nuevoItem.bloque_horario_id) {
      window.alert('Debe seleccionar al menos la asignatura y el bloque horario.')
      return
    }

    try {
      await api.post(`/sinopticos/items`, {
        sinoptico_id: parseInt(sinopticoSel),
        asignatura_id: parseInt(nuevoItem.asignatura_id),
        profesor_id: nuevoItem.profesor_id ? parseInt(nuevoItem.profesor_id) : null,
        sala_id: nuevoItem.sala_id ? parseInt(nuevoItem.sala_id) : null,
        bloque_horario_id: parseInt(nuevoItem.bloque_horario_id),
        capacidad_inicial: nuevoItem.capacidad_inicial !== '' ? parseInt(nuevoItem.capacidad_inicial) : null,
        tipo: nuevoItem.tipo || null,
        color: nuevoItem.color,
      })

      // Si ya existían otros bloques de esta asignatura en el sinóptico con otro
      // color, se iguala el color de todos (incluyendo el recién creado).
      try {
        await api.patch(`/sinopticos/${sinopticoSel}/asignaturas/${nuevoItem.asignatura_id}/color`, {
          color: nuevoItem.color,
        })
      } catch (errColor) {
        console.error('No se pudo propagar el color a la asignatura:', errColor)
      }

      setMensaje('Ramo agregado correctamente.')
      cerrarFormularioNuevo()
      cargarEventosSinoptico(sinopticoSel)
    } catch (err) {
      const detalle = err.response?.data?.detail || 'No se pudo agregar el ramo.'
      window.alert(detalle)
    }
  }

  const etiquetaBloque = (b) => {
    const dia = DIAS_SEMANA.find(d => d.key === b.dia_semana)?.nombre || `Día ${b.dia_semana}`
    return `${dia} ${b.hora_inicio.slice(0, 5)} - ${b.hora_fin.slice(0, 5)} (${b.jornada})`
  }

  const obtenerClaseParaModulo = (diaKey, horaInicioLabel) => {
    const horaMatch = horaInicioLabel.split(' A ')[0]
    return eventos.find(e => {
      const esDia = Array.isArray(e.daysOfWeek) ? e.daysOfWeek.includes(diaKey) : e.daysOfWeek === diaKey
      const esHora = e.startTime && e.startTime.startsWith(horaMatch)
      return esDia && esHora
    })
  }

  const handleDragStart = (e, clase) => {
    e.dataTransfer.setData('claseId', clase.id)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
  }

  const handleDrop = async (e, nuevoDiaKey, nuevoModuloLabel) => {
    e.preventDefault()
    if (finalizadoSel) { avisarFinalizado(); return }
    const claseId = parseInt(e.dataTransfer.getData('claseId'))
    const clase = eventos.find(ev => ev.id === claseId)
    if (!clase) return

    const [horaIni, horaFin] = nuevoModuloLabel.split(' A ')
    const diaActual = Array.isArray(clase.daysOfWeek) ? clase.daysOfWeek[0] : clase.daysOfWeek
    const horaActual = clase.startTime?.slice(0, 5)

    if (diaActual === nuevoDiaKey && horaActual === horaIni) return

    const eventosAnteriores = eventos

    setEventos(prev => prev.map(item =>
      item.id === claseId
        ? { ...item, daysOfWeek: [nuevoDiaKey], startTime: `${horaIni}:00`, endTime: `${horaFin}:00` }
        : item
    ))

    try {
      await api.patch(`/sinopticos/items/${claseId}/mover`, {
        dia_semana: nuevoDiaKey,
        hora_inicio: `${horaIni}:00`,
        hora_fin: `${horaFin}:00`,
        jornada: String(clase.extendedProps?.jornada || jornadaSel).toLowerCase(),
      })
      setMensaje('Bloque movido correctamente.')
    } catch (err) {
      setEventos(eventosAnteriores)
      const detalle = err.response?.data?.detail || 'No se pudo mover el bloque a ese horario.'
      setMensaje(detalle)
      window.alert(detalle)
    }
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <Navbar />

      <div style={{ display: 'flex', gap: '16px', padding: '16px 24px' }}>
        {/* PANEL IZQUIERDO */}
        {panelAbierto ? (
          <div className="duoc-card" style={{ width: '270px', height: 'fit-content', padding: '14px' }}>
            <div style={{ display: 'flex', gap: '6px', marginBottom: '12px' }}>
              <button
                onClick={() => navigate('/sinopticos/galeria')}
                style={{
                  width: '90%', marginBottom: '12px', padding: '7px 10px', fontSize: '12px',
                  border: '1px solid var(--duoc-navy)', borderRadius: 'var(--radius-sm)',
                  background: '#fff', color: 'var(--duoc-navy)', cursor: 'pointer', fontWeight: 600,
                }}
              >
                📂 Ver todos los sinópticos
              </button>
              <button
                onClick={() => setPanelAbierto(false)}
                title="Ocultar panel"
                style={{ width: '30px', marginBottom: '12px', padding: '0 4px', fontSize: '13px',
                  border: '1px solid var(--duoc-navy)', borderRadius: 'var(--radius-sm)',
                  background: '#fff', color: 'var(--duoc-navy)', cursor: 'pointer', fontWeight: 800 }}
              >
                «
              </button>
            </div>

            <h2 style={{ fontSize: '15px', margin: '0 0 10px 0', color: 'var(--duoc-navy)', borderBottom: '2px solid var(--duoc-yellow)', paddingBottom: '4px' }}>
              1. Elegir carrera, semestre y nivel
            </h2>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Plan de estudio</label>
              <select
                className="duoc-select"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={planSel}
                onChange={e => {
                  setPlanSel(e.target.value)
                  const p = planes.find(x => String(x.id) === e.target.value)
                  setCarreraSel(p ? String(p.carrera_id) : '')
                }}
              >
                <option value="">-- Seleccionar Carrera --</option>
                {planes.map(p => {
                  const c = carreras.find(x => x.id === p.carrera_id)
                  return (
                    <option key={p.id} value={p.id}>
                      {p.nombre.replace(/^Plan\s+/, '')}{c ? ` (${c.codigo})` : ''}
                    </option>
                  )
                })}
              </select>
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Semestre (periodo académico)</label>
              <select className="duoc-select" style={{ padding: '6px 8px', fontSize: '12px' }} value={semestreSel} onChange={e => setSemestreSel(e.target.value)}>
                <option value="">-- Seleccionar Semestre --</option>
                {semestres.map(s => <option key={s.id} value={s.id}>{s.anio}-{s.numero} Semestre</option>)}
              </select>
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Nivel (malla curricular)</label>
              <select className="duoc-select" style={{ padding: '6px 8px', fontSize: '12px' }} value={nivelSel} onChange={e => setNivelSel(e.target.value)}>
                <option value="">-- Todos los niveles --</option>
                {niveles.map(n => <option key={n} value={n}>{n}° nivel</option>)}
              </select>
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Jornada</label>
              <select className="duoc-select" style={{ padding: '6px 8px', fontSize: '12px' }} value={jornadaSel} onChange={e => setJornadaSel(e.target.value)}>
                {jornadas.length > 0 ? (
                  jornadas.map(j => (
                    <option key={j.id} value={j.nombre.toLowerCase()}>
                      {j.nombre.charAt(0).toUpperCase() + j.nombre.slice(1)}
                    </option>
                  ))
                ) : (
                  <>
                    <option value="diurno">Diurno</option>
                    <option value="vespertino">Vespertino</option>
                    <option value="mixta">Mixta</option>
                  </>
                )}
              </select>
            </div>

            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                onClick={handleGenerarAuto}
                disabled={Boolean(sinopticoSel) && finalizadoSel}
                className="duoc-btn-primary"
                style={{
                  marginTop: '2px', padding: '7px 10px', fontSize: '12px', flex: 1,
                  opacity: sinopticoSel && finalizadoSel ? 0.6 : 1,
                  cursor: sinopticoSel && finalizadoSel ? 'not-allowed' : 'pointer',
                }}
              >
                Generar automáticamente
              </button>
            </div>
            <button
              onClick={handleCrearVacio}
              style={{
                marginTop: '6px', padding: '7px 10px', fontSize: '12px', width: '100%',
                border: '1px solid var(--duoc-navy)', borderRadius: 'var(--radius-sm)',
                background: '#fff', color: 'var(--duoc-navy)', cursor: 'pointer', fontWeight: 600,
              }}
            >
              + Crear sinóptico vacío (armar a mano)
            </button>

            {mensaje && (
              <div style={{ marginTop: '8px', padding: '6px', backgroundColor: 'var(--duoc-blue-light)', color: 'var(--duoc-navy)', borderRadius: 'var(--radius-sm)', fontSize: '11px', textAlign: 'center', fontWeight: '600' }}>
                {mensaje}
              </div>
            )}

            <div style={{ marginTop: '14px', borderTop: '1px solid var(--border-color)', paddingTop: '10px' }}>
              <label className="duoc-label" style={{ fontWeight: 'bold', fontSize: '11px' }}>Seguir editando existente</label>
              <select className="duoc-select" style={{ padding: '6px 8px', fontSize: '12px' }} value={sinopticoSel} onChange={e => {
                setSinopticoSel(e.target.value)
                if (e.target.value) cargarEventosSinoptico(e.target.value)
              }}>
                <option value="">-- Seleccione Sinóptico --</option>
                {sinopticosExistentes.map(s => (
                  <option key={s.id} value={s.id}>#{s.id} - {s.carrera} ({s.semestre})</option>
                ))}
              </select>

              <button
                onClick={handleExportarPdf}
                disabled={!sinopticoSel}
                className="duoc-btn-accent"
                style={{ marginTop: '8px', padding: '7px 10px', fontSize: '12px', width: '100%', opacity: sinopticoSel ? 1 : 0.6, cursor: sinopticoSel ? 'pointer' : 'not-allowed' }}
              >
                Exportar PDF
              </button>

              <button
                onClick={handleExportarExcel}
                disabled={!sinopticoSel}
                className="duoc-btn-accent"
                style={{ marginTop: '8px', padding: '7px 10px', fontSize: '12px', width: '100%', opacity: sinopticoSel ? 1 : 0.6, cursor: sinopticoSel ? 'pointer' : 'not-allowed' }}
              >
                Exportar Excel
              </button>

              <button
                onClick={abrirHistorial}
                disabled={!sinopticoSel}
                className="duoc-btn-accent"
                style={{ marginTop: '8px', padding: '7px 10px', fontSize: '12px', width: '100%', opacity: sinopticoSel ? 1 : 0.6, cursor: sinopticoSel ? 'pointer' : 'not-allowed' }}
              >
                Historial de cambios
              </button>

              <button
                onClick={handleEliminarSinoptico}
                disabled={!sinopticoSel}
                className="duoc-btn-danger"
                style={{
                  marginTop: '8px',
                  padding: '7px 10px',
                  fontSize: '12px',
                  width: '100%',
                  backgroundColor: sinopticoSel ? '#b02a2a' : '#d1d5db',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  cursor: sinopticoSel ? 'pointer' : 'not-allowed',
                  fontWeight: 600,
                }}
              >
                Eliminar sinóptico completo
              </button>

              <button
                onClick={abrirFormularioNuevo}
                disabled={!sinopticoSel || finalizadoSel}
                className="duoc-btn-primary"
                style={{
                  marginTop: '8px', padding: '7px 10px', fontSize: '12px', width: '100%',
                  opacity: !sinopticoSel || finalizadoSel ? 0.6 : 1,
                  cursor: !sinopticoSel || finalizadoSel ? 'not-allowed' : 'pointer',
                }}
              >
                Agregar ramo manualmente
              </button>

              {/* --- Finalizar sinóptico --- */}
              <div style={{ marginTop: '14px', borderTop: '1px solid var(--border-color)', paddingTop: '10px' }}>
                {sinopticoSel && (
                  <div style={{
                    marginBottom: '8px', padding: '6px 8px', fontSize: '11px', fontWeight: 700,
                    borderRadius: 'var(--radius-sm)', textAlign: 'center',
                    backgroundColor: finalizadoSel ? '#dcfce7' : '#fef9c3',
                    color: finalizadoSel ? '#15803d' : '#854d0e',
                  }}>
                    {finalizadoSel ? '✓ Sinóptico finalizado' : 'Sinóptico en edición'}
                  </div>
                )}
                <button
                  onClick={handleFinalizarSinoptico}
                  disabled={!sinopticoSel || finalizando}
                  style={{
                    padding: '7px 10px', fontSize: '12px', width: '100%', fontWeight: 600,
                    border: 'none', borderRadius: 'var(--radius-sm)',
                    backgroundColor: !sinopticoSel ? '#d1d5db' : finalizadoSel ? '#fff' : '#15803d',
                    color: !sinopticoSel ? '#fff' : finalizadoSel ? '#15803d' : '#fff',
                    boxShadow: finalizadoSel && sinopticoSel ? 'inset 0 0 0 1px #15803d' : 'none',
                    cursor: !sinopticoSel || finalizando ? 'not-allowed' : 'pointer',
                    opacity: finalizando ? 0.7 : 1,
                  }}
                >
                  {finalizando ? 'Procesando...' : finalizadoSel ? 'Desbloquear para editar' : 'Finalizar sinóptico'}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setPanelAbierto(true)}
            title="Expandir panel"
            className="duoc-card"
            style={{ width: '30px', height: 'fit-content', padding: '6px 0', fontSize: '13px',
                border: '1px solid var(--duoc-navy)', borderRadius: 'var(--radius-sm)',
                background: '#fff', color: 'var(--duoc-navy)', cursor: 'pointer', fontWeight: 800 }}
          >
            »
          </button>
        )}

        {/* TABLA HORARIO COMPACTA */}
        <div className="duoc-card" style={{ flex: 1, padding: '12px', overflowX: 'auto' }}>
          {sinopticoSel && finalizadoSel && (
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px',
              marginBottom: '10px', padding: '8px 12px', borderRadius: 'var(--radius-sm)',
              backgroundColor: '#fef3c7', border: '1px solid #f3cf7a', color: '#854d0e', fontSize: '12px',
            }}>
              <span>🔒 Este sinóptico está <strong>finalizado</strong> y quedó bloqueado para edición. Para modificarlo debes desbloquearlo primero.</span>
              <button
                onClick={handleFinalizarSinoptico}
                disabled={finalizando}
                style={{
                  padding: '5px 10px', fontSize: '11px', fontWeight: 700, border: '1px solid #854d0e',
                  borderRadius: 'var(--radius-sm)', background: '#fff', color: '#854d0e',
                  cursor: finalizando ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap',
                }}
              >
                Desbloquear para editar
              </button>
            </div>
          )}
          <div style={{ marginBottom: '8px', borderBottom: '2px solid var(--duoc-navy)', paddingBottom: '4px' }}>
            <h3 style={{ margin: 0, color: 'var(--duoc-navy)', fontSize: '15px', fontWeight: '800' }}>
              BOLETÍN DE CARGA ACADÉMICA - HORARIO DE CLASES
            </h3>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Jornada: {jornadaSel.charAt(0).toUpperCase() + jornadaSel.slice(1)}
              {nivelSel ? ` · Nivel: ${nivelSel}°` : ''}
              {finalizadoSel
                ? ' · Sinóptico finalizado: bloqueado para edición'
                : ' · Haga click en una celda vacía para agregar un ramo · Arrastre los bloques para cambiar de horario'}
            </span>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', fontFamily: 'sans-serif', tableLayout: 'fixed' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--duoc-navy)', color: '#fff' }}>
                <th style={{ padding: '4px', border: '1px solid #cbd5e1', width: '45px', fontSize: '11px' }}>Módulo</th>
                <th style={{ padding: '4px', border: '1px solid #cbd5e1', width: '90px', fontSize: '11px' }}>Horario</th>
                {DIAS_SEMANA.map(d => (
                  <th key={d.key} style={{ padding: '4px', border: '1px solid #cbd5e1', textAlign: 'center', fontSize: '11px' }}>
                    {d.nombre}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MODULOS_DUOC.map((m) => (
                <tr key={m.id} style={{ backgroundColor: m.id % 2 === 0 ? '#f8fafc' : '#ffffff', height: '24px' }}>
                  <td style={{ padding: '1px 2px', border: '1px solid #cbd5e1', textAlign: 'center', fontWeight: 'bold', color: 'var(--duoc-navy)', fontSize: '10px' }}>
                    {m.id}
                  </td>
                  <td style={{ padding: '1px 2px', border: '1px solid #cbd5e1', textAlign: 'center', fontWeight: '600', color: 'var(--text-muted)', whiteSpace: 'nowrap', fontSize: '10px' }}>
                    {m.label}
                  </td>
                  {DIAS_SEMANA.map(d => {
                    const clase = obtenerClaseParaModulo(d.key, m.label)
                    const colorBloque = colorValido(clase?.extendedProps?.color)
                    const colorTexto = colorTextoSobre(colorBloque)
                    return (
                      <td
                        key={d.key}
                        onDragOver={handleDragOver}
                        onDrop={(e) => handleDrop(e, d.key, m.label)}
                        onClick={() => { if (!clase) abrirNuevoEnCelda(d.key, m.label) }}
                        style={{ padding: '1px 2px', border: '1px solid #cbd5e1', verticalAlign: 'middle', height: '24px', cursor: clase ? 'default' : (finalizadoSel ? 'not-allowed' : 'pointer'), position: 'relative', transition: 'background-color 0.15s ease' }}
                        onMouseEnter={(e) => {
                          if (!clase && !finalizadoSel) {
                            e.currentTarget.style.backgroundColor = '#eef6ff'
                            const plus = e.currentTarget.querySelector('.celda-plus')
                            if (plus) plus.style.opacity = '1'
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!clase && !finalizadoSel) {
                            e.currentTarget.style.backgroundColor = ''
                            const plus = e.currentTarget.querySelector('.celda-plus')
                            if (plus) plus.style.opacity = '0'
                          }
                        }}
                      >
                        {clase ? (
                          <div
                            draggable={!finalizadoSel}
                            onDragStart={(e) => handleDragStart(e, clase)}
                            style={{
                              backgroundColor: colorBloque,
                              border: '1px solid rgba(0,0,0,0.18)',
                              padding: '1px 4px',
                              borderRadius: '2px',
                              cursor: finalizadoSel ? 'default' : 'grab',
                              userSelect: 'none',
                              lineHeight: '1.1',
                              position: 'relative',
                            }}
                          >
                            <div style={{ position: 'absolute', top: '0px', right: '0px', display: 'flex', gap: '2px' }}>
                              <button
                                onClick={() => abrirEditorBloque(clase)}
                                title="Editar este bloque"
                                style={{
                                  border: '1px solid rgba(0,0,0,0.25)',
                                  background: '#fff',
                                  color: 'var(--duoc-navy)',
                                  borderRadius: '50%',
                                  width: '12px',
                                  height: '12px',
                                  fontSize: '8px',
                                  lineHeight: '12px',
                                  textAlign: 'center',
                                  cursor: 'pointer',
                                  padding: 0,
                                }}
                              >
                                ✎
                              </button>
                              {!finalizadoSel && (
                                <button
                                  onClick={() => handleEliminarBloque(clase)}
                                  title="Eliminar este bloque"
                                  style={{
                                    border: '1px solid rgba(0,0,0,0.25)',
                                    background: '#fff',
                                    color: '#b02a2a',
                                    borderRadius: '50%',
                                    width: '12px',
                                    height: '12px',
                                    fontSize: '9px',
                                    lineHeight: '12px',
                                    textAlign: 'center',
                                    cursor: 'pointer',
                                    padding: 0,
                                  }}
                                >
                                  ×
                                </button>
                              )}
                            </div>
                            <div style={{ fontWeight: 'bold', color: colorTexto, fontSize: '9px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {clase.title}
                            </div>
                            <div style={{ color: colorTexto, opacity: 0.9, fontSize: '8.5px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {clase.extendedProps?.seccion || clase.extendedProps?.codigo} / {clase.extendedProps?.sala}
                              {clase.extendedProps?.semanas ? ` · ${clase.extendedProps.semanas.length} sem.` : ''}
                            </div>
                          </div>
                        ) : (
                          <div
                            className="celda-plus"
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              height: '100%',
                              color: 'var(--duoc-blue-accent)',
                              fontSize: '16px',
                              fontWeight: 'bold',
                              opacity: 0,
                              transition: 'opacity 0.15s ease',
                              pointerEvents: 'none'
                            }}
                          >
                            +
                          </div>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* PANEL EMERGENTE DE EDICIÓN */}
      {itemEditando && (
        <div
          onClick={cerrarEditorBloque}
          style={{
            position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.45)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="duoc-card"
            style={{ width: '320px', padding: '18px', maxHeight: '92vh', overflowY: 'auto' }}
          >
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '15px', borderBottom: '2px solid var(--duoc-yellow)', paddingBottom: '6px' }}>
              Editar bloque
            </h3>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Asignatura</label>
              <select
                className="duoc-select"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={itemEditando.asignatura_id}
                onChange={e => setItemEditando({ ...itemEditando, asignatura_id: e.target.value })}
              >
                <option value="">-- Seleccionar --</option>
                {opcionesAsignaturas()}
              </select>
            </div>
            {renderInfoHoras(itemEditando.asignatura_id)}

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Sección (Sábana)</label>
              <input
                type="text"
                className="duoc-input"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                placeholder="Ej: ABA1101-001V"
                value={itemEditando.seccion}
                onChange={e => setItemEditando({ ...itemEditando, seccion: e.target.value })}
              />
            </div>

            {/* SELECCIÓN DE PROFESOR FILTRADO POR DISPONIBILIDAD */}
            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>
                Profesor {cargandoProfesores && <span style={{ color: 'var(--duoc-blue-accent)' }}>(buscando disponibles...)</span>}
                {areasCarrera.length > 0 && <span style={{ color: '#16a34a', fontWeight: 600 }}> (★ = área de la carrera)</span>}
              </label>
              <select
                className="duoc-select"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={itemEditando.profesor_id}
                onChange={e => setItemEditando({ ...itemEditando, profesor_id: e.target.value })}
              >
                <option value="">-- Sin asignar --</option>
                {profesoresDisponibles.map(p => (
                  <option
                    key={p.id}
                    value={p.id}
                    style={profesorEsDeLaCarrera(p) ? { color: '#16a34a', fontWeight: 700, backgroundColor: '#f0fdf4' } : undefined}
                  >
                    {profesorEsDeLaCarrera(p) ? '★ ' : ''}{p.nombre} {p.apellido} — {etiquetaAreaProfesor(p)}
                  </option>
                ))}
              </select>
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Cantidad de sillas / capacidad inicial</label>
              <input
                type="number"
                min="0"
                className="duoc-input"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={itemEditando.capacidad_inicial}
                onChange={e => setItemEditando({ ...itemEditando, capacidad_inicial: e.target.value })}
              />
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Sala {itemEditando.capacidad_inicial !== '' && <span style={{ fontWeight: 'normal', color: 'var(--text-muted)' }}>(con {itemEditando.capacidad_inicial} sillas o más)</span>}</label>
              <select
                className="duoc-select"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={itemEditando.sala_id}
                disabled={!capacidadValida(itemEditando.capacidad_inicial) && !itemEditando.sala_id}
                onChange={e => setItemEditando({ ...itemEditando, sala_id: e.target.value })}
              >
                <option value="">{capacidadValida(itemEditando.capacidad_inicial) || itemEditando.sala_id ? '-- Sin asignar --' : 'Primero indica la cantidad de sillas'}</option>
                {salasParaCapacidad(itemEditando.capacidad_inicial, itemEditando.sala_id).map(s => (
                  <option key={s.id} value={s.id}>{s.nombre} ({s.cantidad_sillas} sillas)</option>
                ))}
              </select>
            </div>

            {itemEditando.sala_id && ocupanteDelBloqueEditado() && (
              <p style={{ margin: '-4px 0 10px', fontSize: '11px', color: '#b91c1c' }}>
                ⚠ Esa sala ya está ocupada en este horario por {textoOcupante(ocupanteDelBloqueEditado())}.
              </p>
            )}

            {String(itemEditando.sala_id || '') !== String(itemEditando.salaOriginal || '') && itemEditando.sala_id && hermanosDelBloque(itemEditando).length > 0 && (() => {
              const hermanos = hermanosDelBloque(itemEditando).map(e => {
                const dia = Array.isArray(e.daysOfWeek) ? e.daysOfWeek[0] : e.daysOfWeek
                return { e, dia, ocupante: ocupanteSala(itemEditando.sala_id, dia, e.startTime, e.id) }
              })
              const libres = hermanos.filter(h => !h.ocupante).map(h => h.e.id)
              const porDia = hermanos.reduce((acc, h) => { (acc[h.dia] = acc[h.dia] || []).push(h); return acc }, {})
              return (
                <div style={{ marginBottom: '10px', padding: '8px', background: '#fffbeb', border: '1px solid #fcd34d', borderRadius: '6px', fontSize: '12px' }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '2px' }}>¿A qué días se aplica el cambio de sala?</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    {cargandoOcupacion ? 'Revisando disponibilidad de la sala...' : 'Se revisó la disponibilidad de la sala en cada bloque.'}
                  </div>
                  <label style={{ display: 'block', marginBottom: '4px' }}>
                    <input type="checkbox" checked disabled /> Este bloque
                  </label>
                  {Object.entries(porDia).map(([dia, lista]) => (
                    <div key={dia} style={{ marginBottom: '4px' }}>
                      <div style={{ fontWeight: 'bold', fontSize: '11px' }}>{DIAS_SEMANA.find(d => d.key === Number(dia))?.nombre}</div>
                      {lista.map(({ e, ocupante }) => (
                        <label key={e.id} style={{ display: 'block', marginLeft: '8px', color: ocupante ? '#9ca3af' : 'inherit' }}>
                          <input
                            type="checkbox"
                            disabled={!!ocupante || cargandoOcupacion}
                            checked={salaExtra.includes(e.id)}
                            onChange={ev => setSalaExtra(prev => ev.target.checked ? [...prev, e.id] : prev.filter(x => x !== e.id))}
                          /> {String(e.startTime).slice(0, 5)}{' '}
                          {ocupante
                            ? <span style={{ color: '#b91c1c' }}>— sala ocupada por {textoOcupante(ocupante)}</span>
                            : <span style={{ color: '#15803d' }}>— libre</span>}
                        </label>
                      ))}
                    </div>
                  ))}
                  <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                    <button
                      type="button"
                      onClick={() => setSalaExtra(libres)}
                      style={{ flex: 1, padding: '4px', fontSize: '11px', cursor: 'pointer', border: '1px solid #cbd5e1', background: '#fff', borderRadius: '6px' }}
                    >
                      Todos los libres
                    </button>
                    <button
                      type="button"
                      onClick={() => setSalaExtra([])}
                      style={{ flex: 1, padding: '4px', fontSize: '11px', cursor: 'pointer', border: '1px solid #cbd5e1', background: '#fff', borderRadius: '6px' }}
                    >
                      Solo este
                    </button>
                  </div>
                  {hermanos.some(h => h.ocupante) && (
                    <div style={{ marginTop: '6px', fontSize: '11px', color: '#b45309' }}>
                      Los bloques ocupados no se pueden cambiar. Si aplicas solo a algunos, la asignatura quedará en salas distintas ese día.
                    </div>
                  )}
                </div>
              )
            })()}

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Tipo de clase</label>
              <select
                className="duoc-select"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={itemEditando.tipo}
                onChange={e => setItemEditando({ ...itemEditando, tipo: e.target.value })}
              >
                <option value="">-- Sin definir --</option>
                <option value="teorica">Teórica</option>
                <option value="practica">Práctica</option>
              </select>
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '16px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Bloque horario</label>
              <select
                className="duoc-select"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={itemEditando.bloque_horario_id}
                onChange={e => setItemEditando({ ...itemEditando, bloque_horario_id: e.target.value })}
              >
                <option value="">-- Seleccionar --</option>
                {bloquesHorario.map(b => (
                  <option key={b.id} value={b.id}>{etiquetaBloque(b)}</option>
                ))}
              </select>
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '16px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Color</label>
              <SelectorColor
                value={itemEditando.color}
                onChange={c => setItemEditando({ ...itemEditando, color: c })}
              />
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '16px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>
                Semanas en que se dicta (aplica a toda la asignatura en este sinóptico)
              </label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '6px' }}>
                {PRESETS_SEMANAS.map(p => (
                  <button
                    key={p.nombre}
                    type="button"
                    onClick={() => setItemEditando({ ...itemEditando, semanas: p.semanas })}
                    style={{ fontSize: '10px', padding: '3px 6px', border: '1px solid var(--border-color)', borderRadius: '4px', background: '#fff', cursor: 'pointer' }}
                  >
                    {p.nombre}
                  </button>
                ))}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '4px' }}>
                {TODAS_LAS_SEMANAS.map(w => {
                  const marcada = itemEditando.semanas.includes(w)
                  return (
                    <label
                      key={w}
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '2px',
                        fontSize: '10px', padding: '3px 0', cursor: 'pointer', borderRadius: '4px',
                        border: '1px solid var(--border-color)',
                        background: marcada ? 'var(--duoc-yellow)' : '#fff',
                      }}
                    >
                      <input type="checkbox" checked={marcada} onChange={() => alternarSemana(w)} style={{ margin: 0 }} />
                      {w}
                    </label>
                  )
                })}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>
                {textoSemanas(itemEditando.semanas)}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', position: 'sticky', bottom: '-18px', background: '#fff', padding: '10px 0 4px', marginTop: '6px', borderTop: '1px solid #eef1f5' }}>
              <button
                onClick={guardarEdicionBloque}
                className="duoc-btn-primary"
                style={{ flex: 1, padding: '8px', fontSize: '12px' }}
              >
                Guardar cambios
              </button>
              <button
                onClick={cerrarEditorBloque}
                style={{
                  flex: 1, padding: '8px', fontSize: '12px',
                  border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)',
                  background: '#fff', cursor: 'pointer',
                }}
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL PARA AGREGAR RAMO (antes aparecía como panel al fondo del sidebar) */}
      {agregandoNuevo && (
        <div
          onClick={cerrarFormularioNuevo}
          style={{
            position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.45)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="duoc-card"
            style={{ width: '320px', padding: '18px', maxHeight: '92vh', overflowY: 'auto' }}
          >
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '15px', borderBottom: '2px solid var(--duoc-yellow)', paddingBottom: '6px' }}>
              Agregar ramo
            </h3>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Asignatura</label>
              <select
                className="duoc-select"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={nuevoItem.asignatura_id}
                onChange={e => setNuevoItem({ ...nuevoItem, asignatura_id: e.target.value })}
              >
                <option value="">-- Seleccionar --</option>
                {opcionesAsignaturas()}
              </select>
            </div>
            {renderInfoHoras(nuevoItem.asignatura_id)}

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Bloque horario</label>
              <select
                className="duoc-select"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={nuevoItem.bloque_horario_id}
                disabled={bloqueFijo}
                onChange={e => setNuevoItem({ ...nuevoItem, bloque_horario_id: e.target.value })}
              >
                <option value="">-- Seleccionar --</option>
                {bloquesHorario.map(b => (
                  <option key={b.id} value={b.id}>{etiquetaBloque(b)}</option>
                ))}
              </select>
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>
                Profesor {cargandoProfesores && <span style={{ color: 'var(--duoc-blue-accent)' }}>(buscando disponibles...)</span>}
                {areasCarrera.length > 0 && <span style={{ color: '#16a34a', fontWeight: 600 }}> (★ = área de la carrera)</span>}
              </label>
              <select
                className="duoc-select"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={nuevoItem.profesor_id}
                onChange={e => setNuevoItem({ ...nuevoItem, profesor_id: e.target.value })}
              >
                <option value="">-- Sin asignar --</option>
                {profesoresDisponibles.map(p => (
                  <option
                    key={p.id}
                    value={p.id}
                    style={profesorEsDeLaCarrera(p) ? { color: '#16a34a', fontWeight: 700, backgroundColor: '#f0fdf4' } : undefined}
                  >
                    {profesorEsDeLaCarrera(p) ? '★ ' : ''}{p.nombre} {p.apellido} — {etiquetaAreaProfesor(p)}
                  </option>
                ))}
              </select>
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Cantidad de sillas / capacidad inicial</label>
              <input
                type="number"
                min="0"
                className="duoc-input"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                placeholder="Ej: 30"
                value={nuevoItem.capacidad_inicial}
                onChange={e => setNuevoItem({ ...nuevoItem, capacidad_inicial: e.target.value })}
              />
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Sala {nuevoItem.capacidad_inicial !== '' && <span style={{ fontWeight: 'normal', color: 'var(--text-muted)' }}>(con {nuevoItem.capacidad_inicial} sillas o más)</span>}</label>
              <select
                className="duoc-select"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={nuevoItem.sala_id}
                disabled={!capacidadValida(nuevoItem.capacidad_inicial) && !nuevoItem.sala_id}
                onChange={e => setNuevoItem({ ...nuevoItem, sala_id: e.target.value })}
              >
                <option value="">{capacidadValida(nuevoItem.capacidad_inicial) || nuevoItem.sala_id ? '-- Sin asignar --' : 'Primero indica la cantidad de sillas'}</option>
                {salasParaCapacidad(nuevoItem.capacidad_inicial, nuevoItem.sala_id).map(s => (
                  <option key={s.id} value={s.id}>{s.nombre} ({s.cantidad_sillas} sillas)</option>
                ))}
              </select>
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Tipo de clase</label>
              <select
                className="duoc-select"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={nuevoItem.tipo}
                onChange={e => setNuevoItem({ ...nuevoItem, tipo: e.target.value })}
              >
                <option value="">-- Sin definir --</option>
                <option value="teorica">Teórica</option>
                <option value="practica">Práctica</option>
              </select>
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '16px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Color</label>
              <SelectorColor
                value={nuevoItem.color}
                onChange={c => setNuevoItem({ ...nuevoItem, color: c })}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px', position: 'sticky', bottom: '-18px', background: '#fff', padding: '10px 0 4px', marginTop: '6px', borderTop: '1px solid #eef1f5' }}>
              <button
                onClick={guardarNuevoItem}
                className="duoc-btn-primary"
                style={{ flex: 1, padding: '8px', fontSize: '12px' }}
              >
                Agregar
              </button>
              <button
                onClick={cerrarFormularioNuevo}
                style={{
                  flex: 1, padding: '8px', fontSize: '12px',
                  border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)',
                  background: '#fff', cursor: 'pointer',
                }}
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {verHistorial && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
          onClick={() => setVerHistorial(false)}
        >
          <div className="duoc-card" style={{ width: '560px', maxWidth: '92vw', maxHeight: '80vh', overflowY: 'auto', padding: '18px' }} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 10px', color: 'var(--duoc-navy)', fontSize: '17px' }}>Historial de cambios del sinóptico</h3>
            {cargandoHistorial && <p>Cargando...</p>}
            {!cargandoHistorial && historial.length === 0 && (
              <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Todavía no hay cambios registrados (solo se registran los hechos desde esta versión).</p>
            )}
            {historial.map(h => (
              <div key={h.id} style={{ borderTop: '1px solid #eef1f5', padding: '8px 0', fontSize: '12px' }}>
                <div style={{ color: 'var(--text-muted)' }}>
                  {h.fecha ? new Date(h.fecha + (h.fecha.endsWith('Z') ? '' : 'Z')).toLocaleString('es-CL') : ''} · <strong>{h.usuario}</strong>
                </div>
                <div>{h.detalle}</div>
              </div>
            ))}
            <div style={{ textAlign: 'right', marginTop: '12px' }}>
              <button onClick={() => setVerHistorial(false)} style={{ padding: '7px 14px', fontSize: '13px', cursor: 'pointer', border: '1px solid #cbd5e1', background: '#fff', borderRadius: '6px' }}>
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}