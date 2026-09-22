import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'

export default function CoordinadorPage() {
  return (
    <>
      <Navbar />
      <div style={{ padding: '20px' }}>
        <h2 style={{ margin: '0 0 4px' }}>Panel de Coordinación</h2>
        <p style={{ margin: '0 0 20px', color: '#52606d' }}>
          Gestione la planificación académica: sinópticos, asignaturas y profesores.
        </p>
      </div>

      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h3>🗓️ Sinópticos</h3>
          <p>Crear nuevos sinópticos, generar automáticamente o editar manualmente los bloques.</p>
          <Link to="/sinoptico" className="btn">Ir a sinópticos</Link>
        </div>

        <div className="dashboard-card">
          <h3>📚 Asignaturas y profesores</h3>
          <p>Mantener actualizada la oferta de asignaturas y el cuerpo docente por área.</p>
          <Link to="/sinoptico" className="btn secondary">Abrir módulo</Link>
        </div>

        <div className="dashboard-card">
          <h3>📅 Semestres activos</h3>
          <p>Consulte y gestione los semestres académicos en curso.</p>
          <Link to="/sinopticos" className="btn secondary">Ver sinópticos generados</Link>
        </div>
      </div>
    </>
  )
}