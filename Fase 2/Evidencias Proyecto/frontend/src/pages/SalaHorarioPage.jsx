import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
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

export default function SalaHorarioPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [salas, setSalas] = useState([])
  const [salaSel, setSalaSel] = useState(searchParams.get('id') || '')
  const [eventos, setEventos] = useState([])
  const [cargando, setCargando] = useState(false)

  useEffect(() => {
    api.get('/salas')
      .then(res => setSalas(res.data))
      .catch(err => console.error('Error salas:', err))
  }, [])

  useEffect(() => {
    if (!salaSel) {
      setEventos([])
      return
    }
    setCargando(true)
    api.get(`/salas/${salaSel}/eventos`)
      .then(res => setEventos(res.data))
      .catch(() => setEventos([]))
      .finally(() => setCargando(false))
  }, [salaSel])

  const cambiarSala = (id) => {
    setSalaSel(id)
    setSearchParams(id ? { id } : {})
  }

  const obtenerClaseParaModulo = (diaKey, moduloLabel) => {
    const horaMatch = moduloLabel.split(' A ')[0]
    return eventos.find(e => {
      const esDia = Array.isArray(e.daysOfWeek) ? e.daysOfWeek.includes(diaKey) : e.daysOfWeek === diaKey
      const esHora = e.startTime && e.startTime.startsWith(horaMatch)
      return esDia && esHora
    })
  }

  const salaActual = salas.find(s => String(s.id) === String(salaSel))

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <Navbar />

      <div style={{ padding: '16px 24px' }}>
        <h2 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)' }}>Horario de sala</h2>

        <div className="duoc-card" style={{ padding: '14px', marginBottom: '16px', maxWidth: '320px' }}>
          <label className="duoc-label" style={{ fontSize: '11px' }}>Sala</label>
          <select
            className="duoc-select"
            style={{ padding: '6px 8px', fontSize: '12px' }}
            value={salaSel}
            onChange={e => cambiarSala(e.target.value)}
          >
            <option value="">-- Seleccionar sala --</option>
            {Object.entries(
              salas.reduce((acc, s) => {
                const clave = s.edificio || 'Sin edificio'
                if (!acc[clave]) acc[clave] = []
                acc[clave].push(s)
                return acc
              }, {})
            ).map(([edificio, lista]) => (
              <optgroup key={edificio} label={`Edificio ${edificio}`}>
                {lista.map(s => (
                  <option key={s.id} value={s.id}>{s.nombre} ({s.cantidad_sillas} sillas)</option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        {!salaSel && (
          <p style={{ color: 'var(--text-muted)' }}>Selecciona una sala para ver su horario.</p>
        )}

        {salaSel && (
          <div className="duoc-card" style={{ padding: '12px', overflowX: 'auto' }}>
            {salaActual && (
              <div style={{ fontSize: '13px', color: 'var(--duoc-navy)', fontWeight: 'bold', marginBottom: '10px' }}>
                {salaActual.nombre} — Edificio {salaActual.edificio} — {salaActual.cantidad_sillas} sillas
              </div>
            )}

            {cargando && <p style={{ color: 'var(--text-muted)' }}>Cargando horario...</p>}

            {!cargando && (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', tableLayout: 'fixed' }}>
                <thead>
                  <tr>
                    <th style={{ border: '1px solid var(--border-color)', padding: '4px', width: '90px' }}>Módulo</th>
                    {DIAS_SEMANA.map(d => (
                      <th key={d.key} style={{ border: '1px solid var(--border-color)', padding: '4px' }}>{d.nombre}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {MODULOS_DUOC.map(m => (
                    <tr key={m.id}>
                      <td style={{ border: '1px solid var(--border-color)', padding: '4px', fontSize: '10px', color: 'var(--text-muted)' }}>
                       ({m.label})
                      </td>
                      {DIAS_SEMANA.map(d => {
                        const clase = obtenerClaseParaModulo(d.key, m.label)
                        return (
                          <td key={d.key} style={{ border: '1px solid var(--border-color)', padding: '3px', verticalAlign: 'top' }}>
                            {clase ? (
                              <div style={{
                                backgroundColor: '#fef3c7',
                                borderLeft: '3px solid #b45309',
                                padding: '2px 4px',
                                borderRadius: '2px',
                                lineHeight: '1.2',
                              }}>
                                <div style={{ fontWeight: 'bold', fontSize: '10px' }}>{clase.title}</div>
                                <div style={{ fontSize: '9px', color: '#555' }}>{clase.extendedProps?.profesor}</div>
                                <div style={{ fontSize: '9px', color: '#555' }}>
                                  {clase.extendedProps?.carrera} ({clase.extendedProps?.semestre})
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
            )}
          </div>
        )}
      </div>
    </div>
  )
}