import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import api from "../api/client";
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

export default function SalasGaleria() {
  const navigate = useNavigate()
  const [salas, setSalas] = useState([])
  const [eventosPorSala, setEventosPorSala] = useState({})
  const [cargando, setCargando] = useState(true)
  const [busqueda, setBusqueda] = useState('')

  useEffect(() => {
    const cargarTodo = async () => {
      try {
        // Antes: 1 request a /salas + N requests (una por sala) a
        // /salas/{id}/eventos en paralelo. Con 15-20 salas eso dispara
        // 15-20 queries con varios JOIN cada una. Ahora: 1 request a /salas
        // y 1 sola request batch a /salas/eventos que trae todo agrupado.
        const [resSalas, resEventos] = await Promise.all([
          api.get('/salas'),
          api.get('/salas/eventos'),
        ])
        setSalas(resSalas.data)
        setEventosPorSala(resEventos.data || {})
      } catch (err) {
        console.error('Error al cargar salas:', err)
      } finally {
        setCargando(false)
      }
    }
    cargarTodo()
  }, [])

  // Normaliza para buscar sin importar mayúsculas ni tildes
  const normalizar = (t) =>
    String(t ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()

  // Búsqueda por nombre de sala o por edificio (ej. "W610", "w6", "edificio y")
  const terminos = normalizar(busqueda).split(/\s+/).filter(Boolean)
  const salasFiltradas = terminos.length === 0
    ? salas
    : salas.filter(s => {
        const texto = normalizar(`${s.nombre} edificio ${s.edificio || ''}`)
        return terminos.every(t => texto.includes(t))
      })

  // Agrupa las salas por edificio (W, Y, Z)
  const porEdificio = salasFiltradas.reduce((acc, s) => {
    const clave = s.edificio || 'Sin edificio'
    if (!acc[clave]) acc[clave] = []
    acc[clave].push(s)
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
          <h2 style={{ margin: 0, color: 'var(--duoc-navy)' }}>Salas y su ocupación</h2>

          <div style={{ position: 'relative', width: '320px', maxWidth: '100%' }}>
            <input
              type="text"
              value={busqueda}
              onChange={e => setBusqueda(e.target.value)}
              placeholder="🔍 Buscar sala (ej. W610) o edificio..."
              aria-label="Buscar sala"
              style={{
                width: '100%', boxSizing: 'border-box', padding: '8px 30px 8px 10px', fontSize: '13px',
                border: '1px solid var(--duoc-navy)', borderRadius: 'var(--radius-sm)', outline: 'none',
              }}
            />
            {busqueda && (
              <button
                onClick={() => setBusqueda('')}
                title="Borrar búsqueda"
                style={{
                  position: 'absolute', right: '6px', top: '50%', transform: 'translateY(-50%)',
                  border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '15px', color: 'var(--text-muted)',
                }}
              >
                ×
              </button>
            )}
          </div>
        </div>

        {busqueda && !cargando && (
          <p style={{ margin: '0 0 12px', fontSize: '12px', color: 'var(--text-muted)' }}>
            {salasFiltradas.length} sala{salasFiltradas.length !== 1 ? 's' : ''} encontrada{salasFiltradas.length !== 1 ? 's' : ''} de {salas.length}
          </p>
        )}

        {cargando && <p style={{ color: 'var(--text-muted)' }}>Cargando salas...</p>}

        {!cargando && salas.length === 0 && (
          <p style={{ color: 'var(--text-muted)' }}>Todavía no hay salas registradas.</p>
        )}

        {!cargando && salas.length > 0 && salasFiltradas.length === 0 && (
          <p style={{ color: 'var(--text-muted)' }}>No se encontraron salas que coincidan con "{busqueda}".</p>
        )}

        {Object.entries(porEdificio)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([edificio, lista]) => (
            <div key={edificio} style={{ marginBottom: '26px' }}>
              <h3 style={{ color: 'var(--duoc-navy)', borderBottom: '2px solid var(--duoc-yellow)', paddingBottom: '4px', fontSize: '15px' }}>
                Edificio {edificio}
              </h3>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', marginTop: '10px' }}>
                {lista.map(s => {
                  const eventos = eventosPorSala[String(s.id)] || []
                  return (
                    <div key={s.id} className="duoc-card" style={{ width: '220px', padding: '10px' }}>
                      <div style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--duoc-navy)' }}>
                        {s.nombre}
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                        {s.cantidad_sillas} sillas · {eventos.length} bloque{eventos.length !== 1 ? 's' : ''} ocupado{eventos.length !== 1 ? 's' : ''}
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
                                    title={clase ? `${clase.title} (${clase.extendedProps?.carrera})` : ''}
                                    style={{
                                      width: '16px', height: '8px',
                                      backgroundColor: clase ? '#b45309' : '#eef1f5',
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
                        onClick={() => navigate(`/salas/horario?id=${s.id}`)}
                        className="duoc-btn-primary"
                        style={{ width: '100%', padding: '6px', fontSize: '11px' }}
                      >
                        Ver horario completo
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