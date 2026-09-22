import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import FullCalendar from '@fullcalendar/react'
import timeGridPlugin from '@fullcalendar/timegrid'
import esLocale from '@fullcalendar/core/locales/es'
import api from '../api/axios'

export default function SinopticoPage() {
  const [carreras, setCarreras] = useState([])
  const [semestres, setSemestres] = useState([])
  const [sinopticosExistentes, setSinopticosExistentes] = useState([])
  
  const [carreraSel, setCarreraSel] = useState('')
  const [semestreSel, setSemestreSel] = useState('')
  const [sinopticoSel, setSinopticoSel] = useState('')
  
  const [eventos, setEventos] = useState([])
  const [mensaje, setMensaje] = useState('')

  useEffect(() => {
    // Cargar listas desde FastAPI / Supabase
    api.get('/carreras')
      .then(res => setCarreras(res.data))
      .catch(err => console.error('Error al cargar carreras:', err))

    api.get('/semestres')
      .then(res => setSemestres(res.data))
      .catch(err => console.error('Error al cargar semestres:', err))

    api.get('/sinopticos')
      .then(res => setSinopticosExistentes(res.data))
      .catch(err => console.error('Error al cargar sinópticos:', err))
  }, [])

  const cargarEventosSinoptico = async (id) => {
    try {
      const { data } = await api.get(`/sinopticos/${id}/eventos`)
      setEventos(data)
    } catch (err) {
      console.error('Error al cargar eventos del sinóptico:', err)
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
        semestre_id: parseInt(semestreSel)
      })
      setMensaje(`Sinóptico #${data.sinoptico_id} generado correctamente.`)
      setSinopticoSel(data.sinoptico_id)
      cargarEventosSinoptico(data.sinoptico_id)
    } catch (err) {
      setMensaje(err.response?.data?.detail || 'Error al generar sinóptico.')
    }
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f8fafc', color: '#0f172a' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 20px', background: '#1e293b', color: '#fff' }}>
        <h1 style={{ fontSize: '18px', margin: 0 }}>Boletín de Carga Académica - Horario</h1>
        <Link to="/" style={{ color: '#93c5fd', textDecoration: 'none' }}>Volver al inicio</Link>
      </header>

      <div style={{ display: 'flex', gap: '20px', padding: '20px' }}>
        {/* PANEL IZQUIERDO */}
        <div style={{ width: '300px', background: '#fff', padding: '16px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h2 style={{ fontSize: '16px', marginTop: 0 }}>1. Elegir carrera y semestre</h2>

          <label style={{ display: 'block', margin: '8px 0 4px', fontSize: '14px', fontWeight: '500' }}>Carrera</label>
          <select value={carreraSel} onChange={e => setCarreraSel(e.target.value)} style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}>
            <option value="">-- Seleccionar Carrera --</option>
            {carreras.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </select>

          <label style={{ display: 'block', margin: '12px 0 4px', fontSize: '14px', fontWeight: '500' }}>Semestre</label>
          <select value={semestreSel} onChange={e => setSemestreSel(e.target.value)} style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}>
            <option value="">-- Seleccionar Semestre --</option>
            {semestres.map(s => <option key={s.id} value={s.id}>{s.anio}-{s.numero} Semestre</option>)}
          </select>

          <button onClick={handleGenerarAuto} style={{ marginTop: '16px', width: '100%', padding: '10px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '4px', fontWeight: '600', cursor: 'pointer' }}>
            Generar automáticamente
          </button>

          {mensaje && <p style={{ fontSize: '13px', color: '#2563eb', marginTop: '10px' }}>{mensaje}</p>}

          <div style={{ marginTop: '24px', borderTop: '1px solid #e2e8f0', paddingTop: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', fontWeight: 'bold' }}>Seguir editando existente</label>
            <select value={sinopticoSel} onChange={e => {
              setSinopticoSel(e.target.value)
              if (e.target.value) cargarEventosSinoptico(e.target.value)
            }} style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}>
              <option value="">-- Seleccione Sinóptico --</option>
              {sinopticosExistentes.map(s => (
                <option key={s.id} value={s.id}>#{s.id} - {s.carrera} ({s.semestre})</option>
              ))}
            </select>
          </div>
        </div>

        {/* HORARIO INSTITUCIONAL (DERECHA) */}
        <div style={{ flex: 1, background: '#fff', padding: '16px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <FullCalendar
            plugins={[timeGridPlugin]}
            initialView="timeGridWeek"
            locales={[esLocale]}
            locale="es"
            events={eventos}
            headerToolbar={false}
            allDaySlot={false}
            hiddenDays={[0]} // Ocultar Domingo (Lunes a Sábado)
            slotMinTime="08:30:00"
            slotMaxTime="22:30:00"
            slotDuration="00:40:00"
            slotLabelInterval="00:40:00"
            slotLabelFormat={{
              hour: '2-digit',
              minute: '2-digit',
              hour12: false
            }}
            dayHeaderFormat={{ weekday: 'long' }}
            eventContent={(eventInfo) => (
              <div style={{ padding: '2px 4px', fontSize: '11px', lineHeight: '1.2' }}>
                <strong>{eventInfo.event.title}</strong>
                <div>{eventInfo.event.extendedProps?.codigo}</div>
                <div>{eventInfo.event.extendedProps?.sala}</div>
              </div>
            )}
          />
        </div>
      </div>
    </div>
  )
}