import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'

export default function AdminPage() {
  return (
    <>
      <Navbar />
      <div style={{ padding: '20px' }}>
        <h2 style={{ margin: '0 0 4px' }}>Panel de Administración</h2>
        <p style={{ margin: '0 0 20px', color: '#52606d' }}>
          Acceso completo al sistema. Puede gestionar usuarios, carreras, asignaturas y todos los sinópticos.
        </p>
      </div>

      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h3>👥 Gestión de usuarios</h3>
          <p>Crear, editar y desactivar cuentas de usuario. Asignar roles (administrador, coordinador, docente).</p>
          <Link to="/admin/usuarios" className="btn">Gestionar usuarios</Link>
        </div>

        <div className="dashboard-card">
          <h3>🗓️ Sinópticos</h3>
          <p>Crear, editar y generar automáticamente los sinópticos de cualquier carrera y semestre.</p>
          <Link to="/sinoptico" className="btn">Ir a sinópticos</Link>
        </div>

        <div className="dashboard-card">
          <h3>📚 Datos maestros</h3>
          <p>Carreras, planes de estudio, asignaturas, profesores, salas y bloques horarios.</p>
          <Link to="/sinoptico" className="btn secondary">Abrir módulo</Link>
        </div>

        <div className="dashboard-card">
          <h3>📊 Resumen del sistema</h3>
          <p>Estado general del sistema, conteo de registros y últimos sinópticos generados.</p>
          <Link to="/sinopticos" className="btn secondary">Ver sinópticos</Link>
        </div>
      </div>
    </>
  )
}