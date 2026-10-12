// Utilidades de color para los bloques del sinóptico.
// Los colores se guardan y se reciben SIEMPRE como hexadecimal #RRGGBB.

export const COLOR_DEFAULT = '#2563eb'

// Paleta rápida (todos con buen contraste con texto blanco u oscuro)
export const PALETA_COLORES = [
  '#2563eb', // azul
  '#16a34a', // verde
  '#d97706', // ámbar
  '#dc2626', // rojo
  '#7c3aed', // violeta
  '#db2777', // rosado
  '#0d9488', // turquesa
  '#475569', // gris azulado
]

export const HEX_RE = /^#[0-9a-fA-F]{6}$/

// Devuelve el color si es un hex válido; si no (null, vacío, mal formado) usa el por defecto.
export const colorValido = (color) =>
  typeof color === 'string' && HEX_RE.test(color) ? color : COLOR_DEFAULT

// Elige texto oscuro o blanco según qué tan claro sea el fondo, para que siempre se lea.
export const colorTextoSobre = (hex) => {
  const h = colorValido(hex).slice(1)
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  const luminancia = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminancia > 0.6 ? '#1f2937' : '#ffffff'
}
