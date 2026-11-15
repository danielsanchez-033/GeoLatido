import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import type { Bbox } from '../mapa/tipos'
import { Esqueleto } from './Esqueleto'
import { Icono } from './Iconos'
import { BASE_RESEARCH, VisorHistoria, type Historia } from './VisorHistoria'

type Lugar = { id: string; name: string; bbox: number[]; source: string; approximate?: boolean }
type Trabajo = { id: string; state: 'queued' | 'running' | 'done' | 'failed' | 'cancelled'; step: string | null; error: string | null }
type Estado = { id: string; job: Trabajo | null; story_ids: string[] }
type Resumen = { id: string; question: string; areas: string[]; created_at: string; story_ids: string[] }

const BASE = BASE_RESEARCH
const EJEMPLOS = ['examples.mining', 'examples.flood', 'examples.glacier', 'examples.compare'] as const

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) } })
  if (!r.ok) {
    const cuerpo = await r.json().catch(() => null)
    const det = cuerpo?.detail
    throw new Error(typeof det === 'string' ? det : typeof det?.detail === 'string' ? det.detail : String(r.status))
  }
  return (await r.json()) as T
}

/**
 * Investigación (2026-11-15): una pregunta en lenguaje natural se convierte en una investigación reproducible
 * (catálogo de NASA, veredictos de este proyecto, acontecimientos verificados) y en una historia de 17 capítulos en
 * la que cada afirmación cita su evidencia. Al recorrer un capítulo, el mapa vuela a su zona o abre su par.
 */
