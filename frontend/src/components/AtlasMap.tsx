import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import type { VerdictMapOptions } from '../api/mapOptions'
import { crearMapa } from '../mapa/mapa'
import type { Bbox, CapaRadar, MapaAtlas, MundoMapa } from '../mapa/tipos'

interface Props {
  options: VerdictMapOptions
  /**
   * Comparador antes/después activo: las escenas ópticas de antes y de después, recortadas a la zona y con
   * un deslizador que funciona también en el globo 3D. Cada lado elige escena óptica, HH, HV o hundimiento (`canCompare`).
   */
  compare: boolean
  /** Hay escena óptica que comparar con el radar. */
  canCompare: boolean
  /** Llega un veredicto nuevo: se tapa el mapa para no leer las capas anteriores como actuales. */
  busy: boolean
  /** Globo 3D (true) o plano (false), desde la barra de herramientas (RF-INT-28). */
  modo3d: boolean
  /** Capa radar visible, elegida en la barra de herramientas. */
  layer: CapaRadar
  /** Opacidad de las capas radar, de 0,2 a 1. */
  opacity: number
  /** Cada vez que cambia, el mapa vuelve a encuadrar la zona. */
  reframe: number
  /** Buscador mundial: huellas, gránulo elegido y su vista previa. */
  mundo?: MundoMapa | null
  /** Caja a la que volar; cada objeto nuevo es un vuelo. */
  volar?: { bbox: Bbox } | null
  /** Lo que se ve del mapa al terminar cada movimiento. */
  onVista?: (bbox: Bbox) => void
  /** Clic (o Intro) en el mapa: el punto elegido, en grados con 5 decimales. */
  onPunto?: (p: { lon: number; lat: number }) => void
  /** Clic dentro de una huella del buscador mundial (2026-11-15). */
  onHuella?: (id: string) => void
  /** Nombre del lugar del punto elegido, para su ventana en el mapa (2026-11-15). */
  rotulo?: { lon: number; lat: number; nombre: string } | null
}

/**
 * Monta el mapa de Atlas (T-FAR-05) a pantalla completa (T-FAR-21). `crearMapa` y `destruir` van en el mismo
 * efecto, así que StrictMode no deja dos mapas; los cambios posteriores pasan por `actualizar()`.
 * Las herramientas (3D, capas, opacidad, encuadre y comparador) viven en la barra inferior de la app, así que
 * el mapa se crea sin su botón 3D ni su selector de capas.
 */
export function AtlasMap({ options, compare, canCompare, busy, modo3d, layer, opacity, reframe, mundo, volar, onVista, onPunto, onHuella, rotulo }: Props) {
  const { t } = useTranslation()
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<MapaAtlas | null>(null)
  const swipe = compare && canCompare

  // Las props con que se crea el mapa (solo se leen al montarlo) y lo último que recibió, para no
  // repetir actualizar(): con capas nuevas, actualizar() las vuelve a cargar.
  const latest = useRef({ options, swipe, modo3d, layer, opacity })
  // La función de vista puede cambiar en cada render de la app: el mapa llama siempre a la última.
  const vistaRef = useRef(onVista)
  const puntoRef = useRef(onPunto)
  useEffect(() => {
    puntoRef.current = onPunto
  }, [onPunto])
  const huellaRef = useRef(onHuella)
  useEffect(() => {
    huellaRef.current = onHuella
  }, [onHuella])
  useEffect(() => {
    vistaRef.current = onVista
  }, [onVista])
  const applied = useRef<typeof latest.current | null>(null)

  useEffect(() => {
    if (!container.current) return
    const { options: o, swipe: s, modo3d: m, layer: l, opacity: op } = latest.current
    const created = crearMapa(container.current, {
      ...o,
      // El comparador radar/óptico de Atlas forzaba el 2D; el de antes/después no.
      compare: 'off',
      antesDespues: s,
      modo3d: m,
      activeLayer: l,
      control3d: false,
      controlCapas: false,
      onViewChanged: (v) => vistaRef.current?.(v.bbox),
      onPointSelected: (p) => puntoRef.current?.(p),
      onFootprintSelected: (id) => huellaRef.current?.(id),
    })
    created.fijarOpacidad(op)
    map.current = created
    applied.current = latest.current
    return () => {
      created.destruir()
      map.current = null
      applied.current = null
    }
  }, [])

  useEffect(() => {
    const a = applied.current
    const m = map.current
    if (!m || !a) return
    const cambios: Parameters<MapaAtlas['actualizar']>[0] = {}
    // Solo lo que cambió: reenviar las capas las volvería a cargar.
    if (a.options !== options) Object.assign(cambios, options)
    if (a.options !== options) cambios.compare = 'off'
    if (a.swipe !== swipe) cambios.antesDespues = swipe
    if (a.modo3d !== modo3d) cambios.modo3d = modo3d
    if (a.layer !== layer || a.options !== options) cambios.activeLayer = layer
    if (Object.keys(cambios).length) m.actualizar(cambios)
    if (a.opacity !== opacity) m.fijarOpacidad(opacity)
    applied.current = { options, swipe, modo3d, layer, opacity }
  }, [options, swipe, modo3d, layer, opacity])

  useEffect(() => {
    map.current?.mostrarMundo(mundo ?? null)
  }, [mundo])

  useEffect(() => {
    if (volar) map.current?.volarA(volar.bbox)
  }, [volar])

  useEffect(() => {
    if (rotulo) map.current?.rotularPunto({ lon: rotulo.lon, lat: rotulo.lat }, rotulo.nombre)
  }, [rotulo])

  const primerEncuadre = useRef(reframe)
  useEffect(() => {
    if (reframe !== primerEncuadre.current) map.current?.encuadrar()
  }, [reframe])

  return (
    <section className="atlas-map" aria-label={t('map.label')}>
      <div className="atlas-map-frame" aria-busy={busy}>
        <div ref={container} className="atlas-map-canvas" />
        {busy && (
          <p className="atlas-map-busy" role="status">
            {t('picker.loading')}
          </p>
        )}
      </div>
    </section>
  )
}
