import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { Verdict } from '../api/client'

type Fila = { clave: string; valor: ReactNode }

/**
 * Números de `evidence` en una tabla con unidades (vistas Estudiante e Investigador).
 * Va fuera de la tarjeta del veredicto, que es idéntica en las tres vistas (specs/08-interfaz).
 * En Estudiante, cada fila lleva una línea que explica qué es (RF-INT-04).
 */
export function Evidencia({ verdict, explicar }: { verdict: Verdict; explicar: boolean }) {
  const { t, i18n } = useTranslation()
  const e = verdict.evidence
  const pct = new Intl.NumberFormat(i18n.language, { style: 'percent', maximumFractionDigits: 2 })
  const num = new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 2 })
  const conSigno = new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 2, signDisplay: 'exceptZero' })
  const db = (v: number | null, f = num) => (v == null ? t('evidence.noData') : t('evidence.db', { v: f.format(v) }))
  const pol = (hh: string, hv: string) => t('evidence.hhhv', { hh, hv })
  const regla = e.decision_rule
  const ss = e.scene_shift

  const filas: Fila[] = [
    { clave: 'changed', valor: t('evidence.ofObserved', { v: pct.format(e.changed_fraction) }) },
    { clave: 'observed', valor: t('evidence.ofZone', { v: pct.format(e.observed_fraction) }) },
    {
      clave: 'rule',
      valor: (
        <>
          {t('evidence.ruleValue', {
            change: pct.format(regla.min_changed_fraction),
            observed: pct.format(regla.min_observed_fraction),
          })}{' '}
          {!regla.calibrated && <span className="muted">{t('evidence.notCalibrated')}</span>}
        </>
      ),
    },
    { clave: 'threshold', valor: pol(db(e.threshold_hh_db), db(e.threshold_hv_db)) },
    { clave: 'meanChange', valor: pol(db(e.mean_change_hh_db, conSigno), db(e.mean_change_hv_db, conSigno)) },
    {
      clave: 'sceneShift',
      valor: ss
        ? (
            <>
              {pol(db(ss.hh_db, conSigno), db(ss.hv_db, conSigno))}.{' '}
              {t(ss.exceeds_threshold ? 'evidence.shiftExceeds' : 'evidence.shiftBelow', {
                v: num.format(ss.threshold_db),
              })}{' '}
              {t(ss.corrected ? 'evidence.shiftCorrected' : 'evidence.shiftNotCorrected')}
            </>
          )
        : t('evidence.noData'),
    },
  ]

  return (
    <section className="evidencia" aria-labelledby={`evidencia-${verdict.id}`}>
      <h3 id={`evidencia-${verdict.id}`}>{t('evidence.heading')}</h3>
      <table>
        <tbody>
          {filas.map((f) => (
            <tr key={f.clave}>
              <th scope="row">
                {t(`evidence.rows.${f.clave}`)}
                {explicar && <span className="evidencia-explica">{t(`evidence.explain.${f.clave}`)}</span>}
              </th>
              <td>{f.valor}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
