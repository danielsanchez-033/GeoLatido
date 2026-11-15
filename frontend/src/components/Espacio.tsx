import { useEffect, useRef } from 'react'
import { puntoSubsolar } from '../mapa/sol'

/** Generador pseudoaleatorio con semilla: el cielo sale igual en cada carga y en cada redimensión. */
function aleatorio(semilla: number) {
  let s = semilla >>> 0
  return () => {
    s = (s + 0x6d2b79f5) >>> 0
    let t = s
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const TINTES = ['255,255,255', '200,220,255', '255,236,210', '180,200,255', '255,215,190']
const RAD = Math.PI / 180

/** Lo que publica el mapa con el evento `sar:camara` (src/mapa/mapa.ts). */
interface Camara {
  globo: boolean
  x: number
  y: number
  radio: number
  lng: number
  lat: number
  bearing: number
  pitch: number
  zoom: number
}

/**
 * Dirección del Sol vista desde la cámara: la misma cuenta que hace MapLibre para iluminar su atmósfera
 * (src/webgl/draw/draw_sky.ts), así el Sol del fondo cae del lado iluminado del globo. Marco de la vista:
 * x a la derecha, y hacia arriba y z hacia quien mira.
 */
function solEnVista(c: Pick<Camara, 'lng' | 'lat' | 'bearing' | 'pitch'>, fecha: Date): [number, number, number] {
  const s = puntoSubsolar(fecha)
  let x = Math.sin(s.lon * RAD) * Math.cos(s.lat * RAD)
  let y = Math.sin(s.lat * RAD)
  let z = Math.cos(s.lon * RAD) * Math.cos(s.lat * RAD)
  // rotateY(−lng)
  let a = -c.lng * RAD
  ;[x, z] = [x * Math.cos(a) + z * Math.sin(a), -x * Math.sin(a) + z * Math.cos(a)]
  // rotateX(lat)
  a = c.lat * RAD
  ;[y, z] = [y * Math.cos(a) - z * Math.sin(a), y * Math.sin(a) + z * Math.cos(a)]
  // rotateZ(bearing)
  a = c.bearing * RAD
  ;[x, y] = [x * Math.cos(a) - y * Math.sin(a), x * Math.sin(a) + y * Math.cos(a)]
  // rotateX(−pitch)
  a = -c.pitch * RAD
  ;[y, z] = [y * Math.cos(a) - z * Math.sin(a), y * Math.sin(a) + z * Math.cos(a)]
  return [x, y, z]
}

/** Punto de luz con halo, ya dibujado: se pega muchas veces sin recalcular el degradado. */
function sprite(tam: number, tinte: string): HTMLCanvasElement {
  const c = document.createElement('canvas')
  c.width = c.height = tam
  const ctx = c.getContext('2d')!
  const g = ctx.createRadialGradient(tam / 2, tam / 2, 0, tam / 2, tam / 2, tam / 2)
  g.addColorStop(0, `rgba(${tinte},1)`)
  g.addColorStop(0.08, `rgba(${tinte},0.9)`)
  g.addColorStop(0.22, `rgba(${tinte},0.28)`)
  g.addColorStop(0.5, `rgba(${tinte},0.06)`)
  g.addColorStop(1, `rgba(${tinte},0)`)
  ctx.fillStyle = g
  ctx.fillRect(0, 0, tam, tam)
  return c
}

interface Brillante {
  x: number
  y: number
  tam: number
  tinte: number
  fase: number
  velocidad: number
}

/**
 * Fondo espacial animado detrás del globo (correcciones de diseño del 2026-11-14):
 * - el cielo (vacío, Vía Láctea, nebulosas y estrellas) deriva despacio y se desplaza un poco con la cámara
 *   del mapa (paralaje), y las estrellas brillantes titilan;
 * - bloom: todo lo que brilla se dibuja también en un lienzo a un cuarto de resolución que se amplía encima
 *   en modo aditivo, que equivale a un desenfoque barato;
 * - el Sol, en la dirección real del punto subsolar (src/mapa/sol.ts) vista desde la cámara: cae del lado
 *   iluminado del globo y el globo lo tapa cuando queda detrás;
 * - un halo atmosférico alrededor de la Tierra, más intenso del lado del Sol.
 * Con movimiento reducido se dibuja un solo cuadro. Decorativo: oculto al lector de pantalla.
 */
export function Espacio() {
  const lienzo = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = lienzo.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const reducido = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches

    let w = 0
    let h = 0
    let dpr = 1
    // Cielo fijo, más grande que la pantalla para poder derivar sin que se vean los bordes.
    const cielo = document.createElement('canvas')
    const bloom = document.createElement('canvas')
    const bctx = bloom.getContext('2d')!
    let brillantes: Brillante[] = []
    const sprites = TINTES.map((t) => sprite(64, t))
    const spriteSol = sprite(256, '255,244,220')
    const MARGEN = 0.08

    let camara: Camara | null = null
    let paralajeX = 0
    let paralajeY = 0

    function prepararCielo() {
      // Memoria: el cielo es difuso, 1,25 píxeles por píxel CSS bastan.
      dpr = Math.min(window.devicePixelRatio || 1, 1.25)
      // Con la ventana a 0 × 0 (pestaña oculta o panel recogido) la nebulosa dividía entre Math.hypot(0, 0) y
      // createRadialGradient recibía NaN, lo que tumbaba toda la app (2026-11-15): como mínimo, 1 píxel.
      w = Math.max(1, window.innerWidth)
      h = Math.max(1, window.innerHeight)
      canvas!.width = Math.round(w * dpr)
      canvas!.height = Math.round(h * dpr)
      bloom.width = Math.max(1, Math.round(w / 4))
      bloom.height = Math.max(1, Math.round(h / 4))
      const cw = w * (1 + MARGEN * 2)
      const ch = h * (1 + MARGEN * 2)
      cielo.width = Math.round(cw * dpr)
      cielo.height = Math.round(ch * dpr)
      const c = cielo.getContext('2d')!
      c.setTransform(dpr, 0, 0, dpr, 0, 0)

      const vacio = c.createRadialGradient(cw * 0.5, ch * 0.55, 0, cw * 0.5, ch * 0.55, Math.max(cw, ch) * 0.8)
      vacio.addColorStop(0, '#0a0f1c')
      vacio.addColorStop(0.6, '#05070d')
      vacio.addColorStop(1, '#020305')
      c.fillStyle = vacio
      c.fillRect(0, 0, cw, ch)

      const r = aleatorio(20261114)
      const x0 = -cw * 0.1
      const y0 = ch * 0.95
      const dx = cw * 1.2
      const dy = -ch * 0.9
      const largo = Math.hypot(dx, dy)
      const nx = -dy / largo
      const ny = dx / largo
      c.globalCompositeOperation = 'lighter'
      for (let i = 0; i < 16; i++) {
        const t = r()
        const off = (r() - 0.5) * ch * 0.18
        const cx = x0 + dx * t + nx * off
        const cy = y0 + dy * t + ny * off
        const rad = (0.08 + r() * 0.18) * Math.max(cw, ch)
        const g = c.createRadialGradient(cx, cy, 0, cx, cy, rad)
        const tinte = r() < 0.5 ? '110,135,210' : '175,125,195'
        g.addColorStop(0, `rgba(${tinte},0.08)`)
        g.addColorStop(1, `rgba(${tinte},0)`)
        c.fillStyle = g
        c.fillRect(cx - rad, cy - rad, rad * 2, rad * 2)
      }
      for (let i = 0; i < 2600; i++) {
        const t = r()
        const off = (r() + r() + r() - 1.5) * ch * 0.16
        c.fillStyle = `rgba(255,255,255,${0.08 + r() * 0.25})`
        c.fillRect(x0 + dx * t + nx * off, y0 + dy * t + ny * off, 0.8, 0.8)
      }
      c.globalCompositeOperation = 'source-over'
      const total = Math.round((cw * ch) / 1400)
      for (let i = 0; i < total; i++) {
        const tam = r() ** 3 * 1.2 + 0.3
        c.fillStyle = `rgba(${TINTES[Math.floor(r() * TINTES.length)]},${0.25 + r() * 0.6})`
        c.beginPath()
        c.arc(r() * cw, r() * ch, tam, 0, Math.PI * 2)
        c.fill()
      }
      brillantes = Array.from({ length: Math.round(total / 28) }, () => ({
        x: r() * cw,
        y: r() * ch,
        tam: 10 + r() * 22,
        tinte: Math.floor(r() * TINTES.length),
        fase: r() * Math.PI * 2,
        velocidad: 0.4 + r() * 1.2,
      }))
    }

    // El halo de la atmósfera y el Sol, en coordenadas de pantalla. `escala` multiplica el tamaño (1 en el
    // lienzo final, 1/4 en el del bloom).
    function dibujarLuz(c: CanvasRenderingContext2D, escala: number, ahora: Date) {
      if (!camara || !camara.globo) return
      const visible = Math.max(0, Math.min(1, (8 - camara.zoom) / 3))
      if (visible <= 0) return
      const [sx, sy, sz] = solEnVista(camara, ahora)
      const cx = camara.x * escala
      const cy = camara.y * escala
      const R = camara.radio * escala
      // Sin WebGL (o antes de que el mapa tenga tamaño) la cámara puede llegar con NaN: createRadialGradient lanza
      // con valores no finitos y, como corre dentro de un efecto, tumbaba toda la app (2026-11-15).
      if (![cx, cy, R, sx, sy, sz].every(Number.isFinite) || R <= 0) return

      // Halo atmosférico: un anillo azul alrededor del borde del globo, desplazado hacia el Sol.
      const lado = Math.hypot(sx, sy) || 1
      const hx = cx + (sx / lado) * R * 0.06
      const hy = cy - (sy / lado) * R * 0.06
      const halo = c.createRadialGradient(hx, hy, R * 0.96, hx, hy, R * 1.28)
      const fuerza = 0.25 + 0.35 * Math.max(0, -sz + 0.3)
      halo.addColorStop(0, `rgba(120,175,255,${0.55 * fuerza * visible})`)
      halo.addColorStop(0.25, `rgba(90,140,255,${0.25 * fuerza * visible})`)
      halo.addColorStop(1, 'rgba(60,100,220,0)')
      c.fillStyle = halo
      c.beginPath()
      c.arc(hx, hy, R * 1.28, 0, Math.PI * 2)
      c.fill()

      // El Sol: lejos, en la dirección del punto subsolar. Se ve cuando queda al lado o detrás del globo
      // (z < 0.3) y se apaga cuando queda detrás de quien mira.
      const delante = Math.max(0, Math.min(1, (0.3 - sz) / 0.5))
      if (delante <= 0) return
      const dist = R * (1.15 + 1.6 * Math.max(0, 1 - Math.abs(sz)))
      const px = cx + (sx / lado) * dist
      const py = cy - (sy / lado) * dist
      const t = performance.now() / 1000
      const pulso = 1 + 0.03 * Math.sin(t * 0.8)
      const tam = Math.max(160 * escala, R * 0.9) * pulso
      c.globalAlpha = delante * visible
      c.drawImage(spriteSol, px - tam / 2, py - tam / 2, tam, tam)
      // Núcleo y corona.
      const corona = c.createRadialGradient(px, py, 0, px, py, tam * 1.6)
      corona.addColorStop(0, 'rgba(255,250,235,0.9)')
      corona.addColorStop(0.05, 'rgba(255,236,200,0.5)')
      corona.addColorStop(0.25, 'rgba(255,200,140,0.08)')
      corona.addColorStop(1, 'rgba(255,180,120,0)')
      c.fillStyle = corona
      c.fillRect(px - tam * 1.6, py - tam * 1.6, tam * 3.2, tam * 3.2)
      // Rayos de destello, que giran muy despacio.
      c.save()
      c.translate(px, py)
      c.rotate(t * 0.02)
      for (let i = 0; i < 6; i++) {
        c.rotate(Math.PI / 3)
        const rayo = c.createLinearGradient(0, 0, tam * 1.4, 0)
        rayo.addColorStop(0, 'rgba(255,245,225,0.35)')
        rayo.addColorStop(1, 'rgba(255,245,225,0)')
        c.fillStyle = rayo
        c.fillRect(0, -1.2 * escala, tam * 1.4, 2.4 * escala)
      }
      c.restore()
      c.globalAlpha = 1
    }

    function cuadro(ms: number) {
      const t = ms / 1000
      const ahora = new Date()
      // Deriva lenta (una vuelta de Lissajous cada pocos minutos) más el paralaje de la cámara, suavizado.
      const objetivoX = camara ? -((camara.lng + camara.bearing) / 360) * w * 0.12 : 0
      const objetivoY = camara ? (camara.lat / 180) * h * 0.12 : 0
      paralajeX += (objetivoX - paralajeX) * 0.05
      paralajeY += (objetivoY - paralajeY) * 0.05
      const deriva = reducido ? 0 : 1
      const ox = -w * MARGEN + Math.sin(t * 0.021) * w * 0.05 * deriva + paralajeX
      const oy = -h * MARGEN + Math.cos(t * 0.017) * h * 0.05 * deriva + paralajeY
      const ox2 = Math.max(-w * MARGEN * 2, Math.min(0, ox))
      const oy2 = Math.max(-h * MARGEN * 2, Math.min(0, oy))

      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx!.globalCompositeOperation = 'source-over'
      ctx!.drawImage(cielo, ox2, oy2, cielo.width / dpr, cielo.height / dpr)

      // Estrellas brillantes que titilan, en el lienzo final y en el del bloom.
      bctx.setTransform(1, 0, 0, 1, 0, 0)
      bctx.clearRect(0, 0, bloom.width, bloom.height)
      ctx!.globalCompositeOperation = 'lighter'
      bctx.globalCompositeOperation = 'lighter'
      for (const b of brillantes) {
        const brillo = reducido ? 0.8 : 0.55 + 0.45 * Math.sin(t * b.velocidad + b.fase)
        const x = b.x + ox2
        const y = b.y + oy2
        if (x < -40 || y < -40 || x > w + 40 || y > h + 40) continue
        ctx!.globalAlpha = brillo
        ctx!.drawImage(sprites[b.tinte], x - b.tam / 2, y - b.tam / 2, b.tam, b.tam)
        bctx.globalAlpha = brillo * 0.8
        bctx.drawImage(sprites[b.tinte], x / 4 - b.tam / 4, y / 4 - b.tam / 4, b.tam / 2, b.tam / 2)
      }
      ctx!.globalAlpha = 1
      bctx.globalAlpha = 1

      dibujarLuz(ctx!, 1, ahora)
      dibujarLuz(bctx, 0.25, ahora)

      // Bloom: el lienzo de cuarto de resolución, ampliado (y por eso desenfocado) en modo aditivo.
      ctx!.globalAlpha = 0.85
      ctx!.imageSmoothingEnabled = true
      ctx!.drawImage(bloom, 0, 0, w, h)
      ctx!.globalAlpha = 1
      ctx!.globalCompositeOperation = 'source-over'
    }

    let pedido = 0
    let ultimo = 0
    function bucle(ms: number) {
      pedido = requestAnimationFrame(bucle)
      // Unos 20 cuadros por segundo bastan para un movimiento tan lento, y nada con la pestaña oculta.
      if (ms - ultimo < 50 || document.hidden) return
      ultimo = ms
      cuadro(ms)
    }

    prepararCielo()
    cuadro(performance.now())
    if (!reducido) pedido = requestAnimationFrame(bucle)

    const alCamara = (e: Event) => {
      camara = (e as CustomEvent<Camara>).detail
      if (reducido) cuadro(performance.now())
    }
    let espera = 0
    const alRedimensionar = () => {
      window.clearTimeout(espera)
      espera = window.setTimeout(() => {
        prepararCielo()
        cuadro(performance.now())
      }, 150)
    }
    window.addEventListener('sar:camara', alCamara)
    window.addEventListener('resize', alRedimensionar)
    return () => {
      cancelAnimationFrame(pedido)
      window.clearTimeout(espera)
      window.removeEventListener('sar:camara', alCamara)
      window.removeEventListener('resize', alRedimensionar)
    }
  }, [])

  return (
    <div className="espacio" aria-hidden="true">
      <canvas ref={lienzo} />
    </div>
  )
}
