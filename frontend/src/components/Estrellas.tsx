import { useTranslation } from 'react-i18next'
import type { Historia } from '../comunidad/historias'
import { BotonIcono } from './Iconos'

/** Promedio con una cifra decimal en el idioma de la interfaz; "sin valorar" si no hay votos. */
function promedio(media: number | null | undefined, n: number, idioma: string, sin: string) {
  if (media == null || n === 0) return sin
  return new Intl.NumberFormat(idioma, { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(media)
}

/** Estrellas de una historia: promedio general y desglose por perfil declarado (RF-ACC-15). */
export function ResumenEstrellas({ historia }: { historia: Historia }) {
  const { t, i18n } = useTranslation()
  const r = historia.ratings
  const sin = t('community.notRated')
  return (
    <dl className="estrellas-resumen">
      <div>
        <dt>{t('community.stars')}</dt>
        <dd>
          <span aria-hidden="true">★ </span>
          {promedio(r.average, r.count, i18n.language, sin)}
          {r.count > 0 && <span className="muted"> {t('community.votes', { count: r.count })}</span>}
        </dd>
      </div>
      {(['student', 'researcher'] as const).map((p) => (
        <div key={p}>
          <dt>{t(`community.byRole.${p}`)}</dt>
          <dd>
            {promedio(r.by_role[p].average, r.by_role[p].count, i18n.language, sin)}
            {r.by_role[p].count > 0 && <span className="muted"> ({r.by_role[p].count})</span>}
          </dd>
        </div>
      ))}
    </dl>
  )
}

/** Valorar de 1 a 5. Cada botón dice su número de estrellas; el elegido va marcado con aria-pressed. */
export function ValorarEstrellas({
  actual,
  onValorar,
  onQuitar,
  ocupado,
}: {
  actual: number | null | undefined
  onValorar: (n: number) => void
  onQuitar: () => void
  ocupado: boolean
}) {
  const { t } = useTranslation()
  return (
    <div className="estrellas-valorar" role="group" aria-label={t('community.rate')}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          className="estrella"
          aria-pressed={actual === n}
          aria-label={t('community.starsN', { count: n })}
          disabled={ocupado}
          onClick={() => onValorar(n)}
        >
          <span aria-hidden="true">{actual != null && n <= actual ? '★' : '☆'}</span>
        </button>
      ))}
      {actual != null && (
        <BotonIcono icono="quitar" etiqueta={t('community.unrate')} disabled={ocupado} onClick={onQuitar} />
      )}
    </div>
  )
}
