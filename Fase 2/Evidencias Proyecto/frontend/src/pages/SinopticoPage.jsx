import { useEffect, useState } from 'react'
import Navbar from '../components/Navbar'
import api from '../api/axios'
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
  const [carreras, setCarreras] = useState([])
  const [semestres, setSemestres] = useState([])
  const [sinopticosExistentes, setSinopticosExistentes] = useState([])

  // Listas para llenar los combos del panel de edición
  const [asignaturas, setAsignaturas] = useState([])
  const [profesores, setProfesores] = useState([])
  const [salas, setSalas] = useState([])
  const [bloquesHorario, setBloquesHorario] = useState([])

  const [carreraSel, setCarreraSel] = useState('')
  const [semestreSel, setSemestreSel] = useState('')
  const [jornadaSel, setJornadaSel] = useState('diurno')
  const [sinopticoSel, setSinopticoSel] = useState('')

  const [eventos, setEventos] = useState([])
  const [mensaje, setMensaje] = useState('')

  // Panel de edición de una clase (null = cerrado)
  const [itemEditando, setItemEditando] = useState(null)

  useEffect(() => {
    api.get('/carreras')
      .then(res => setCarreras(res.data))
      .catch(err => console.error('Error carreras:', err))

    api.get('/semestres')
      .then(res => setSemestres(res.data))
      .catch(err => console.error('Error semestres:', err))

    api.get('/sinopticos')
      .then(res => setSinopticosExistentes(res.data))
      .catch(err => console.error('Error sinopticos:', err))

    api.get('/asignaturas')
      .then(res => setAsignaturas(res.data))
      .catch(err => console.error('Error asignaturas:', err))

    api.get('/profesores')
      .then(res => setProfesores(res.data))
      .catch(err => console.error('Error profesores:', err))

    api.get('/salas')
      .then(res => setSalas(res.data))
      .catch(err => console.error('Error salas:', err))

    api.get('/bloques-horario')
      .then(res => setBloquesHorario(res.data))
      .catch(err => console.error('Error bloques horario:', err))
  }, [])

  const cargarEventosSinoptico = async (id) => {
    try {
      const { data } = await api.get(`/sinopticos/${id}/eventos`)
      setEventos(data)
    } catch (err) {
      console.error('Error al cargar eventos:', err)
      setEventos([])
    }
  }

  const handleGenerarAuto = async () => {
    if (!carreraSel || !semestreSel) {
      setMensaje('Debe seleccionar carrera y semestre.')
      return
    }
    try {
      const { data } = await api.post('/sinopticos/generar', {
        carrera_id: parseInt(carreraSel),
        semestre_id: parseInt(semestreSel),
        jornada: jornadaSel
      })
      setMensaje(`Sinóptico #${data.sinoptico_id} generado correctamente.`)
      setSinopticoSel(data.sinoptico_id)
      cargarEventosSinoptico(data.sinoptico_id)
    } catch (err) {
      setMensaje(err.response?.data?.detail || 'Error al generar sinóptico.')
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
    const confirmado = window.confirm(
      `¿Está seguro de que desea eliminar el bloque "${clase.title}"? Esta acción no se puede deshacer.`
    )
    if (!confirmado) return

    try {
      await api.delete(`/sinopticos/items/${clase.id}`)
      setEventos(prev => prev.filter(e => e.id !== clase.id))
      setMensaje('Bloque de horario eliminado.')
    } catch (err) {
      setMensaje(err.response?.data?.detail || 'Error al eliminar el bloque.')
    }
  }

  const abrirEditorBloque = (clase) => {
    setItemEditando({
      id: clase.id,
      asignatura_id: clase.extendedProps?.asignatura_id ?? '',
      profesor_id: clase.extendedProps?.profesor_id ?? '',
      sala_id: clase.extendedProps?.sala_id ?? '',
      bloque_horario_id: clase.extendedProps?.bloque_horario_id ?? '',
    })
  }

  const cerrarEditorBloque = () => setItemEditando(null)

  const guardarEdicionBloque = async () => {
    if (!itemEditando.asignatura_id || !itemEditando.bloque_horario_id) {
      window.alert('Debe seleccionar al menos la asignatura y el bloque horario.')
      return
    }

    try {
      await api.put(`/sinopticos/items/${itemEditando.id}`, {
        asignatura_id: parseInt(itemEditando.asignatura_id),
        profesor_id: itemEditando.profesor_id ? parseInt(itemEditando.profesor_id) : null,
        sala_id: itemEditando.sala_id ? parseInt(itemEditando.sala_id) : null,
        bloque_horario_id: parseInt(itemEditando.bloque_horario_id),
      })
      setMensaje('Bloque actualizado correctamente.')
      cerrarEditorBloque()
      if (sinopticoSel) cargarEventosSinoptico(sinopticoSel)
    } catch (err) {
      const detalle = err.response?.data?.detail || 'No se pudo guardar la edición.'
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
    const claseId = parseInt(e.dataTransfer.getData('claseId'))
    const clase = eventos.find(ev => ev.id === claseId)
    if (!clase) return

    const [horaIni, horaFin] = nuevoModuloLabel.split(' A ')
    const diaActual = Array.isArray(clase.daysOfWeek) ? clase.daysOfWeek[0] : clase.daysOfWeek
    const horaActual = clase.startTime?.slice(0, 5)

    // Si se soltó en la misma celda de donde salió, no hacer nada
    if (diaActual === nuevoDiaKey && horaActual === horaIni) return

    const eventosAnteriores = eventos

    // Actualización optimista: se mueve visualmente de inmediato
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
        jornada: clase.extendedProps?.jornada || jornadaSel,
      })
      setMensaje('Bloque movido correctamente.')
    } catch (err) {
      // El backend rechazó el cambio (profesor u sala ya ocupados, u otro error):
      // se revierte el movimiento visual y se avisa el motivo exacto.
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
        <div className="duoc-card" style={{ width: '270px', height: 'fit-content', padding: '14px' }}>
          <h2 style={{ fontSize: '15px', margin: '0 0 10px 0', color: 'var(--duoc-navy)', borderBottom: '2px solid var(--duoc-yellow)', paddingBottom: '4px' }}>
            1. Elegir carrera y semestre
          </h2>

          <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
            <label className="duoc-label" style={{ fontSize: '11px' }}>Carrera</label>
            <select className="duoc-select" style={{ padding: '6px 8px', fontSize: '12px' }} value={carreraSel} onChange={e => setCarreraSel(e.target.value)}>
              <option value="">-- Seleccionar Carrera --</option>
              {carreras.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
            </select>
          </div>

          <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
            <label className="duoc-label" style={{ fontSize: '11px' }}>Semestre</label>
            <select className="duoc-select" style={{ padding: '6px 8px', fontSize: '12px' }} value={semestreSel} onChange={e => setSemestreSel(e.target.value)}>
              <option value="">-- Seleccionar Semestre --</option>
              {semestres.map(s => <option key={s.id} value={s.id}>{s.anio}-{s.numero} Semestre</option>)}
            </select>
          </div>

          <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
            <label className="duoc-label" style={{ fontSize: '11px' }}>Jornada</label>
            <select className="duoc-select" style={{ padding: '6px 8px', fontSize: '12px' }} value={jornadaSel} onChange={e => setJornadaSel(e.target.value)}>
              <option value="diurno">Diurno</option>
              <option value="vespertino">Vespertino</option>
            </select>
          </div>

          <button onClick={handleGenerarAuto} className="duoc-btn-primary" style={{ marginTop: '2px', padding: '7px 10px', fontSize: '12px' }}>
            Generar automáticamente
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
          </div>
        </div>

        {/* TABLA HORARIO COMPACTA AL MÁXIMO */}
        <div className="duoc-card" style={{ flex: 1, padding: '12px', overflowX: 'auto' }}>
          <div style={{ marginBottom: '8px', borderBottom: '2px solid var(--duoc-navy)', paddingBottom: '4px' }}>
            <h3 style={{ margin: 0, color: 'var(--duoc-navy)', fontSize: '15px', fontWeight: '800' }}>
              BOLETÍN DE CARGA ACADÉMICA - HORARIO DE CLASES
            </h3>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Jornada: Diurno · Arrastre los bloques para cambiar de horario</span>
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
                    return (
                      <td
                        key={d.key}
                        onDragOver={handleDragOver}
                        onDrop={(e) => handleDrop(e, d.key, m.label)}
                        style={{ padding: '1px 2px', border: '1px solid #cbd5e1', verticalAlign: 'middle', height: '24px' }}
                      >
                        {clase ? (
                          <div
                            draggable
                            onDragStart={(e) => handleDragStart(e, clase)}
                            style={{
                              backgroundColor: 'var(--duoc-blue-light)',
                              borderLeft: '3px solid var(--duoc-blue-accent)',
                              padding: '1px 4px',
                              borderRadius: '2px',
                              cursor: 'grab',
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
                                  border: 'none',
                                  background: 'var(--duoc-blue-accent, #2563eb)',
                                  color: '#fff',
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
                              <button
                                onClick={() => handleEliminarBloque(clase)}
                                title="Eliminar este bloque"
                                style={{
                                  border: 'none',
                                  background: '#b02a2a',
                                  color: '#fff',
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
                            </div>
                            <div style={{ fontWeight: 'bold', color: 'var(--duoc-navy)', fontSize: '9px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {clase.title}
                            </div>
                            <div style={{ color: '#0369a1', fontSize: '8.5px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {clase.extendedProps?.codigo} / {clase.extendedProps?.sala}
                            </div>
                          </div>
                        ) : null}
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
            style={{ width: '320px', padding: '18px' }}
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
                {asignaturas.map(a => (
                  <option key={a.id} value={a.id}>{a.nombre} ({a.codigo})</option>
                ))}
              </select>
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Profesor</label>
              <select
                className="duoc-select"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={itemEditando.profesor_id}
                onChange={e => setItemEditando({ ...itemEditando, profesor_id: e.target.value })}
              >
                <option value="">-- Sin asignar --</option>
                {profesores.map(p => (
                  <option key={p.id} value={p.id}>{p.nombre} {p.apellido}</option>
                ))}
              </select>
            </div>

            <div className="duoc-form-group" style={{ marginBottom: '10px' }}>
              <label className="duoc-label" style={{ fontSize: '11px' }}>Sala</label>
              <select
                className="duoc-select"
                style={{ padding: '6px 8px', fontSize: '12px' }}
                value={itemEditando.sala_id}
                onChange={e => setItemEditando({ ...itemEditando, sala_id: e.target.value })}
              >
                <option value="">-- Sin asignar --</option>
                {salas.map(s => (
                  <option key={s.id} value={s.id}>{s.nombre} ({s.cantidad_sillas} sillas)</option>
                ))}
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

            <div style={{ display: 'flex', gap: '8px' }}>
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
    </div>
  )
}