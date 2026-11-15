import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { API_BASE } from '../api/client'
import type { Bbox } from '../mapa/tipos'
import type { ResumenProcesado } from './ProcesadoZona'
import { Icono } from './Iconos'

const BASE = `${API_BASE}/api/online`
type Estado = { fase: 'listo' } | { fase: 'enviando' } | { fase: 'procesando'; paso: string } | { fase: 'error'; texto: string }

/**
 * «Regenerar veredictos», al final de Hallazgos (2026-11-15). Vuelve a procesar la zona en línea con sus fechas
 * más recientes (`POST /api/online/zones/{id}/regenerate`), enseña el avance y, al terminar, recarga los veredictos.
 * Las zonas de configuración (Parral) se procesan fuera de línea con sus series completas: el botón no se ofrece y
 * se dice por qué.
 */
export function Regenerar({
  aoi,
  onListo,
}: {
  aoi: string
  onListo: (aoi: string, bbox: Bbox, resumen: ResumenProcesado | null) => void
}) {
  const { t } = useTranslation()
  const [estado, setEstado] = useState<Estado>({ fase: 'listo' })
  const temporizador = useRef<number | undefined>(undefined)
  const enLinea = aoi.startsWith('z-')

  useEffect(() => () => window.clearTimeout(temporizador.current), [])

  async function seguir() {
    const r = await fetch(`${BASE}/zones/${encodeURIComponent(aoi)}`)
    if (!r.ok) throw new Error(String(r.status))
    const j = await r.json()
    if (j.state === 'done') {
      setEstado({ fase: 'listo' })
      onListo(aoi, j.bbox as Bbox, j.summary ?? null)
    } else if (j.state === 'queued' || j.state === 'running') {
      setEstado({ fase: 'procesando', paso: t(`regenerate.step.${j.step ?? 'queued'}`) })
      temporizador.current = window.setTimeout(() => void seguir().catch(() => setEstado({ fase: 'error', texto: t('regenerate.error') })), 4000)
    } else {
      setEstado({ fase: 'error', texto: j.error || t('regenerate.error') })
    }
  }

  async function regenerar() {
    setEstado({ fase: 'enviando' })
    try {
      const r = await fetch(`${BASE}/zones/${encodeURIComponent(aoi)}/regenerate`, { method: 'POST' })
      if (r.status === 503) return setEstado({ fase: 'error', texto: t('regenerate.noToken') })
      if (!r.ok) return setEstado({ fase: 'error', texto: t('regenerate.error') })
      setEstado({ fase: 'procesando', paso: t('regenerate.step.queued') })
      await seguir()
    } catch {
      setEstado({ fase: 'error', texto: t('regenerate.error') })
    }
  }

  const ocupado = estado.fase === 'enviando' || estado.fase === 'procesando'
  return (
    <section className="regenerar" aria-labelledby="regenerar-titulo">
      <h3 id="regenerar-titulo" className="sr-solo">
        {t('regenerate.button')}
      </h3>
      <button type="button" className="boton-con-texto" disabled={!enLinea || ocupado} aria-busy={ocupado} onClick={() => void regenerar()}>
        <Icono nombre="volver" tamano={16} /> {ocupado ? t('regenerate.working') : t('regenerate.button')}
      </button>
      <p className="muted" role="status">
        {!enLinea
          ? t('regenerate.offline')
          : estado.fase === 'procesando'
            ? estado.paso
            : estado.fase === 'error'
              ? estado.texto
              : t('regenerate.help')}
      </p>
    </section>
  )
}
