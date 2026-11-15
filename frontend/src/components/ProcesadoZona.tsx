import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { API_BASE } from '../api/client'
import type { Bbox } from '../mapa/tipos'
import { Icono } from './Iconos'

type Paso = 'zone' | 'series' | 'process'
const PASOS: Paso[] = ['zone', 'series', 'process']
type Trabajo = {
  id: string
  state: 'queued' | 'running' | 'done' | 'failed' | 'cancelled' | 'no_processable_series'
  step: Paso | null
  steps: Record<Paso, string>
  series: { id: string; polarization: string; dates: number } | null
  series_found: { id: string; polarization: string; dates: number }[]
  log: string[]
  error: string | null
  bbox: number[]
  max_dates: number
  aoi?: string
  summary?: ResumenProcesado
}

/** Resumen ligero que `online` saca del manifiesto al terminar (2026-11-15): llega antes que teselas y veredictos. */
export type ResumenProcesado = {
  series: string | null
  data_kind: string | null
  dates: string[]
  pairs: {
    id: string
    from: string
    to: string
    kind: string | null
    interval_days: number
    state: 'change_probable' | 'no_detectable_change' | 'not_observable'
    cause: string | null
    observed_fraction: number
    changed_fraction: number
  }[]
  rules: { min_observed_fraction: number; min_changed_fraction: number; calibrated: boolean }
}

const BASE = `${API_BASE}/api/online`

/**
 * Procesado en línea de la zona buscada (2026-11-15). Al llegar a un lugar sin veredictos se pide a `online` que lo
 * procese: elegir la serie NISAR con HH y HV y leer de NASA en memoria solo la ventana de las últimas fechas para
 * calcular los pares. No se guarda ningún recorte; solo el resultado. Al terminar, la zona pasa a tener veredictos.
 */
