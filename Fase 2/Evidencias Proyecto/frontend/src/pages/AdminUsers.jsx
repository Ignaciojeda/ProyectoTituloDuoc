import { useEffect, useState } from 'react'
import api from '../api/axios'
import Navbar from '../components/Navbar'
import '../duoc.css'

const ROLES = [
  { value: 'administrador', label: 'Administrador', color: '#b45309', bg: '#fef3c7' },
  { value: 'coordinador',   label: 'Coordinador',   color: '#1e40af', bg: '#dbeafe' },
  { value: 'docente',       label: 'Docente',       color: '#065f46', bg: '#d1fae5' },
]

const ESTADO = {
  true:  { label: 'Activo',   color: '#065f46', bg: '#d1fae5' },
  false: { label: 'Inactivo', color: '#991b1b', bg: '#fee2e2' },
}

export default function AdminUsers() {
  const [users, setUsers]                 = useState([])
  const [loading, setLoading]             = useState(true)
  const [error, setError]                 = useState(null)
  const [currentUserId, setCurrentUserId] = useState(null)

  // Estado para la subida de disponibilidad docente
  const [uploadingDisp, setUploadingDisp] = useState(false)
  const [dispMsg, setDispMsg]             = useState(null) // { type: 'success' | 'error', text }

  // Modal crear
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm]           = useState({ nombre: '', email: '', password: '', rol: 'docente' })
  const [formErrors, setFormErrors] = useState({})
  const [creating, setCreating]   = useState(false)
  const [createMsg, setCreateMsg] = useState(null)

  // Modal confirmar eliminar
  const [delTarget, setDelTarget] = useState(null)

  useEffect(() => {
    const stored = localStorage.getItem('user')
    if (stored) {
      try { setCurrentUserId(JSON.parse(stored).id) } catch {}
    }
    fetchUsers()
  }, [])

  // ── Traer usuarios ─────────────────────────────────────────────────────────
  const fetchUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.get('/admin/usuarios')
      setUsers(res.data)
    } catch (err) {
      setError('No se pudieron cargar los usuarios. Verifique su conexión.')
    } finally {
      setLoading(false)
    }
  }

  // ── Subir disponibilidad docente (Excel) ──────────────────────────────────
  const handleUploadDisponibilidad = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    const formData = new FormData()
    formData.append('archivo', file)

    setUploadingDisp(true)
    setDispMsg(null)

    try {
      const res = await api.post('/profesores/disponibilidad/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setDispMsg({
        type: 'success',
        text: `✅ ${res.data.mensaje || 'Disponibilidad cargada correctamente.'} (${res.data.registros_procesados || 0} registros procesados)`,
      })
    } catch (err) {
      setDispMsg({
        type: 'error',
        text: `❌ ${err.response?.data?.detail || 'Error al procesar la planilla de disponibilidad.'}`,
      })
    } finally {
      setUploadingDisp(false)
      event.target.value = '' // Limpiar selección del input file
    }
  }

  // ── Validación del formulario ───────────────────────────────────────────────
  const validate = () => {
    const e = {}
    if (!form.nombre.trim())  e.nombre   = 'Requerido'
    if (!form.email.trim())   e.email    = 'Requerido'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
                                e.email   = 'Formato inválido'
    if (!form.password)       e.password = 'Requerida (mín. 6 caracteres)'
    else if (form.password.length < 6)
                                e.password = 'Mínimo 6 caracteres'
    setFormErrors(e)
    return Object.keys(e).length === 0
  }

  // ── Crear usuario ───────────────────────────────────────────────────────────
  const handleCreate = async (e) => {
    e.preventDefault()
    if (!validate()) return
    setCreating(true)
    setCreateMsg(null)
    try {
      await api.post('/admin/usuarios', {
        nombre:   form.nombre.trim(),
        email:    form.email.trim().toLowerCase(),
        password: form.password,
        rol:      form.rol,
      })
      setShowCreate(false)
      setForm({ nombre: '', email: '', password: '', rol: 'docente' })
      setFormErrors({})
      fetchUsers()
    } catch (err) {
      setCreateMsg({
        type: 'error',
        text: err.response?.data?.detail || 'Error al crear el usuario',
      })
    } finally {
      setCreating(false)
    }
  }

  // ── Eliminar usuario ────────────────────────────────────────────────────────
  const handleDelete = async () => {
    if (!delTarget) return
    try {
      await api.delete(`/admin/usuarios/${delTarget.id}`)
      setDelTarget(null)
      fetchUsers()
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al eliminar'
      if (msg.includes('sí mismo')) {
        alert('⚠️ No puede eliminarse a sí mismo.')
      } else {
        alert(`❌ ${msg}`)
      }
      setDelTarget(null)
    }
  }

  const rolInfo = (v) => {
    const val = typeof v === 'object' && v !== null ? v.value : String(v)
    const normalized = val ? val.toLowerCase() : 'docente'
    return ROLES.find(r => r.value === normalized) || ROLES[2]
  }

  const estInfo = (v) => ESTADO[String(v)] || ESTADO['false']

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main, #f4f5f7)' }}>
      <Navbar />

      <div style={{ padding: '28px 32px 12px' }}>
        <h2 style={{ margin: '0 0 4px', color: 'var(--duoc-navy)', fontSize: '24px', fontWeight: '800' }}>
          Gestión de Usuarios y Disponibilidad Docente
        </h2>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '14px' }}>
          Cree, visualice y gestione cuentas de usuario, y cargue las planillas de disponibilidad horaria para docentes.
        </p>
      </div>

      {/* ── Sección: Cargar Disponibilidad y Crear Usuario ────────────────── */}
      <div style={{ padding: '8px 32px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        
        {/* Botón Cargar Disponibilidad Excel */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <label
            className="duoc-btn-accent"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              cursor: uploadingDisp ? 'not-allowed' : 'pointer',
              opacity: uploadingDisp ? 0.7 : 1,
              margin: 0,
            }}
          >
            {uploadingDisp ? '⏳ Procesando Excel...' : '📊 Cargar Disponibilidad Docente (.xlsx)'}
            <input
              type="file"
              accept=".xlsx, .xls"
              onChange={handleUploadDisponibilidad}
              disabled={uploadingDisp}
              style={{ display: 'none' }}
            />
          </label>

          {dispMsg && (
            <span style={{
              fontSize: 13,
              fontWeight: 600,
              color: dispMsg.type === 'error' ? '#b91c1c' : '#065f46',
              background: dispMsg.type === 'error' ? '#fee2e2' : '#d1fae5',
              padding: '4px 10px',
              borderRadius: 6,
            }}>
              {dispMsg.text}
            </span>
          )}
        </div>

        {/* Botón Crear Usuario */}
        <button
          className="duoc-btn-primary"
          onClick={() => { setShowCreate(true); setFormErrors({}); setCreateMsg(null) }}
        >
          ➕ Crear Usuario
        </button>
      </div>

      {/* ── Tabla de Usuarios ─────────────────────────────────────────────── */}
      <div style={{ padding: '0 32px 32px' }}>
        <div className="duoc-card" style={{ padding: 0, overflowX: 'auto' }}>

          {loading && (
            <div style={{ padding: '48px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <div className="spinner-border text-primary" role="status" />
              <p style={{ marginTop: 12 }}>Cargando usuarios…</p>
            </div>
          )}

          {error && !loading && (
            <div style={{ padding: 24, color: '#b91c1c', background: '#fee2e2', borderRadius: 8 }}>
              ⚠️ {error}
            </div>
          )}

          {!loading && !error && users.length === 0 && (
            <div style={{ padding: '48px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <p style={{ fontSize: 32 }}>👤</p>
              <p>No hay usuarios registrados.</p>
            </div>
          )}

          {!loading && users.length > 0 && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ background: '#f8f9fa', color: 'var(--duoc-navy)' }}>
                  {['Nombre', 'Email', 'Rol', 'Estado', 'Acciones'].map(h => (
                    <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 700, fontSize: 12, textTransform: 'uppercase', letterSpacing: '.5px' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map(u => {
                  const r = rolInfo(u.rol)
                  const e = estInfo(u.activo)
                  const isSelf = u.id === currentUserId
                  return (
                    <tr key={u.id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                      <td style={{ padding: '12px 16px', fontWeight: 500 }}>{u.nombre}</td>
                      <td style={{ padding: '12px 16px', color: '#6b7280' }}>{u.email}</td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '3px 10px',
                          borderRadius: 12,
                          fontSize: 12,
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          background: r.bg,
                          color: r.color,
                        }}>
                          {r.label}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          display: 'inline-flex', alignItems: 'center', gap: 4,
                          padding: '2px 8px', borderRadius: 4, fontSize: 12,
                          fontWeight: 500,
                          background: e.bg, color: e.color,
                        }}>
                          {u.activo ? '●' : '○'} {e.label}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <button
                          className="duoc-btn-danger"
                          style={{ padding: '5px 12px', fontSize: 13, opacity: isSelf ? 0.4 : 1, cursor: isSelf ? 'not-allowed' : 'pointer' }}
                          disabled={isSelf}
                          title={isSelf ? 'No puede eliminarse a sí mismo' : 'Eliminar usuario'}
                          onClick={() => !isSelf && setDelTarget({ id: u.id, nombre: u.nombre })}
                        >
                          🗑️ Eliminar
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ── Modal: Crear Usuario ─────────────────────────────────────────── */}
      {showCreate && (
        <Modal onClose={() => setShowCreate(false)} title="Crear Nuevo Usuario">
          <form onSubmit={handleCreate} noValidate>
            <FormField label="Nombre completo" error={formErrors.nombre}>
              <input
                type="text" className={`form-control ${formErrors.nombre ? 'is-invalid' : ''}`}
                value={form.nombre}
                onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))}
                placeholder="Ej: Juan Pérez López"
              />
            </FormField>

            <FormField label="Correo electrónico" error={formErrors.email}>
              <input
                type="email" className={`form-control ${formErrors.email ? 'is-invalid' : ''}`}
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                placeholder="ejemplo@duoc.cl"
              />
            </FormField>

            <FormField label="Contraseña" error={formErrors.password}>
              <input
                type="password" className={`form-control ${formErrors.password ? 'is-invalid' : ''}`}
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                placeholder="Mínimo 6 caracteres"
              />
            </FormField>

            <FormField label="Rol">
              <select
                className="form-control"
                value={form.rol}
                onChange={e => setForm(f => ({ ...f, rol: e.target.value }))}
              >
                {ROLES.map(r => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </FormField>

            {createMsg && (
              <div style={{
                padding: '10px 14px', borderRadius: 6, marginBottom: 16,
                background: createMsg.type === 'error' ? '#fee2e2' : '#d1fae5',
                color: createMsg.type === 'error' ? '#b91c1c' : '#065f46',
                fontSize: 14,
              }}>
                {createMsg.text}
              </div>
            )}

            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button type="button" className="duoc-btn-accent" onClick={() => setShowCreate(false)}>
                Cancelar
              </button>
              <button type="submit" className="duoc-btn-primary" disabled={creating}>
                {creating ? 'Creando…' : '✅ Crear Usuario'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* ── Modal: Confirmar Eliminar ─────────────────────────────────────── */}
      {delTarget && (
        <Modal onClose={() => setDelTarget(null)} title="Confirmar Eliminación">
          <p style={{ margin: '0 0 16px', fontSize: 15 }}>
            ¿Está seguro que desea eliminar al usuario{' '}
            <strong>{delTarget.nombre}</strong>?<br />
            <small style={{ color: 'var(--text-muted)' }}>Esta acción no se puede deshacer.</small>
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
            <button className="duoc-btn-accent" onClick={() => setDelTarget(null)}>
              Cancelar
            </button>
            <button className="duoc-btn-danger" onClick={handleDelete}>
              🗑️ Eliminar
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}

// ── Sub-componentes reutilizables ─────────────────────────────────────────────

function Modal({ children, onClose, title }) {
  return (
    <div
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,0.55)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 1050,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#fff', borderRadius: 12,
          width: '100%', maxWidth: 460,
          maxHeight: '90vh', overflowY: 'auto',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{
          background: 'var(--duoc-navy)', color: '#fff',
          padding: '16px 20px', borderRadius: '12px 12px 0 0',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <h5 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>{title}</h5>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#fff', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}
          >✕</button>
        </div>
        <div style={{ padding: 20 }}>
          {children}
        </div>
      </div>
    </div>
  )
}

function FormField({ label, error, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: 14, color: 'var(--duoc-navy)' }}>
        {label}
        {error && (
          <span style={{ color: '#dc2626', fontWeight: 400, fontSize: 12, marginLeft: 6 }}>
            — {error}
          </span>
        )}
      </label>
      {children}
    </div>
  )
}