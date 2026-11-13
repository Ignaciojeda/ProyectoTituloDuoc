import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

/**
 * Bloquea el acceso a una ruta si no hay sesión válida o el rol no está en `rolesPermitidos`.
 * Esto es solo comodidad de la UI: la barrera real, la que no se puede saltar, es el backend
 * (require_admin / require_coordinador / require_docente en auth.py).
 * El usuario y su rol vienen del servidor (/auth/me), no de localStorage.
 */
export default function ProtectedRoute({ rolesPermitidos, children }) {
  const { user, cargando } = useAuth()

  if (cargando) return null   // esperando la respuesta de /auth/me

  if (!user) return <Navigate to="/login" replace />

  const rol = (user.rol || '').toString().toLowerCase()

  if (rolesPermitidos && !rolesPermitidos.includes(rol)) {
    // Logeado, pero con un rol que no debería estar aquí: se manda a su propio panel
    const destino =
      rol === 'administrador' ? '/admin' :
      rol === 'coordinador'   ? '/coordinador' :
      rol === 'docente'       ? '/docente' :
      '/login'
    return <Navigate to={destino} replace />
  }

  return children
}