export function ProcesadoZona({
  lugar,
  onListo,
  autoIniciar,
}: {
  lugar: { name: string; bbox: Bbox }
  onListo: (aoi: string, bbox: Bbox, resumen: ResumenProcesado | null) => void
  /** Ciudades buscadas: se procesa sola. Puntos del mapa: espera al botón (2026-11-15). */
  autoIniciar: boolean
}) {
  const { t } = useTranslation()
  const [trabajo, setTrabajo] = useState<Trabajo | null>(null)
  const [error, setError] = useState<string | null>(null)
  // La pila no tiene EARTHDATA_TOKEN: se dice sin pedir el procesado, que respondería 503 (2026-11-15).
  const [sinToken, setSinToken] = useState(false)
  const [intento, setIntento] = useState(0)
  // Por la caja y no por el nombre: el nombre de un punto llega después (geocodificación inversa) y no debe
  // reiniciar el procesado ni volver a pedir el botón.
  const lugarClave = lugar.bbox.join(',')
  // Lugar para el que se pulsó «Procesar»; con otro lugar vuelve a esperar al botón.
  const [pedido, setPedido] = useState<string | null>(null)
  const iniciado = autoIniciar || pedido === lugarClave
  const clave = `${lugarClave}|${intento}|${iniciado}`

  useEffect(() => {
    if (!iniciado) {
      setTrabajo(null)
      setError(null)
      return
    }
    let vigente = true
    let temporizador: number | undefined
    const seguir = async (id: string) => {
      const r = await fetch(`${BASE}/zones/${id}`)
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as Trabajo
      if (!vigente) return
      setTrabajo(j)
      if (j.state === 'done' && j.aoi) onListo(j.aoi, j.bbox as Bbox, j.summary ?? null)
      else if (j.state === 'queued' || j.state === 'running') temporizador = window.setTimeout(() => void seguir(id).catch(() => undefined), 4000)
    }
    ;(async () => {
      setError(null)
      setTrabajo(null)
      setSinToken(false)
      const salud = await fetch(`${BASE}/health`)
      if (!salud.ok) throw new Error(String(salud.status))
      if (((await salud.json()) as { earthdata_token?: boolean }).earthdata_token === false) {
        if (vigente) setSinToken(true)
        return
      }
      const r = await fetch(`${BASE}/zones`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: lugar.name, bbox: lugar.bbox }),
      })
      const cuerpo = await r.json().catch(() => null)
      if (!r.ok) throw new Error(typeof cuerpo?.detail === 'string' ? cuerpo.detail : String(r.status))
      if (vigente) await seguir((cuerpo as Trabajo).id)
    })().catch((e: unknown) => vigente && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      vigente = false
      window.clearTimeout(temporizador)
    }
    // onListo cambia en cada render del padre; el trabajo depende solo del lugar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clave])

  const enMarcha = trabajo && (trabajo.state === 'queued' || trabajo.state === 'running')
  return (
    <section className="procesado-zona vidrio-suave" aria-live="polite" aria-busy={Boolean(enMarcha)}>
      <h3>{t('online.heading')}</h3>
      {!iniciado && (
        <>
          <p className="muted">{t('online.pointIntro')}</p>
          <button type="button" className="boton-con-texto" onClick={() => setPedido(lugarClave)}>
            <Icono nombre="hallazgos" tamano={16} />
            {t('online.processPoint')}
          </button>
        </>
      )}
      {iniciado && error && <p role="alert">{t('online.error', { error })}</p>}
      {iniciado && sinToken && <p>{t('online.noToken')}</p>}
      {iniciado && !error && !sinToken && !trabajo && <p className="muted">{t('online.starting')}</p>}
      {trabajo && (
        <>
          <p className="muted">{t(`online.state.${trabajo.state}`)}</p>
          {trabajo.series && (
            <p>
              {t('online.series', { id: trabajo.series.id, pol: trabajo.series.polarization, dates: Math.min(trabajo.series.dates, trabajo.max_dates) })}
            </p>
          )}
          <ol className="procesado-pasos">
            {PASOS.map((p) => {
              const s = trabajo.steps[p] ?? 'pending'
              return (
                <li key={p} data-estado={s.split(' ')[0]}>
                  <span>{t(`online.step.${p}`)}</span> <span className="muted">{t(`online.stepState.${s.split(' ')[0]}`)}{s.includes('(') ? ` ${s.slice(s.indexOf('('))}` : ''}</span>
                </li>
              )
            })}
          </ol>
          {trabajo.state === 'done' && trabajo.summary && <ResumenPares resumen={trabajo.summary} />}
          {enMarcha && trabajo.log.length > 0 && <p className="muted procesado-log">{trabajo.log.at(-1)}</p>}
          {trabajo.state === 'no_processable_series' && (
            <>
              <p>{t('online.noSeries')}</p>
              {trabajo.series_found.length > 0 && (
                <ul className="muted">
                  {trabajo.series_found.map((s) => (
                    <li key={s.id}>
                      {s.id} · {s.polarization} · {s.dates}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
          {(trabajo.state === 'failed' || trabajo.state === 'cancelled') && (
            <>
              {trabajo.error && <p role="alert">{trabajo.error}</p>}
              <button type="button" className="boton-con-texto" onClick={() => setIntento((n) => n + 1)}>
                <Icono nombre="centrar" tamano={16} />
                {t('online.retry')}
              </button>
            </>
          )}
          {enMarcha && (
            <button
              type="button"
              className="boton-con-texto"
              onClick={() => void fetch(`${BASE}/zones/${trabajo.id}/cancel`, { method: 'POST' }).catch(() => undefined)}
            >
              <Icono nombre="quitar" tamano={16} />
              {t('online.cancel')}
            </button>
          )}
        </>
      )}
    </section>
  )
}

/**
 * Lista por par del resumen ligero: fechas, días, estado y fracción de cambio. Se enseña en cuanto termina el
 * procesado, mientras verdicts prepara el veredicto completo, que es el que manda.
 */
export function ResumenPares({ resumen }: { resumen: ResumenProcesado }) {
  const { t, i18n } = useTranslation()
  const pct = (x: number) =>
    new Intl.NumberFormat(i18n.language === 'en' ? 'en' : 'es', { style: 'percent', maximumFractionDigits: 2 }).format(x)
  return (
    <section className="procesado-resumen" aria-label={t('online.summary.heading')}>
      <h4>{t('online.summary.heading')}</h4>
      {resumen.data_kind === 'synthetic' && <p role="note">{t('online.summary.synthetic')}</p>}
      <ul className="procesado-pares">
        {resumen.pairs.map((p) => (
          <li key={p.id} data-estado={p.state}>
            <strong>
              {p.from.slice(0, 10)} → {p.to.slice(0, 10)}
            </strong>{' '}
            <span className="muted">{t('online.summary.days', { count: p.interval_days })}</span>
            <br />
            {t(`online.summary.state.${p.state}`)}
            {p.state === 'not_observable'
              ? ` · ${t('online.summary.observed', { pct: pct(p.observed_fraction) })}`
              : ` · ${t('online.summary.changed', { pct: pct(p.changed_fraction) })}`}
          </li>
        ))}
      </ul>
      <p className="muted">{t('online.summary.note', { pct: pct(resumen.rules.min_changed_fraction) })}</p>
    </section>
  )
}
