import api from '../api/axios'

// Descarga el PDF de un sinóptico (el backend lo genera con el formato del boletín de Duoc UC).
export async function descargarPdfSinoptico(sinopticoId) {
  const res = await api.get(`/sinopticos/${sinopticoId}/pdf`, { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `sinoptico_${sinopticoId}.pdf`
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}