import * as maplibregl from "maplibre-gl";
import { prepararVistaPrevia } from "./vistaPrevia";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre 6 busca su worker junto a su propio módulo. En `vite build` ese módulo
// queda dentro del bundle y el worker no se copia: "Worker failed to load" y mapa
// en blanco. Con ?url, Vite emite el worker y le pasamos su ruta (vale también
// para el comparador, porque es un ajuste global).
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import "./mapa.css";
import { crearComparador, type Comparador } from "./comparador";
import { normalizarAvisoEscena } from "./escena";
import { Control3d } from "./control3d";
import { capacidadGrafica, elegirProyeccion, escalaValida, transicionGlobo } from "./globo";
import {
  anclaEtiqueta,
  centroZona,
  describirHuella,
  geojsonHuellas,
  huellasValidas,
  nombreCorto,
  puntoEtiqueta,
  type Huella,
  dentroDeAnillo,
} from "./huellas";
import { crearLeyenda, limitarOpacidad, rangoReescalado } from "./leyenda";
import { ladoDisponible } from "./optico";
import {
  atribuciones,
  bboxContinuo,
  contornoZona,
  estiloMapaBase,
  fuenteDatos,
  textoExtension,
  validarBbox,
  ZOOM_MAXIMO_MAPA,
} from "./mapaBase";
import { OPACIDAD_MINIMA_TRAMA } from "./estado";
import { plantillaEstado } from "./protocolo";
import {
  contenidoCargando,
  contenidoError,
  contenidoSerie,
  puntoSeleccionado,
  urlPixel,
  type SeriePixel,
} from "./seleccion";
import { TEXTOS } from "./textos";
import { luzDelSol, nocheGeojson } from "./sol";
import { crearAntesDespues, fuentesDisponibles, type AntesDespues } from "./antesDespues";
import type { Bbox, CambiosMapa, CapaRadar, MapaAtlas, MundoMapa, OpcionesMapa } from "./tipos";

maplibregl.setWorkerUrl(workerUrl);

const CAPA_ENCIMA = "aoi-contorno-halo";
/** Desde este zoom la huella ocupa más que la pantalla y su nombre estorbaría a los datos. */
const ZOOM_SIN_ETIQUETAS = 9;
/** Hasta este zoom la caja de la zona es diminuta: se marca también con un punto. */
const ZOOM_PUNTO_ZONA = 7;
const IDS_RADAR = ["radar-state", "radar-change_hh", "radar-change_hv", "radar-subsidence", "radar-trama"] as const;

/**
 * Crea el mapa de Atlas dentro de `contenedor`. Independiente del framework:
 * Faro lo monta, lo cambia con `actualizar()` y lo desmonta con `destruir()`.
 *
 * Teclado, con el mapa enfocado: flechas para desplazar y + y − para el zoom
 * (de MapLibre); Enter selecciona el punto bajo la cruz central y Escape cierra
 * la ventana del punto.
 */
