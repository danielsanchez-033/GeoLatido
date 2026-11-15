// @vitest-environment node
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { contraste, leerColores, type Tema } from './contraste'

// Prueba de contraste del sistema de diseño (T-FAR-12, RF-INT-01; plan en specs/08-interfaz/plan.md).
const css = readFileSync(new URL('./tokens.css', import.meta.url), 'utf8')
const colores = leerColores(css)

const TEXTO = 4.5 // WCAG 1.4.3, texto normal
const NO_TEXTO = 3 // WCAG 1.4.11: bordes de control, foco e iconos; y 1.4.3 en texto grande

// [primer plano, fondo, mínimo, dónde se usa]
const PARES: [string, string, number, string][] = [
  ['color-texto', 'color-fondo', TEXTO, 'texto general'],
  ['color-texto', 'color-superficie', TEXTO, 'botones y caja de la historia'],
  ['color-texto', 'color-aviso-fondo', TEXTO, 'distintivo de datos sintéticos'],
  ['color-texto-suave', 'color-fondo', TEXTO, 'textos secundarios (.muted)'],
  ['color-texto-suave', 'color-superficie', TEXTO, 'textos secundarios en la historia'],
  ['color-acento', 'color-fondo', TEXTO, 'enlace para saltar al contenido'],
  ['color-acento', 'color-superficie', NO_TEXTO, 'contorno de foco sobre botones'],
  ['color-borde-control', 'color-fondo', NO_TEXTO, 'borde de selectores y campos'],
  ['color-borde-control', 'color-superficie', NO_TEXTO, 'borde de botones'],
  ['color-texto', 'color-superficie', NO_TEXTO, 'borde del botón activo'],
  ['color-cambio', 'color-fondo', NO_TEXTO, 'icono y borde de cambio probable'],
  ['color-sin-cambio', 'color-fondo', NO_TEXTO, 'icono y borde de sin cambio'],
  ['color-no-observable', 'color-fondo', NO_TEXTO, 'borde discontinuo de no observable'],
  ['color-acento', 'color-fondo', NO_TEXTO, 'borde de observable en la consulta de evento'],
  ['color-aviso-borde', 'color-aviso-fondo', NO_TEXTO, 'borde del distintivo de datos sintéticos'],
  ['color-aviso-borde', 'color-fondo', NO_TEXTO, 'borde del aviso de datos sintéticos'],
  // Vidrio (T-FAR-21): peor caso, vidrio sobre la parte más clara de la imagen de satélite.
  ['color-texto', 'color-vidrio-peor', TEXTO, 'texto sobre los paneles de vidrio'],
  ['color-texto-suave', 'color-vidrio-peor', TEXTO, 'textos secundarios sobre vidrio'],
  ['color-borde-control', 'color-vidrio-peor', NO_TEXTO, 'bordes de control y foco sobre vidrio'],
  ['color-texto', 'color-vidrio-activo-peor', TEXTO, 'botón activo sobre vidrio'],
]

// Solo se usa el tema oscuro (T-FAR-21): el claro ya no se aplica ni se comprueba.
const TEMAS: Tema[] = ['oscuro']

describe('variables del sistema de diseño', () => {
  it('lee los colores declarados con light-dark()', () => {
    expect(Object.keys(colores).length).toBeGreaterThanOrEqual(10)
  })

  it('fija el tema oscuro, sin islas claras (T-FAR-21)', () => {
    expect(css).toMatch(/:root\s*\{\s*color-scheme:\s*dark;/)
    expect(css).not.toContain('isla-clara')
  })

  it('cada par declarado usa variables que existen', () => {
    const faltan = PARES.flatMap(([a, b]) => [a, b]).filter((v) => !(v in colores))
    expect(faltan).toEqual([])
  })

  for (const tema of TEMAS) {
    it.each(PARES)(`tema ${tema}: %s sobre %s llega a %d:1 (%s)`, (a, b, minimo) => {
      const razon = contraste(colores[a][tema], colores[b][tema])
      expect(razon, `${a} sobre ${b} en tema ${tema}: ${razon.toFixed(2)}:1`).toBeGreaterThanOrEqual(
        minimo,
      )
    })
  }
})

describe('contraste()', () => {
  it('coincide con los valores de referencia de WCAG', () => {
    expect(contraste('#000000', '#ffffff')).toBeCloseTo(21, 5)
    expect(contraste('#ffffff', '#ffffff')).toBeCloseTo(1, 5)
    // #767676 sobre blanco es el gris más claro que pasa 4,5:1.
    expect(contraste('#767676', '#ffffff')).toBeGreaterThanOrEqual(4.5)
    expect(contraste('#777777', '#ffffff')).toBeLessThan(4.5)
  })

  it('rechaza formatos que no sabe leer', () => {
    expect(() => contraste('red', '#ffffff')).toThrow()
  })
})
