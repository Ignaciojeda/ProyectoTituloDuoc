import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import '../duoc.css'

export default function CoordinadorPage() {
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <Navbar />

      <div style={{ padding: '28px 32px 12px 32px' }}>
        <h2 style={{ margin: '0 0 6px 0', color: 'var(--duoc-navy)', fontSize: '24px', fontWeight: '800' }}>
          Panel de Coordinación Académica
        </h2>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '15px' }}>
          Bienvenido/a, <strong>{user.nombre || 'Coordinador'}</strong>. Planifique y organice los horarios de asignaturas y la disponibilidad docente.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px', padding: '24px 32px' }}>
        <div className="duoc-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
              🗓️ Generador y Editor de Sinópticos
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.5', margin: 0 }}>
              Ejecute el algoritmo de asignación automática de bloques o arrastre los módulos para resolver solapamientos.
            </p>
          </div>
          <Link to="/sinopticos/galeria" className="duoc-btn-accent" style={{ textAlign: 'center', textDecoration: 'none', marginTop: '20px', boxSizing: 'border-box' }}>
            Ver sinópticos
          </Link>
          <Link to="/sinoptico" className="duoc-btn-primary" style={{ textAlign: 'center', textDecoration: 'none', marginTop: '8px', boxSizing: 'border-box' }}>
            Crear un sinóptico nuevo
          </Link>
        </div>

        <div className="duoc-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
              👨‍🏫 Asignación Docente y Infraestructura
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.5', margin: 0 }}>
              Verifique la disponibilidad de profesores por área técnica y la capacidad de las salas por edificio.
            </p>
          </div>
          <Link to="/salas/galeria" className="duoc-btn-accent" style={{ textAlign: 'center', textDecoration: 'none', marginTop: '20px', boxSizing: 'border-box' }}>
            Ver horarios de salas
          </Link>
        </div>
      </div>
    </div>
  )
}