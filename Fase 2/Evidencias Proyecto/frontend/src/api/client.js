import axios from 'axios'

// La sesión vive en una cookie HttpOnly que pone el servidor: JavaScript no la ve ni la guarda.
// Aquí solo se guarda, EN MEMORIA (no en localStorage), el token CSRF que exige el servidor en
// las peticiones que modifican datos. Se recupera con /auth/me al recargar la página.
let csrfToken = null
export function setCsrfToken(valor) {
  csrfToken = valor || null
}

// Si VITE_API_URL no está definida se usa el mismo host desde el que se abrió la web (localhost o 127.0.0.1),
// para que web y API sean "same-site" y el navegador envíe la cookie.
const base = (import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`)
  .replace(/\/+$/, '')

const api = axios.create({
  baseURL: base.endsWith('/api') ? base : `${base}/api`,
  withCredentials: true,   // envía la cookie de sesión
})

const METODOS_SEGUROS = ['get', 'head', 'options']

api.interceptors.request.use((config) => {
  if (csrfToken && !METODOS_SEGUROS.includes((config.method || 'get').toLowerCase())) {
    config.headers['X-CSRF-Token'] = csrfToken
  }
  return config
})

// Sesión vencida o revocada: se avisa a la app para que vuelva al login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const url = err.config?.url || ''
    if (err.response?.status === 401 && !url.startsWith('/auth/')) {
      setCsrfToken(null)
      window.dispatchEvent(new Event('sesion-expirada'))
    }
    return Promise.reject(err)
  },
)

export default api
