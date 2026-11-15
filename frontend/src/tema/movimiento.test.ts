// @vitest-environment node
import { readFileSync } from 'node:fs'
import { expect, test } from 'vitest'

// RF-INT-09: jsdom no aplica media queries, así que se comprueba que la regla existe.
// El mapa ya lo respeta por su cuenta (sinAnimacion() en src/mapa/mapa.ts).
test('la hoja de estilos quita el movimiento con prefers-reduced-motion', () => {
  const css = readFileSync(new URL('../index.css', import.meta.url), 'utf8')
  const regla = css.match(/@media \(prefers-reduced-motion: reduce\)\s*\{([\s\S]*?)\n\}/)
  expect(regla, 'falta la regla de movimiento reducido').not.toBeNull()
  for (const prop of ['animation-duration', 'transition-duration', 'scroll-behavior: auto']) {
    expect(regla![1]).toContain(prop)
  }
})
