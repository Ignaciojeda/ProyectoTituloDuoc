import { useEffect, useMemo, useState } from 'react'
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
  // 'todos' | 'mios' (pestaña "Hechos por mí")
  const [pestana, setPestana] = useState('todos')

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

  const visibles = useMemo(
    () => (pestana === 'mios' ? sinopticos.filter(s => s.es_mio) : sinopticos),
    [sinopticos, pestana]
  )
  const cantidadMios = useMemo(() => sinopticos.filter(s => s.es_mio).length, [sinopticos])

  // Año de la carrera según el nivel: niveles 1-2 = 1er año, 3-4 = 2º año, etc.
  const claveAnio = (nivel) => (nivel ? Math.ceil(nivel / 2) : 0)
  const tituloAnio = (anio) => (anio === 0 ? 'Sin nivel definido (vacíos o varios niveles)' : `${anio}º año`)

  // carrera -> año de la carrera -> sinópticos ordenados por nivel (uno al lado del otro)
  const porCarrera = useMemo(() => {
    const mapa = {}
    visibles.forEach(s => {
      const anio = claveAnio(s.nivel_semestral)
      mapa[s.carrera] = mapa[s.carrera] || {}
      mapa[s.carrera][anio] = mapa[s.carrera][anio] || []
      mapa[s.carrera][anio].push(s)
    })
    Object.values(mapa).forEach(anios =>
      Object.values(anios).forEach(lista =>
        lista.sort((x, y) => (x.nivel_semestral || 99) - (y.nivel_semestral || 99) || x.id - y.id)
      )
    )
    return mapa
  }, [visibles])

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

        <div style={{ display: 'flex', gap: '6px', marginBottom: '16px' }}>
          {[
            { key: 'todos', texto: `Todos (${sinopticos.length})` },
            { key: 'mios', texto: `Hechos por mí (${cantidadMios})` },
          ].map(t => {
            const activa = pestana === t.key
            return (
              <button
                key={t.key}
                onClick={() => setPestana(t.key)}
                style={{
                  padding: '7px 16px', fontSize: '13px', cursor: 'pointer', borderRadius: '6px 6px 0 0',
                  border: '1px solid var(--duoc-navy)', borderBottom: activa ? '3px solid var(--duoc-yellow)' : '1px solid var(--duoc-navy)',
                  background: activa ? 'var(--duoc-navy)' : '#fff', color: activa ? '#fff' : 'var(--duoc-navy)',
                  fontWeight: activa ? 'bold' : 'normal',
                }}
              >
                {t.texto}
              </button>
            )
          })}
        </div>

        {cargando && <p style={{ color: 'var(--text-muted)' }}>Cargando sinópticos...</p>}

        {!cargando && sinopticos.length === 0 && (
          <p style={{ color: 'var(--text-muted)' }}>Todavía no hay sinópticos generados.</p>
        )}

        {!cargando && sinopticos.length > 0 && visibles.length === 0 && (
          <p style={{ color: 'var(--text-muted)' }}>
            Aún no has creado ningún sinóptico. Los que crees o generes desde ahora aparecerán aquí.
          </p>
        )}

        {Object.entries(porCarrera).map(([carrera, anios]) => (
          <div key={carrera} style={{ marginBottom: '30px' }}>
            <h3 style={{ color: 'var(--duoc-navy)', borderBottom: '2px solid var(--duoc-yellow)', paddingBottom: '4px', fontSize: '16px' }}>
              {carrera}
            </h3>

            <div style={{ display: 'flex', flexWrap: 'nowrap', alignItems: 'flex-start', gap: '22px', marginTop: '12px', overflowX: 'auto', paddingBottom: '10px' }}>
            {Object.entries(anios)
              .sort(([x], [y]) => Number(x === '0' ? 99 : x) - Number(y === '0' ? 99 : y))
              .map(([anio, lista], idx) => (
                <div key={anio} style={{ flex: '0 0 auto', paddingLeft: idx > 0 ? '22px' : 0, borderLeft: idx > 0 ? '2px dashed #cbd5e1' : 'none' }}>
                  <div style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    {tituloAnio(Number(anio))} · {lista.length} sinóptico{lista.length !== 1 ? 's' : ''}
                  </div>

                  {/* Un sinóptico al lado del otro, ordenados por nivel; con barra horizontal si no caben */}
                  <div style={{ display: 'flex', flexWrap: 'nowrap', gap: '14px', marginTop: '8px' }}>
                    {lista.map(s => {
                const eventos = eventosPorSinoptico[String(s.id)] || []
                return (
                  <div key={s.id} className="duoc-card" style={{ width: '220px', minWidth: '220px', flexShrink: 0, padding: '10px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--duoc-navy)' }}>
                      #{s.id} · {s.nivel_semestral ? `Nivel ${s.nivel_semestral}°` : 'Sin nivel'} · {s.semestre}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                      {s.jornada ? s.jornada.charAt(0).toUpperCase() + s.jornada.slice(1) : ''} · {eventos.length} clase{eventos.length !== 1 ? 's' : ''}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                      {s.es_mio ? 'Hecho por ti' : s.creado_por ? `Hecho por ${s.creado_por}` : 'Autor sin registrar'}
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
        ))}
      </div>
    </div>
  )
}