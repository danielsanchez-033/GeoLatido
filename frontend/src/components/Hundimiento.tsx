import { useTranslation } from 'react-i18next'
import type { DatosHundimiento } from '../api/hundimiento'
import { Icono } from './Iconos'

/**
 * Tarjeta «¿Se hunde el suelo?» en Hallazgos: el resumen en palabras de todos los días, qué no prueba y qué falta,
 * con botones para ver la capa en el mapa y volar al punto que más se hunde.
 */
export function Hundimiento({
  datos,
  capaActiva,
  onVerCapa,
  onVolar,
}: {
  datos: DatosHundimiento
  capaActiva: boolean
  onVerCapa: () => void
  onVolar: (lon: number, lat: number) => void
}) {
  const { t } = useTranslation()
  const punto = datos.fastest_point as { lon?: number; lat?: number } | null | undefined
  const hunde = (datos.sinking_fraction ?? 0) >= 0.01
  return (
    <section className="hundimiento tarjeta-veredicto" aria-labelledby="hundimiento-titulo">
      <h3 id="hundimiento-titulo">
        <Icono nombre="capas" tamano={18} /> {t('subsidence.title')}
      </h3>
      <p className="hundimiento-estado">{hunde ? t('subsidence.yes') : datos.status === 'computed' ? t('subsidence.no') : t('subsidence.none')}</p>
      <p>{datos.summary.detected}</p>
      <details className="hundimiento-mas">
        <summary>{t('subsidence.more')}</summary>
        <p>{datos.summary.does_not_prove}</p>
        {datos.summary.missing && <p>{datos.summary.missing}</p>}
        <p className="muted">{t('subsidence.source', { days: datos.days ?? 0, pairs: datos.pairs?.length ?? 0 })}</p>
      </details>
      <div className="hundimiento-acciones">
        {datos.tiles && (
          <button type="button" className="boton-con-texto" aria-pressed={capaActiva} onClick={onVerCapa}>
            <Icono nombre="mapa" tamano={16} /> {t('subsidence.showLayer')}
          </button>
        )}
        {hunde && punto?.lon !== undefined && punto?.lat !== undefined && (
          <button type="button" className="boton-con-texto" onClick={() => onVolar(punto.lon!, punto.lat!)}>
            <Icono nombre="ubicacion" tamano={16} /> {t('subsidence.fly')}
          </button>
        )}
      </div>
    </section>
  )
}
