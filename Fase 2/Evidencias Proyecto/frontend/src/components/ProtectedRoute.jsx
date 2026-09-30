import { Navigate } from 'react-router-dom'

/**
 * Bloquea el acceso a una ruta si el rol del usuario logeado no
 * está en `rolesPermitidos`. Esto es la segunda barrera (en la UI);
 * la barrera real, la que no se puede saltar, es el backend
 * (require_admin / require_coordinador / require_docente en
 * auth.py) -- esto solo evita que alguien vea una pantalla que
 * de todas formas no podría usar.
 *
 * Espera que LoginPage haya guardado en localStorage:
 *   localStorage.setItem('token', ...)
 *   localStorage.setItem('user', JSON.stringify(usuario))  // con 'rol'
 */
export default function ProtectedRoute({ rolesPermitidos, children }) {
  const token = localStorage.getItem('token')
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  const rol = (user.rol || '').toString().toLowerCase()

  if (!token) {
    return <Navigate to="/login" replace />
  }

  if (rolesPermitidos && !rolesPermitidos.includes(rol)) {
    // Logeado, pero con un rol que no debería estar aquí.
    // Se manda a su propio panel en vez de a /login.
    const destino =
      rol === 'administrador' ? '/admin' :
      rol === 'coordinador'   ? '/coordinador' :
      rol === 'docente'       ? '/docente' :
      '/login'
    return <Navigate to={destino} replace />
  }

  return children
}
