import { useTranslation } from 'react-i18next'
import { Marca } from './Marca'

/**
 * Distintivo permanente de datos sintéticos (RF-FAR-03). No se puede cerrar
 * y queda fijo en la cabecera mientras la serie elegida sea sintética.
 * Lleva la marca de trama: el mismo signo que lo que no describe la realidad observada.
 */
export function SyntheticBanner() {
  const { t } = useTranslation()
  return (
    <p className="synthetic-banner" role="note">
      <Marca estado="not_observable" />
      <span>{t('synthetic.banner')}</span>
    </p>
  )
}

/** Versión corta dentro de la tarjeta: el aviso viaja con el veredicto. */
export function SyntheticNotice() {
  const { t } = useTranslation()
  return (
    <p className="synthetic-notice">
      <Marca estado="not_observable" />
      <span>{t('synthetic.card')}</span>
    </p>
  )
}
