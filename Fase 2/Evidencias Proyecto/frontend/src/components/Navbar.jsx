import { useNavigate } from 'react-router-dom'

export default function Navbar() {
  const navigate = useNavigate()
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  const handleLogout = () => {
    localStorage.clear()
    navigate('/login')
  }

  const rolLower = user.rol ? (typeof user.rol === 'string' ? user.rol.toLowerCase() : user.rol.value?.toLowerCase()) : ''

  return (
    <>
      <style>{`
        .navbar-rol {
          display: inline-block;
          padding: 3px 10px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: bold;
          text-transform: uppercase;
          margin-left: 10px;
        }
        .rol-administrador { background: #fde68a; color: #92400e; }
        .rol-coordinador   { background: #bfdbfe; color: #1e3a8a; }
        .rol-docente       { background: #bbf7d0; color: #14532d; }

        .user-info {
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 14px;
        }
        .user-info .btn-logout {
          color: #fff;
          text-decoration: none;
          border: 1px solid rgba(255, 255, 255, 0.4);
          padding: 6px 12px;
          border-radius: 4px;
          background: transparent;
          cursor: pointer;
        }
        .user-info .btn-logout:hover { background: rgba(255, 255, 255, 0.1); }
      `}</style>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#1e293b', color: '#fff', padding: '12px 24px' }}>
        <h1 style={{ fontSize: '18px', margin: 0, display: 'flex', alignItems: 'center' }}>
          Sistema de Sinópticos
          <span className={`navbar-rol rol-${rolLower}`}>
            {user.rol}
          </span>
        </h1>
        <div className="user-info">
          <span>👤 {user.nombre}</span>
          <button onClick={handleLogout} className="btn-logout">Cerrar sesión</button>
        </div>
      </header>
    </>
  )
}