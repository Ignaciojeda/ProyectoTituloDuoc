import { useEffect, useMemo, useState } from 'react'
import Navbar from '../components/Navbar'
import api from '../api/axios'
import '../duoc.css'

const DIAS = [
  { key: 1, nombre: 'Lunes' },
  { key: 2, nombre: 'Martes' },
  { key: 3, nombre: 'Miércoles' },
  { key: 4, nombre: 'Jueves' },
  { key: 5, nombre: 'Viernes' },
  { key: 6, nombre: 'Sábado' },
]

// La ruta ya está restringida a coordinador y administrador (ProtectedRoute en App.jsx).
export default function ProfesorDisponibilidadPage() {
  const [profesores, setProfesores] = useState([])
  const [resumen, setResumen] = useState({})
  const [bloques, setBloques] = useState([])
  const [busqueda, setBusqueda] = useState('')
  const [profId, setProfId] = useState('')
  const [disponibles, setDisponibles] = useState(new Set())
  const [ocupados, setOcupados] = useState(new Set())
  const [cargando, setCargando] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [mensaje, setMensaje] = useState({ tipo: '', texto: '' })
  // Cambio pendiente de confirmar: { ids: [...], disponible: true|false, descripcion }
  const [pendiente, setPendiente] = useState(null)

  useEffect(() => {
    const init = async () => {
      try {
        const [rp, rr, rb] = await Promise.all([
          api.get('/profesores'),
          api.get('/profesores/disponibilidad'),
          api.get('/bloques-horario'),
        ])
        setProfesores(rp.data)
        setResumen(rr.data || {})
        setBloques(rb.data)
      } catch (err) {
        setMensaje({ tipo: 'error', texto: 'No se pudieron cargar los datos.' })
      }
    }
    init()
  }, [])

  const cargarProfesor = async (id) => {
    setProfId(id)
    setMensaje({ tipo: '', texto: '' })
    setPendiente(null)
    if (!id) return
    setCargando(true)
    try {
      const { data } = await api.get(`/profesores/${id}/disponibilidad`)
      setDisponibles(new Set(data.bloques_disponibles))
      setOcupados(new Set(data.bloques_ocupados))
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.response?.data?.detail || 'Error al cargar la disponibilidad.' })
    } finally {
      setCargando(false)
    }
  }

  // Filas = horas de inicio distintas; celda = bloque de ese día/hora
  const filas = useMemo(() => {
    const mapa = new Map()
    bloques.forEach(b => {
      const ini = b.hora_inicio.slice(0, 5)
      if (!mapa.has(ini)) mapa.set(ini, { ini, fin: b.hora_fin.slice(0, 5), porDia: {} })
      mapa.get(ini).porDia[b.dia_semana] = b
    })
    return [...mapa.values()].sort((a, b) => a.ini.localeCompare(b.ini))
  }, [bloques])

  const nombreDia = (k) => DIAS.find(d => d.key === k)?.nombre || `Día ${k}`
  const profActual = profesores.find(p => String(p.id) === String(profId))
  const nombreProf = profActual ? `${profActual.nombre} ${profActual.apellido}` : ''

  // Clic en una celda: pregunta antes de agregar (o quitar) ese bloque
  const pedirConfirmacionCelda = (b) => {
    if (!profId || guardando) return
    const esDisp = disponibles.has(b.id)
    setPendiente({
      ids: [b.id],
      disponible: !esDisp,
      descripcion: `${nombreDia(b.dia_semana)} ${b.hora_inicio.slice(0, 5)} - ${b.hora_fin.slice(0, 5)}`,
      conClase: esDisp && ocupados.has(b.id),
    })
  }

  // Clic en día u hora: agrega todos los bloques que falten, o quita todos si ya estaban
  const pedirConfirmacionGrupo = (ids, descripcion) => {
    if (!profId || guardando || !ids.length) return
    const todos = ids.every(i => disponibles.has(i))
    const afectados = todos ? ids : ids.filter(i => !disponibles.has(i))
    setPendiente({
      ids: afectados,
      disponible: !todos,
      descripcion: `${descripcion} (${afectados.length} bloque${afectados.length !== 1 ? 's' : ''})`,
      conClase: todos && afectados.some(i => ocupados.has(i)),
    })
  }

  const idsDia = (diaKey) => filas.map(f => f.porDia[diaKey]?.id).filter(Boolean)
  const idsFila = (fila) => DIAS.map(d => fila.porDia[d.key]?.id).filter(Boolean)

  const confirmar = async () => {
    if (!pendiente) return
    const { ids, disponible } = pendiente
    setGuardando(true)
    setMensaje({ tipo: '', texto: '' })
    try {
      await api.put(`/profesores/${profId}/disponibilidad`, { bloque_horario_ids: ids, disponible })
      const nuevo = new Set(disponibles)
      ids.forEach(i => (disponible ? nuevo.add(i) : nuevo.delete(i)))
      setDisponibles(nuevo)
      setResumen(r => ({ ...r, [String(profId)]: nuevo.size }))
      setMensaje({ tipo: 'ok', texto: disponible ? 'Bloque agregado y guardado.' : 'Bloque quitado y guardado.' })
      setPendiente(null)
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.response?.data?.detail || 'Error al guardar el cambio.' })
      setPendiente(null)
    } finally {
      setGuardando(false)
    }
  }

  const filtrados = profesores.filter(p =>
    `${p.nombre} ${p.apellido}`.toLowerCase().includes(busqueda.toLowerCase())
  )

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <Navbar />
      <div style={{ padding: '16px 24px', display: 'flex', gap: '20px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* Lista de profesores */}
        <div className="duoc-card" style={{ width: '280px', padding: '12px' }}>
          <h3 style={{ margin: '0 0 8px', color: 'var(--duoc-navy)', fontSize: '15px' }}>Profesores</h3>
          <input
            placeholder="Buscar profesor..."
            value={busqueda}
            onChange={e => setBusqueda(e.target.value)}
            style={{ width: '100%', padding: '6px', marginBottom: '8px', boxSizing: 'border-box' }}
          />
          <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
            {filtrados.map(p => {
              const total = resumen[String(p.id)] || 0
              const activo = String(p.id) === String(profId)
              return (
                <div
                  key={p.id}
                  onClick={() => cargarProfesor(String(p.id))}
                  style={{
                    padding: '6px 8px', cursor: 'pointer', fontSize: '12px', borderRadius: '4px',
                    backgroundColor: activo ? 'var(--duoc-yellow)' : 'transparent',
                    display: 'flex', justifyContent: 'space-between', gap: '8px',
                  }}
                >
                  <span>{p.nombre} {p.apellido}</span>
                  <span style={{ color: total ? '#15803d' : '#b45309', fontWeight: 'bold' }}>
                    {total ? `${total} bl.` : 'sin horario'}
                  </span>
                </div>
              )
            })}
            {filtrados.length === 0 && <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Sin resultados.</p>}
          </div>
        </div>

        {/* Grilla */}
        <div style={{ flex: 1, minWidth: '420px' }}>
          {!profActual && <p style={{ color: 'var(--text-muted)' }}>Selecciona un profesor para ver y modificar su disponibilidad.</p>}

          {profActual && (
            <div className="duoc-card" style={{ padding: '12px' }}>
              <h3 style={{ margin: '0 0 8px', color: 'var(--duoc-navy)' }}>{nombreProf}</h3>

              <div style={{ display: 'flex', gap: '14px', fontSize: '11px', marginBottom: '8px', flexWrap: 'wrap' }}>
                <span><span style={{ background: '#16a34a', padding: '0 8px' }}>&nbsp;</span> Disponible</span>
                <span><span style={{ background: '#b45309', padding: '0 8px' }}>&nbsp;</span> Con clase asignada</span>
                <span><span style={{ background: '#eef1f5', padding: '0 8px', border: '1px solid #ccc' }}>&nbsp;</span> No disponible</span>
                <span style={{ color: 'var(--text-muted)' }}>Clic en una celda para agregar o quitar el bloque (se pide confirmación y se guarda al instante).</span>
              </div>

              {!disponibles.size && !cargando && (
                <p style={{ fontSize: '12px', color: '#b45309', margin: '4px 0 8px' }}>
                  Este profesor no tiene horarios cargados: al generar sinópticos se considera sin restricciones.
                </p>
              )}

              {cargando ? <p>Cargando...</p> : (
                <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                  <thead>
                    <tr>
                      <th></th>
                      {DIAS.map(d => (
                        <th
                          key={d.key}
                          onClick={() => pedirConfirmacionGrupo(idsDia(d.key), `Todo el ${d.nombre.toLowerCase()}`)}
                          style={{ fontSize: '12px', padding: '4px', cursor: 'pointer', color: 'var(--duoc-navy)' }}
                        >
                          {d.nombre}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filas.map(f => (
                      <tr key={f.ini}>
                        <td
                          onClick={() => pedirConfirmacionGrupo(idsFila(f), `Toda la franja ${f.ini} - ${f.fin}`)}
                          style={{ fontSize: '11px', padding: '2px 6px', whiteSpace: 'nowrap', cursor: 'pointer', color: 'var(--text-muted)' }}
                        >
                          {f.ini} - {f.fin}
                        </td>
                        {DIAS.map(d => {
                          const b = f.porDia[d.key]
                          if (!b) return <td key={d.key} style={{ background: '#f8f9fb', border: '1px solid #fff' }} />
                          const ocupado = ocupados.has(b.id)
                          const libre = disponibles.has(b.id)
                          const color = ocupado ? '#b45309' : libre ? '#16a34a' : '#eef1f5'
                          return (
                            <td
                              key={d.key}
                              onClick={() => pedirConfirmacionCelda(b)}
                              title={ocupado ? 'Con clase asignada en un sinóptico' : libre ? 'Disponible (clic para quitar)' : 'No disponible (clic para agregar)'}
                              style={{
                                height: '22px', background: color, border: '1px solid #fff', cursor: 'pointer',
                                outline: ocupado && libre ? '2px solid #16a34a' : 'none', outlineOffset: '-2px',
                              }}
                            />
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {mensaje.texto && (
            <p style={{ marginTop: '10px', fontSize: '13px', color: mensaje.tipo === 'ok' ? '#15803d' : '#b91c1c' }}>
              {mensaje.texto}
            </p>
          )}
        </div>
      </div>

      {/* Ventana de confirmación */}
      {pendiente && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
          onClick={() => !guardando && setPendiente(null)}
        >
          <div className="duoc-card" style={{ width: '380px', padding: '20px' }} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 10px', color: 'var(--duoc-navy)', fontSize: '17px' }}>
              {pendiente.disponible ? 'Agregar disponibilidad' : 'Quitar disponibilidad'}
            </h3>
            <p style={{ margin: '0 0 8px', fontSize: '14px', lineHeight: 1.5 }}>
              {pendiente.disponible
                ? <>¿Quieres agregar <strong>{pendiente.descripcion}</strong> al horario disponible de <strong>{nombreProf}</strong>?</>
                : <>¿Quieres quitar <strong>{pendiente.descripcion}</strong> del horario disponible de <strong>{nombreProf}</strong>?</>}
            </p>
            {pendiente.conClase && (
              <p style={{ margin: '0 0 8px', fontSize: '12px', color: '#b45309' }}>
                Ojo: el profesor ya tiene clase asignada en este horario. Quitar su disponibilidad no modifica los sinópticos existentes.
              </p>
            )}
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button
                onClick={() => setPendiente(null)}
                disabled={guardando}
                style={{ padding: '8px 14px', fontSize: '13px', cursor: 'pointer', border: '1px solid #cbd5e1', background: '#fff', borderRadius: '6px' }}
              >
                Cancelar
              </button>
              <button
                onClick={confirmar}
                disabled={guardando}
                className="duoc-btn-primary"
                style={{ padding: '8px 14px', fontSize: '13px', opacity: guardando ? 0.6 : 1 }}
              >
                {guardando ? 'Guardando...' : pendiente.disponible ? 'Sí, agregar' : 'Sí, quitar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}