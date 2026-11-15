import { useEffect, useId, useRef, useState, type FormEvent, type Ref } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchTimeline, verdictsApi, type EventVerdict, type Lang } from '../api/client'
import type { LineaTiempoApi } from '../mapa/lineaTiempo'
import { EVENT_TYPES, EXAMPLE, type Query } from '../story/data'
import { Esqueleto } from './Esqueleto'
import { Icono } from './Iconos'
import { Marca } from './Marca'
import { PassTimeline } from './PassTimeline'
import { SyntheticNotice } from './SyntheticBadge'

type Result =
  | { key: string; status: 'error' }
  | { key: string; status: 'ready'; event: EventVerdict }

function keyOf(q: Query, lang: Lang) {
  return `${q.date}|${q.eventType}|${q.time}|${lang}`
}

export function EventAnswer({
  event,
  headingRef,
  headingId = 'event-answer-heading',
}: {
  event: EventVerdict
  headingRef?: Ref<HTMLHeadingElement>
  headingId?: string
}) {
  const { t } = useTranslation()
  const observable = event.state === 'observable'
  return (
    <article className={`verdict-card event-${event.state}`} aria-labelledby={headingId}>
      {event.data_kind === 'synthetic' && <SyntheticNotice />}
      <header className="verdict-head">
        <h3 id={headingId} className="verdict-state" tabIndex={-1} ref={headingRef}>
          <Marca estado={event.state} className="verdict-icon" />
          {t(`event.state.${event.state}`)}
        </h3>
        {!observable && event.cause_label && (
          <p className="verdict-cause">{t('event.cause', { cause: event.cause_label })}</p>
        )}
        {observable && <p className="verdict-cause">{t('event.observableNote')}</p>}
      </header>

      <dl className="verdict-summary">
        <div>
          <dt>{t('event.detected')}</dt>
          <dd>{event.summary.detected}</dd>
        </div>
        <div>
          <dt>{t('verdict.doesNotProve')}</dt>
          <dd>{event.summary.does_not_prove}</dd>
        </div>
        <div>
          <dt>{t('verdict.missing')}</dt>
          <dd>{event.summary.missing}</dd>
        </div>
      </dl>

      <dl className="event-facts">
        <dt>{t('event.previousPass')}</dt>
        <dd>{event.previous_pass ?? t('event.none')}</dd>
        <dt>{t('event.nextPass')}</dt>
        <dd>{event.next_pass ?? t('event.none')}</dd>
        {event.excluded_passes.length > 0 && (
          <>
            <dt>{t('event.excluded')}</dt>
            <dd>
              <ul>
                {event.excluded_passes.map((p) => (
                  <li key={p.granule}>
                    {p.date} ({p.series}): {p.reason}
                  </li>
                ))}
              </ul>
            </dd>
          </>
        )}
      </dl>
    </article>
  )
}

/**
 * Consulta de evento (RF-FAR-02): ¿pasó el satélite dentro de la duración supuesta del evento?
 * Los textos llegan de la API; aquí solo hay rótulos.
 */
