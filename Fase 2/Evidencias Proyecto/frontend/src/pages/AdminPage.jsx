import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import '../duoc.css' // Importación directa de estilos institucionales

export default function AdminPage() {
  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <Navbar />
      
      <div style={{ padding: '28px 32px 12px 32px' }}>
        <h2 style={{ margin: '0 0 6px 0', color: 'var(--duoc-navy)', fontSize: '24px', fontWeight: '800' }}>
          Panel de Administración
        </h2>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '15px' }}>
          Acceso completo al sistema. Puede gestionar usuarios, carreras, asignaturas y todos los sinópticos.
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '24px',
        padding: '24px 32px'
      }}>
        <div className="duoc-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
              👥 Gestión de usuarios
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.5', margin: 0 }}>
              Crear, editar y desactivar cuentas de usuario. Asignar roles (administrador, coordinador, docente).
            </p>
          </div>
          <Link to="/admin/usuarios" className="duoc-btn-primary" style={{ textAlign: 'center', textDecoration: 'none', marginTop: '20px', boxSizing: 'border-box' }}>
            Gestionar usuarios
          </Link>
        </div>

        <div className="duoc-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
              🗓️ Sinópticos
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.5', margin: 0 }}>
              Crear, editar y generar automáticamente los sinópticos de cualquier carrera y semestre.
            </p>
          </div>
          <Link to="/sinoptico" className="duoc-btn-primary" style={{ textAlign: 'center', textDecoration: 'none', marginTop: '20px', boxSizing: 'border-box' }}>
            Ir a sinópticos
          </Link>
        </div>

        <div className="duoc-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
              📚 Datos maestros
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.5', margin: 0 }}>
              Carreras, planes de estudio, asignaturas, profesores, salas y bloques horarios.
            </p>
          </div>
          <Link to="/sinoptico" className="duoc-btn-accent" style={{ textAlign: 'center', textDecoration: 'none', marginTop: '20px', boxSizing: 'border-box' }}>
            Abrir módulo
          </Link>
        </div>

        <div className="duoc-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
              📊 Resumen del sistema
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.5', margin: 0 }}>
              Estado general del sistema, conteo de registros y últimos sinópticos generados.
            </p>
          </div>
          <Link to="/sinopticos" className="duoc-btn-accent" style={{ textAlign: 'center', textDecoration: 'none', marginTop: '20px', boxSizing: 'border-box' }}>
            Ver sinópticos
          </Link>
        </div>
      </div>
    </div>
  )
}