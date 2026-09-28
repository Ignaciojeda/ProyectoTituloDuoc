import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import api from '../api/axios'
import '../duoc.css'

export default function DocentePage() {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  const [sinopticos, setSinopticos] = useState([])

  useEffect(() => {
    // Permite al docente listar los sinópticos activos para revisar sus módulos
    api.get('/sinopticos')
      .then(res => setSinopticos(res.data))
      .catch(err => console.error('Error al cargar sinópticos:', err))
  }, [])

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <Navbar />

      <div style={{ padding: '28px 32px 12px 32px' }}>
        <h2 style={{ margin: '0 0 6px 0', color: 'var(--duoc-navy)', fontSize: '24px', fontWeight: '800' }}>
          Portal Docente - Carga Académica
        </h2>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '15px' }}>
          Bienvenido/a, <strong>{user.nombre || 'Docente'}</strong>. Consulte los módulos, salas y horarios asignados para el semestre.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px', padding: '24px 32px' }}>
        <div className="duoc-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
              📅 Visualizador de Horarios
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.5', margin: 0 }}>
              Acceda a la grilla horaria para revisar las salas asignadas y bloques de sus asignaturas.
            </p>
          </div>
          <Link to="/sinoptico" className="duoc-btn-primary" style={{ textAlign: 'center', textDecoration: 'none', marginTop: '20px', boxSizing: 'border-box' }}>
            Ver mi horario
          </Link>
        </div>

        <div className="duoc-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 12px 0', color: 'var(--duoc-navy)', fontSize: '18px' }}>
              📋 Sinópticos Vigentes ({sinopticos.length})
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.5', margin: 0 }}>
              Examine los boletines de carga académica por carrera y semestre publicados por la coordinación.
            </p>
          </div>
          <Link to="/sinoptico" className="duoc-btn-accent" style={{ textAlign: 'center', textDecoration: 'none', marginTop: '20px', boxSizing: 'border-box' }}>
            Explorar sinópticos
          </Link>
        </div>
      </div>
    </div>
  )
}