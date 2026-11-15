import { useEffect, useState } from 'react'

/** Lo que dura la animación de cierre (vidrio.css, `gelatina-cierra`). */
const DURACION_CIERRE = 300

function sinAnimacion(): boolean {
  return typeof window.matchMedia !== 'function' || window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * Cierre animado de un panel (2026-11-15). Al pasar `abierta` a false, el panel sigue a la vista e inerte
 * durante DURACION_CIERRE mientras se encoge, y después recibe `hidden`. Con la transición de CSS no bastaba: al
 * quitar `hidden` se retira a la vez la animación de apertura y el navegador saltaba al estado final sin
 * animar. Con movimiento reducido (o sin matchMedia, como en jsdom) se cierra al momento.
 */
export function useCierreAnimado(abierta: boolean): { oculto: boolean; cerrando: boolean } {
  const [previa, setPrevia] = useState(abierta)
  const [cerrando, setCerrando] = useState(false)
  if (previa !== abierta) {
    setPrevia(abierta)
    setCerrando(!abierta && !sinAnimacion())
  }
  useEffect(() => {
    if (!cerrando) return
    const id = window.setTimeout(() => setCerrando(false), DURACION_CIERRE)
    return () => window.clearTimeout(id)
  }, [cerrando])
  return { oculto: !abierta && !cerrando, cerrando: !abierta && cerrando }
}
