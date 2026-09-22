import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/axios'
import '../duoc.css'

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
    <main style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <section className="duoc-card" style={{ width: '100%', maxWidth: '380px', padding: '36px', boxShadow: 'var(--shadow-lg)' }}>
        <header style={{ textAlign: 'center', marginBottom: '28px' }}>
          <h1 style={{ fontSize: '22px', color: 'var(--duoc-navy)', margin: '0 0 6px 0', fontWeight: '800' }}>
            Sistema de Sinópticos
          </h1>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '14px' }}>Iniciar sesión</p>
        </header>

        {error && (
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', padding: '10px 14px', borderRadius: 'var(--radius-sm)', marginBottom: '18px', fontSize: '13px', textAlign: 'center', fontWeight: '600' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div className="duoc-form-group">
            <label className="duoc-label">Correo electrónico</label>
            <input
              type="email"
              className="duoc-input"
              placeholder="usuario@duoc.cl"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="duoc-form-group">
            <label className="duoc-label">Contraseña</label>
            <input
              type="password"
              className="duoc-input"
              placeholder="••••••••"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="duoc-btn-primary" style={{ marginTop: '8px' }}>
            Ingresar
          </button>
        </form>

        <footer style={{ marginTop: '28px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
          Roles: administrador · coordinador · docente
        </footer>
      </section>
    </main>
  )
}