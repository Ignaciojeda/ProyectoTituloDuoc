import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import api from "../api/client";
import '../duoc.css'

export default function DocentePage() {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  const [archivo, setArchivo] = useState(null)
  const [subiendo, setSubiendo] = useState(false)
  const [mensaje, setMensaje] = useState({ tipo: '', texto: '' })

  const [cambios, setCambios] = useState([])

  useEffect(() => {
    api.get('/docente/mis-cambios')
      .then(({ data }) => setCambios(data))
      .catch(() => setCambios([]))
  }, [])

  const subirHorario = async () => {
    if (!archivo) return
    const formData = new FormData()
    formData.append('archivo', archivo)
    setSubiendo(true)
    setMensaje({ tipo: '', texto: '' })
    try {
      const { data } = await api.post('/docente/disponibilidad/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setMensaje({ tipo: 'ok', texto: data.mensaje || 'Horario cargado correctamente.' })
      setArchivo(null)
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.response?.data?.detail || 'No se pudo cargar el archivo.' })
    } finally {
      setSubiendo(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <Navbar />

      <div style={{ padding: '28px 32px 12px 32px' }}>
        <h2 style={{ margin: '0 0 6px 0', color: 'var(--duoc-navy)', fontSize: '24px', fontWeight: '800' }}>
          Portal Docente - Carga Académica
        </h2>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '15px' }}>
          Bienvenido/a, <strong>{user.nombre || 'Docente'}</strong>. Consulte sus clases asignadas y envíe su disponibilidad horaria.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px', padding: '24px 32px' }}>
        <div className="duoc-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
              📅 Visualizador de Horarios
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.5', margin: 0 }}>
              Revise su horario personal: asignaturas, días, horas y salas donde dicta clases.
            </p>
          </div>
          <Link to="/docente/horario" className="duoc-btn-primary" style={{ textAlign: 'center', textDecoration: 'none', marginTop: '20px', boxSizing: 'border-box' }}>
            Ver mi horario
          </Link>
        </div>

        <div className="duoc-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
              📤 Subir mi horario
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.5', margin: '0 0 12px 0' }}>
              Cargue su archivo Excel con los días y horas en que tiene disponibilidad. Reemplaza el archivo que envió anteriormente.
            </p>
            <input
              type="file"
              accept=".xlsx,.xls"
              onChange={e => { setArchivo(e.target.files?.[0] || null); setMensaje({ tipo: '', texto: '' }) }}
              style={{ fontSize: '13px', width: '100%' }}
            />
            {mensaje.texto && (
              <p style={{ margin: '10px 0 0', fontSize: '13px', color: mensaje.tipo === 'ok' ? '#15803d' : '#b91c1c' }}>
                {mensaje.texto}
              </p>
            )}
          </div>
          <button
            onClick={subirHorario}
            disabled={!archivo || subiendo}
            className="duoc-btn-accent"
            style={{ marginTop: '20px', boxSizing: 'border-box', opacity: !archivo || subiendo ? 0.6 : 1 }}
          >
            {subiendo ? 'Subiendo...' : 'Subir horario'}
          </button>
        </div>
      </div>

      <div style={{ padding: '0 32px 32px 32px' }}>
        <div className="duoc-card">
          <h3 style={{ margin: '0 0 6px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
            🕘 Cambios en mi horario y disponibilidad
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', margin: '0 0 8px 0' }}>
            Registro de los cambios que coordinación ha hecho sobre su disponibilidad o sus clases, con el motivo y cómo se acordaron.
          </p>
          {cambios.length === 0 && (
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0 }}>Aún no hay cambios registrados.</p>
          )}
          {cambios.map(c => (
            <div key={c.id} style={{ borderTop: '1px solid #eef1f5', padding: '10px 0', fontSize: '13px' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                {c.fecha ? new Date(c.fecha + (c.fecha.endsWith('Z') ? '' : 'Z')).toLocaleString('es-CL') : ''} · {c.usuario}
              </div>
              <div style={{ fontWeight: 'bold' }}>{c.detalle}</div>
              {c.medio_texto && <div>📌 Acordado por: <strong>{c.medio_texto}</strong></div>}
              {c.motivo && <div>Motivo: {c.motivo}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}