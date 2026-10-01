import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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

export default function SinopticosGaleria() {
  const navigate = useNavigate()
  const [sinopticos, setSinopticos] = useState([])
  const [eventosPorSinoptico, setEventosPorSinoptico] = useState({})
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    const cargarTodo = async () => {
      try {
        const { data } = await api.get('/sinopticos')
        setSinopticos(data)

        // Trae las clases de cada sinóptico en paralelo, para armar la mini-previsualización
        const resultados = await Promise.all(
          data.map(s =>
            api.get(`/sinopticos/${s.id}/eventos`)
              .then(r => ({ id: s.id, eventos: r.data }))
              .catch(() => ({ id: s.id, eventos: [] }))
          )
        )
        const mapa = {}
        resultados.forEach(r => { mapa[r.id] = r.eventos })
        setEventosPorSinoptico(mapa)
      } catch (err) {
        console.error('Error al cargar sinópticos:', err)
      } finally {
        setCargando(false)
      }
    }
    cargarTodo()
  }, [])

  // Agrupa los sinópticos por nombre de carrera
  const porCarrera = sinopticos.reduce((acc, s) => {
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

        {Object.entries(porCarrera).map(([carrera, lista]) => (
          <div key={carrera} style={{ marginBottom: '26px' }}>
            <h3 style={{ color: 'var(--duoc-navy)', borderBottom: '2px solid var(--duoc-yellow)', paddingBottom: '4px', fontSize: '15px' }}>
              {carrera}
            </h3>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', marginTop: '10px' }}>
              {lista.map(s => {
                const eventos = eventosPorSinoptico[s.id] || []
                return (
                  <div key={s.id} className="duoc-card" style={{ width: '220px', padding: '10px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--duoc-navy)' }}>
                      #{s.id} - {s.semestre}
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
                                    backgroundColor: clase ? 'var(--duoc-blue-accent, #2563eb)' : '#eef1f5',
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
