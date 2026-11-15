import { useTranslation } from 'react-i18next'
import type { Verdict } from '../api/client'
import { Icono } from './Iconos'
import { Marca } from './Marca'
import { SyntheticNotice } from './SyntheticBadge'

type PassFreshness = Verdict['receipt']['freshness']['before']

function Pass({ label, pass }: { label: string; pass: PassFreshness }) {
  const { t, i18n } = useTranslation()
  const hours = pass.publication_latency_hours
  const latency =
    pass.latency_status === 'available' && hours != null
      ? t('receipt.latency', {
          hours: new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 1 }).format(hours),
        })
      : t(`receipt.latencyStatus.${pass.latency_status}`, { defaultValue: pass.latency_status })
  return (
    <li>
      {label}: {t('receipt.age', { date: pass.date, count: pass.age_days })}; {latency}
    </li>
  )
}

function Receipt({ verdict }: { verdict: Verdict }) {
  const { t } = useTranslation()
  const r = verdict.receipt
  const optical = verdict.evidence.optical
  const water = verdict.evidence.water
  return (
    <details className="receipt">
      <summary>
        <Icono nombre="recibo" tamano={16} />
        <span>{t('receipt.summary')}</span>
      </summary>
      <dl>
        <dt>{t('receipt.dataKind')}</dt>
        <dd>{t(`dataKind.${r.data_kind}`)}</dd>
        <dt>{t('receipt.maturity')}</dt>
        <dd>{r.maturity}</dd>
        <dt>{t('receipt.series')}</dt>
        <dd>
          {t('receipt.seriesValue', {
            id: r.series,
            track: r.track,
            direction: t(`receipt.direction.${r.direction}`, { defaultValue: r.direction }),
            frame: r.frame,
          })}
        </dd>
        <dt>{t('receipt.modePolarization')}</dt>
        <dd>
          {r.mode} · {r.polarization}
        </dd>
        <dt>{t('receipt.crid')}</dt>
        <dd>{r.crid}</dd>
        <dt>{t('receipt.dataGap')}</dt>
        <dd>{t(r.spans_data_gap ? 'receipt.yes' : 'receipt.no')}</dd>
        <dt>{t('receipt.freshness')}</dt>
        <dd>
          <ul>
            <Pass label={t('receipt.before')} pass={r.freshness.before} />
            <Pass label={t('receipt.after')} pass={r.freshness.after} />
          </ul>
        </dd>
        {optical && (
          <>
            <dt>{t('receipt.optical')}</dt>
            <dd>{optical.text}</dd>
          </>
        )}
        {water?.text && (
          <>
            <dt>{t('receipt.water')}</dt>
            <dd>{water.text}</dd>
          </>
        )}
        <dt>{t('receipt.granules')}</dt>
        <dd>
          <ul className="granules">
            {r.granules.map((g) => (
              <li key={g}>
                <code>{g}</code>
              </li>
            ))}
          </ul>
        </dd>
        {r.notices.length > 0 && (
          <>
            <dt>{t('receipt.notices')}</dt>
            <dd>
              <ul>
                {r.notices.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </dd>
          </>
        )}
      </dl>
    </details>
  )
}

/**
 * Tarjeta de veredicto (RF-FAR-01). Los textos vienen de la API tal cual; aquí solo hay rótulos.
 * Jerarquía de specs/05-faro/plan.md: estado, tres textos siempre visibles, hipótesis y recibo plegado.
 */
export function VerdictCard({ verdict }: { verdict: Verdict }) {
  const { t } = useTranslation()
  const headingId = `verdict-${verdict.series}-${verdict.id}`
  return (
    <article className={`verdict-card verdict-${verdict.state}`} aria-labelledby={headingId}>
      {verdict.receipt.data_kind === 'synthetic' && <SyntheticNotice />}
      <header className="verdict-head">
        <h3 id={headingId} className="verdict-state">
          {/* La marca (relleno, contorno o trama) lleva el estado sin depender del color (WCAG 1.4.1). */}
          <Marca estado={verdict.state} className="verdict-icon" />
          {t(`verdict.state.${verdict.state}`)}
        </h3>
        {verdict.state === 'not_observable' && verdict.cause_label && (
          <p className="verdict-cause">{t('verdict.cause', { cause: verdict.cause_label })}</p>
        )}
        <p className="verdict-fechas">
          <Icono nombre="evento" tamano={14} />
          {t('verdict.dates', { from: verdict.from_date, to: verdict.to_date, count: verdict.interval_days })}
        </p>
      </header>

      <dl className="verdict-summary">
        <div className="resumen-detectado">
          <dt>
            <Icono nombre="ver" tamano={15} />
            {t('verdict.detected')}
          </dt>
          <dd>{verdict.summary.detected}</dd>
        </div>
        <div className="resumen-no-prueba">
          <dt>
            <Icono nombre="quitar" tamano={15} />
            {t('verdict.doesNotProve')}
          </dt>
          <dd>{verdict.summary.does_not_prove}</dd>
        </div>
        <div className="resumen-falta">
          <dt>
            <Icono nombre="info" tamano={15} />
            {t('verdict.missing')}
          </dt>
          <dd>{verdict.summary.missing}</dd>
        </div>
      </dl>

      {verdict.hypotheses.length > 0 && (
        <section className="verdict-hypotheses" aria-label={t('verdict.hypotheses')}>
          <h4>{t('verdict.hypotheses')}</h4>
          <ul>
            {verdict.hypotheses.map((h) => (
              <li key={h}>{h}</li>
            ))}
          </ul>
        </section>
      )}

      <Receipt verdict={verdict} />
    </article>
  )
}
