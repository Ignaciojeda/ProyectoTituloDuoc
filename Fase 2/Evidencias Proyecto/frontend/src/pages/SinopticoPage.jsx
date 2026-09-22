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
  
  const [carreraSel, setCarreraSel] = useState('')
  const [semestreSel, setSemestreSel] = useState('')
  const [sinopticoSel, setSinopticoSel] = useState('')
  
  const [eventos, setEventos] = useState([])
  const [mensaje, setMensaje] = useState('')

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
        semestre_id: parseInt(semestreSel)
      })
      setMensaje(`Sinóptico #${data.sinoptico_id} generado correctamente.`)
      setSinopticoSel(data.sinoptico_id)
      cargarEventosSinoptico(data.sinoptico_id)
    } catch (err) {
      setMensaje(err.response?.data?.detail || 'Error al generar sinóptico.')
    }
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

  const handleDrop = (e, nuevoDiaKey, nuevoModuloLabel) => {
    e.preventDefault()
    const claseId = e.dataTransfer.getData('claseId')
    const horaMatch = nuevoModuloLabel.split(' A ')[0]

    setEventos(prev => prev.map(item => {
      if (item.id === parseInt(claseId)) {
        return {
          ...item,
          daysOfWeek: [nuevoDiaKey],
          startTime: `${horaMatch}:00`
        }
      }
      return item
    }))
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
                              lineHeight: '1.1'
                            }}
                          >
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
    </div>
  )
}