import { useTranslation } from 'react-i18next'
import type { Verdict } from '../api/client'

export type EstadoMarca = Verdict['state'] | 'observable'

/**
 * Marca de estado del sistema en blanco y negro: relleno (cambio probable), contorno
 * (sin cambio detectable) y trama (no observable). La forma lleva el estado, no el color
 * (constitución IX.2). Siempre va junto al texto del estado: es decorativa.
 */
export function Marca({ estado, className }: { estado: EstadoMarca; className?: string }) {
  return <span className={`marca marca-${estado}${className ? ` ${className}` : ''}`} aria-hidden="true" />
}

const ESTADOS: Verdict['state'][] = ['change_probable', 'no_detectable_change', 'not_observable']

/** Cómo se lee cada respuesta: las tres marcas con su nombre y una frase. */
export function LeyendaEstados() {
  const { t } = useTranslation()
  return (
    <ul className="leyenda-estados" aria-label={t('states.label')}>
      {ESTADOS.map((e) => (
        <li key={e}>
          <Marca estado={e} />
          <span>
            <strong>{t(`verdict.state.${e}`)}</strong>
            <span className="muted">{t(`states.${e}`)}</span>
          </span>
        </li>
      ))}
    </ul>
  )
}
