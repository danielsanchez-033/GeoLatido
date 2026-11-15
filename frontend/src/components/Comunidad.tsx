import { useCallback, useEffect, useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { Historia } from '../comunidad/historias'
import { authApi, detalle, useSesion } from '../sesion/sesion'
import { Esqueleto } from './Esqueleto'
import { ResumenEstrellas, ValorarEstrellas } from './Estrellas'
import { BotonIcono } from './Iconos'

type Lista =
  | { estado: 'cargando' }
  | { estado: 'apagado' }
  | { estado: 'error' }
  | { estado: 'lista'; historias: Historia[]; total: number }

/**
 * Historias de la comunidad (RF-ACC-13 a 16): se leen sin cuenta; con sesión se descargan y se valoran
 * con estrellas, que se muestran con el desglose por perfil declarado.
 */
export function Comunidad({
  aoi,
  version,
  onAbrir,
  onDescargar,
}: {
  aoi: string
  /** Sube al guardar una historia nueva, para volver a pedir la lista. */
  version: number
  onAbrir: (h: Historia) => void
  onDescargar: (h: Historia) => Promise<void>
}) {
  const { t } = useTranslation()
  const { sesion, cabeceras } = useSesion()
  const orden = useId()
  const [sort, setSort] = useState<'recent' | 'stars'>('recent')
  const [lista, setLista] = useState<Lista>({ estado: 'cargando' })
  const [ocupada, setOcupada] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const token = sesion.estado === 'abierta' ? sesion.token : null

  // Con el acceso apagado no se pide nada: se dice en el render (ver `mostrada`).
  const pedir = sesion.estado !== 'comprobando' && sesion.estado !== 'apagado'
  const cargar = useCallback(
    () =>
      authApi
        .GET('/stories', {
          params: { query: { aoi, sort, limit: 50 } },
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        .then(({ data, response }) => {
          if (data) setLista({ estado: 'lista', historias: data.stories, total: data.total })
          else setLista(response.status === 503 ? { estado: 'apagado' } : { estado: 'error' })
        })
        .catch(() => setLista({ estado: 'error' })),
    [aoi, sort, token],
  )

  useEffect(() => {
    if (pedir) void cargar()
  }, [cargar, pedir, version])
  const mostrada: Lista = sesion.estado === 'apagado' ? { estado: 'apagado' } : lista

  /** Sustituye una historia de la lista por la respuesta de la API. */
  const poner = (h: Historia) =>
    setLista((l) => (l.estado === 'lista' ? { ...l, historias: l.historias.map((x) => (x.id === h.id ? h : x)) } : l))

  async function valorar(h: Historia, estrellas: number | null) {
    setOcupada(h.id)
    setAviso(null)
    const path = { params: { path: { story_id: h.id } }, headers: cabeceras() }
    const { data, error } =
      estrellas == null
        ? await authApi.DELETE('/stories/{story_id}/rating', path)
        : await authApi.POST('/stories/{story_id}/rating', { ...path, body: { stars: estrellas } })
    setOcupada(null)
    if (data) poner(data)
    else setAviso(detalle(error) ?? t('community.error'))
  }

  async function borrar(h: Historia) {
    if (!window.confirm(t('community.confirmDelete', { title: h.title }))) return
    setOcupada(h.id)
    const { response } = await authApi.DELETE('/stories/{story_id}', {
      params: { path: { story_id: h.id } },
      headers: cabeceras(),
    })
    setOcupada(null)
    if (response.ok) await cargar()
    else setAviso(t('community.error'))
  }

  return (
    <section className="comunidad" aria-labelledby="comunidad-titulo">
      <h3 id="comunidad-titulo" className="sr-solo">
        {t('community.heading')}
      </h3>
      <div className="comunidad-barra">
        <label htmlFor={orden}>{t('community.sort')}</label>
        <select id={orden} value={sort} onChange={(e) => setSort(e.target.value as 'recent' | 'stars')}>
          <option value="recent">{t('community.sortRecent')}</option>
          <option value="stars">{t('community.sortStars')}</option>
        </select>
      </div>
      {aviso && <p role="alert">{aviso}</p>}
      {mostrada.estado === 'cargando' && <Esqueleto etiqueta={t('community.loading')} variante="lista" filas={3} />}
      {mostrada.estado === 'apagado' && <p className="muted">{t('session.off')}</p>}
      {mostrada.estado === 'error' && <p role="alert">{t('community.error')}</p>}
      {mostrada.estado === 'lista' && mostrada.historias.length === 0 && <p className="muted">{t('community.empty')}</p>}
      {mostrada.estado === 'lista' && (
        <ol className="comunidad-lista">
          {mostrada.historias.map((h) => (
            <li key={h.id}>
              <article aria-labelledby={`historia-${h.id}`}>
                <h4 id={`historia-${h.id}`}>{h.title}</h4>
                <p className="muted comunidad-meta">
                  <strong className="autoria">{h.author_alias}</strong>
                  {' · '}
                  {t('community.meta', { role: t(`community.role.${h.author_role}`), from: h.from_date, to: h.to_date })}
                  {' · '}
                  {t('community.pairs', { count: h.pairs.length })}
                  {' · '}
                  {t('community.downloads', { count: h.downloads })}
                </p>
                <ResumenEstrellas historia={h} />
                <div className="acciones">
                  <BotonIcono icono="abrir" etiqueta={t('community.open')} onClick={() => onAbrir(h)} />
                  <BotonIcono
                    icono="descargar"
                    etiqueta={t('community.download')}
                    disabled={ocupada === h.id}
                    onClick={async () => {
                      setOcupada(h.id)
                      await onDescargar(h)
                      setOcupada(null)
                      await cargar()
                    }}
                  />
                  {h.is_mine && (
                    <BotonIcono
                      icono="borrar"
                      etiqueta={t('community.delete')}
                      disabled={ocupada === h.id}
                      onClick={() => void borrar(h)}
                    />
                  )}
                </div>
                {token && !h.is_mine && (
                  <ValorarEstrellas
                    actual={h.my_stars}
                    ocupado={ocupada === h.id}
                    onValorar={(n) => void valorar(h, n)}
                    onQuitar={() => void valorar(h, null)}
                  />
                )}
                {token && h.is_mine && <p className="muted ayuda">{t('community.ownStory')}</p>}
              </article>
            </li>
          ))}
        </ol>
      )}
      {sesion.estado === 'anonima' && mostrada.estado === 'lista' && (
        <p className="muted ayuda">{t('community.loginToRate')}</p>
      )}
    </section>
  )
}
