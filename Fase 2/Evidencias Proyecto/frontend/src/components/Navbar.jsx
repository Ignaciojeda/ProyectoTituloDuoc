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
    <header className="duoc-header">
      <h1>
        Sistema de Sinópticos
        <span className="duoc-header-badge">
          {user.rol || 'USUARIO'}
        </span>
      </h1>
      <div className="duoc-user-section">
        <span>👤 {user.nombre || 'Administrador'}</span>
        <button onClick={handleLogout} className="duoc-btn-logout">
          Cerrar sesión
        </button>
      </div>
    </header>
  )
}