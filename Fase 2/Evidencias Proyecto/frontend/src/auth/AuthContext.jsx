import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import api, { setCsrfToken } from '../api/client'

const AuthContext = createContext(null)

/**
 * Estado de sesión. La verdad la tiene el servidor: al cargar se consulta /auth/me (con la cookie).
 * Nada de token ni de datos del usuario se guarda en localStorage, así que no hay nada que editar
 * desde la consola del navegador para "hacerse" administrador.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    let activo = true
    api.get('/auth/me')
      .then(({ data }) => {
        if (!activo) return
        setCsrfToken(data.csrf_token)
        setUser(data.user)
      })
      .catch(() => { if (activo) setUser(null) })
      .finally(() => { if (activo) setCargando(false) })

    const alExpirar = () => setUser(null)
    window.addEventListener('sesion-expirada', alExpirar)
    return () => {
      activo = false
      window.removeEventListener('sesion-expirada', alExpirar)
    }
  }, [])

  const login = useCallback(async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password })
    setCsrfToken(data.csrf_token)
    setUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(async () => {
    try { await api.post('/auth/logout') } catch { /* si falla igual se limpia el estado local */ }
    setCsrfToken(null)
    setUser(null)
  }, [])

  const valor = useMemo(() => ({ user, cargando, login, logout }), [user, cargando, login, logout])
  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return ctx
}
