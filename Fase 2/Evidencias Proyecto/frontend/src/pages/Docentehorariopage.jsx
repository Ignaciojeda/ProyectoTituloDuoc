import { useEffect, useState } from 'react'
import Navbar from '../components/Navbar'
import api from "../api/client";
import { colorValido } from '../utils/color'
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

export default function DocenteHorarioPage() {
  const [profesor, setProfesor] = useState('')
  const [eventos, setEventos] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/docente/mi-horario')
      .then(res => {
        setProfesor(res.data.profesor)
        setEventos(res.data.eventos || [])
      })
      .catch(err => setError(err.response?.data?.detail || 'No se pudo cargar tu horario.'))
      .finally(() => setCargando(false))
  }, [])

  const claseEn = (diaKey, label) => {
    const hora = label.split(' A ')[0]
    return eventos.find(e => e.daysOfWeek.includes(diaKey) && e.startTime.startsWith(hora))
  }

  const asignaturas = [...new Map(eventos.map(e => [e.title, e])).values()]

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <Navbar />
      <div style={{ padding: '16px 24px' }}>
        <h2 style={{ margin: '0 0 4px', color: 'var(--duoc-navy)' }}>Mi horario</h2>
        {profesor && (
          <p style={{ margin: '0 0 16px', color: 'var(--text-muted)', fontSize: '14px' }}>
            {profesor} · {eventos.length} módulo{eventos.length !== 1 ? 's' : ''} asignado{eventos.length !== 1 ? 's' : ''}
          </p>
        )}

        {cargando && <p style={{ color: 'var(--text-muted)' }}>Cargando...</p>}
        {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

        {!cargando && !error && eventos.length === 0 && (
          <p style={{ color: 'var(--text-muted)' }}>Todavía no tienes clases asignadas en ningún sinóptico.</p>
        )}

        {!cargando && !error && eventos.length > 0 && (
          <div className="duoc-card" style={{ padding: '12px', overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '760px' }}>
              <thead>
                <tr>
                  <th style={{ width: '110px' }}></th>
                  {DIAS_SEMANA.map(d => (
                    <th key={d.key} style={{ fontSize: '13px', padding: '6px', color: 'var(--duoc-navy)' }}>{d.nombre}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {MODULOS_DUOC.map(m => (
                  <tr key={m.id}>
                    <td style={{ fontSize: '11px', color: 'var(--text-muted)', padding: '2px 8px', whiteSpace: 'nowrap' }}>
                      {m.id}. {m.label.replace(' A ', ' - ')}
                    </td>
                    {DIAS_SEMANA.map(d => {
                      const c = claseEn(d.key, m.label)
                      return (
                        <td key={d.key} style={{ border: '1px solid #fff', backgroundColor: c ? colorValido(c.extendedProps?.color) : '#f3f5f8', height: '44px', padding: '3px 5px', verticalAlign: 'top' }}>
                          {c && (
                            <div style={{ fontSize: '11px', lineHeight: 1.25, color: '#111' }}>
                              <strong>{c.title}</strong>
                              <div>Sala: {c.extendedProps?.sala}</div>
                              {c.extendedProps?.seccion && <div>Sección {c.extendedProps.seccion}</div>}
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
        )}

        {asignaturas.length > 0 && (
          <div style={{ marginTop: '14px', display: 'flex', flexWrap: 'wrap', gap: '10px', fontSize: '12px' }}>
            {asignaturas.map(a => (
              <span key={a.title}>
                <span style={{ display: 'inline-block', width: '12px', height: '12px', background: colorValido(a.extendedProps?.color), marginRight: '5px', verticalAlign: 'middle' }} />
                {a.title}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}