import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { Bbox } from '../mapa/tipos'
import { Esqueleto } from './Esqueleto'
import { BASE_RESEARCH, VisorHistoria, type Historia } from './VisorHistoria'

export type ZonaHistoria = { id: string; name: string; bbox: Bbox }

// Historias ya generadas en esta visita, por zona: volver a una zona no repite la investigación.
const generadas = new Map<string, string>()
const DIA = 86_400_000
const iso = (t: number) => new Date(t).toISOString().slice(0, 10)

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) } })
  if (!r.ok) throw new Error(String(r.status))
  return (await r.json()) as T
}

/**
 * Historia de la zona activa (2026-11-15). Sustituye a la historia fija de Parral: para la zona buscada (o la zona con
 * veredictos en pantalla) pide a `research` una investigación del último año con todas sus fuentes (veredictos,
 * catálogo de NASA y acontecimientos citados de USGS, GDACS, Copernicus EMS, IBTrACS, EONET y el registro
 * verificado) y la muestra con reproducción. Nada se escribe aquí: cada frase sale de la API con su evidencia.
 */
export function HistoriaZona({
  zona,
  onVolar,
  onVerPar,
}: {
  zona: ZonaHistoria
  onVolar: (bbox: Bbox) => void
  onVerPar: (series: string, pairId: string) => void
}) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language === 'en' ? 'en' : 'es'
  const clave = `${zona.id}|${zona.bbox.map((v) => v.toFixed(3)).join(',')}`
  const [estado, setEstado] = useState<{ clave: string; tipo: 'cargando' | 'error' | 'lista'; paso?: string | null; historia?: Historia }>({
    clave,
    tipo: 'cargando',
  })

  useEffect(() => {
    let vigente = true
    let temporizador: number | undefined
    const mostrar = async (sid: string) => {
      const h = await json<Historia>(`${BASE_RESEARCH}/stories/${sid}`)
      if (vigente) setEstado({ clave, tipo: 'lista', historia: h })
    }
    const seguir = async (rid: string) => {
      const s = await json<{ job: { state: string; step: string | null } | null; story_ids: string[] }>(`${BASE_RESEARCH}/research/${rid}/status`)
      if (!vigente) return
      if (s.job?.state === 'done' && s.story_ids[0]) {
        generadas.set(clave, s.story_ids[0])
        await mostrar(s.story_ids[0])
      } else if (s.job && (s.job.state === 'failed' || s.job.state === 'cancelled')) {
        setEstado({ clave, tipo: 'error' })
      } else {
        setEstado({ clave, tipo: 'cargando', paso: s.job?.step ?? null })
        temporizador = window.setTimeout(() => void seguir(rid).catch(() => vigente && setEstado({ clave, tipo: 'error' })), 2000)
      }
    }
    const empezar = async () => {
      const ya = generadas.get(clave)
      if (ya) return mostrar(ya)
      const hasta = iso(Date.now())
      const doc = await json<{ id: string }>(`${BASE_RESEARCH}/research`, {
        method: 'POST',
        body: JSON.stringify({
          question: t('zoneStory.question', { name: zona.name }),
          areas: [{ id: zona.id, name: zona.name, bbox: zona.bbox }],
          period: { start: iso(Date.now() - 365 * DIA), end: hasta },
          lang,
          run: true,
        }),
      })
      await seguir(doc.id)
    }
    empezar().catch(() => vigente && setEstado({ clave, tipo: 'error' }))
    return () => {
      vigente = false
      window.clearTimeout(temporizador)
    }
    // Se genera una vez por zona; el idioma de la pregunta no cambia la investigación.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clave])

  const actual = estado.clave === clave ? estado : { tipo: 'cargando' as const, paso: null, historia: undefined }
  return (
    <section className="historia-zona" aria-busy={actual.tipo === 'cargando'}>
      {actual.tipo === 'cargando' && (
        <>
          <h2>{t('zoneStory.heading', { name: zona.name })}</h2>
          <p className="muted">{t('zoneStory.intro')}</p>
          <Esqueleto etiqueta={t(`research.step.${actual.paso ?? 'queued'}`)} variante="tarjeta" filas={5} />
        </>
      )}
      {actual.tipo === 'error' && (
        <>
          <h2>{t('zoneStory.heading', { name: zona.name })}</h2>
          <p role="alert">{t('research.error')}</p>
        </>
      )}
      {actual.tipo === 'lista' && actual.historia && (
        <VisorHistoria key={actual.historia.id} historia={actual.historia} onVolar={onVolar} onVerPar={onVerPar} nivel={2} />
      )}
    </section>
  )
}
