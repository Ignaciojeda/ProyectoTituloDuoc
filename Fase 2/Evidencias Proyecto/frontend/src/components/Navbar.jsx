import { useNavigate, useLocation } from 'react-router-dom'

export default function Navbar() {
  const navigate = useNavigate()
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  const handleLogout = () => {
    localStorage.clear()
    navigate('/login')
  }

  const rolLower = user.rol ? (typeof user.rol === 'string' ? user.rol.toLowerCase() : user.rol.value?.toLowerCase()) : ''
  const { pathname } = useLocation()  

  return (
    <header className="duoc-header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {pathname !== '/admin' && pathname !== '/coordinador' && (
        <button
          onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/'))}
          title="Volver"
          style={{
            padding: '10px 10px', fontSize: '12px', fontWeight: 600,
            border: '1px solid #fff', borderRadius: 'var(--radius-sm)',
            background: 'transparent', color: '#fff', cursor: 'pointer',
          }}
        >
          ← Volver
        </button>
        )}
        <h1>
          Sistema de Sinópticos
          <span className="duoc-header-badge">
            {user.rol || 'USUARIO'}
          </span>
        </h1>
      </div>
      <div className="duoc-user-section">
        <span>👤 {user.nombre || 'Administrador'}</span>
        <button onClick={handleLogout} className="duoc-btn-logout">
          Cerrar sesión
        </button>
      </div>
    </header>
  )
}