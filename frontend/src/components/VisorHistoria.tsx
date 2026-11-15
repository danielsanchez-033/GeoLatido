import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { API_BASE } from '../api/client'
import type { Bbox } from '../mapa/tipos'
import { Icono } from './Iconos'

/** Tipos de la API de investigación (contracts/research.openapi.json); solo los campos que usa la vista. */
export type Afirmacion = { text: string; evidence: string[]; kind: string }
export type MapaCapitulo = { bbox?: number[]; aoi?: string; series?: string; pair_id?: string } | null
export type Capitulo = { key: string; title: string; claims: Afirmacion[]; map: MapaCapitulo }
export type Evidencia = { id: string; kind: string; label: string; urls?: string[]; verdict_path?: string; [k: string]: unknown }
export type Historia = {
  id: string
  research_id: string
  title: string
  data_kind: string
  chapters: Capitulo[]
  evidence: Evidencia[]
  traceability: { ok: boolean }
}

export const BASE_RESEARCH = `${API_BASE}/api/research`
/** Segundos que se queda cada capítulo al reproducir la historia. */
const PASO_MS = 7000

/**
 * Historia científica por capítulos (2026-11-15), compartida por la pestaña Historia (la zona activa) e Investigar.
 * Cada afirmación despliega su evidencia con los enlaces a sus fuentes y al veredicto JSON. «Reproducir» recorre los
 * capítulos solo: el mapa vuela a la zona de cada uno o abre su par, como al pulsarlos.
 */
export function VisorHistoria({
  historia,
  onVolar,
  onVerPar,
  nivel = 3,
}: {
  historia: Historia
  onVolar: (bbox: Bbox) => void
  onVerPar: (series: string, pairId: string) => void
  /** Nivel del título: 3 dentro de Investigar, 2 en la pestaña Historia. */
  nivel?: 2 | 3
}) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language === 'en' ? 'en' : 'es'
  const [activo, setActivo] = useState(1)
  const [reproduciendo, setReproduciendo] = useState(false)
  const capitulos = historia.chapters
  const capitulo = capitulos[activo]
  const evidencia = new Map(historia.evidence.map((e) => [e.id, e]))
  const Titulo = nivel === 2 ? 'h2' : 'h3'
  const Sub = nivel === 2 ? 'h3' : 'h4'

  function irA(c: Capitulo | undefined) {
    if (!c?.map) return
    if (c.map.series && c.map.pair_id) onVerPar(c.map.series, c.map.pair_id)
    else if (c.map.bbox) onVolar(c.map.bbox as Bbox)
  }
  function elegir(i: number) {
    setActivo(i)
    irA(capitulos[i])
  }

  // Reproducción: avanza un capítulo cada PASO_MS y se para al final. Con movimiento reducido no se reproduce sola.
  useEffect(() => {
    if (!reproduciendo) return
    const id = window.setTimeout(() => {
      if (activo >= capitulos.length - 1) {
        setReproduciendo(false)
        return
      }
      setActivo(activo + 1)
      irA(capitulos[activo + 1])
    }, PASO_MS)
    return () => window.clearTimeout(id)
    // irA solo depende de las funciones del padre, que no cambian el ritmo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reproduciendo, activo, capitulos])

  return (
    <article className="investigacion-historia">
      <Titulo>{historia.title}</Titulo>
      {historia.data_kind === 'synthetic' && <p className="aviso-sintetico">{t('research.synthetic')}</p>}
      {lang === 'en' && <p className="muted">{t('research.spanishOnly')}</p>}
      <p className="muted">
        {historia.traceability.ok ? t('research.traceOk') : t('research.traceFail')} ·{' '}
        <a href={`${BASE_RESEARCH}/stories/${historia.id}/export?format=md`} download>
          Markdown
        </a>{' '}
        ·{' '}
        <a href={`${BASE_RESEARCH}/stories/${historia.id}/export?format=json`} download>
          JSON
        </a>
      </p>
      <div className="historia-controles">
        <button
          type="button"
          className="boton-principal boton-con-texto"
          aria-pressed={reproduciendo}
          onClick={() => {
            if (!reproduciendo && activo >= capitulos.length - 1) elegir(1)
            else if (!reproduciendo) irA(capitulo)
            setReproduciendo((r) => !r)
          }}
        >
          <Icono nombre={reproduciendo ? 'quitar' : 'historia'} tamano={16} />
          {reproduciendo ? t('research.pause') : t('research.play')}
        </button>
        <span className="muted" aria-live="polite">
          {t('research.chapterOf', { n: activo, total: capitulos.length - 1 })}
        </span>
      </div>
      <nav aria-label={t('research.chapters')}>
        <ol className="investigacion-capitulos">
          {capitulos.slice(1).map((c, i) => (
            <li key={c.key}>
              <button type="button" aria-current={activo === i + 1 ? 'step' : undefined} onClick={() => elegir(i + 1)}>
                {i + 1}. {c.title}
              </button>
            </li>
          ))}
        </ol>
      </nav>
      {capitulo && (
        <section className="investigacion-capitulo" aria-label={capitulo.title}>
          <Sub>{capitulo.title}</Sub>
          {capitulo.map && (
            <button type="button" className="boton-con-texto" onClick={() => irA(capitulo)}>
              <Icono nombre="mapa" tamano={16} />
              {t('research.showOnMap')}
            </button>
          )}
          <ul>
            {capitulo.claims.map((c, i) => (
              <li key={i} data-tipo={c.kind}>
                {c.kind === 'caveat' || c.kind === 'warning' ? <strong>{t('research.caveat')} </strong> : null}
                {c.kind === 'hypothesis' ? <em>{t('research.hypothesis')} </em> : null}
                {c.text}
                {c.evidence.length > 0 && (
                  <details className="investigacion-evidencia">
                    <summary>{t('research.evidence', { count: c.evidence.length })}</summary>
                    <ul>
                      {c.evidence.map((id) => {
                        const e = evidencia.get(id)
                        const ruta = typeof e?.verdict_path === 'string' ? `${API_BASE}${e.verdict_path}` : null
                        const fuentes = (e?.urls ?? []).filter((u) => typeof u === 'string' && u.startsWith('http'))
                        return (
                          <li key={id}>
                            <code>{id}</code> — {e?.label ?? '?'} ({e?.kind})
                            {ruta && (
                              <>
                                {' '}
                                <a href={ruta} target="_blank" rel="noopener noreferrer">
                                  JSON
                                </a>
                              </>
                            )}
                            {fuentes.map((u, k) => (
                              <span key={u}>
                                {' '}
                                <a href={u} target="_blank" rel="noopener noreferrer">
                                  {t('research.source', { n: k + 1 })}
                                  <span className="sr-solo"> ({new URL(u).hostname})</span>
                                </a>
                              </span>
                            ))}
                          </li>
                        )
                      })}
                    </ul>
                  </details>
                )}
              </li>
            ))}
          </ul>
          <div className="investigacion-pasos">
            <button type="button" disabled={activo <= 1} onClick={() => elegir(activo - 1)}>
              {t('research.prev')}
            </button>
            <button type="button" disabled={activo >= capitulos.length - 1} onClick={() => elegir(activo + 1)}>
              {t('research.next')}
            </button>
          </div>
        </section>
      )}
    </article>
  )
}