export function crearMapa(contenedor: HTMLElement, opciones: OpcionesMapa): MapaAtlas {
  const capacidad = capacidadGrafica();
  if (capacidad === "sin_webgl2") return mapaSinWebgl(contenedor, opciones);

  const estado = {
    aoi: validarBbox(opciones.aoi),
    zona: opciones.nombreZona,
    layers: opciones.layers,
    capa: opciones.activeLayer ?? ("state" as CapaRadar),
    causa: opciones.causaNoObservable,
    avisoEscena: normalizarAvisoEscena(opciones.desplazamientoEscena),
    dataKind: opciones.dataKind,
    idioma: opciones.idioma ?? "es",
    opacidad: 0.85,
    pixelUrl: opciones.pixelUrl,
    punto: null as { lon: number; lat: number } | null,
    optical: opciones.optical,
    compare: opciones.compare ?? "off",
    modo3d: opciones.modo3d ?? false,
    falloGlobo: false,
    huellas: huellasValidas(opciones.huellas),
    antesDespues: opciones.antesDespues ?? false,
  };

  // Comparador óptico (T-ATL-07): solo con compare "swipe" y al menos un lado con datos.
  const quiereComparador = () =>
    estado.compare === "swipe" && ladoDisponible(estado.optical, "after") !== null;
  const proyeccion = () =>
    elegirProyeccion({
      modo3d: estado.modo3d,
      capacidad,
      falloGlobo: estado.falloGlobo,
      comparadorActivo: quiereComparador(),
    });

  contenedor.classList.add("atlas-mapa");
  const lienzo = document.createElement("div");
  lienzo.className = "atlas-lienzo";
  contenedor.append(lienzo);

  const map = new maplibregl.Map({
    container: lienzo,
    style: estiloMapaBase(proyeccion().tipo),
    bounds: bboxContinuo(estado.aoi),
    fitBoundsOptions: { padding: 32 },
    // Dos niveles sobre el dato de 10 m: se ve cada píxel sin aparentar más detalle (T-ATL-08).
    maxZoom: ZOOM_MAXIMO_MAPA,
    // Memoria (2026-11-14): como mucho 1,5 píxeles por píxel CSS (en pantallas de 2× el lienzo ocupaba casi el
    // doble de GPU sin que se note en el radar de 10 m) y una caché de teselas acotada.
    pixelRatio: Math.min(window.devicePixelRatio || 1, 1.5),
    maxTileCacheSize: 300,
    attributionControl: false,
    // En 2D, sin giro ni inclinación: la escala y el contorno se leen con el norte arriba.
    // En 3D se activan (T-ATL-10); ver aplicarInteraccion.
    dragRotate: false,
    pitchWithRotate: true,
    touchPitch: false,
  });
  map.touchZoomRotate.disableRotation();
  map.keyboard.disableRotation();

  // La atribución se monta con textos propios para que siga al idioma y al tipo de dato.
  let atribucion: maplibregl.AttributionControl | null = null;
  let atribucionActual = "";
  function ponerAtribucion() {
    const textos = atribuciones(estado.idioma, Boolean(estado.layers) && estado.dataKind === "real");
    const clave = textos.join("|");
    if (atribucion && clave === atribucionActual) return;
    if (atribucion) map.removeControl(atribucion);
    atribucion = new maplibregl.AttributionControl({ compact: false, customAttribution: textos });
    map.addControl(atribucion, "bottom-right");
    atribucionActual = clave;
  }
  ponerAtribucion();
  const escala = new maplibregl.ScaleControl({ unit: "metric", maxWidth: 120 });
  map.addControl(escala, "bottom-left");
  // La brújula solo se ve en 3D (CSS con .atlas-plano): devuelve el norte y quita la inclinación.
  map.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), "top-right");
  const control3d =
    opciones.control3d === false
      ? null
      : new Control3d(() => {
          estado.modo3d = !estado.modo3d;
          aplicarComparador();
          redibujarLeyenda();
          opciones.onModo3dChanged?.(estado.modo3d);
        });
  if (control3d) {
    map.addControl(control3d, "top-right");
    contenedor.classList.add("atlas-con-3d");
  }

  // La caja de extensión de la zona ya no se pinta (2026-11-15: «quita el recorte artificial»): con la búsqueda
  // mundial la zona cambia y el recuadro fijo confundía. Sus textos y la lista de huellas siguen para el lector.
  const extension = document.createElement("div");
  extension.className = "atlas-solo-lector";
  extension.append(document.createElement("strong"), document.createElement("span"));
  // Las etiquetas del mapa no se leen en voz alta; la lista sí (RF-INT-16).
  const listaHuellas = document.createElement("ul");
  extension.append(listaHuellas);
  contenedor.append(extension);

  const sello = document.createElement("div");
  sello.className = "atlas-sintetico";
  sello.setAttribute("role", "status");
  contenedor.append(sello);

  // Cruz central y ayuda: solo se ven cuando el mapa tiene el foco del teclado.
  const cruz = document.createElement("div");
  cruz.className = "atlas-cruz";
  cruz.setAttribute("aria-hidden", "true");
  const ayuda = document.createElement("div");
  ayuda.className = "atlas-ayuda";
  ayuda.setAttribute("aria-hidden", "true");
  // Anuncio para lectores de pantalla al seleccionar un punto.
  const anuncio = document.createElement("div");
  anuncio.className = "atlas-solo-lector";
  anuncio.setAttribute("role", "status");
  // Por qué el mapa está en 2D si se pidió el 3D (RF-INT-17).
  const aviso3d = document.createElement("div");
  aviso3d.className = "atlas-aviso-3d";
  aviso3d.setAttribute("role", "status");
  // Sustituye a la barra de escala cuando no vale (RF-INT-13).
  const avisoEscala = document.createElement("div");
  avisoEscala.className = "atlas-aviso-escala";
  avisoEscala.hidden = true;
  contenedor.append(cruz, ayuda, anuncio, aviso3d, avisoEscala);

  // setProjection necesita el estilo cargado; antes, la proyección va en el propio estilo.
  let cargado = false;
  let proyeccionActual = proyeccion().tipo;
  function aplicarProyeccion() {
    let p = proyeccion();
    if (p.tipo !== proyeccionActual && cargado) {
      try {
        map.setProjection({ type: p.tipo });
      } catch (e) {
        console.warn("[atlas] el globo falló; el mapa sigue en 2D", e);
        estado.falloGlobo = true;
        p = proyeccion();
        map.setProjection({ type: p.tipo });
      }
      proyeccionActual = p.tipo;
      // La ayuda del teclado y la leyenda cuentan las teclas de 3D solo con el globo.
      redibujarTextos();
      redibujarLeyenda();
    }
    aviso3d.textContent = p.motivo ? TEXTOS[estado.idioma].sin3d[p.motivo] : "";
    aviso3d.hidden = !p.motivo;
    control3d?.dibujar({ pulsado: estado.modo3d, idioma: estado.idioma });
    if (cargado) emitirCamara();
    aplicarInteraccion();
    actualizarEscala();
  }

  const sinAnimacion = () =>
    typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

  /** Giro e inclinación solo con el globo; al volver a 2D, norte arriba y sin inclinación. */
  function aplicarInteraccion() {
    const en3d = proyeccionActual === "globe";
    contenedor.classList.toggle("atlas-plano", !en3d);
    if (en3d) {
      map.dragRotate.enable();
      map.touchPitch.enable();
      map.touchZoomRotate.enableRotation();
      map.keyboard.enableRotation();
      return;
    }
    map.dragRotate.disable();
    map.touchPitch.disable();
    map.touchZoomRotate.disableRotation();
    map.keyboard.disableRotation();
    if (map.getBearing() !== 0 || map.getPitch() !== 0) {
      if (sinAnimacion()) map.jumpTo({ bearing: 0, pitch: 0 });
      else map.easeTo({ bearing: 0, pitch: 0 });
    }
  }

  /** `transitionState` de la proyección de MapLibre es interno: si no está, se estima por el zoom. */
  function transicion(): number {
    const leido = (map as unknown as { style?: { projection?: { transitionState?: number } } }).style
      ?.projection?.transitionState;
    return transicionGlobo(map.getZoom(), leido);
  }

  function actualizarEscala() {
    const ok = escalaValida({ tipo: proyeccionActual, pitch: map.getPitch(), transicion: transicion() });
    const barra = contenedor.querySelector<HTMLElement>(".maplibregl-ctrl-scale");
    if (barra) barra.style.display = ok ? "" : "none";
    avisoEscala.hidden = ok;
    if (!ok) avisoEscala.textContent = TEXTOS[estado.idioma].sinEscala;
  }
  map.on("move", actualizarEscala);

  // Cámara del globo para el fondo espacial (components/Espacio.tsx): dónde está el centro de la Tierra en
  // pantalla, su radio y la orientación, para dibujar el Sol y el halo de la atmósfera detrás del mapa.
  // Va por un evento de ventana para que el mapa no dependa de la app.
  function emitirCamara() {
    const c = map.getCenter();
    const caja = map.getCanvas().getBoundingClientRect();
    const p = map.project(c);
    const lat = Math.min(Math.abs(c.lat), 85.051129);
    const radio = (512 * Math.pow(2, map.getZoom())) / (2 * Math.PI) / Math.cos((lat * Math.PI) / 180);
    window.dispatchEvent(
      new CustomEvent("sar:camara", {
        detail: {
          globo: proyeccionActual === "globe",
          x: caja.left + p.x,
          y: caja.top + p.y,
          radio,
          lng: c.lng,
          lat: c.lat,
          bearing: map.getBearing(),
          pitch: map.getPitch(),
          zoom: map.getZoom(),
        },
      }),
    );
  }
  map.on("move", emitirCamara);
  map.on("resize", emitirCamara);
  map.on("load", emitirCamara);

  const marcador = new maplibregl.Marker({ color: "#000000" });
  const ventana = new maplibregl.Popup({ maxWidth: "300px", closeOnClick: false, focusAfterOpen: false });
  let peticion: AbortController | null = null;

  /** Huellas del buscador mundial que contienen el punto, en el orden en que llegaron (las más recientes antes). */
  function huellasEn(lng: number, lat: number): string[] {
    return (mundo?.huellas.features ?? [])
      .filter((f) => dentroDeAnillo(lng, lat, f.geometry.coordinates[0] ?? []))
      .map((f) => f.properties.id);
  }

  // Nombre del punto elegido (rotularPunto); se vuelve a poner cada vez que cambia el contenido de la ventana.
  let nombrePunto = "";
  function mostrarVentana(p: { lon: number; lat: number }, contenido: HTMLElement) {
    const lugar = contenido.querySelector(".atlas-serie-lugar");
    if (lugar) lugar.textContent = nombrePunto;
    ventana.setLngLat([p.lon, p.lat]).setDOMContent(contenido).addTo(map);
  }

  async function seleccionar(lng: number, lat: number) {
    // Clic dentro de una huella: se elige esa pasada (2026-11-15). Con varias encimadas, cada clic en el mismo sitio
    // pasa a la siguiente. Fuera de las huellas, el clic sigue eligiendo un punto.
    const debajo = opciones.onFootprintSelected ? huellasEn(lng, lat) : [];
    if (debajo.length) {
      const actual = mundo?.elegido ? debajo.indexOf(mundo.elegido) : -1;
      opciones.onFootprintSelected!(debajo[(actual + 1) % debajo.length]);
      return;
    }
    const p = puntoSeleccionado(lng, lat);
    estado.punto = p;
    nombrePunto = "";
    const t = TEXTOS[estado.idioma];
    marcador.setLngLat([p.lon, p.lat]).addTo(map);
    anuncio.textContent = `${t.puntoSeleccionado}: ${t.lon} ${p.lon}, ${t.lat} ${p.lat}`;
    opciones.onPointSelected?.(p);

    peticion?.abort();
    if (!estado.pixelUrl) {
      ventana.remove();
      return;
    }
    // Fuera de la zona con datos no se pregunta: la API respondería 404 y la consola lo apuntaría como error.
    const [oeste, sur, este, norte] = estado.aoi;
    const lonDentro = oeste <= este ? p.lon >= oeste && p.lon <= este : p.lon >= oeste || p.lon <= este;
    if (!(lonDentro && p.lat >= sur && p.lat <= norte)) {
      mostrarVentana(p, contenidoError(p, t.fueraDeSerie, estado.idioma));
      return;
    }
    const control = new AbortController();
    peticion = control;
    mostrarVentana(p, contenidoCargando(p, estado.idioma));
    try {
      const r = await fetch(urlPixel(estado.pixelUrl, p), { signal: control.signal });
      if (r.status === 404) throw new Error(t.fueraDeSerie);
      if (!r.ok) throw new Error(`${t.errorSerie} (HTTP ${r.status})`);
      const serie = (await r.json()) as SeriePixel;
      if (peticion === control) mostrarVentana(p, contenidoSerie(serie, estado.idioma));
    } catch (e) {
      if (control.signal.aborted) return;
      const msg = e instanceof TypeError ? t.errorSerie : (e as Error).message;
      mostrarVentana(p, contenidoError(p, msg, estado.idioma));
    }
  }

  function quitarSeleccion() {
    peticion?.abort();
    estado.punto = null;
    ventana.remove();
    marcador.remove();
  }

  map.on("click", (e) => seleccionar(e.lngLat.lng, e.lngLat.lat));
  // Sobre una huella elegible, el puntero lo anuncia.
  map.on("mousemove", (e) => {
    if (!opciones.onFootprintSelected || !mundo) return;
    map.getCanvas().style.cursor = huellasEn(e.lngLat.lng, e.lngLat.lat).length ? "pointer" : "";
  });

  const canvas = map.getCanvas();
  canvas.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const c = map.getCenter();
      seleccionar(c.lng, c.lat);
    } else if (e.key === "Escape" && estado.punto) {
      quitarSeleccion();
    } else if ((e.key === "n" || e.key === "N") && !e.ctrlKey && !e.metaKey && !e.altKey) {
      // Volver al norte y quitar la inclinación (RF-INT-15). En 2D ya está así.
      if (map.getBearing() !== 0 || map.getPitch() !== 0) {
        e.preventDefault();
        if (sinAnimacion()) map.jumpTo({ bearing: 0, pitch: 0 });
        else map.resetNorthPitch();
      }
    }
  });
  // La cruz se muestra solo con foco de teclado, no al hacer clic.
  canvas.addEventListener("focus", () => {
    contenedor.classList.toggle("atlas-foco-teclado", canvas.matches(":focus-visible"));
  });
  canvas.addEventListener("blur", () => contenedor.classList.remove("atlas-foco-teclado"));

  const dibujarLeyenda = crearLeyenda(contenedor, {
          alCambiarCapa: (c) => {
            estado.capa = c;
            aplicarVisibilidad();
            redibujarLeyenda();
            opciones.onLayerChanged?.(c);
          },
          alCambiarOpacidad: (o) => fijarOpacidad(o),
        });

  function redibujarLeyenda() {
    dibujarLeyenda(!estado.layers ? null : {
      idioma: estado.idioma,
      capa: estado.capa,
      capasDisponibles: opciones.controlCapas !== false,
      opacidad: estado.opacidad,
      rango: estado.capa === "state" ? null : rangoReescalado(estado.layers[estado.capa] ?? ""),
      causa: estado.causa,
      avisoEscena: estado.avisoEscena,
      teclas3d: proyeccionActual === "globe",
    });
  }

  function redibujarTextos() {
    const t = TEXTOS[estado.idioma];
    const zona = estado.zona ?? t.zonaPorDefecto;
    map.getCanvas().setAttribute("aria-label", t.mapaDe(zona));
    extension.querySelector("strong")!.textContent = t.extensionDe(zona);
    extension.querySelector("span")!.textContent = textoExtension(estado.aoi);
    listaHuellas.setAttribute("aria-label", t.huellas);
    listaHuellas.replaceChildren(
      ...estado.huellas.map((h) => {
        const li = document.createElement("li");
        li.textContent = `${h.properties.series}: ${describirHuella(h.properties, estado.idioma)}`;
        return li;
      }),
    );
    sello.textContent = t.sintetico;
    sello.hidden = estado.dataKind !== "synthetic";
    ayuda.textContent =
      proyeccionActual === "globe" ? `${t.ayudaTeclado}. ${t.teclas3d}` : t.ayudaTeclado;
  }

  function quitarCapasRadar() {
    for (const id of IDS_RADAR) {
      if (map.getLayer(id)) map.removeLayer(id);
      if (map.getSource(id)) map.removeSource(id);
    }
  }

  function aplicarCapas() {
    quitarCapasRadar();
    if (!estado.layers) return;
    const fuentes: Record<(typeof IDS_RADAR)[number], string> = {
      "radar-state": plantillaEstado(estado.layers.state, "cambio"),
      "radar-change_hh": estado.layers.change_hh,
      "radar-change_hv": estado.layers.change_hv,
      "radar-subsidence": estado.layers.subsidence ?? "",
      "radar-trama": plantillaEstado(estado.layers.state, "trama"),
    };
    for (const id of IDS_RADAR) {
      // El hundimiento solo existe en zonas con cálculo de NISAR GUNW.
      if (!fuentes[id]) continue;
      // Acotada a la zona y, salvo la trama, al zoom del dato (T-ATL-08).
      map.addSource(id, fuenteDatos(fuentes[id], estado.aoi, { ampliar: id !== "radar-trama" }));
      const categorica = id === "radar-state" || id === "radar-trama";
      map.addLayer(
        {
          id,
          type: "raster",
          source: id,
          paint: {
            "raster-opacity": opacidadDe(id),
            // Los códigos y la trama se ven nítidos; el cambio continuo, suavizado.
            "raster-resampling": categorica ? "nearest" : "linear",
            "raster-fade-duration": 0,
          },
        },
        CAPA_ENCIMA,
      );
    }
    aplicarVisibilidad();
  }

  function aplicarVisibilidad() {
    if (!estado.layers || !map.getLayer("radar-state")) return;
    // La trama de lo no observable está siempre encima: nunca queda transparente.
    const visibles = new Set([`radar-${estado.capa}`, "radar-trama"]);
    for (const id of IDS_RADAR) {
      map.setLayoutProperty(id, "visibility", visibles.has(id) ? "visible" : "none");
    }
  }

  function opacidadDe(id: (typeof IDS_RADAR)[number]): number {
    return id === "radar-trama" ? Math.max(estado.opacidad, OPACIDAD_MINIMA_TRAMA) : estado.opacidad;
  }

  function fijarOpacidad(o: number) {
    estado.opacidad = limitarOpacidad(o);
    for (const id of IDS_RADAR) {
      if (map.getLayer(id)) map.setPaintProperty(id, "raster-opacity", opacidadDe(id));
    }
  }

  // Huellas (T-ATL-13): contorno y relleno tenue bajo el radar, y el nombre en una etiqueta HTML,
  // porque el estilo base no trae fuentes tipográficas para capas de texto.
  let etiquetas: maplibregl.Marker[] = [];
  function aplicarHuellas() {
    (map.getSource("huellas") as maplibregl.GeoJSONSource | undefined)?.setData(
      geojsonHuellas(estado.huellas),
    );
    for (const e of etiquetas) e.remove();
    etiquetas = estado.huellas.map((h: Huella) => {
      const el = document.createElement("div");
      el.className = "atlas-etiqueta-huella";
      el.setAttribute("aria-hidden", "true");
      el.textContent = nombreCorto(h.properties);
      return new maplibregl.Marker({ element: el, anchor: anclaEtiqueta(h), offset: [0, -2] }).setLngLat(puntoEtiqueta(h)).addTo(map);
    });
    mostrarEtiquetas();
  }
  function mostrarEtiquetas() {
    contenedor.classList.toggle("atlas-sin-etiquetas", map.getZoom() >= ZOOM_SIN_ETIQUETAS);
  }
  map.on("zoom", mostrarEtiquetas);

  // Día y noche en tiempo real: la sombra del lado nocturno sobre el globo y la luz de la atmósfera
  // se recalculan cada minuto (src/mapa/sol.ts).
  const reloj = window.setInterval(() => {
    const ahora = new Date();
    (map.getSource("noche") as maplibregl.GeoJSONSource | undefined)?.setData(nocheGeojson(ahora));
    if (cargado) map.setLight(luzDelSol(ahora));
  }, 60_000);

  map.on("load", () => {
    map.addSource("noche", { type: "geojson", data: nocheGeojson(new Date()) });
    map.addLayer({
      id: "noche",
      type: "fill",
      source: "noche",
      // Cuatro bandas apiladas (bajo el horizonte y los tres crepúsculos): la noche se oscurece hacia
      // su centro. Solo se ve de lejos; a la escala de la zona no tapa los datos.
      paint: {
        "fill-color": "#020611",
        "fill-opacity": ["interpolate", ["linear"], ["zoom"], 0, 0.2, 5, 0.12, 8, 0],
        "fill-antialias": false,
      },
    });
    map.addSource("huellas", { type: "geojson", data: geojsonHuellas(estado.huellas) });
    map.addLayer({
      id: "huellas-relleno",
      type: "fill",
      source: "huellas",
      paint: { "fill-color": "#1d4e89", "fill-opacity": 0.08 },
    });
    map.addLayer({
      id: "huellas-contorno",
      type: "line",
      source: "huellas",
      paint: { "line-color": "#1d4e89", "line-width": 1.5 },
    });
    map.addSource("aoi", { type: "geojson", data: contornoZona(estado.aoi) });
    map.addSource("aoi-centro", { type: "geojson", data: centroZona(estado.aoi) });
    map.addLayer({
      id: "aoi-punto",
      type: "circle",
      layout: { visibility: "none" },
      source: "aoi-centro",
      maxzoom: ZOOM_PUNTO_ZONA,
      paint: {
        "circle-radius": 5,
        "circle-color": "#000000",
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 2,
      },
    });
    map.addLayer({
      id: "aoi-contorno-halo",
      type: "line",
      source: "aoi",
      layout: { visibility: "none" },
      paint: { "line-color": "#ffffff", "line-width": 4, "line-opacity": 0.9 },
    });
    map.addLayer({
      id: "aoi-contorno",
      type: "line",
      source: "aoi",
      layout: { visibility: "none" },
      paint: { "line-color": "#000000", "line-width": 2, "line-dasharray": [3, 2] },
    });
    aplicarCapas();
    aplicarHuellas();
    cargado = true;
    aplicarProyeccion();
  });

  let comparador: Comparador | null = null;
  let antesDespues: AntesDespues | null = null;

  // ---- Buscador mundial: huellas de gránulos de cualquier parte y la vista previa del elegido ----
  let mundo: MundoMapa | null = null;
  let vistaMundo = "";
  const FC_VACIA = { type: "FeatureCollection" as const, features: [] };
  function aplicarMundo() {
    if (!cargado) return;
    if (!map.getSource("mundo")) {
      map.addSource("mundo", { type: "geojson", data: FC_VACIA });
      // De abajo arriba (2026-11-15): los no elegidos solo con su contorno; encima, la vista previa del elegido (se
      // inserta antes de "mundo-elegido-relleno"), su relleno tenue y su contorno grueso.
      map.addLayer(
        {
          id: "mundo-contorno",
          type: "line",
          source: "mundo",
          paint: { "line-color": "#ffffff", "line-width": 1.2, "line-opacity": 0.75, "line-dasharray": [2, 2] },
        },
        "huellas-relleno",
      );
      map.addLayer(
        {
          id: "mundo-elegido-relleno",
          type: "fill",
          source: "mundo",
          filter: ["==", ["get", "id"], ""],
          paint: { "fill-color": "#ffffff", "fill-opacity": 0.08 },
        },
        "huellas-relleno",
      );
      map.addLayer(
        {
          id: "mundo-elegido",
          type: "line",
          source: "mundo",
          filter: ["==", ["get", "id"], ""],
          paint: { "line-color": "#ffffff", "line-width": 3 },
        },
        "huellas-relleno",
      );
    }
    (map.getSource("mundo") as maplibregl.GeoJSONSource).setData(mundo?.huellas ?? FC_VACIA);
    const elegido = mundo?.elegido ?? "";
    map.setFilter("mundo-contorno", ["!=", ["get", "id"], elegido]);
    map.setFilter("mundo-elegido-relleno", ["==", ["get", "id"], elegido]);
    map.setFilter("mundo-elegido", ["==", ["get", "id"], elegido]);
    const vista = mundo?.vista ?? null;
    const clave = vista ? `${vista.url}|${vista.bbox.join(",")}` : "";
    if (clave === vistaMundo) return;
    vistaMundo = clave;
    if (map.getLayer("mundo-vista")) map.removeLayer("mundo-vista");
    if (map.getSource("mundo-vista")) map.removeSource("mundo-vista");
    if (!vista) return;
    // La vista previa es mayor que la escena: se georreferencia por el contenido (vistaPrevia.ts) y sin el negro.
    void prepararVistaPrevia(vista.url, vista.bbox).then((lista) => {
      if (!lista || vistaMundo !== clave || !cargado || map.getSource("mundo-vista")) return;
      map.addSource("mundo-vista", {
        type: "image",
        url: lista.url,
        coordinates: lista.coordinates as [[number, number], [number, number], [number, number], [number, number]],
      });
      map.addLayer(
        { id: "mundo-vista", type: "raster", source: "mundo-vista", paint: { "raster-opacity": 0.9, "raster-fade-duration": 300 } },
        "mundo-elegido-relleno",
      );
    });
  }
  map.on("load", () => aplicarMundo());

  /** Comparador antes/después recortado a la zona (corrección del 2026-11-14). No fuerza el 2D. */
  function aplicarAntesDespues() {
    // Además de las escenas ópticas, el comparador puede enseñar las capas de cambio y la de hundimiento.
    const capas = estado.layers
      ? { change_hh: estado.layers.change_hh, change_hv: estado.layers.change_hv, subsidence: estado.layers.subsidence }
      : undefined;
    const activo = estado.antesDespues && fuentesDisponibles({ optical: estado.optical, capas }).length > 0;
    if (activo && !antesDespues) {
      antesDespues = crearAntesDespues(contenedor, map, { optical: estado.optical, idioma: estado.idioma, aoi: estado.aoi, capas });
    } else if (activo && antesDespues) {
      antesDespues.actualizar({ optical: estado.optical, idioma: estado.idioma, aoi: estado.aoi, capas });
    } else if (!activo && antesDespues) {
      antesDespues.destruir();
      antesDespues = null;
    }
  }

  function aplicarComparador() {
    const activo = quiereComparador();
    // Antes que el comparador: su mapa óptico copia la cámara del principal ya en 2D.
    aplicarProyeccion();
    if (activo && !comparador) {
      comparador = crearComparador(contenedor, map, {
        optical: estado.optical,
        idioma: estado.idioma,
        aoi: estado.aoi,
      });
    } else if (activo && comparador) {
      comparador.actualizar({ optical: estado.optical, idioma: estado.idioma, aoi: estado.aoi });
    } else if (!activo && comparador) {
      comparador.destruir();
      comparador = null;
    }
  }

  function avisarVista() {
    if (!opciones.onViewChanged) return;
    const b = map.getBounds();
    const bbox: Bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()];
    opciones.onViewChanged({ bbox, zoom: map.getZoom() });
  }
  map.on("moveend", avisarVista);
  // También la vista inicial: sin movimiento, el buscador mundial no sabría qué se ve (prueba del 2026-11-14).
  map.once("load", () => window.setTimeout(avisarVista, 0));

  redibujarTextos();
  redibujarLeyenda();
  aplicarComparador();
  aplicarAntesDespues();

  return {
    actualizar(c: CambiosMapa) {
      if (c.aoi) {
        estado.aoi = validarBbox(c.aoi);
        (map.getSource("aoi") as maplibregl.GeoJSONSource | undefined)?.setData(
          contornoZona(estado.aoi),
        );
        (map.getSource("aoi-centro") as maplibregl.GeoJSONSource | undefined)?.setData(
          centroZona(estado.aoi),
        );
        map.fitBounds(bboxContinuo(estado.aoi), { padding: 32 });
      }
      if ("nombreZona" in c) estado.zona = c.nombreZona;
      if ("huellas" in c) {
        estado.huellas = huellasValidas(c.huellas);
        if (cargado) aplicarHuellas();
      }
      if ("causaNoObservable" in c) estado.causa = c.causaNoObservable;
      if ("desplazamientoEscena" in c) estado.avisoEscena = normalizarAvisoEscena(c.desplazamientoEscena);
      if (c.idioma) estado.idioma = c.idioma;
      if (c.activeLayer) estado.capa = c.activeLayer;
      const recargar = "layers" in c || (c.dataKind && c.dataKind !== estado.dataKind);
      if ("layers" in c) estado.layers = c.layers;
      if (c.dataKind) estado.dataKind = c.dataKind;
      if (c.idioma || "layers" in c || c.dataKind) ponerAtribucion();
      // La fuente "aoi" existe desde el evento load; antes, load ya aplicará las capas.
      if (recargar && map.getSource("aoi")) aplicarCapas();
      else aplicarVisibilidad();
      redibujarTextos();
      redibujarLeyenda();
      // Otra serie o idioma: se vuelve a pedir la historia del punto ya elegido.
      const cambiaSerie = "pixelUrl" in c && c.pixelUrl !== estado.pixelUrl;
      if ("pixelUrl" in c) estado.pixelUrl = c.pixelUrl;
      if (estado.punto && estado.pixelUrl && (cambiaSerie || c.idioma)) {
        seleccionar(estado.punto.lon, estado.punto.lat);
      } else if (cambiaSerie && !estado.pixelUrl) {
        ventana.remove();
      }
      if ("optical" in c) estado.optical = c.optical;
      if (c.compare) estado.compare = c.compare;
      if ("modo3d" in c) estado.modo3d = c.modo3d ?? false;
      if ("optical" in c || c.compare || c.idioma || c.aoi || "modo3d" in c) aplicarComparador();
      if ("antesDespues" in c) estado.antesDespues = c.antesDespues ?? false;
      if ("optical" in c || "antesDespues" in c || "layers" in c || c.idioma || c.aoi) aplicarAntesDespues();
    },
    fijarOpacidad,
    // «Encuadrar» (2026-11-15): alterna entre la zona que se analiza y el espacio. Lejos de la zona (o sin ver
    // su centro), se acerca hasta encuadrarla; ya encuadrada, se aleja al espacio con la Tierra centrada en ella.
    encuadrar: () => {
      const caja = bboxContinuo(estado.aoi);
      const objetivo = map.cameraForBounds(caja, { padding: 48 });
      const centro = map.getCenter();
      const [o, s, e, n] = caja;
      const dentro = centro.lng >= o && centro.lng <= e && centro.lat >= s && centro.lat <= n;
      const encuadrada = Boolean(objetivo?.zoom !== undefined && dentro && Math.abs(map.getZoom() - objetivo.zoom!) < 1);
      if (!encuadrada) {
        if (sinAnimacion()) map.fitBounds(caja, { padding: 48, pitch: 0, bearing: 0, animate: false });
        else map.fitBounds(caja, { padding: 48, pitch: 0, bearing: 0, duration: 1600 });
        return;
      }
      const destino = { center: [(o + e) / 2, Math.max(-60, Math.min(60, (s + n) / 2))] as [number, number], zoom: 1.3, pitch: 0, bearing: 0 };
      if (sinAnimacion()) map.jumpTo(destino);
      else map.flyTo({ ...destino, duration: 1800 });
    },
    mostrarMundo(m) {
      mundo = m;
      aplicarMundo();
    },
    rotularPunto(p, nombre) {
      if (!estado.punto || estado.punto.lon !== p.lon || estado.punto.lat !== p.lat) return;
      nombrePunto = nombre;
      const lugar = ventana.getElement()?.querySelector(".atlas-serie-lugar");
      if (lugar) lugar.textContent = nombre;
    },
    volarA(bbox) {
      const opciones = { padding: 48, maxZoom: 9 };
      if (sinAnimacion()) map.fitBounds(bbox, { ...opciones, animate: false });
      else map.fitBounds(bbox, { ...opciones, duration: 1600 });
    },
    destruir: () => {
      peticion?.abort();
      window.clearInterval(reloj);
      comparador?.destruir();
      comparador = null;
      antesDespues?.destruir();
      antesDespues = null;
      map.remove();
      contenedor.replaceChildren();
      contenedor.classList.remove("atlas-mapa", "atlas-con-3d", "atlas-plano");
    },
  };
}

