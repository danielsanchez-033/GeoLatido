import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { API_BASE, absoluteTileUrl, verdictJsonUrl, verdictsApi, type Lang, type SeriesInfo, type Verdict } from './api/client'
import { mapOptionsFor, type VerdictMapOptions } from './api/mapOptions'
import {
  ESTADOS,
  buscar,
  claveVeredicto,
  descargarTexto,
  markdownHistoria,
  nombreArchivo,
  type Filtro,
  type Historia,
  type HistoriaNueva,
} from './comunidad/historias'
import { AtlasMap } from './components/AtlasMap'
import { Espacio } from './components/Espacio'
import { Mundo, type GranuloMundo } from './components/Mundo'
import type { Bbox, MundoMapa } from './mapa/tipos'
import { Portal, type SeccionPortal } from './components/Portal'
import { Buscador } from './components/Buscador'
import { Comunidad } from './components/Comunidad'
import { EventQuery } from './components/EventQuery'
import { Evidencia } from './components/Evidencia'
import { Hundimiento } from './components/Hundimiento'
import { Regenerar } from './components/Regenerar'
import { Bienvenida } from './components/Bienvenida'
import { useHundimiento } from './api/hundimiento'
import { Interprete } from './components/Interprete'
import { BuscadorLugares, type Lugar } from './components/BuscadorLugares'
import { zonaParaLugar } from './api/zonaLugar'
import { Investigacion } from './components/Investigacion'
import { BarraRecogible, BotonRecoger, CabeceraPanel } from './components/Barra'
import { useCierreAnimado } from './components/useCierreAnimado'
import { Esqueleto } from './components/Esqueleto'
import { BotonIcono, Icono, type NombreIcono } from './components/Iconos'
import { LanguageSwitch } from './components/LanguageSwitch'
import { LeyendaEstados } from './components/Marca'
import { Reproductor } from './components/Reproductor'
import { SesionBoton } from './components/SesionBoton'
import { HistoriaZona, type ZonaHistoria } from './components/HistoriaZona'
import { ProcesadoZona, ResumenPares, type ResumenProcesado } from './components/ProcesadoZona'
import { SyntheticBanner } from './components/SyntheticBadge'
import { VerdictCard } from './components/VerdictCard'
import { authApi, detalle, useSesion } from './sesion/sesion'
import { SesionProvider } from './sesion/SesionProvider'
import { VistaProvider } from './vista/VistaContexto'
import type { CapaRadar } from './mapa/tipos'

type Load =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; zonas: Zona[] }

/** Zona con veredictos procesados: su id, su nombre (de catalog si responde) y la caja de sus series. */
type Zona = { aoi: string; nombre: string; bbox: Bbox; series: SeriesInfo[] }

/** Veredictos de todas las series, con el idioma en que se pidieron. */
type Todos = { aoi: string; lang: Lang; status: 'ready' | 'error'; items: Verdict[]; fallidas: string[] }

/** Pestañas de la barra derecha (T-FAR-21, RF-INT-27). */
type PestanaDer = 'hallazgos' | 'historia' | 'evento' | 'comunidad' | 'investigacion'
const PESTANAS_DER: PestanaDer[] = ['hallazgos', 'historia', 'evento', 'investigacion', 'comunidad']
const ICONO_PESTANA: Record<PestanaDer, NombreIcono> = {
  hallazgos: 'hallazgos',
  historia: 'historia',
  evento: 'evento',
  comunidad: 'comunidad',
  investigacion: 'interprete',
}
const CAPAS: CapaRadar[] = ['state', 'change_hh', 'change_hv', 'subsidence']

/** Milisegundos que se queda cada par al reproducir una historia (RF-INT-30). */
const PASO_REPRODUCCION = 4000

/** Pantalla estrecha (móvil): las barras empiezan recogidas y solo una lateral a la vez (RF-INT-26). */
function pantallaEstrecha(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 40rem)').matches
}

type Reproduccion = { titulo: string; claves: string[]; indice: number; enMarcha: boolean }

async function loadSeries(): Promise<Load> {
  const aois = await verdictsApi.GET('/aois')
  if (!aois.data) return { status: 'error' }
  // Sin zonas procesadas (con token no hay datos sintéticos de Parral): la API responde y se busca un lugar.
  if (!aois.data.length) return { status: 'ready', zonas: [] }
  // Nombres legibles de catalog; si no responde, se usa el id de la zona.
  const nombres = new Map<string, string>()
  try {
    const r = await globalThis.fetch(`${API_BASE}/api/catalog/aois`)
    if (r.ok) for (const a of (await r.json()) as { id: string; name: string }[]) nombres.set(a.id, a.name)
  } catch {
    // sin nombres
  }
  const zonas: Zona[] = []
  for (const aoi of aois.data) {
    const series = await verdictsApi.GET('/aois/{aoi}/series', { params: { path: { aoi } } })
    if (!series.data?.length) continue
    const b = series.data.map((x) => x.bbox)
    const bbox: Bbox = [Math.min(...b.map((x) => x[0])), Math.min(...b.map((x) => x[1])), Math.max(...b.map((x) => x[2])), Math.max(...b.map((x) => x[3]))]
    zonas.push({ aoi, nombre: nombres.get(aoi) ?? aoi, bbox, series: series.data })
  }
  return { status: 'ready', zonas }
}


/** Primer par consecutivo de la primera serie; si no hay, el primero que haya. */
function defaultPair(items: Verdict[], series: SeriesInfo[]): Verdict | undefined {
  const primera = items.filter((v) => v.series === series[0]?.id)
  return primera.find((v) => v.kind === 'consecutive') ?? primera[0] ?? items[0]
}

