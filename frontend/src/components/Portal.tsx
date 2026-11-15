import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Carrusel } from './Carrusel'
import { BotonIcono, Icono } from './Iconos'
import { Marca } from './Marca'
import { contenidoPortal } from './portalContenido'

export type SeccionPortal = 'inicio' | 'como' | 'ciencia' | 'datos' | 'cuenta'
const SECCIONES: SeccionPortal[] = ['inicio', 'como', 'ciencia', 'datos', 'cuenta']
const ESTADOS = ['change_probable', 'no_detectable_change', 'not_observable'] as const

/** Abre el diálogo como modal; sin `showModal` (jsdom, navegadores viejos), como no modal. */
function abrirDialogo(d: HTMLDialogElement | null) {
  if (!d || d.open) return
  if (typeof d.showModal === 'function') d.showModal()
  else d.setAttribute('open', '')
}

/**
 * Ventanas informativas del sitio (corrección de diseño del 2026-11-14): una ventana de vidrio líquido sobre el
 * mapa con cinco secciones en pestañas (Inicio, Cómo funciona, Radar y ciencia, Los datos y Tu cuenta), carruseles y las
 * ventajas de iniciar sesión. Es un `<dialog>` modal: atrapa el foco, Escape lo cierra y al cerrar el foco
 * vuelve al botón que lo abrió.
 */
