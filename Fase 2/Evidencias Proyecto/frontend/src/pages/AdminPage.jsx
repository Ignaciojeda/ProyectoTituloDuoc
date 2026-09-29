import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import api from '../api/axios'
import '../duoc.css'

export default function AdminPage() {
  const [stats, setStats] = useState({ usuarios: 0, carreras: 0, profesores: 0, sinopticos: 0 })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Carga paralela de métricas generales para el panel
    Promise.all([
      api.get('/admin/usuarios').catch(() => ({ data: [] })),
      api.get('/carreras').catch(() => ({ data: [] })),
      api.get('/profesores').catch(() => ({ data: [] })),
      api.get('/sinopticos').catch(() => ({ data: [] }))
    ]).then(([u, c, p, s]) => {
      setStats({
        usuarios: Array.isArray(u.data) ? u.data.length : 0,
        carreras: Array.isArray(c.data) ? c.data.length : 0,
        profesores: Array.isArray(p.data) ? p.data.length : 0,
        sinopticos: Array.isArray(s.data) ? s.data.length : 0
      })
      setLoading(false)
    })
  }, [])

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <Navbar />

      <div style={{ padding: '28px 32px 12px 32px' }}>
        <h2 style={{ margin: '0 0 6px 0', color: 'var(--duoc-navy)', fontSize: '24px', fontWeight: '800' }}>
          Panel de Administración
        </h2>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '15px' }}>
          Control global del sistema: gestión de cuentas, configuración institucional y supervisión de sinópticos.
        </p>
      </div>

      {/* Indicadores Clave (KPIs) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', padding: '12px 32px' }}>
        <div className="duoc-card" style={{ padding: '16px', textAlign: 'center' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 'bold' }}>USUARIOS</span>
          <h3 style={{ margin: '4px 0 0 0', color: 'var(--duoc-navy)', fontSize: '22px' }}>
            {loading ? '...' : stats.usuarios}
          </h3>
        </div>
        <div className="duoc-card" style={{ padding: '16px', textAlign: 'center' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 'bold' }}>CARRERAS</span>
          <h3 style={{ margin: '4px 0 0 0', color: 'var(--duoc-navy)', fontSize: '22px' }}>
            {loading ? '...' : stats.carreras}
          </h3>
        </div>
        <div className="duoc-card" style={{ padding: '16px', textAlign: 'center' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 'bold' }}>DOCENTES</span>
          <h3 style={{ margin: '4px 0 0 0', color: 'var(--duoc-navy)', fontSize: '22px' }}>
            {loading ? '...' : stats.profesores}
          </h3>
        </div>
        <div className="duoc-card" style={{ padding: '16px', textAlign: 'center' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 'bold' }}>SINÓPTICOS</span>
          <h3 style={{ margin: '4px 0 0 0', color: 'var(--duoc-navy)', fontSize: '22px' }}>
            {loading ? '...' : stats.sinopticos}
          </h3>
        </div>
      </div>

      {/* Tarjetas de Acción */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px', padding: '16px 32px 32px 32px' }}>
        <div className="duoc-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
              👥 Gestión de usuarios
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.5', margin: 0 }}>
              Administración de cuentas, habilitación de usuarios y asignación de roles (Administrador, Coordinador, Docente).
            </p>
          </div>
          <Link to="/admin/usuarios" className="duoc-btn-primary" style={{ textAlign: 'center', textDecoration: 'none', marginTop: '20px', boxSizing: 'border-box' }}>
            Gestionar usuarios
          </Link>
        </div>

        <div className="duoc-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
              🗓️ Planificación de Sinópticos
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.5', margin: 0 }}>
              Generación automática mediante algoritmos de asignación, resolución manual de choques horarios y eliminación.
            </p>
          </div>
          <Link to="/sinoptico" className="duoc-btn-primary" style={{ textAlign: 'center', textDecoration: 'none', marginTop: '20px', boxSizing: 'border-box' }}>
            Editor de sinópticos
          </Link>
        </div>

        <div className="duoc-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
              📚 Módulos y Oferta Académica
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.5', margin: 0 }}>
              Revisar catálogo de asignaturas, infraestructura de salas por edificio y asignaciones de bloques por jornada.
            </p>
          </div>
          <Link to="/sinoptico" className="duoc-btn-accent" style={{ textAlign: 'center', textDecoration: 'none', marginTop: '20px', boxSizing: 'border-box' }}>
            Ver datos maestros
          </Link>
        </div>
      </div>
    </div>
  )
}