export default function App() {
  return (
    <SesionProvider>
      <VistaProvider>
        <Contenido />
      </VistaProvider>
    </SesionProvider>
  )
}

/**
 * Pestañas verticales de la barra derecha (patrón ARIA de pestañas, orientación vertical): flechas arriba y
 * abajo cambian de pestaña. Pulsar la activa con el panel abierto lo recoge (RF-INT-27).
 */
function PestanasDer({
  activa,
  abierta,
  onElegir,
}: {
  activa: PestanaDer
  abierta: boolean
  onElegir: (k: PestanaDer) => void
}) {
  const { t } = useTranslation()
  function teclas(e: KeyboardEvent<HTMLDivElement>) {
    const i = PESTANAS_DER.indexOf(activa)
    const sig = e.key === 'ArrowDown' ? i + 1 : e.key === 'ArrowUp' ? i - 1 : null
    if (sig === null) return
    e.preventDefault()
    const k = PESTANAS_DER[(sig + PESTANAS_DER.length) % PESTANAS_DER.length]
    onElegir(k)
    document.getElementById(`derecha-tab-${k}`)?.focus()
  }
  return (
    <div role="tablist" aria-label={t('layout.right')} aria-orientation="vertical" className="pestanas-der" onKeyDown={teclas}>
      {PESTANAS_DER.map((k) => (
        <button
          key={k}
          id={`derecha-tab-${k}`}
          type="button"
          role="tab"
          aria-selected={abierta && activa === k}
          aria-controls={`derecha-panel-${k}`}
          aria-expanded={abierta && activa === k}
          tabIndex={activa === k ? 0 : -1}
          data-etiqueta={t(`layout.tabs.${k}`)}
          onClick={() => onElegir(k)}
        >
          {/* Solo icono a la vista; el nombre de la pestaña lo lee el lector de pantalla. */}
          <Icono nombre={ICONO_PESTANA[k]} tamano={22} />
          <span className="sr-solo">{t(`layout.tabs.${k}`)}</span>
        </button>
      ))}
    </div>
  )
}

function PanelPestana({ clave, activa, children }: { clave: PestanaDer; activa: PestanaDer; children: ReactNode }) {
  return (
    <div
      role="tabpanel"
      id={`derecha-panel-${clave}`}
      aria-labelledby={`derecha-tab-${clave}`}
      hidden={activa !== clave}
      className="panel-pestana"
    >
      {children}
    </div>
  )
}