/** Sin WebGL 2, MapLibre no dibuja nada: se dice y se deja la zona en texto, sin romper la página. */
function mapaSinWebgl(contenedor: HTMLElement, opciones: OpcionesMapa): MapaAtlas {
  let aoi = validarBbox(opciones.aoi);
  let zona = opciones.nombreZona;
  let idioma = opciones.idioma ?? "es";
  let dataKind = opciones.dataKind;
  let huellas = huellasValidas(opciones.huellas);
  contenedor.classList.add("atlas-mapa", "atlas-sin-mapa");
  const extension = document.createElement("div");
  extension.className = "atlas-extension";
  extension.append(document.createElement("strong"), document.createElement("span"));
  const sello = document.createElement("div");
  sello.className = "atlas-sintetico";
  sello.setAttribute("role", "status");
  const aviso = document.createElement("p");
  aviso.className = "atlas-aviso-sin-mapa";
  aviso.setAttribute("role", "alert");
  // Sin mapa, las huellas quedan en texto (RF-INT-16).
  const lista = document.createElement("ul");
  lista.className = "atlas-lista-huellas";
  contenedor.append(extension, sello, aviso, lista);
  function dibujar() {
    const t = TEXTOS[idioma];
    extension.querySelector("strong")!.textContent = t.extensionDe(zona ?? t.zonaPorDefecto);
    extension.querySelector("span")!.textContent = textoExtension(aoi);
    sello.textContent = t.sintetico;
    sello.hidden = dataKind !== "synthetic";
    aviso.textContent = t.sinMapa;
    lista.setAttribute("aria-label", t.huellas);
    lista.hidden = huellas.length === 0;
    lista.replaceChildren(
      ...huellas.map((h) => {
        const li = document.createElement("li");
        li.textContent = `${h.properties.series}: ${describirHuella(h.properties, idioma)}`;
        return li;
      }),
    );
  }
  dibujar();
  return {
    actualizar(c) {
      if (c.aoi) aoi = validarBbox(c.aoi);
      if ("nombreZona" in c) zona = c.nombreZona;
      if (c.idioma) idioma = c.idioma;
      if (c.dataKind) dataKind = c.dataKind;
      if ("huellas" in c) huellas = huellasValidas(c.huellas);
      dibujar();
    },
    fijarOpacidad: () => {},
    encuadrar: () => {},
    mostrarMundo: () => {},
    rotularPunto: () => {},
    volarA: () => {},
    destruir: () => {
      contenedor.replaceChildren();
      contenedor.classList.remove("atlas-mapa", "atlas-sin-mapa");
    },
  };
}
