import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import AdminPage from './pages/AdminPage'
import AdminUsers from './pages/AdminUsers'
import CoordinadorPage from './pages/CoordinadorPage'
import DocentePage from './pages/DocentePage'
import SinopticoPage from './pages/SinopticoPage'
import ProtectedRoute from './components/ProtectedRoute'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route path="/admin" element={
          <ProtectedRoute rolesPermitidos={['administrador']}><AdminPage /></ProtectedRoute>
        } />
        <Route path="/admin/usuarios" element={
          <ProtectedRoute rolesPermitidos={['administrador']}><AdminUsers /></ProtectedRoute>
        } />

        <Route path="/coordinador" element={
          <ProtectedRoute rolesPermitidos={['coordinador']}><CoordinadorPage /></ProtectedRoute>
        } />

        <Route path="/docente" element={
          <ProtectedRoute rolesPermitidos={['docente']}><DocentePage /></ProtectedRoute>
        } />

        {/* Coordinador Y administrador pueden generar/editar sinópticos
            (coincide con require_coordinador en main.py, que deja
            pasar a ambos roles). */}
        <Route path="/sinoptico" element={
          <ProtectedRoute rolesPermitidos={['coordinador', 'administrador']}><SinopticoPage /></ProtectedRoute>
        } />
        <Route path="/sinopticos" element={
          <ProtectedRoute rolesPermitidos={['coordinador', 'administrador']}><SinopticoPage /></ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
