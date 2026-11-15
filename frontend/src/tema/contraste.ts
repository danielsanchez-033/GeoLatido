// Contraste WCAG 2.1 y lectura de las variables de tokens.css (T-FAR-12, RF-INT-01).

export type Tema = 'claro' | 'oscuro'

export type Colores = Record<string, Record<Tema, string>>

/** Luminancia relativa de un color #rrggbb (WCAG 2.1, definición 1.4.3). */
export function luminancia(hex: string): number {
  const m = /^#([0-9a-f]{6})$/i.exec(hex)
  if (!m) throw new Error(`Color no admitido: ${hex}`)
  const canal = (i: number) => {
    const c = parseInt(m[1].slice(i, i + 2), 16) / 255
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * canal(0) + 0.7152 * canal(2) + 0.0722 * canal(4)
}

/** Razón de contraste entre dos colores, de 1 a 21. */
export function contraste(a: string, b: string): number {
  const [l1, l2] = [luminancia(a), luminancia(b)].sort((x, y) => y - x)
  return (l1 + 0.05) / (l2 + 0.05)
}

/**
 * Lee las variables de color declaradas como light-dark(#claro, #oscuro).
 * Las que usan otro formato (rgba, sombras) no se devuelven: no entran en pares de contraste.
 */
export function leerColores(css: string): Colores {
  const colores: Colores = {}
  const re = /--([\w-]+):\s*light-dark\(\s*(#[0-9a-fA-F]{6})\s*,\s*(#[0-9a-fA-F]{6})\s*\)/g
  for (const [, nombre, claro, oscuro] of css.matchAll(re)) {
    colores[nombre] = { claro, oscuro }
  }
  return colores
}