export function EventQuery({ aoi, lang }: { aoi: string; lang: Lang }) {
  const { t } = useTranslation()
  const ids = { date: useId(), dateHelp: useId(), type: useId(), time: useId(), timeHelp: useId() }
  const [form, setForm] = useState<Query>({ date: '', eventType: '', time: '' })
  const [query, setQuery] = useState<Query>()
  const [result, setResult] = useState<Result>()
  const heading = useRef<HTMLHeadingElement>(null)
  const focusOnArrival = useRef(false)

  const requestKey = query ? keyOf(query, lang) : undefined

  // Se repite al cambiar de idioma: los textos llegan de la API con `lang`.
  useEffect(() => {
    if (!query) return
    let current = true
    const key = keyOf(query, lang)
    verdictsApi
      .GET('/aois/{aoi}/events', {
        params: {
          path: { aoi },
          query: {
            date: query.date,
            lang,
            ...(query.eventType ? { event_type: query.eventType } : {}),
            ...(query.time ? { time: query.time } : {}),
          },
        },
      })
      .then(({ data }) => {
        if (!current) return
        setResult(data ? { key, status: 'ready', event: data } : { key, status: 'error' })
      })
      .catch(() => current && setResult({ key, status: 'error' }))
    return () => {
      current = false
    }
  }, [aoi, query, lang])

  const shown = result && result.key === requestKey ? result : undefined
  const loading = query !== undefined && !shown
  const answered = shown?.status === 'ready'

  // La línea de tiempo no depende del idioma ni de la consulta: se pide una vez, con la primera respuesta.
  const [timeline, setTimeline] = useState<{ aoi: string; data: LineaTiempoApi | null }>()
  useEffect(() => {
    if (!answered || timeline?.aoi === aoi) return
    let current = true
    fetchTimeline(aoi).then((data) => current && setTimeline({ aoi, data }))
    return () => {
      current = false
    }
  }, [answered, aoi, timeline])
  const timelineData = timeline?.aoi === aoi ? timeline.data : null

  useEffect(() => {
    if (shown?.status === 'ready' && focusOnArrival.current) {
      focusOnArrival.current = false
      heading.current?.focus()
    }
  }, [shown])

  function ask(q: Query) {
    focusOnArrival.current = true
    setQuery({ ...q })
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (form.date) ask(form)
  }

  return (
    <section className="event-query" aria-labelledby="event-heading" aria-busy={loading}>
      <h2 id="event-heading">{t('event.heading')}</h2>
      <p className="muted">{t('event.intro')}</p>

      <form className="picker" onSubmit={onSubmit}>
        <label htmlFor={ids.date}>{t('event.date')}</label>
        <div>
          <input
            id={ids.date}
            type="date"
            required
            value={form.date}
            aria-describedby={ids.dateHelp}
            onChange={(e) => setForm({ ...form, date: e.target.value })}
          />
          <p id={ids.dateHelp} className="muted field-help">
            {t('event.dateHelp')}
          </p>
        </div>

        <label htmlFor={ids.type}>{t('event.type')}</label>
        <select
          id={ids.type}
          value={form.eventType}
          onChange={(e) => setForm({ ...form, eventType: e.target.value as Query['eventType'] })}
        >
          <option value="">{t('event.types.none')}</option>
          {EVENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {t(`event.types.${type}`)}
            </option>
          ))}
        </select>

        <label htmlFor={ids.time}>{t('event.time')}</label>
        <div>
          <input
            id={ids.time}
            type="time"
            value={form.time}
            aria-describedby={ids.timeHelp}
            onChange={(e) => setForm({ ...form, time: e.target.value })}
          />
          <p id={ids.timeHelp} className="muted field-help">
            {t('event.timeHelp')}
          </p>
        </div>

        <div className="form-actions">
          <button type="submit" className="boton-principal boton-con-texto">
            <Icono nombre="buscar" tamano={16} />
            {t('event.submit')}
          </button>
          {/* El ejemplo es la tormenta verificada de Parral: solo tiene sentido en esa zona. */}
          {aoi === 'parral' && (
            <button
              type="button"
              onClick={() => {
                setForm(EXAMPLE)
                ask(EXAMPLE)
              }}
            >
              {t('event.example')}
            </button>
          )}
        </div>
      </form>

      {loading && <Esqueleto etiqueta={t('event.loading')} variante="tarjeta" filas={4} />}
      {shown?.status === 'error' && <p role="alert">{t('event.error')}</p>}
      {shown?.status === 'ready' && (
        <>
          <EventAnswer event={shown.event} headingRef={heading} />
          {timeline?.data !== null && <PassTimeline timeline={timelineData} event={shown.event} lang={lang} />}
        </>
      )}
    </section>
  )
}
