import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import AdminPage from './pages/AdminPage'
import CoordinadorPage from './pages/CoordinadorPage'
import DocentePage from './pages/DocentePage'
import SinopticoPage from './pages/SinopticoPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/coordinador" element={<CoordinadorPage />} />
        <Route path="/docente" element={<DocentePage />} />
        <Route path="/sinoptico" element={<SinopticoPage />} />
        <Route path="/sinopticos" element={<SinopticoPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App