export function Investigacion({
  onVolar,
  onVerPar,
  semilla,
}: {
  onVolar: (bbox: Bbox) => void
  onVerPar: (series: string, pairId: string) => void
  /** Zona buscada en la barra superior que se quiere investigar: entra como área elegida. */
  semilla?: { id: string; name: string; bbox: number[]; source: string } | null
}) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language === 'en' ? 'en' : 'es'
  const ids = { titulo: useId(), pregunta: useId(), lugar: useId(), desde: useId(), hasta: useId() }
  const [pregunta, setPregunta] = useState('')
  const [lugarQ, setLugarQ] = useState('')
  const [sugeridos, setSugeridos] = useState<Lugar[] | null>(null)
  const [areas, setAreas] = useState<Lugar[]>([])
  const [periodo, setPeriodo] = useState(() => ({ usar: false, desde: '2026-06-01', hasta: new Date().toISOString().slice(0, 10) }))
  const [error, setError] = useState<string | null>(null)
  const [estado, setEstado] = useState<Estado | null>(null)
  const [historia, setHistoria] = useState<Historia | null>(null)
  const [previas, setPrevias] = useState<Resumen[]>([])
  const sondeo = useRef<number | null>(null)

  // Una zona nueva desde la barra superior entra como área (ajuste de estado al cambiar la prop, sin efecto).
  const [semillaVista, setSemillaVista] = useState(semilla)
  if (semilla !== semillaVista) {
    setSemillaVista(semilla)
    if (semilla) {
      const area = { ...semilla, id: semilla.id === 'vista' ? `vista_${semilla.bbox.map((v) => v.toFixed(2)).join('_')}` : semilla.id }
      setAreas((a) => (a.some((x) => x.id === area.id) ? a : [...a, area].slice(-4)))
    }
  }

  useEffect(() => {
    json<Resumen[]>(`${BASE}/research?limit=8`).then(setPrevias).catch(() => setPrevias([]))
    return () => {
      if (sondeo.current) window.clearTimeout(sondeo.current)
    }
  }, [])

  async function buscarLugar() {
    if (lugarQ.trim().length < 2) return
    try {
      const r = await json<{ results: Lugar[] }>(`${BASE}/places?q=${encodeURIComponent(lugarQ.trim())}`)
      setSugeridos(r.results.slice(0, 6))
    } catch {
      setSugeridos([])
    }
  }

  function seguir(id: string) {
    const paso = async () => {
      try {
        const s = await json<Estado>(`${BASE}/research/${id}/status`)
        setEstado(s)
        if (s.job && (s.job.state === 'queued' || s.job.state === 'running')) {
          sondeo.current = window.setTimeout(paso, 1500)
        } else if (s.job?.state === 'done' && s.story_ids[0]) {
          setHistoria(await json<Historia>(`${BASE}/stories/${s.story_ids[0]}`))
          json<Resumen[]>(`${BASE}/research?limit=8`).then(setPrevias).catch(() => undefined)
        }
      } catch {
        setError(t('research.error'))
      }
    }
    void paso()
  }

  async function investigar(e?: FormEvent) {
    e?.preventDefault()
    setError(null)
    setHistoria(null)
    const cuerpo: Record<string, unknown> = { lang, run: true }
    if (pregunta.trim()) cuerpo.question = pregunta.trim()
    if (areas.length) cuerpo.areas = areas.map((a) => ({ id: a.id, name: a.name, bbox: a.bbox }))
    if (periodo.usar) cuerpo.period = { start: periodo.desde, end: periodo.hasta }
    try {
      const doc = await json<{ id: string }>(`${BASE}/research`, { method: 'POST', body: JSON.stringify(cuerpo) })
      setEstado({ id: doc.id, job: null, story_ids: [] })
      seguir(doc.id)
    } catch (err) {
      setError(err instanceof Error && err.message.length > 3 ? err.message : t('research.error'))
    }
  }

  async function cancelar() {
    if (!estado) return
    await fetch(`${BASE}/research/${estado.id}/cancel`, { method: 'POST' }).catch(() => undefined)
  }

  async function abrir(r: Resumen) {
    setError(null)
    setEstado({ id: r.id, job: null, story_ids: r.story_ids })
    if (r.story_ids[0]) {
      setHistoria(await json<Historia>(`${BASE}/stories/${r.story_ids[0]}`).catch(() => null))
    }
  }

  const enMarcha = estado?.job && (estado.job.state === 'queued' || estado.job.state === 'running')

  return (
    <section className="investigacion" aria-labelledby={ids.titulo}>
      <h2 id={ids.titulo}>{t('research.heading')}</h2>
      <p className="muted">{t('research.intro')}</p>

      <form className="investigacion-formulario" onSubmit={investigar}>
        <div className="campo">
          <label htmlFor={ids.pregunta}>{t('research.question')}</label>
          <textarea id={ids.pregunta} rows={3} maxLength={1000} value={pregunta} onChange={(e) => setPregunta(e.target.value)} placeholder={t('research.placeholder')} />
        </div>
        <div className="chips" role="group" aria-label={t('research.examplesLabel')}>
          {EJEMPLOS.map((k) => (
            <button key={k} type="button" className="chip" onClick={() => setPregunta(t(`research.${k}`))}>
              {t(`research.${k}`)}
            </button>
          ))}
        </div>

        <details className="pliegue">
          <summary>{t('research.manual')}</summary>
          <div className="campo">
            <label htmlFor={ids.lugar}>{t('research.place')}</label>
            <div className="investigacion-lugar">
              <input
                id={ids.lugar}
                type="text"
                value={lugarQ}
                onChange={(e) => setLugarQ(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    void buscarLugar()
                  }
                }}
              />
              <button type="button" className="boton-con-texto" onClick={() => void buscarLugar()}>
                <Icono nombre="buscar" tamano={16} />
                {t('research.findPlace')}
              </button>
            </div>
          </div>
          {sugeridos && (
            <ul className="investigacion-sugeridos">
              {sugeridos.length === 0 && <li className="muted">{t('research.noPlace')}</li>}
              {sugeridos.map((l) => (
                <li key={l.id}>
                  <button
                    type="button"
                    disabled={areas.length >= 4 || areas.some((a) => a.id === l.id)}
                    onClick={() => {
                      setAreas((a) => [...a, l])
                      onVolar(l.bbox as Bbox)
                    }}
                  >
                    {l.name}
                  </button>
                  <span className="muted"> · {l.source}</span>
                </li>
              ))}
            </ul>
          )}
          <label className="investigacion-check">
            <input type="checkbox" checked={periodo.usar} onChange={(e) => setPeriodo((p) => ({ ...p, usar: e.target.checked }))} />
            {t('research.usePeriod')}
          </label>
          {periodo.usar && (
            <div className="rango-campos">
              <div className="campo">
                <label htmlFor={ids.desde}>{t('search.from')}</label>
                <input id={ids.desde} type="date" value={periodo.desde} max={periodo.hasta} onChange={(e) => setPeriodo((p) => ({ ...p, desde: e.target.value }))} />
              </div>
              <div className="campo">
                <label htmlFor={ids.hasta}>{t('search.to')}</label>
                <input id={ids.hasta} type="date" value={periodo.hasta} min={periodo.desde} onChange={(e) => setPeriodo((p) => ({ ...p, hasta: e.target.value }))} />
              </div>
            </div>
          )}
        </details>

        {areas.length > 0 && (
          <ul className="chips" aria-label={t('research.areas')}>
            {areas.map((a) => (
              <li key={a.id} className="chip">
                {a.name}
                <button type="button" aria-label={t('research.removeArea', { name: a.name })} onClick={() => setAreas((x) => x.filter((y) => y.id !== a.id))}>
                  <Icono nombre="quitar" tamano={14} />
                </button>
              </li>
            ))}
          </ul>
        )}
        <button type="submit" className="boton-principal boton-con-texto" disabled={Boolean(enMarcha) || (!pregunta.trim() && areas.length === 0)}>
          <Icono nombre="interprete" tamano={16} />
          {t('research.run')}
        </button>
      </form>

      <div aria-live="polite" aria-busy={Boolean(enMarcha)}>
        {error && <p role="alert">{error}</p>}
        {enMarcha && (
          <>
            <Esqueleto etiqueta={t(`research.step.${estado?.job?.step ?? 'queued'}`)} variante="lista" filas={3} />
            <button type="button" className="boton-con-texto" onClick={() => void cancelar()}>
              <Icono nombre="quitar" tamano={16} />
              {t('research.cancel')}
            </button>
          </>
        )}
        {estado?.job?.state === 'failed' && <p role="alert">{t('research.failed', { error: estado.job.error ?? '' })}</p>}
        {estado?.job?.state === 'cancelled' && <p>{t('research.cancelled')}</p>}
      </div>

      {historia && <VisorHistoria key={historia.id} historia={historia} onVolar={onVolar} onVerPar={onVerPar} />}

      {previas.length > 0 && (
        <details className="pliegue">
          <summary>{t('research.previous')}</summary>
          <ul className="investigacion-previas">
            {previas.map((r) => (
              <li key={r.id}>
                <button type="button" onClick={() => void abrir(r)} disabled={!r.story_ids.length}>
                  {r.question || r.areas.join(', ')}
                </button>
                <span className="muted"> · {r.created_at.slice(0, 16).replace('T', ' ')}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
      <p className="muted">{t('research.sources')}</p>
    </section>
  )
}
