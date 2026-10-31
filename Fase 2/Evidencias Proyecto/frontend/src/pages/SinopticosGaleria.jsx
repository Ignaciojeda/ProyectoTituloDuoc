import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import api from '../api/client'
import { colorValido } from '../utils/color'
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

export default function SinopticosGaleria() {
  const navigate = useNavigate()
  const [sinopticos, setSinopticos] = useState([])
  const [eventosPorSinoptico, setEventosPorSinoptico] = useState({})
  const [cargando, setCargando] = useState(true)

  // Filtros: por carrera y por estado (todos / finalizados / por finalizar)
  const [carreraFiltro, setCarreraFiltro] = useState('')
  const [estadoFiltro, setEstadoFiltro] = useState('todos')

  useEffect(() => {
    const cargarTodo = async () => {
      try {
        // Antes: 1 request a /sinopticos + N requests (una por sinóptico) a
        // /sinopticos/{id}/eventos en paralelo. Con muchos sinópticos eso son
        // decenas de queries al backend. Ahora: 1 request a /sinopticos y
        // 1 sola request batch a /sinopticos/eventos que trae todo agrupado.
        const [resSinopticos, resEventos] = await Promise.all([
          api.get('/sinopticos'),
          api.get('/sinopticos/eventos'),
        ])
        setSinopticos(resSinopticos.data)
        setEventosPorSinoptico(resEventos.data || {})
      } catch (err) {
        console.error('Error al cargar sinópticos:', err)
      } finally {
        setCargando(false)
      }
    }
    cargarTodo()
  }, [])

  // Carreras disponibles para el selector de filtro (únicas, ordenadas)
  const carrerasDisponibles = Object.values(
    sinopticos.reduce((acc, s) => {
      acc[s.carrera_id] = { id: s.carrera_id, nombre: s.carrera }
      return acc
    }, {})
  ).sort((a, b) => a.nombre.localeCompare(b.nombre))

  // Sinópticos ya filtrados por carrera (para que los contadores de estado
  // reflejen la carrera elegida, si hay alguna elegida)
  const sinopticosPorCarrera = carreraFiltro
    ? sinopticos.filter(s => String(s.carrera_id) === String(carreraFiltro))
    : sinopticos

  const totalFinalizados = sinopticosPorCarrera.filter(s => s.finalizado).length
  const totalPorFinalizar = sinopticosPorCarrera.filter(s => !s.finalizado).length

  // Lista final que se agrupa y se muestra, aplicando además el filtro de estado
  const sinopticosFiltrados = sinopticosPorCarrera.filter(s => {
    if (estadoFiltro === 'finalizados') return s.finalizado
    if (estadoFiltro === 'pendientes') return !s.finalizado
    return true
  })

  // Agrupa los sinópticos (ya filtrados) por nombre de carrera
  const porCarrera = sinopticosFiltrados.reduce((acc, s) => {
    if (!acc[s.carrera]) acc[s.carrera] = []
    acc[s.carrera].push(s)
    return acc
  }, {})

  const celdaOcupada = (eventos, diaKey, horaInicioLabel) => {
    const horaMatch = horaInicioLabel.split(' A ')[0]
    return eventos.find(e => {
      const esDia = Array.isArray(e.daysOfWeek) ? e.daysOfWeek.includes(diaKey) : e.daysOfWeek === diaKey
      const esHora = e.startTime && e.startTime.startsWith(horaMatch)
      return esDia && esHora
    })
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <Navbar />

      <div style={{ padding: '16px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ margin: 0, color: 'var(--duoc-navy)' }}>Sinópticos generados</h2>
          <button
            onClick={() => navigate('/sinoptico')}
            className="duoc-btn-primary"
            style={{ padding: '8px 14px', fontSize: '13px' }}
          >
            + Crear nuevo sinóptico
          </button>
        </div>

        {cargando && <p style={{ color: 'var(--text-muted)' }}>Cargando sinópticos...</p>}

        {!cargando && sinopticos.length === 0 && (
          <p style={{ color: 'var(--text-muted)' }}>Todavía no hay sinópticos generados.</p>
        )}

        {!cargando && sinopticos.length > 0 && (
          <div style={{
            display: 'flex', flexWrap: 'wrap', gap: '14px', alignItems: 'flex-end',
            marginBottom: '20px', padding: '12px 14px', backgroundColor: '#fff',
            border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)',
          }}>
            {/* Filtro por carrera */}
            <div>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: 'var(--duoc-navy)', marginBottom: '4px' }}>
                Carrera
              </label>
              <select
                className="duoc-select"
                value={carreraFiltro}
                onChange={e => setCarreraFiltro(e.target.value)}
                style={{ padding: '6px 10px', fontSize: '12px', minWidth: '220px' }}
              >
                <option value="">Todas las carreras</option>
                {carrerasDisponibles.map(c => (
                  <option key={c.id} value={c.id}>{c.nombre}</option>
                ))}
              </select>
            </div>

            {/* Aparte: estado (finalizados / por finalizar) */}
            <div>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: 'var(--duoc-navy)', marginBottom: '4px' }}>
                Estado
              </label>
              <div style={{ display: 'flex', gap: '6px' }}>
                {[
                  { key: 'todos', label: 'Todos', cuenta: sinopticosPorCarrera.length },
                  { key: 'finalizados', label: '✓ Finalizados', cuenta: totalFinalizados },
                  { key: 'pendientes', label: 'Por finalizar', cuenta: totalPorFinalizar },
                ].map(op => {
                  const activo = estadoFiltro === op.key
                  return (
                    <button
                      key={op.key}
                      onClick={() => setEstadoFiltro(op.key)}
                      style={{
                        padding: '6px 10px', fontSize: '12px', fontWeight: 700,
                        borderRadius: 'var(--radius-sm)', cursor: 'pointer',
                        border: activo ? '1px solid var(--duoc-navy)' : '1px solid #cbd5e1',
                        backgroundColor: activo ? 'var(--duoc-navy)' : '#fff',
                        color: activo ? '#fff' : 'var(--text-muted)',
                      }}
                    >
                      {op.label} ({op.cuenta})
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        )}

        {!cargando && sinopticos.length > 0 && sinopticosFiltrados.length === 0 && (
          <p style={{ color: 'var(--text-muted)' }}>No hay sinópticos que calcen con ese filtro.</p>
        )}

        {Object.entries(porCarrera).map(([carrera, lista]) => (
          <div key={carrera} style={{ marginBottom: '26px' }}>
            <h3 style={{ color: 'var(--duoc-navy)', borderBottom: '2px solid var(--duoc-yellow)', paddingBottom: '4px', fontSize: '15px' }}>
              {carrera}
            </h3>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', marginTop: '10px' }}>
              {lista.map(s => {
                const eventos = eventosPorSinoptico[String(s.id)] || []
                return (
                  <div key={s.id} className="duoc-card" style={{ width: '220px', padding: '10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--duoc-navy)' }}>
                        #{s.id} - {s.semestre}
                      </div>
                      <span style={{
                        fontSize: '9px', fontWeight: 700, padding: '2px 6px', borderRadius: '10px',
                        backgroundColor: s.finalizado ? '#dcfce7' : '#fef9c3',
                        color: s.finalizado ? '#15803d' : '#854d0e',
                        whiteSpace: 'nowrap',
                      }}>
                        {s.finalizado ? '✓ Finalizado' : 'Por finalizar'}
                      </span>
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                      {eventos.length} clase{eventos.length !== 1 ? 's' : ''} asignada{eventos.length !== 1 ? 's' : ''}
                    </div>

                    {/* Mini previsualización: un cuadradito por módulo/día, relleno si está ocupado */}
                    <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '8px' }}>
                      <thead>
                        <tr>
                          <th style={{ width: '14px' }}></th>
                          {DIAS_SEMANA.map(d => (
                            <th key={d.key} style={{ fontSize: '8px', color: 'var(--text-muted)' }}>{d.nombre.slice(0, 1)}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {MODULOS_DUOC.map(m => (
                          <tr key={m.id}>
                            <td style={{ fontSize: '7px', color: 'var(--text-muted)', textAlign: 'right', paddingRight: '2px' }}>{m.id}</td>
                            {DIAS_SEMANA.map(d => {
                              const clase = celdaOcupada(eventos, d.key, m.label)
                              return (
                                <td
                                  key={d.key}
                                  title={clase ? clase.title : ''}
                                  style={{
                                    width: '16px', height: '8px',
                                    backgroundColor: clase ? colorValido(clase.extendedProps?.color) : '#eef1f5',
                                    border: '1px solid #fff',
                                  }}
                                />
                              )
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>

                    <button
                      onClick={() => navigate(`/sinoptico?id=${s.id}`)}
                      className="duoc-btn-primary"
                      style={{ width: '100%', padding: '6px', fontSize: '11px' }}
                    >
                      Ver / Editar
                    </button>
                    <button
                      onClick={() => descargarPdfSinoptico(s.id).catch(() => window.alert('No se pudo generar el PDF.'))}
                      className="duoc-btn-accent"
                      style={{ width: '100%', padding: '6px', fontSize: '11px', marginTop: '6px' }}
                    >
                      Exportar PDF
                    </button>
                    <button
                      onClick={() => descargarExcelSinoptico(s.id).catch(() => window.alert('No se pudo generar el Excel.'))}
                      className="duoc-btn-accent"
                      style={{ width: '100%', padding: '6px', fontSize: '11px', marginTop: '6px' }}
                    >
                      Exportar Excel
                    </button>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}