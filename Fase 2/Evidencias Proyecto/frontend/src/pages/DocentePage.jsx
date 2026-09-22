import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'

export default function DocentePage() {
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  return (
    <>
      <Navbar />
      <div style={{ padding: '20px' }}>
        <h2 style={{ margin: '0 0 4px' }}>Mi horario docente</h2>
        <p style={{ margin: '0 0 20px', color: '#52606d' }}>
          Bienvenido/a, {user.nombre}. Aquí puede consultar su carga académica.
        </p>
      </div>

      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h3>📅 Mi sinóptico</h3>
          <p>Visualice los bloques horarios en los que tiene clases asignadas.</p>
          <Link to="/sinoptico" className="btn">Ver calendario</Link>
        </div>

        <div className="dashboard-card">
          <h3>ℹ️ Información</h3>
          <p>Si necesita ajustes en su horario, contacte al coordinador de su carrera.</p>
        </div>
      </div>
    </>
  )
}