export function Portal({
  abierta,
  seccion,
  onSeccion,
  onCerrar,
}: {
  abierta: boolean
  seccion: SeccionPortal
  onSeccion: (s: SeccionPortal) => void
  onCerrar: () => void
}) {
  const { t, i18n } = useTranslation()
  const c = contenidoPortal(i18n.language)
  const dialogo = useRef<HTMLDialogElement>(null)
  const id = useId()
  const [cerrando, setCerrando] = useState(false)

  useEffect(() => {
    const d = dialogo.current
    if (!d) return
    if (abierta) {
      abrirDialogo(d)
    } else if (d.open) {
      if (typeof d.close === 'function') d.close()
      else d.removeAttribute('open')
    }
  }, [abierta])

  // Cerrar con una salida breve (se encoge como una gota) antes de quitar el diálogo.
  function cerrar() {
    const reducido = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reducido) return onCerrar()
    setCerrando(true)
    window.setTimeout(() => {
      setCerrando(false)
      onCerrar()
    }, 220)
  }

  function teclasPestanas(e: KeyboardEvent<HTMLDivElement>) {
    const i = SECCIONES.indexOf(seccion)
    const sig = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : null
    if (sig === null) return
    e.preventDefault()
    const k = SECCIONES[(sig + SECCIONES.length) % SECCIONES.length]
    onSeccion(k)
    document.getElementById(`${id}-tab-${k}`)?.focus()
  }

  function pedirSesion(modo: 'entrar' | 'registrar') {
    onCerrar()
    // El formulario vive en SesionBoton; se abre en el siguiente ciclo, ya cerrado este diálogo.
    window.setTimeout(() => window.dispatchEvent(new CustomEvent('sar:abrir-sesion', { detail: modo })), 0)
  }

  return (
    <dialog
      ref={dialogo}
      className="portal"
      data-cerrando={cerrando}
      aria-labelledby={`${id}-titulo`}
      onCancel={(e) => {
        e.preventDefault()
        cerrar()
      }}
      onClick={(e) => {
        // Clic en el velo (fuera de la ventana) cierra.
        if (e.target === e.currentTarget) cerrar()
      }}
    >
      <div className="portal-ventana vidrio">
        <header className="portal-cabecera">
          <p className="portal-marca" id={`${id}-titulo`}>
            <span>GeoLatido</span>
            <span className="app-separador" aria-hidden="true" />
            <Icono nombre="satelite" tamano={20} />
            <span className="sr-solo">{t('portal.title')}</span>
          </p>
          <div role="tablist" aria-label={t('portal.sections')} className="portal-pestanas" onKeyDown={teclasPestanas}>
            {SECCIONES.map((k) => (
              <button
                key={k}
                id={`${id}-tab-${k}`}
                type="button"
                role="tab"
                aria-selected={seccion === k}
                aria-controls={`${id}-panel`}
                tabIndex={seccion === k ? 0 : -1}
                onClick={() => onSeccion(k)}
              >
                {c.secciones[k]}
              </button>
            ))}
          </div>
          <BotonIcono icono="cerrar" etiqueta={t('portal.close')} onClick={cerrar} className="portal-cerrar" />
        </header>

        <div
          id={`${id}-panel`}
          key={seccion}
          role="tabpanel"
          aria-labelledby={`${id}-tab-${seccion}`}
          className="portal-cuerpo"
          tabIndex={-1}
        >
          {seccion === 'inicio' && (
            <>
              <section className="portal-heroe">
                <p className="portal-antetitulo">{c.inicio.antetitulo}</p>
                <h2>{c.inicio.titulo}</h2>
                <p className="portal-entrada">{c.inicio.entrada}</p>
                <div className="portal-acciones">
                  <button type="button" className="boton-principal" onClick={cerrar}>
                    <Icono nombre="mapa" tamano={18} />
                    {c.inicio.empezar}
                  </button>
                  <button type="button" onClick={() => onSeccion('ciencia')}>
                    <Icono nombre="satelite" tamano={18} />
                    {c.secciones.ciencia}
                  </button>
                  <button type="button" onClick={() => onSeccion('cuenta')}>
                    <Icono nombre="cuenta" tamano={18} />
                    {c.secciones.cuenta}
                  </button>
                </div>
              </section>
              <ul className="portal-cifras">
                {c.inicio.cifras.map((x) => (
                  <li key={x.texto} className="portal-tarjeta">
                    <strong>{x.valor}</strong>
                    <span>{x.texto}</span>
                  </li>
                ))}
              </ul>
              <Carrusel diapositivas={c.inicio.carrusel} etiqueta={c.secciones.inicio} />
            </>
          )}

          {seccion === 'como' && (
            <>
              <section className="portal-heroe portal-heroe-corto">
                <h2>{c.como.titulo}</h2>
                <p className="portal-entrada">{c.como.entrada}</p>
              </section>
              <Carrusel diapositivas={c.como.carrusel} etiqueta={c.como.titulo} />
              <h3 className="portal-subtitulo">{c.como.estadosTitulo}</h3>
              <ul className="portal-estados">
                {c.como.estados.map((x, i) => (
                  <li key={x.titulo} className="portal-tarjeta">
                    <Marca estado={ESTADOS[i]} />
                    <div>
                      <strong>{x.titulo}</strong>
                      <span>{x.texto}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}

          {seccion === 'ciencia' && (
            <>
              <section className="portal-heroe portal-heroe-corto">
                <h2>{c.ciencia.titulo}</h2>
                <p className="portal-entrada">{c.ciencia.entrada}</p>
              </section>
              <ul className="portal-ventajas portal-ventajas-anchas" aria-label={c.ciencia.titulo}>
                {c.ciencia.mide.map((v, i) => (
                  <li key={v.titulo} className="portal-tarjeta" style={{ animationDelay: `${i * 60}ms` }}>
                    <span className="portal-ventaja-icono" aria-hidden="true">
                      <Icono nombre={v.icono} tamano={22} />
                    </span>
                    <p className="carrusel-antetitulo">{v.antetitulo}</p>
                    <strong>{v.titulo}</strong>
                    <span>{v.texto}</span>
                    {v.puntos && (
                      <ul className="portal-puntos">
                        {v.puntos.map((x) => (
                          <li key={x}>{x}</li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>

              <h3 className="portal-subtitulo">{c.ciencia.polTitulo}</h3>
              <p className="portal-entrada">{c.ciencia.polEntrada}</p>
              <div className="portal-tabla-caja">
                <table className="portal-tabla portal-tabla-texto">
                  <thead>
                    <tr>
                      {c.ciencia.polColumnas.map((x) => (
                        <th key={x} scope="col">
                          {x}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {c.ciencia.polarizaciones.map((p) => (
                      <tr key={p.codigo}>
                        <th scope="row">{p.codigo}</th>
                        <td>{p.resalta}</td>
                        <td>{p.disponible}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <h3 className="portal-subtitulo">{c.ciencia.polParral.titulo}</h3>
              <ul className="portal-cifras">
                {c.ciencia.polParral.cifras.map((x) => (
                  <li key={x.valor} className="portal-tarjeta">
                    <strong>{x.valor}</strong>
                    <span>{x.texto}</span>
                  </li>
                ))}
              </ul>
              <p className="portal-nota portal-tarjeta">
                <Icono nombre="capas" tamano={18} />
                <span>{c.ciencia.polParral.lectura}</span>
              </p>

              <h3 className="portal-subtitulo">{c.ciencia.zona.titulo}</h3>
              <div className="portal-tarjeta portal-bloque">
                <p>{c.ciencia.zona.texto}</p>
                <ul>
                  {c.ciencia.zona.puntos.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              </div>

              <h3 className="portal-subtitulo">{c.ciencia.bloquesTitulo}</h3>
              <ul className="portal-ventajas portal-ventajas-anchas">
                {c.ciencia.bloques.map((v, i) => (
                  <li key={v.titulo} className="portal-tarjeta" style={{ animationDelay: `${i * 60}ms` }}>
                    <span className="portal-ventaja-icono" aria-hidden="true">
                      <Icono nombre={v.icono} tamano={22} />
                    </span>
                    <p className="carrusel-antetitulo">{v.antetitulo}</p>
                    <strong>{v.titulo}</strong>
                    <span>{v.texto}</span>
                    {v.puntos && (
                      <ul className="portal-puntos">
                        {v.puntos.map((x) => (
                          <li key={x}>{x}</li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
              <p className="portal-nota portal-tarjeta">
                <Icono nombre="info" tamano={18} />
                <span>{c.ciencia.nota}</span>
              </p>
            </>
          )}

          {seccion === 'datos' && (
            <>
              <section className="portal-heroe portal-heroe-corto">
                <h2>{c.datos.titulo}</h2>
                <p className="portal-entrada">{c.datos.entrada}</p>
              </section>
              <Carrusel diapositivas={c.datos.carrusel} etiqueta={c.datos.titulo} />
              <p className="portal-nota portal-tarjeta">
                <Icono nombre="info" tamano={18} />
                <span>{c.datos.honestidad}</span>
              </p>

              <h3 className="portal-subtitulo">{c.creditos.creditosTitulo}</h3>
              <div className="portal-tabla-caja">
                <table className="portal-tabla portal-tabla-texto">
                  <thead>
                    <tr>
                      {c.creditos.columnas.map((x) => (
                        <th key={x} scope="col">
                          {x}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {c.creditos.creditos.map((f) => (
                      <tr key={f.datos}>
                        <th scope="row">{f.datos}</th>
                        <td>{f.quien}</td>
                        <td>{f.licencia}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="portal-nota portal-tarjeta">
                <Icono nombre="recibo" tamano={18} />
                <span>{c.creditos.licencia}</span>
              </p>

              <h3 className="portal-subtitulo">{c.creditos.privacidadTitulo}</h3>
              <p className="portal-entrada">{c.creditos.privacidadEntrada}</p>
              <ul className="portal-ventajas portal-ventajas-anchas">
                {c.creditos.privacidad.map((v) => (
                  <li key={v.titulo} className="portal-tarjeta">
                    <strong>{v.titulo}</strong>
                    <span>{v.texto}</span>
                  </li>
                ))}
              </ul>
            </>
          )}

          {seccion === 'cuenta' && (
            <>
              <section className="portal-heroe portal-heroe-corto">
                <h2>{c.cuenta.titulo}</h2>
                <p className="portal-entrada">{c.cuenta.entrada}</p>
                <div className="portal-acciones">
                  <button type="button" className="boton-principal" onClick={() => pedirSesion('registrar')}>
                    <Icono nombre="cuenta" tamano={18} />
                    {c.cuenta.crear}
                  </button>
                  <button type="button" onClick={() => pedirSesion('entrar')}>
                    <Icono nombre="entrar" tamano={18} />
                    {c.cuenta.entrar}
                  </button>
                </div>
              </section>
              <ul className="portal-ventajas">
                {c.cuenta.ventajas.map((v, i) => (
                  <li key={v.titulo} className="portal-tarjeta" style={{ animationDelay: `${i * 60}ms` }}>
                    <span className="portal-ventaja-icono" aria-hidden="true">
                      <Icono nombre={v.icono} tamano={22} />
                    </span>
                    <p className="carrusel-antetitulo">{v.antetitulo}</p>
                    <strong>{v.titulo}</strong>
                    <span>{v.texto}</span>
                  </li>
                ))}
              </ul>
              <h3 className="portal-subtitulo">{c.cuenta.tablaTitulo}</h3>
              <div className="portal-tabla-caja">
                <table className="portal-tabla">
                  <thead>
                    <tr>
                      <th scope="col">
                        <span className="sr-solo">{t('portal.feature')}</span>
                      </th>
                      {c.cuenta.columnas.map((x) => (
                        <th key={x} scope="col">
                          {x}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {c.cuenta.filas.map((f) => (
                      <tr key={f.que}>
                        <th scope="row">{f.que}</th>
                        {[f.publico, f.estudiante, f.investigacion].map((v, i) => (
                          <td key={i}>
                            {v === true ? (
                              <span className="portal-si" role="img" aria-label={t('portal.yes')}>
                                ✓
                              </span>
                            ) : v === false ? (
                              <span className="portal-no" role="img" aria-label={t('portal.no')}>
                                —
                              </span>
                            ) : (
                              <span className="portal-detalle">{v}</span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="portal-nota portal-tarjeta">
                <Icono nombre="info" tamano={18} />
                <span>{c.cuenta.nota}</span>
              </p>
            </>
          )}
        </div>
      </div>
    </dialog>
  )
}
