import { useEffect, useRef } from 'react'
import type { EventVerdict, Lang } from '../api/client'
import { crearLineaTiempo, type LineaTiempoAtlas, type LineaTiempoApi } from '../mapa/lineaTiempo'

/**
 * Monta la línea de tiempo de Atlas (T-ATL-06) y le pasa las respuestas tal cual:
 * el timeline del catálogo y, si lo hay, el evento consultado.
 */
export function PassTimeline({
  timeline,
  event,
  lang,
}: {
  timeline: LineaTiempoApi | null
  event?: EventVerdict
  lang: Lang
}) {
  const container = useRef<HTMLDivElement>(null)
  const line = useRef<LineaTiempoAtlas>(null)

  useEffect(() => {
    const l = crearLineaTiempo(container.current!, { timeline: null })
    line.current = l
    return () => {
      l.destruir()
      line.current = null
    }
  }, [])

  useEffect(() => {
    line.current?.actualizar({ timeline, evento: event ?? null, idioma: lang })
  }, [timeline, event, lang])

  return <div className="pass-timeline" ref={container} />
}