function Contenido() {
  const { t, i18n } = useTranslation()
  // Desde el 2026-11-14 todo se ve igual con o sin sesión (decisión del usuario): la evidencia explicada y en
  // tabla, el enlace al JSON, las capas y el comparador. La cuenta solo sirve para publicar, valorar y borrar
  // historias, que salen con el seudónimo y el perfil de quien las escribe.
  const { cabeceras } = useSesion()
  const publica = false
  const lang: Lang = i18n.language === 'en' ? 'en' : 'es'

  const [state, setState] = useState<Load>({ status: 'loading' })
  const [todos, setTodos] = useState<Todos>()
  // Buscador mundial (pestaña Mundo): lo que se ve del mapa, las pasadas encontradas y la elegida.
  const [vistaMapa, setVistaMapa] = useState<Bbox | null>(null)
  const [granulosMundo, setGranulosMundo] = useState<GranuloMundo[]>([])
  const [elegidoMundo, setElegidoMundo] = useState<string | null>(null)
  const [volarMundo, setVolarMundo] = useState<{ bbox: Bbox } | null>(null)
  const mundoMapa = useMemo<MundoMapa | null>(() => {
    if (granulosMundo.length === 0) return null
    const elegido = granulosMundo.find((g) => g.id === elegidoMundo)
    return {
      huellas: {
        type: 'FeatureCollection',
        features: granulosMundo
          .filter((g) => g.footprint.length >= 4)
          .map((g) => ({ type: 'Feature', properties: { id: g.id }, geometry: { type: 'Polygon', coordinates: [g.footprint] } })),
      },
      elegido: elegidoMundo,
      vista: elegido?.browse_url && elegido.bbox ? { url: elegido.browse_url, bbox: elegido.bbox as Bbox } : null,
    }
  }, [granulosMundo, elegidoMundo])

  const [filtro, setFiltro] = useState<Filtro>({ series: 'all', desde: '', hasta: '', estados: [...ESTADOS], ventanas: false })
  const [seleccion, setSeleccion] = useState<string>()
  const [pestanaDer, setPestanaDer] = useState<PestanaDer>('hallazgos')
  const [abierta, setAbierta] = useState<Historia | null>(null)
  const [version, setVersion] = useState(0)

  // Barras recogibles (RF-INT-26): en escritorio abren Filtros y Hallazgos; en móvil, todas recogidas.
  const [estrecha] = useState(pantallaEstrecha)
  const [barraArriba, setBarraArriba] = useState(true)
  const [barraAbajo, setBarraAbajo] = useState(true)
  const [barraIzq, setBarraIzq] = useState(!estrecha)
  const [barraDer, setBarraDer] = useState(!estrecha)
  // En pantalla estrecha cada lateral ocupa el ancho: abrir una recoge la otra.
  const abrirIzq = (a: boolean) => {
    setBarraIzq(a)
    if (a && pantallaEstrecha()) setBarraDer(false)
  }
  const abrirDer = (a: boolean) => {
    setBarraDer(a)
    if (a && pantallaEstrecha()) setBarraIzq(false)
  }
  // El panel derecho también se encoge al cerrarse (2026-11-15).
  const cierreDer = useCierreAnimado(barraDer)
  // El panel nace de la pestaña que se pulsa y vuelve a ella al cerrarse: su transform-origin es el centro de la
  // pestaña activa. Se mide antes de pintar, con offset* (no les afecta la escala de la animación).
  useLayoutEffect(() => {
    const panel = document.getElementById('panel-der')
    const tab = document.getElementById(`derecha-tab-${pestanaDer}`)
    const lista = tab?.parentElement
    if (!panel || !tab || !lista) return
    const x = lista.offsetLeft + tab.offsetLeft + tab.offsetWidth / 2 - panel.offsetLeft
    const y = lista.offsetTop + tab.offsetTop + tab.offsetHeight / 2 - panel.offsetTop
    panel.style.setProperty('--origen-x', `${x}px`)
    panel.style.setProperty('--origen-y', `${y}px`)
  }, [pestanaDer, barraDer])
  function elegirPestanaDer(k: PestanaDer) {
    if (barraDer && k === pestanaDer) return abrirDer(false)
    setPestanaDer(k)
    abrirDer(true)
  }

  // Herramientas del mapa (RF-INT-28).
  const [modo3d, setModo3d] = useState(true)
  const [capa, setCapa] = useState<CapaRadar>('state')
  const [opacidad, setOpacidad] = useState(0.85)
  const [encuadre, setEncuadre] = useState(0)
  const [comparar, setComparar] = useState(false)
  const [capasAbiertas, setCapasAbiertas] = useState(false)
  const [completa, setCompleta] = useState(false)
  useEffect(() => {
    const alCambiar = () => setCompleta(Boolean(document.fullscreenElement))
    document.addEventListener('fullscreenchange', alCambiar)
    return () => document.removeEventListener('fullscreenchange', alCambiar)
  }, [])
  function pantallaCompleta() {
    if (document.fullscreenElement) void document.exitFullscreen?.()
    else void document.documentElement.requestFullscreen?.().catch(() => {})
  }

  // Reproducción de una historia de la comunidad (RF-INT-30).
  const [reproduccion, setReproduccion] = useState<Reproduccion | null>(null)

  useEffect(() => {
    loadSeries()
      .then(setState)
      .catch(() => setState({ status: 'error' }))
  }, [])

  // Zona de los filtros (2026-11-15): sin lugar buscado, la primera zona con veredictos; con uno, la zona procesada
  // que lo toca o, si ninguna, sus pasadas de NISAR (modo mundo). Los veredictos siguen cargados para el mapa.
  const [lugar, setLugar] = useState<Lugar | null>(null)
  // Un punto elegido con un clic en el mapa (2026-11-15): no se procesa solo, y la historia y la investigación son suyas.
  const esPunto = lugar?.source === 'map-click'
  const [semilla, setSemilla] = useState<Lugar | null>(null)
  const zonas = useMemo(() => (state.status === 'ready' ? state.zonas : []), [state])
  const zonaDelLugar = lugar ? zonaParaLugar(zonas, lugar) : undefined
  const [zonaVeredictos, setZonaVeredictos] = useState<string>()
  const zona = zonas.find((z) => z.aoi === zonaVeredictos) ?? zonas[0]
  const modoMundo = Boolean(lugar && !zonaDelLugar)
  // Zona de la pestaña Historia: el lugar buscado si no tiene veredictos; si no, la zona con veredictos en pantalla.
  const zonaHistoria: ZonaHistoria | null = (modoMundo || esPunto) && lugar
    ? { id: lugar.id === 'vista' ? `vista-${lugar.bbox.map((v) => v.toFixed(2)).join('_')}` : lugar.id, name: lugar.name, bbox: lugar.bbox }
    : zona
      ? { id: zona.aoi, name: zona.nombre, bbox: zona.bbox }
      : null
  // Resumen ligero del procesado en línea: Hallazgos lo enseña mientras llegan los veredictos de la zona nueva.
  const [resumenOnline, setResumenOnline] = useState<{ aoi: string; resumen: ResumenProcesado } | null>(null)
  // El procesado en línea terminó: se recargan las zonas y la nueva pasa a tener veredictos.
  function zonaProcesada(nueva: string, bbox: Bbox, resumen: ResumenProcesado | null) {
    setResumenOnline(resumen ? { aoi: nueva, resumen } : null)
    loadSeries()
      .then((st) => {
        setState(st)
        setZonaVeredictos(nueva)
        setLugar(null)
        setGranulosMundo([])
        setElegidoMundo(null)
        setVolarMundo({ bbox })
      })
      .catch(() => undefined)
  }
  const aoi = zona?.aoi
  const series = useMemo(() => zona?.series ?? [], [zona])
  function irALugar(l: Lugar) {
    setLugar(l)
    const z = zonaParaLugar(zonas, l)
    if (z) setZonaVeredictos(z.aoi)
    setVolarMundo({ bbox: l.bbox })
    setGranulosMundo([])
    setElegidoMundo(null)
    abrirIzq(true)
    // Hallazgos sigue a la zona elegida: sus veredictos o, sin ellos, el procesado en línea con su avance.
    setPestanaDer('hallazgos')
    abrirDer(true)
  }

  // Nombre del lugar del último punto elegido (geocodificación inversa de research), para la ventana del mapa.
  const [rotulo, setRotulo] = useState<{ lon: number; lat: number; nombre: string } | null>(null)
  const pidiendoNombre = useRef<AbortController | null>(null)

  // Un clic en el mapa cambia la zona de Filtros a ese punto (caja de ±0,05°), sin mover el mapa.
  function irAPunto(p: { lon: number; lat: number }) {
    const r = (v: number) => Math.round(v * 1e5) / 1e5
    const bbox: Bbox = [r(p.lon - 0.05), r(p.lat - 0.05), r(p.lon + 0.05), r(p.lat + 0.05)]
    const l: Lugar = {
      id: `punto_${p.lat.toFixed(4)}_${p.lon.toFixed(4)}`,
      name: t('places.point', { lat: p.lat.toFixed(4), lon: p.lon.toFixed(4) }),
      bbox,
      source: 'map-click',
    }
    setLugar(l)
    setSemilla(l)
    setRotulo(null)
    // El nombre del lugar llega después (Nominatim, a través de research) y se añade a las coordenadas. Si mientras
    // tanto se elige otro punto, la respuesta vieja se descarta.
    pidiendoNombre.current?.abort()
    const control = new AbortController()
    pidiendoNombre.current = control
    const q = new URLSearchParams({ lat: String(p.lat), lon: String(p.lon), lang })
    fetch(`${API_BASE}/api/research/places/reverse?${q}`, { signal: control.signal })
      .then((r) => (r.ok ? (r.json() as Promise<{ place: { name: string } | null }>) : null))
      .then((d) => {
        if (control.signal.aborted || !d?.place?.name) return
        const nombrado = { ...l, name: t('places.pointNamed', { place: d.place.name, lat: p.lat.toFixed(4), lon: p.lon.toFixed(4) }) }
        setLugar((actual) => (actual?.id === l.id ? nombrado : actual))
        setSemilla((actual) => (actual?.id === l.id ? nombrado : actual))
        setRotulo({ lon: p.lon, lat: p.lat, nombre: d.place.name })
      })
      .catch(() => undefined)
    const z = zonaParaLugar(zonas, l)
    if (z) setZonaVeredictos(z.aoi)
    setGranulosMundo([])
    setElegidoMundo(null)
    // Como con el buscador: Hallazgos enseña la carga de los veredictos o el botón para procesar el punto.
    setPestanaDer('hallazgos')
    abrirDer(true)
  }

  // Veredictos de todas las series. Se vuelven a pedir al cambiar de idioma: los textos llegan con `lang`.
  useEffect(() => {
    if (!aoi || series.length === 0) return
    let current = true
    Promise.all(
      series.map((s) =>
        verdictsApi
          .GET('/aois/{aoi}/series/{series_id}/verdicts', { params: { path: { aoi, series_id: s.id }, query: { lang } } })
          .then(({ data }) => ({ id: s.id, data }))
          .catch(() => ({ id: s.id, data: undefined })),
      ),
    ).then((rs) => {
      if (!current) return
      const items = rs.flatMap((r) => r.data ?? [])
      const fallidas = rs.filter((r) => !r.data).map((r) => r.id)
      setTodos({ aoi, lang, status: fallidas.length === rs.length ? 'error' : 'ready', items, fallidas })
      setSeleccion((prev) => (prev && items.some((v) => claveVeredicto(v) === prev) ? prev : (() => {
        const d = defaultPair(items, series)
        return d && claveVeredicto(d)
      })()))
    })
    return () => {
      current = false
    }
  }, [aoi, series, lang])

  // Mientras llega la respuesta en otro idioma, el mapa y la lista siguen con la anterior (tapados).
  // Al cambiar de zona, los veredictos de la anterior no se enseñan en Hallazgos mientras llegan los nuevos.
  const deOtraZona = Boolean(todos && todos.aoi !== aoi)
  const cargando = !todos || todos.lang !== lang || deOtraZona
  const items = useMemo(() => todos?.items ?? [], [todos])
  const porClave = useMemo(() => new Map(items.map((v) => [claveVeredicto(v), v])), [items])
  const resultados = useMemo(() => buscar(items, filtro), [items, filtro])
  // Mientras se reproduce una historia, el par elegido es el que toca; la barra derecha se queda en la historia.
  const claveReproducida = reproduccion?.claves[reproduccion.indice]
  const elegida = claveReproducida ?? seleccion
  const verdict = elegida ? porClave.get(elegida) : undefined
  const verdictSeries = series.find((s) => s.id === verdict?.series)
  const synthetic = series.some((s) => s.data_kind === 'synthetic') || verdict?.receipt.data_kind === 'synthetic'

  // Hundimiento con NISAR GUNW, si la zona lo tiene: tarjeta en Hallazgos y cuarta capa del mapa.
  const hundimiento = useHundimiento(aoi, lang)
  const tilesHundimiento = hundimiento?.tiles ? absoluteTileUrl(hundimiento.tiles) : undefined
  const capas = tilesHundimiento ? CAPAS : CAPAS.filter((c) => c !== 'subsidence')
  // Si la zona nueva no tiene hundimiento, el mapa vuelve al estado sin tocar la elección guardada.
  const capaVisible: CapaRadar = capa === 'subsidence' && !tilesHundimiento ? 'state' : capa

  // El último mapa con veredicto sigue en pantalla mientras llegan los de otra zona (marcado como «cargando»): sin
  // esto, al elegir un punto o terminar un procesado el mapa desaparecía hasta tenerlo todo.
  const [ultimoMapa, setUltimoMapa] = useState<{ options: VerdictMapOptions; verdict: Verdict } | null>(null)
  const mapOptions = useMemo(() => {
    const o = aoi && verdictSeries && verdict ? mapOptionsFor(aoi, verdictSeries, verdict, lang) : null
    return o && tilesHundimiento ? { ...o, layers: { ...o.layers, subsidence: tilesHundimiento } } : o
  }, [aoi, verdictSeries, verdict, lang, tilesHundimiento])
  if (mapOptions && verdict && (ultimoMapa?.options !== mapOptions || ultimoMapa.verdict !== verdict)) {
    setUltimoMapa({ options: mapOptions, verdict })
  }
  const mapaEnPantalla = mapOptions && verdict ? { options: mapOptions, verdict } : ultimoMapa

  // Elegir un par lo enseña en el mapa y abre Hallazgos con su tarjeta.
  function seleccionar(v: Verdict) {
    setSeleccion(claveVeredicto(v))
    setPestanaDer('hallazgos')
    abrirDer(true)
  }

  function reproducir(pares: Verdict[]) {
    const orden = [...pares].sort((x, y) => x.from_date.localeCompare(y.from_date) || x.to_date.localeCompare(y.to_date))
    if (!orden.length || !abierta) return
    setReproduccion({ titulo: abierta.title, claves: orden.map(claveVeredicto), indice: 0, enMarcha: true })
  }

  // Al cerrar, el último par reproducido se queda elegido.
  function cerrarReproduccion() {
    if (claveReproducida) setSeleccion(claveReproducida)
    setReproduccion(null)
  }

  useEffect(() => {
    if (!reproduccion?.enMarcha) return
    const id = window.setTimeout(() => {
      setReproduccion((r) =>
        !r ? r : r.indice < r.claves.length - 1 ? { ...r, indice: r.indice + 1 } : { ...r, enMarcha: false },
      )
    }, PASO_REPRODUCCION)
    return () => window.clearTimeout(id)
  }, [reproduccion])
  const paresReproducidos = useMemo(
    () => (reproduccion ? reproduccion.claves.flatMap((k) => porClave.get(k) ?? []) : []),
    [reproduccion, porClave],
  )


  const guardar = useCallback(
    async (h: HistoriaNueva): Promise<string | null> => {
      const { data, error } = await authApi.POST('/stories', { body: h, headers: cabeceras() })
      if (!data) return detalle(error) ?? t('community.error')
      setVersion((n) => n + 1)
      return null
    },
    [cabeceras, t],
  )

  const descargar = useCallback(
    async (h: HistoriaNueva | Historia, pares: Verdict[]) => {
      let datos: HistoriaNueva | Historia = h
      if ('id' in h) {
        // Una historia guardada cuenta la descarga en auth (RF-ACC-14) y se descarga como está guardada.
        const { data } = await authApi.POST('/stories/{story_id}/download', {
          params: { path: { story_id: h.id } },
          headers: cabeceras(),
        })
        if (data) datos = data
      }
      const lista = datos.pairs.map((p) => ({ par: p, veredicto: pares.find((v) => v.series === p.series && v.id === p.pair) ?? porClave.get(`${p.series}/${p.pair}`) }))
      descargarTexto(nombreArchivo(datos.title), markdownHistoria(datos, lista, t, lang, new Date()))
    },
    [cabeceras, lang, porClave, t],
  )

  function abrirHistoria(h: Historia) {
    setAbierta(h)
    setReproduccion(null)
    setPestanaDer('comunidad')
    setFiltro((f) => ({ ...f, series: h.series, desde: h.from_date, hasta: h.to_date }))
  }

  // Ventanas informativas (components/Portal.tsx): desde «Acerca de GeoLatido». La primera visita ya no abre el
  // portal entero (con «Tu cuenta» en primer plano parecía un registro obligatorio), sino una bienvenida breve.
  const [portal, setPortal] = useState(false)
  const [bienvenida, setBienvenida] = useState(() => {
    if (import.meta.env.MODE === 'test') return false
    try {
      return localStorage.getItem('portal-visto') !== '1'
    } catch {
      return false
    }
  })
  function marcarVisto() {
    try {
      localStorage.setItem('portal-visto', '1')
    } catch {
      // Sin almacenamiento, la bienvenida volverá a salir en la próxima visita.
    }
  }
  const [seccionPortal, setSeccionPortal] = useState<SeccionPortal>('inicio')
  function cerrarPortal() {
    setPortal(false)
    marcarVisto()
  }
  function cerrarBienvenida(conocerMas: boolean) {
    setBienvenida(false)
    marcarVisto()
    if (conocerMas) {
      setSeccionPortal('inicio')
      setPortal(true)
    }
  }

  const intro = (
    <section className="intro-publico" aria-labelledby="intro-heading">
      <h2 id="intro-heading">{t('public.question')}</h2>
      <p className="intro-lead">{t('public.lead')}</p>
      <LeyendaEstados />
    </section>
  )

  const listo = state.status === 'ready' && aoi
  const estadoApi = state.status === 'ready' ? 'online' : state.status === 'error' ? 'offline' : 'connecting'

  return (
    <div
      className="app-vidrio"
      data-izq={barraIzq}
      data-der={barraDer}
      data-arriba={barraArriba}
      data-abajo={barraAbajo}
      data-reproduciendo={Boolean(reproduccion)}
    >
      <a className="skip-link" href="#main">
        {t('app.skipToMain')}
      </a>

      {/* Barra superior: marca, buscador de ubicación (próximamente), estado de la API, idioma y cuenta. */}
      {/* Sin losa de vidrio: marca suelta, buscador y controles en piezas de vidrio líquido (como el prototipo). */}
      <BarraRecogible
        lado="arriba"
        id="barra-arriba"
        nombre={t('layout.top')}
        abierta={barraArriba}
        onCambiar={setBarraArriba}
        vidrio={false}
      >
        <header className="app-header">
          {/* Marca mínima: «GeoLatido» y el satélite (nombre del proyecto desde el 2026-11-15; antes «SAR»). */}
          <div className="app-marca">
            <h1>GeoLatido</h1>
            <span className="app-separador" aria-hidden="true" />
            <Icono nombre="satelite" tamano={22} />
          </div>
          {/* Buscador de lugares (2026-11-15): sustituye a la pestaña Mundo; el lugar elegido manda en Filtros. */}
          <BuscadorLugares vista={vistaMapa} onElegir={irALugar} />
          {/* Solo idioma y cuenta: la vista sale del perfil de la sesión y el tema es oscuro (specs/08-interfaz). */}
          <div className="app-controls">
            <p className="estado-api" data-estado={estadoApi} role="status">
              <span className="estado-api-punto" aria-hidden="true" />
              {t(`status.${estadoApi}`)}
            </p>
            <BotonIcono
              icono="info"
              etiqueta={t('portal.open')}
              aria-haspopup="dialog"
              onClick={() => {
                setSeccionPortal('inicio')
                setPortal(true)
              }}
            />
            <LanguageSwitch />
            <SesionBoton />
            <BotonRecoger lado="arriba" abierta nombre={t('layout.top')} controla="barra-arriba" onCambiar={setBarraArriba} />
          </div>
        </header>
      </BarraRecogible>

      {/* Fuera de las barras: el aviso de datos sintéticos no se puede recoger (RF-INT-32). */}
      {synthetic && (
        <div className="aviso-fijo">
          <SyntheticBanner />
        </div>
      )}

      {/* Barra izquierda: Filtros (búsqueda de veredictos con línea de tiempo y resultados). */}
      <BarraRecogible
        lado="izq"
        id="panel-izq"
        nombre={t('layout.filters')}
        abierta={barraIzq}
        onCambiar={abrirIzq}
        icono="filtros"
      >
        <aside className="panel-izq" aria-labelledby="titulo-filtros">
          <CabeceraPanel icono="filtros" titulo={t('layout.filters')} idTitulo="titulo-filtros">
            <BotonRecoger lado="izq" abierta nombre={t('layout.filters')} controla="panel-izq" onCambiar={abrirIzq} />
          </CabeceraPanel>
          <div className="panel-cuerpo">
            {state.status === 'loading' && <Esqueleto etiqueta={t('series.loading')} variante="lista" filas={6} />}
            {state.status === 'error' && (
              <p role="alert" className="estado-carga">
                {t('series.error')}
              </p>
            )}
            {!modoMundo && state.status === 'ready' && zonas.length === 0 && <p className="estado-carga">{t('series.noZones')}</p>}
            {modoMundo && lugar && (
              <>
                {zonas.length > 0 && (
                  <div className="chips zona-volver" role="group" aria-label={t('zone.processedList')}>
                    {zonas.map((z) => (
                      <button
                        key={z.aoi}
                        type="button"
                        className="chip"
                        onClick={() => {
                          setLugar(null)
                          setGranulosMundo([])
                          setZonaVeredictos(z.aoi)
                          setVolarMundo({ bbox: z.bbox })
                        }}
                      >
                        <Icono nombre="hallazgos" tamano={14} /> {t('zone.back', { name: z.nombre })}
                      </button>
                    ))}
                  </div>
                )}
                <Mundo
                  zona={lugar}
                  elegido={elegidoMundo}
                  onResultados={(g) => {
                    setGranulosMundo(g)
                    setElegidoMundo(null)
                  }}
                  onElegir={(g) => {
                    setElegidoMundo(g.id)
                    if (g.bbox) setVolarMundo({ bbox: g.bbox as Bbox })
                  }}
                  onInvestigar={() => {
                    setSemilla(lugar)
                    setPestanaDer('investigacion')
                    abrirDer(true)
                  }}
                />
              </>
            )}
            {listo && !modoMundo && zona && zonas.length > 1 && (
              <p className="muted zona-actual">{t('zone.processed', { name: zona.nombre })}</p>
            )}
            {listo && !modoMundo && (
              <Buscador
                series={series}
                todos={items}
                filtro={filtro}
                onFiltro={(f) => {
                  setFiltro(f)
                  setAbierta(null)
                  setReproduccion(null)
                  // Si el par elegido queda fuera de la búsqueda, se pasa al primero que sí está.
                  const nuevos = buscar(items, f)
                  if (nuevos.length && !nuevos.some((v) => claveVeredicto(v) === seleccion)) {
                    setSeleccion(claveVeredicto(nuevos[0]))
                  }
                }}
                resultados={cargando ? [] : resultados}
                seleccion={elegida}
                onSeleccionar={(v) => {
                  setReproduccion(null)
                  seleccionar(v)
                }}
                cargando={cargando}
                error={todos?.status === 'error'}
                plegarAvanzado={publica}
              />
            )}
            <footer className="muted pie">
              <p>{t('footer.attribution')}</p>
              <p>{t('footer.license')}</p>
              <button
                type="button"
                className="pie-creditos"
                onClick={() => {
                  setSeccionPortal('datos')
                  setPortal(true)
                }}
              >
                {t('footer.credits')}
              </button>
            </footer>
          </div>
        </aside>
      </BarraRecogible>

      <main id="main" tabIndex={-1} className="zona-principal">
        {/* El mapa, siempre de fondo y a pantalla completa (RF-INT-24). */}
        <div className="fondo-mapa">
          {/* El espacio detrás del globo: el lienzo del mapa es transparente fuera de la Tierra. */}
          <Espacio />
          {mapaEnPantalla && (
            <AtlasMap
              options={mapaEnPantalla.options}
              compare={comparar}
              canCompare={Boolean(mapaEnPantalla.verdict)}
              busy={cargando}
              modo3d={modo3d}
              layer={capaVisible}
              opacity={opacidad}
              reframe={encuadre}
              mundo={mundoMapa}
              volar={volarMundo}
              onVista={setVistaMapa}
              onPunto={irAPunto}
              rotulo={rotulo}
              onHuella={(id) => {
                // Elegir una pasada con un clic en su huella: se resalta y se pone encima, sin mover el mapa.
                setElegidoMundo(id)
                abrirIzq(true)
              }}
            />
          )}
        </div>

        {/* Barra derecha: un solo panel con cuatro pestañas verticales pegadas al borde (RF-INT-27). */}
        <div className="lateral-der" data-abierta={barraDer}>
          <div
            id="panel-der"
            className="lateral-der-panel vidrio"
            hidden={cierreDer.oculto}
            inert={cierreDer.cerrando}
            data-cerrando={cierreDer.cerrando || undefined}
          >
            <PanelPestana clave="hallazgos" activa={pestanaDer}>
              <CabeceraPanel icono="hallazgos" titulo={t('layout.tabs.hallazgos')}>
                <BotonRecoger lado="der" abierta nombre={t('layout.tabs.hallazgos')} controla="panel-der" onCambiar={abrirDer} />
              </CabeceraPanel>
              <div className="panel-cuerpo" aria-busy={cargando}>
                {/* Zona sin veredictos (buscada o punto del mapa): Hallazgos es el procesado en línea con su avance. */}
                {modoMundo && lugar && <ProcesadoZona lugar={lugar} onListo={zonaProcesada} autoIniciar={!esPunto && lugar.id !== 'vista'} />}
                {!modoMundo && state.status === 'error' && <p role="alert">{t('series.error')}</p>}
                {!modoMundo && todos?.fallidas.length ? <p role="alert">{t('picker.error')}</p> : null}
                {!modoMundo && !cargando && items.length === 0 && todos?.status === 'ready' && <p>{t('picker.empty')}</p>}
                {/* Recién procesada: el resumen del manifiesto se ve mientras llegan los veredictos completos. */}
                {!modoMundo && resumenOnline && resumenOnline.aoi === aoi && (cargando || !verdict) && (
                  <ResumenPares resumen={resumenOnline.resumen} />
                )}
                {!modoMundo && state.status === 'ready' && zonas.length === 0 && <p>{t('series.noZones')}</p>}
                {!modoMundo && (!verdict || deOtraZona) && state.status !== 'error' && !(state.status === 'ready' && zonas.length === 0) && (
                  <Esqueleto etiqueta={t('picker.loading')} variante="tarjeta" filas={5} />
                )}
                {!modoMundo && verdict && !deOtraZona && (
                  <>
                    <VerdictCard verdict={verdict} />
                    {hundimiento && (
                      <Hundimiento
                        datos={hundimiento}
                        capaActiva={capaVisible === 'subsidence'}
                        onVerCapa={() => setCapa('subsidence')}
                        onVolar={(lon, lat) => setVolarMundo({ bbox: [lon - 0.03, lat - 0.03, lon + 0.03, lat + 0.03] })}
                      />
                    )}
                    <Evidencia verdict={verdict} explicar />
                    {verdict && (
                      <p className="enlace-json">
                        <a href={verdictJsonUrl(verdict, lang)} target="_blank" rel="noreferrer">
                          {t('evidence.json')}
                        </a>
                      </p>
                    )}
                    {aoi && <Regenerar key={aoi} aoi={aoi} onListo={zonaProcesada} />}
                  </>
                )}
              </div>
            </PanelPestana>
            <PanelPestana clave="historia" activa={pestanaDer}>
              <CabeceraPanel icono="historia" titulo={t('layout.tabs.historia')}>
                <BotonRecoger lado="der" abierta nombre={t('layout.tabs.historia')} controla="panel-der" onCambiar={abrirDer} />
              </CabeceraPanel>
              <div className="panel-cuerpo">
                {intro}
                {zonaHistoria && (
                  <HistoriaZona
                    zona={zonaHistoria}
                    onVolar={(bbox) => setVolarMundo({ bbox })}
                    onVerPar={(s, p) => {
                      const v = porClave.get(`${s}/${p}`)
                      if (v) setSeleccion(claveVeredicto(v))
                    }}
                  />
                )}
              </div>
            </PanelPestana>
            <PanelPestana clave="evento" activa={pestanaDer}>
              <CabeceraPanel icono="evento" titulo={t('layout.tabs.evento')}>
                <BotonRecoger lado="der" abierta nombre={t('layout.tabs.evento')} controla="panel-der" onCambiar={abrirDer} />
              </CabeceraPanel>
              <div className="panel-cuerpo">{listo && <EventQuery aoi={aoi} lang={lang} />}</div>
            </PanelPestana>
            <PanelPestana clave="investigacion" activa={pestanaDer}>
              <CabeceraPanel icono="interprete" titulo={t('layout.tabs.investigacion')}>
                <BotonRecoger lado="der" abierta nombre={t('layout.tabs.investigacion')} controla="panel-der" onCambiar={abrirDer} />
              </CabeceraPanel>
              <div className="panel-cuerpo">
                <Investigacion
                  semilla={semilla}
                  onVolar={(bbox) => setVolarMundo({ bbox })}
                  onVerPar={(s, p) => {
                    const v = porClave.get(`${s}/${p}`)
                    if (v) setSeleccion(claveVeredicto(v))
                  }}
                />
              </div>
            </PanelPestana>
            <PanelPestana clave="comunidad" activa={pestanaDer}>
              <CabeceraPanel icono="comunidad" titulo={t('layout.tabs.comunidad')}>
                <BotonRecoger lado="der" abierta nombre={t('layout.tabs.comunidad')} controla="panel-der" onCambiar={abrirDer} />
              </CabeceraPanel>
              <div className="panel-cuerpo">
                {listo && (
                  <>
                    <Comunidad aoi={aoi} version={version} onAbrir={abrirHistoria} onDescargar={(h) => descargar(h, [])} />

                    <Interprete
                      aoi={aoi}
                      nombreZona={zona?.nombre}
                      filtro={filtro}
                      resultados={cargando ? [] : resultados}
                      abierta={abierta}
                      todos={porClave}
                      onCerrar={() => {
                        setAbierta(null)
                        setReproduccion(null)
                      }}
                      onGuardar={guardar}
                      onDescargar={descargar}
                      onReproducir={reproducir}
                    />
                  </>
                )}
              </div>
            </PanelPestana>
          </div>
          <PestanasDer activa={pestanaDer} abierta={barraDer} onElegir={elegirPestanaDer} />
        </div>
      </main>

      {reproduccion && (
        <Reproductor
          titulo={reproduccion.titulo}
          pares={paresReproducidos}
          indice={reproduccion.indice}
          enMarcha={reproduccion.enMarcha}
          onIr={(i) => setReproduccion((r) => (r ? { ...r, indice: Math.max(0, Math.min(i, r.claves.length - 1)) } : r))}
          onAlternar={() =>
            setReproduccion((r) =>
              !r ? r : r.enMarcha ? { ...r, enMarcha: false } : { ...r, enMarcha: true, indice: r.indice >= r.claves.length - 1 ? 0 : r.indice },
            )
          }
          onCerrar={cerrarReproduccion}
        />
      )}

      <Portal abierta={portal} seccion={seccionPortal} onSeccion={setSeccionPortal} onCerrar={cerrarPortal} />
      {bienvenida && <Bienvenida onCerrar={() => cerrarBienvenida(false)} onConocerMas={() => cerrarBienvenida(true)} />}

      {/* Barra inferior: herramientas del mapa (RF-INT-28). */}
      <BarraRecogible
        lado="abajo"
        id="barra-abajo"
        nombre={t('layout.tools')}
        abierta={barraAbajo}
        onCambiar={setBarraAbajo}
        icono="cubo"
      >
        <nav className="herramientas" aria-label={t('layout.tools')}>
          <div className="segmentado" role="group" aria-label={t('tools.projection')}>
            <button type="button" aria-pressed={modo3d} title={t('tools.view3d')} onClick={() => setModo3d(true)}>
              <Icono nombre="cubo" />
              <span aria-hidden="true">3D</span>
              <span className="sr-solo">{t('tools.view3d')}</span>
            </button>
            <button type="button" aria-pressed={!modo3d} title={t('tools.view2d')} onClick={() => setModo3d(false)}>
              <Icono nombre="plano" />
              <span aria-hidden="true">2D</span>
              <span className="sr-solo">{t('tools.view2d')}</span>
            </button>
          </div>
          <span className="herramientas-separador" aria-hidden="true" />
          <BotonIcono icono="centrar" etiqueta={t('tools.reframe')} disabled={!mapOptions} onClick={() => setEncuadre((n) => n + 1)} />
          {(
            <div className="capas-caja">
              <BotonIcono
                icono="capas"
                etiqueta={t('tools.layers')}
                aria-expanded={capasAbiertas}
                aria-controls="capas-panel"
                onClick={() => setCapasAbiertas((a) => !a)}
              />
              <div id="capas-panel" className="capas-panel vidrio" hidden={!capasAbiertas}>
                <fieldset>
                  <legend>{t('tools.layer')}</legend>
                  {capas.map((c) => (
                    <label key={c}>
                      <input type="radio" name="capa-radar" checked={capaVisible === c} onChange={() => setCapa(c)} />
                      {t(`tools.layerNames.${c}`)}
                    </label>
                  ))}
                </fieldset>
                <label className="capas-opacidad">
                  {t('tools.opacity')}
                  <input
                    type="range"
                    min={0.2}
                    max={1}
                    step={0.05}
                    value={opacidad}
                    onChange={(e) => setOpacidad(Number(e.target.value))}
                  />
                </label>
              </div>
            </div>
          )}
          {/* Comparador: escenas ópticas de antes y después, y también las capas HH, HV y de hundimiento. */}
          {verdict && (
            <BotonIcono icono="comparar" etiqueta={t('map.compare')} aria-pressed={comparar} onClick={() => setComparar((c) => !c)} />
          )}
          <BotonIcono
            icono="pantalla"
            etiqueta={t(completa ? 'tools.exitFullscreen' : 'tools.fullscreen')}
            aria-pressed={completa}
            onClick={pantallaCompleta}
          />
          <span className="herramientas-separador" aria-hidden="true" />
          <BotonRecoger lado="abajo" abierta nombre={t('layout.tools')} controla="barra-abajo" onCambiar={setBarraAbajo} />
        </nav>
      </BarraRecogible>
    </div>
  )
}
