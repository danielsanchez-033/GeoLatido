import { useCallback, useEffect, useId, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { BotonIcono, Icono, type NombreIcono } from './Iconos'

export interface Diapositiva {
  icono: NombreIcono
  /** Texto corto encima del título: el paso o la categoría. */
  antetitulo?: string
  titulo: string
  texto: string
  /** Lista breve de puntos bajo el texto. */
  puntos?: string[]
  /** Contenido propio debajo (una ilustración o un botón). */
  extra?: ReactNode
}

const PAUSA_MS = 7000

const sinMovimiento = () =>
  typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches

/**
 * Carrusel de vidrio para las ventanas informativas (patrón de carrusel de la WAI-ARIA APG): flechas, puntos,
 * teclado (← →, Inicio, Fin), arrastre con el dedo o el ratón y avance solo cada 7 s, que se detiene al
 * pasar el puntero, al enfocar dentro y con movimiento reducido, y que se puede pausar.
 */
export function Carrusel({ diapositivas, etiqueta }: { diapositivas: Diapositiva[]; etiqueta: string }) {
  const { t } = useTranslation()
  const id = useId()
  const [actual, setActual] = useState(0)
  const [direccion, setDireccion] = useState<1 | -1>(1)
  const [enPausa, setEnPausa] = useState(sinMovimiento)
  const [encima, setEncima] = useState(false)
  const arrastre = useRef<{ x: number; id: number } | null>(null)
  const total = diapositivas.length

  const ir = useCallback(
    (i: number, dir?: 1 | -1) => {
      const siguiente = ((i % total) + total) % total
      setDireccion(dir ?? (siguiente >= actual ? 1 : -1))
      setActual(siguiente)
    },
    [actual, total],
  )

  useEffect(() => {
    if (enPausa || encima || total < 2) return
    const reloj = window.setTimeout(() => ir(actual + 1, 1), PAUSA_MS)
    return () => window.clearTimeout(reloj)
  }, [actual, enPausa, encima, ir, total])

  function teclas(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === 'ArrowRight') ir(actual + 1, 1)
    else if (e.key === 'ArrowLeft') ir(actual - 1, -1)
    else if (e.key === 'Home') ir(0, -1)
    else if (e.key === 'End') ir(total - 1, 1)
    else return
    e.preventDefault()
  }

  function alBajar(e: PointerEvent<HTMLDivElement>) {
    if ((e.target as HTMLElement).closest('button, a, input')) return
    arrastre.current = { x: e.clientX, id: e.pointerId }
  }
  function alSubir(e: PointerEvent<HTMLDivElement>) {
    const a = arrastre.current
    arrastre.current = null
    if (!a || a.id !== e.pointerId) return
    const dx = e.clientX - a.x
    if (Math.abs(dx) > 50) ir(actual + (dx < 0 ? 1 : -1), dx < 0 ? 1 : -1)
  }

  const d = diapositivas[actual]
  return (
    <section
      className="carrusel"
      aria-roledescription={t('portal.carousel')}
      aria-label={etiqueta}
      onPointerEnter={() => setEncima(true)}
      onPointerLeave={() => setEncima(false)}
      onFocus={() => setEncima(true)}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setEncima(false)
      }}
    >
      <div
        className="carrusel-marco"
        tabIndex={0}
        onKeyDown={teclas}
        onPointerDown={alBajar}
        onPointerUp={alSubir}
        onPointerCancel={() => (arrastre.current = null)}
        aria-live={enPausa ? 'polite' : 'off'}
      >
        <article
          key={actual}
          id={`${id}-${actual}`}
          className="carrusel-diapositiva"
          data-direccion={direccion}
          role="group"
          aria-roledescription={t('portal.slide')}
          aria-label={t('portal.slideOf', { n: actual + 1, total })}
        >
          <div className="carrusel-icono" aria-hidden="true">
            <Icono nombre={d.icono} tamano={30} />
          </div>
          <div className="carrusel-texto">
            {d.antetitulo && <p className="carrusel-antetitulo">{d.antetitulo}</p>}
            <h3>{d.titulo}</h3>
            <p>{d.texto}</p>
            {d.puntos && (
              <ul className="carrusel-puntos">
                {d.puntos.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            )}
            {d.extra}
          </div>
        </article>
      </div>
      <div className="carrusel-controles">
        <BotonIcono icono="anterior" etiqueta={t('portal.previous')} onClick={() => ir(actual - 1, -1)} />
        <div className="carrusel-indicadores" role="group" aria-label={t('portal.slides')}>
          {diapositivas.map((x, i) => (
            <button
              key={x.titulo}
              type="button"
              className="carrusel-punto"
              aria-current={i === actual ? 'true' : undefined}
              aria-label={t('portal.goTo', { n: i + 1, title: x.titulo })}
              title={x.titulo}
              onClick={() => ir(i)}
            >
              {/* La barra del punto activo se llena con el tiempo que falta para avanzar. */}
              {i === actual && !enPausa && !encima && <span className="carrusel-progreso" style={{ animationDuration: `${PAUSA_MS}ms` }} />}
            </button>
          ))}
        </div>
        <BotonIcono icono="siguiente" etiqueta={t('portal.next')} onClick={() => ir(actual + 1, 1)} />
        <BotonIcono
          icono={enPausa ? 'reproducir' : 'pausa'}
          etiqueta={t(enPausa ? 'portal.play' : 'portal.pause')}
          aria-pressed={enPausa}
          onClick={() => setEnPausa((p) => !p)}
        />
      </div>
    </section>
  )
}
