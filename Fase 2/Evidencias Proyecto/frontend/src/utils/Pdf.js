import api from '../api/client'

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

// Descarga el sinóptico en Excel (hoja "Horario" con la grilla y hoja "Detalle" con una fila por bloque).
export async function descargarExcelSinoptico(sinopticoId) {
  const res = await api.get(`/sinopticos/${sinopticoId}/excel`, { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([res.data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  }))
  const a = document.createElement('a')
  a.href = url
  a.download = `sinoptico_${sinopticoId}.xlsx`
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}