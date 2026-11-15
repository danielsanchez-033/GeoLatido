import { useId, useMemo } from 'react'
import { useTranslation } from 'react-i18next'

const DIA = 86_400_000
const dia = (iso: string) => Math.floor(Date.parse(iso.length === 10 ? `${iso}T00:00:00Z` : iso) / DIA)

export type PasadaLinea = { id: string; serie: string; direction: string; acquired_at: string }

/**
 * Línea de tiempo de las pasadas de una zona (2026-11-15): un solo eje de la fecha más antigua posible a la más nueva,
 * un carril por órbita con un punto por pasada y dos asas para el periodo. Pulsar el nombre de un carril lo
 * activa o lo quita del filtro. Las asas son `input type=range`: se mueven con el teclado y anuncian su fecha.
 */
export function LineaPasadas({
  pasadas,
  minimo,
  maximo,
  desde,
  hasta,
  onPeriodo,
  series,
  activas,
  onSeries,
}: {
  pasadas: PasadaLinea[]
  /** Primer y último día posibles (días desde 1970), referencia fija de los extremos. */
  minimo: number
  maximo: number
  desde: number
  hasta: number
  onPeriodo: (desde: number, hasta: number) => void
  series: { id: string; direction: string; n: number }[]
  /** Órbitas visibles; vacío = todas. */
  activas: string[]
  onSeries: (activas: string[]) => void
}) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language === 'en' ? 'en' : 'es'
  const ids = { titulo: useId(), desde: useId(), hasta: useId() }
  const rango = Math.max(1, maximo - minimo)
  const x = (d: number) => `${((d - minimo) / rango) * 100}%`
  const fecha = (d: number) => new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(d * DIA))
  const porSerie = useMemo(() => {
    const m = new Map<string, number[]>()
    for (const p of pasadas) m.set(p.serie, [...(m.get(p.serie) ?? []), dia(p.acquired_at)])
    return m
  }, [pasadas])
  const visible = (s: string) => activas.length === 0 || activas.includes(s)

  return (
    <section className="linea-pasadas" aria-labelledby={ids.titulo}>
      <h3 className="paso-titulo" id={ids.titulo}>
        {t('timeline.heading')}
      </h3>
      <p className="paso-ayuda">{t('timeline.help')}</p>
      <div className="linea-extremos muted">
        <span>{t('timeline.oldest', { date: fecha(minimo) })}</span>
        <span>{t('timeline.newest', { date: fecha(maximo) })}</span>
      </div>
      <div className="linea-carriles">
        {series.map((s) => (
          <div key={s.id} className="linea-carril" data-activo={visible(s.id)}>
            <button
              type="button"
              className="linea-nombre"
              aria-pressed={activas.includes(s.id)}
              onClick={() => onSeries(activas.includes(s.id) ? activas.filter((a) => a !== s.id) : [...activas, s.id])}
            >
              {s.direction === 'A' ? '↗' : '↘'} {s.id} · {s.n}
            </button>
            <div className="linea-eje" aria-hidden="true">
              <span className="linea-rango" style={{ left: x(desde), width: `calc(${x(hasta)} - ${x(desde)})` }} />
              {(porSerie.get(s.id) ?? []).map((d, i) => (
                <span key={i} className="linea-punto" data-dentro={d >= desde && d <= hasta} style={{ left: x(d) }} />
              ))}
            </div>
          </div>
        ))}
        {series.length === 0 && <p className="muted">{t('timeline.empty')}</p>}
      </div>
      <div className="linea-asas">
        <label className="sr-solo" htmlFor={ids.desde}>
          {t('timeline.from')}
        </label>
        <input
          id={ids.desde}
          type="range"
          min={minimo}
          max={maximo}
          value={desde}
          aria-valuetext={fecha(desde)}
          onChange={(e) => onPeriodo(Math.min(Number(e.target.value), hasta), hasta)}
        />
        <label className="sr-solo" htmlFor={ids.hasta}>
          {t('timeline.to')}
        </label>
        <input
          id={ids.hasta}
          type="range"
          min={minimo}
          max={maximo}
          value={hasta}
          aria-valuetext={fecha(hasta)}
          onChange={(e) => onPeriodo(desde, Math.max(Number(e.target.value), desde))}
        />
      </div>
      <p className="linea-periodo">
        <strong>{fecha(desde)}</strong> → <strong>{fecha(hasta)}</strong>
      </p>
    </section>
  )
}
