import { useState } from 'react'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import api from '../api/axios'
import '../duoc.css'

export default function DocentePage() {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  const [archivo, setArchivo] = useState(null)
  const [subiendo, setSubiendo] = useState(false)
  const [mensaje, setMensaje] = useState({ tipo: '', texto: '' })

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
    </div>
  )
}