import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/axios'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const { data } = await api.post('/auth/login', { email, password })
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))

      const rol = data.user.rol.toLowerCase()
      if (rol === 'administrador') navigate('/admin')
      else if (rol === 'coordinador') navigate('/coordinador')
      else navigate('/docente')
    } catch (err) {
      setError('Credenciales inválidas')
    }
  }

  return (
    <main className="login-wrapper" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: '#f1f5f9' }}>
      <section className="login-card" style={{ background: '#fff', padding: '32px', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', width: '100%', maxWidth: '360px' }}>
        <header className="login-header" style={{ textAlign: 'center', marginBottom: '24px' }}>
          <h1 style={{ fontSize: '20px', margin: '0 0 8px 0', color: '#0f172a' }}>Sistema de Sinópticos</h1>
          <p className="subtitulo" style={{ margin: 0, color: '#64748b', fontSize: '14px' }}>Iniciar sesión</p>
        </header>

        {error && (
          <div className="alerta alerta-error" role="alert" style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', padding: '10px', borderRadius: '4px', marginBottom: '16px', fontSize: '14px', textAlign: 'center' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="login-form" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label htmlFor="email" style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>Correo electrónico</label>
            <input
              type="email"
              id="email"
              name="email"
              placeholder="usuario@duoc.cl"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', borderRadius: '4px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }}
            />
          </div>

          <div>
            <label htmlFor="password" style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>Contraseña</label>
            <input
              type="password"
              id="password"
              name="password"
              placeholder="••••••••"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', borderRadius: '4px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }}
            />
          </div>

          <button type="submit" style={{ backgroundColor: '#2563eb', color: '#fff', border: 'none', padding: '10px', borderRadius: '4px', fontWeight: '600', cursor: 'pointer', marginTop: '8px' }}>
            Ingresar
          </button>
        </form>

        <footer className="login-footer" style={{ marginTop: '24px', textAlign: 'center', color: '#94a3b8' }}>
          <small>Roles: administrador · coordinador · docente</small>
        </footer>
      </section>
    </main>
  )
}