import { useEffect, useState } from 'react'
import { PALETA_COLORES, HEX_RE, COLOR_DEFAULT } from '../utils/color'

/**
 * Selector de color en hexadecimal (#RRGGBB):
 *  - paleta de colores rápidos,
 *  - selector nativo del navegador,
 *  - campo de texto para escribir el código exacto.
 *
 * Props:
 *  - value:    color actual (hex)
 *  - onChange: se llama con el nuevo hex (siempre válido y en minúsculas)
 */
export default function SelectorColor({ value, onChange }) {
  const actual = HEX_RE.test(value || '') ? value.toLowerCase() : COLOR_DEFAULT
  const [texto, setTexto] = useState(actual)

  // Mantiene el campo de texto al día cuando el color cambia desde la paleta o el selector nativo
  useEffect(() => {
    setTexto(actual)
  }, [actual])

  const handleTexto = (e) => {
    let v = e.target.value.trim()
    if (v && !v.startsWith('#')) v = '#' + v
    setTexto(v)
    if (HEX_RE.test(v)) onChange(v.toLowerCase())
  }

  const textoValido = HEX_RE.test(texto)

  return (
    <div>
      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '8px' }}>
        {PALETA_COLORES.map(c => (
          <button
            key={c}
            type="button"
            title={c}
            onClick={() => onChange(c)}
            style={{
              width: '22px',
              height: '22px',
              borderRadius: '50%',
              backgroundColor: c,
              cursor: 'pointer',
              padding: 0,
              border: actual === c ? '2px solid var(--duoc-navy)' : '1px solid #fff',
              boxShadow: '0 0 0 1px #cbd5e1',
            }}
          />
        ))}
      </div>

      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
        <input
          type="color"
          value={actual}
          onChange={e => onChange(e.target.value.toLowerCase())}
          title="Elegir un color"
          style={{
            width: '40px',
            height: '30px',
            padding: '2px',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            flexShrink: 0,
          }}
        />
        <input
          type="text"
          className="duoc-input"
          value={texto}
          onChange={handleTexto}
          maxLength={7}
          placeholder="#2563eb"
          spellCheck={false}
          style={{
            padding: '6px 8px',
            fontSize: '12px',
            fontFamily: 'monospace',
            flex: 1,
            minWidth: 0,
            borderColor: textoValido ? undefined : '#b02a2a',
          }}
        />
      </div>
      {!textoValido && (
        <div style={{ fontSize: '10px', color: '#b02a2a', marginTop: '3px' }}>
          Formato hexadecimal: #RRGGBB (ej. #2563eb)
        </div>
      )}
    </div>
  )
}
