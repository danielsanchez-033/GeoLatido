import { useEffect, useState } from 'react'
import { API_BASE } from './client'
import type { components } from './verdicts'

export type DatosHundimiento = components['schemas']['Subsidence']

/**
 * Pide el hundimiento de la zona (`/aois/{aoi}/subsidence`, NISAR GUNW). 404 es normal: la zona aún no tiene
 * cálculo, y entonces devuelve null. La respuesta se guarda con la zona y el idioma que la pidieron, así que al
 * cambiar de zona no se enseña la de la anterior.
 */
export function useHundimiento(aoi: string | undefined, lang: string): DatosHundimiento | null {
  const idioma = lang === 'en' ? 'en' : 'es'
  const [guardado, setGuardado] = useState<{ clave: string; datos: DatosHundimiento | null } | null>(null)
  const clave = `${aoi}|${idioma}`
  useEffect(() => {
    if (!aoi) return
    const ctrl = new AbortController()
    fetch(`${API_BASE}/api/verdicts/aois/${encodeURIComponent(aoi)}/subsidence?lang=${idioma}`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((datos) => setGuardado({ clave: `${aoi}|${idioma}`, datos }))
      .catch(() => {})
    return () => ctrl.abort()
  }, [aoi, idioma])
  return aoi && guardado?.clave === clave ? guardado.datos : null
}
