// Comparador antes/después con deslizador, recortado a la zona (corrección de diseño del 2026-11-14).
//
// Dos mapas MapLibre transparentes, sin interacción propia, siguen la cámara del principal (también su
// proyección: globo o plano). Uno pinta la escena óptica de después y otro la de antes. Cada uno se
// recorta con `clip-path` al contorno de la zona proyectado en pantalla: el de después a toda la zona y
// el de antes a la parte al oeste del deslizador. El deslizador no es una línea vertical de pantalla:
// es un meridiano dentro de la zona, así que en 3D se inclina y se curva con el globo y la cámara, y
// funciona igual en 2D. Fuera de la zona se sigue viendo el mapa principal.
import * as maplibregl from "maplibre-gl";
import type { StyleSpecification } from "maplibre-gl";
import type { MapProps, VistaOptica } from "../types/map";
import { plantillaOptica } from "./comparador";
import { bboxContinuo, fuenteDatos, ZOOM_MAXIMO_MAPA } from "./mapaBase";
import { formatoFechaUtc, limitarPosicion, moverConTecla, POSICION_INICIAL } from "./optico";
import type { Idioma } from "./textos";
import type { Bbox } from "./tipos";

type Lado = "before" | "after";

/** Qué pinta cada lado del deslizador (2026-11-15): una escena óptica o una capa de radar de la zona. */
export type FuenteComparador = "before" | "after" | "change_hh" | "change_hv" | "subsidence";
const FUENTES: FuenteComparador[] = ["before", "after", "change_hh", "change_hv", "subsidence"];

const TEXTOS: Record<
  Idioma,
  {
    antes: string; despues: string; sinEscena: string; deslizador: string; ayuda: string;
    izquierda: string; derecha: string; izquierdaCorta: string; derechaCorta: string; fuentes: Record<FuenteComparador, string>;
  }
> = {
  es: {
    antes: "Antes",
    despues: "Después",
    sinEscena: "sin escena óptica",
    deslizador: "Comparar antes y después",
    ayuda: "Arrastra o usa las flechas para mover la división dentro de la zona",
    izquierda: "Lado izquierdo del comparador",
    derecha: "Lado derecho del comparador",
    izquierdaCorta: "Izquierda",
    derechaCorta: "Derecha",
    fuentes: { before: "Óptico antes", after: "Óptico después", change_hh: "Cambio en HH", change_hv: "Cambio en HV", subsidence: "Hundimiento" },
  },
  en: {
    antes: "Before",
    despues: "After",
    sinEscena: "no optical scene",
    deslizador: "Compare before and after",
    ayuda: "Drag or use the arrow keys to move the split inside the area",
    izquierda: "Left side of the comparator",
    derecha: "Right side of the comparator",
    izquierdaCorta: "Left",
    derechaCorta: "Right",
    fuentes: { before: "Optical before", after: "Optical after", change_hh: "HH change", change_hv: "HV change", subsidence: "Subsidence" },
  },
};

/** Puntos por lado al proyectar el contorno: el globo curva los bordes de la zona. */
const PUNTOS_POR_LADO = 24;

export interface OpcionesAntesDespues {
  optical: MapProps["optical"];
  idioma: Idioma;
  aoi: Bbox;
  /** Capas de radar que se pueden comparar (plantillas XYZ ya absolutas). Hundimiento solo si la zona lo tiene. */
  capas?: { change_hh?: string; change_hv?: string; subsidence?: string };
}

/** Fuentes que se pueden elegir con lo que hay: una escena óptica sin teselas o una capa sin plantilla no salen. */
export function fuentesDisponibles(o: Pick<OpcionesAntesDespues, "optical" | "capas">): FuenteComparador[] {
  return FUENTES.filter((f) =>
    f === "before" || f === "after" ? Boolean(o.optical?.[f]?.tiles.length) : Boolean(o.capas?.[f]),
  );
}

export interface AntesDespues {
  actualizar(c: Partial<OpcionesAntesDespues>): void;
  destruir(): void;
}

/** Contorno del rectángulo [o, s, e, n] con puntos intermedios, en sentido horario desde el noroeste. */
export function contornoDenso(o: number, s: number, e: number, n: number, k = PUNTOS_POR_LADO): [number, number][] {
  const pts: [number, number][] = [];
  for (let i = 0; i < k; i++) pts.push([o + ((e - o) * i) / k, n]);
  for (let i = 0; i < k; i++) pts.push([e, n - ((n - s) * i) / k]);
  for (let i = 0; i < k; i++) pts.push([e - ((e - o) * i) / k, s]);
  for (let i = 0; i < k; i++) pts.push([o, s + ((n - s) * i) / k]);
  return pts;
}

/** Longitud del deslizador para una posición de 0 (oeste) a 100 (este). */
export function longitudDivision(aoi: Bbox, posicion: number): number {
  const [o, , e] = bboxContinuo(aoi);
  return o + ((e - o) * limitarPosicion(posicion)) / 100;
}

/** Posición (0-100) para una longitud, limitada a la zona. */
export function posicionDeLongitud(aoi: Bbox, lon: number): number {
  const [o, , e] = bboxContinuo(aoi);
  return limitarPosicion(((lon - o) / (e - o)) * 100);
}

function estiloTransparente(proyeccion: "globe" | "mercator"): StyleSpecification {
  // Sin capa de fondo: fuera de la escena el lienzo queda transparente y se ve el mapa principal.
  return { version: 8, projection: { type: proyeccion }, sources: {}, layers: [] };
}

function tipoProyeccion(map: maplibregl.Map): "globe" | "mercator" {
  return map.getProjection()?.type === "globe" ? "globe" : "mercator";
}

export function crearAntesDespues(
  contenedor: HTMLElement,
  principal: maplibregl.Map,
  opciones: OpcionesAntesDespues,
): AntesDespues {
  const estado = { ...opciones, posicion: POSICION_INICIAL };
  // Por omisión, antes a la izquierda y después a la derecha; si falta una escena, la primera capa que haya.
  const fuente: Record<Lado, FuenteComparador> = { before: "before", after: "after" };
  function fuenteValida(lado: Lado): FuenteComparador | null {
    const disponibles = fuentesDisponibles(estado);
    if (disponibles.includes(fuente[lado])) return fuente[lado];
    const otra = disponibles.find((f) => f !== fuente[lado === "before" ? "after" : "before"]) ?? disponibles[0];
    return otra ?? null;
  }
  const raiz = principal.getContainer();

  function crearCapa(lado: Lado) {
    const capa = document.createElement("div");
    capa.className = `atlas-ad-capa atlas-ad-${lado}`;
    capa.setAttribute("aria-hidden", "true");
    const lienzo = document.createElement("div");
    lienzo.className = "atlas-lienzo";
    capa.append(lienzo);
    const map = new maplibregl.Map({
      container: lienzo,
      style: estiloTransparente(tipoProyeccion(principal)),
      center: principal.getCenter(),
      zoom: principal.getZoom(),
      bearing: principal.getBearing(),
      pitch: principal.getPitch(),
      maxZoom: ZOOM_MAXIMO_MAPA,
      // Memoria: igual que el mapa principal, y caché pequeña porque solo pinta la zona.
      pixelRatio: Math.min(window.devicePixelRatio || 1, 1.5),
      maxTileCacheSize: 80,
      interactive: false,
      attributionControl: false,
      fadeDuration: 0,
    });
    return { lado, capa, map, cargado: false, capas: [] as string[] };
  }

  // Después debajo y antes encima: el de antes se recorta a la parte oeste.
  const despues = crearCapa("after");
  const antes = crearCapa("before");
  const vistas = [despues, antes];

  // Contorno de la zona y línea de división, dibujados sobre las dos escenas.
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "atlas-ad-trazo");
  svg.setAttribute("aria-hidden", "true");
  const contorno = document.createElementNS(svg.namespaceURI, "polygon");
  contorno.setAttribute("class", "atlas-ad-contorno");
  const linea = document.createElementNS(svg.namespaceURI, "polyline");
  linea.setAttribute("class", "atlas-ad-linea");
  svg.append(contorno, linea);

  // Las esquinas de la zona dicen qué se ve en cada lado; se elige en un panel fijo arriba, porque al acercarse
  // las esquinas quedan fuera de pantalla o bajo los paneles. Lo elegido se pinta encima en su lado.
  const etiquetaAntes = document.createElement("span");
  etiquetaAntes.className = "atlas-ad-etiqueta atlas-ad-etiqueta-antes";
  const etiquetaDespues = document.createElement("span");
  etiquetaDespues.className = "atlas-ad-etiqueta atlas-ad-etiqueta-despues";
  const panelFuentes = document.createElement("div");
  panelFuentes.className = "atlas-ad-panel";
  panelFuentes.setAttribute("role", "group");
  // Que los clics en el panel no lleguen al mapa (no deben elegir un punto).
  for (const ev of ["pointerdown", "click", "dblclick", "wheel"]) panelFuentes.addEventListener(ev, (e) => e.stopPropagation());
  function crearSelector(lado: Lado) {
    const caja = document.createElement("label");
    caja.className = "atlas-ad-campo";
    const nombre = document.createElement("span");
    const select = document.createElement("select");
    select.className = "atlas-ad-selector";
    select.addEventListener("change", () => {
      fuente[lado] = select.value as FuenteComparador;
      aplicarEscena(lado === "before" ? antes : despues);
      redibujarTextos();
    });
    caja.append(nombre, select);
    panelFuentes.append(caja);
    return { nombre, select };
  }
  const selectorAntes = crearSelector("before");
  const selectorDespues = crearSelector("after");
  const atribucion = document.createElement("span");
  atribucion.className = "atlas-ad-atribucion";

  const asa = document.createElement("div");
  asa.className = "atlas-ad-asa";
  asa.tabIndex = 0;
  asa.setAttribute("role", "slider");
  asa.setAttribute("aria-valuemin", "0");
  asa.setAttribute("aria-valuemax", "100");
  asa.setAttribute("aria-orientation", "horizontal");
  asa.innerHTML =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 7l-5 5 5 5M15 7l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  raiz.after(despues.capa, antes.capa, svg, etiquetaAntes, etiquetaDespues, atribucion, asa, panelFuentes);
  contenedor.classList.add("atlas-con-antes-despues");

  // ---- Escenas ----
  function aplicarEscena(v: (typeof vistas)[number]) {
    if (!v.cargado) return;
    for (const id of v.capas) {
      if (v.map.getLayer(id)) v.map.removeLayer(id);
      if (v.map.getSource(id)) v.map.removeSource(id);
    }
    v.capas = [];
    const elegida = fuenteValida(v.lado);
    if (elegida === "before" || elegida === "after") {
      const vista: VistaOptica | undefined = estado.optical?.[elegida];
      vista?.tiles.forEach((plantilla, i) => {
        const id = `ad-${v.lado}-${i}`;
        v.map.addSource(id, fuenteDatos(plantillaOptica(plantilla), estado.aoi));
        v.map.addLayer({ id, type: "raster", source: id, paint: { "raster-fade-duration": 0 } });
        v.capas.push(id);
      });
    } else if (elegida && estado.capas?.[elegida]) {
      // Capa de radar de la zona (cambio en dB o hundimiento): misma plantilla que el mapa principal.
      const id = `ad-${v.lado}-radar`;
      v.map.addSource(id, fuenteDatos(estado.capas[elegida]!, estado.aoi, { ampliar: true }));
      v.map.addLayer({ id, type: "raster", source: id, paint: { "raster-fade-duration": 0, "raster-resampling": "linear" } });
      v.capas.push(id);
    }
  }
  for (const v of vistas) {
    v.map.on("load", () => {
      v.cargado = true;
      aplicarEscena(v);
      sincronizar();
    });
  }

  // ---- Cámara: la misma que el principal, también la proyección ----
  function sincronizar() {
    const tipo = tipoProyeccion(principal);
    for (const v of vistas) {
      if (v.cargado && tipoProyeccion(v.map) !== tipo) v.map.setProjection({ type: tipo });
      v.map.jumpTo({
        center: principal.getCenter(),
        zoom: principal.getZoom(),
        bearing: principal.getBearing(),
        pitch: principal.getPitch(),
      });
    }
  }
  let destruido = false;
  const alRedimensionar = () => {
    if (destruido) return;
    for (const v of vistas) v.map.resize();
    recortar();
  };
  principal.on("move", sincronizar);
  principal.on("resize", alRedimensionar);
  // MapLibre toma 400 × 300 px si el lienzo aún no tiene tamaño al crearse (pasaba al activar el comparador):
  // las escenas de antes y después solo ocupaban la esquina de arriba a la izquierda y el resto mostraba el mapa
  // base a los dos lados. Cada lienzo se ajusta cuando cambia su propio tamaño, no solo el del mapa principal.
  const observador = typeof ResizeObserver === "function" ? new ResizeObserver(alRedimensionar) : null;
  for (const v of vistas) observador?.observe(v.capa);
  requestAnimationFrame(alRedimensionar);

  // ---- Recorte y deslizador en pantalla ----
  const proyectar = (pts: [number, number][]) => pts.map(([lon, lat]) => principal.project([lon, lat]));
  const aPoligono = (pts: maplibregl.Point[]) =>
    `polygon(${pts.map((p) => `${p.x.toFixed(1)}px ${p.y.toFixed(1)}px`).join(", ")})`;

  function recortar() {
    const [o, s, e, n] = bboxContinuo(estado.aoi);
    const division = longitudDivision(estado.aoi, estado.posicion);
    const zona = proyectar(contornoDenso(o, s, e, n));
    // Cada lado solo enseña su parte: si la capa de la izquierda es transparente (cambio cerca de 0 dB), debajo se
    // ve el mapa principal, no la capa del otro lado.
    despues.capa.style.clipPath =
      division < e ? aPoligono(proyectar(contornoDenso(division, s, e, n))) : "polygon(0 0, 0 0, 0 0)";
    // Si el oeste queda vacío (posición 0), un polígono degenerado no deja ver nada de antes.
    antes.capa.style.clipPath =
      division > o ? aPoligono(proyectar(contornoDenso(o, s, division, n))) : "polygon(0 0, 0 0, 0 0)";
    contorno.setAttribute("points", zona.map((p) => `${p.x},${p.y}`).join(" "));

    const meridiano: [number, number][] = [];
    for (let i = 0; i <= PUNTOS_POR_LADO; i++) meridiano.push([division, n - ((n - s) * i) / PUNTOS_POR_LADO]);
    const lineaPx = proyectar(meridiano);
    linea.setAttribute("points", lineaPx.map((p) => `${p.x},${p.y}`).join(" "));

    const medio = principal.project([division, (s + n) / 2]);
    asa.style.left = `${medio.x}px`;
    asa.style.top = `${medio.y}px`;

    // Etiquetas en las esquinas de arriba de la zona, por dentro.
    const no = principal.project([o, n]);
    const ne = principal.project([e, n]);
    const so = principal.project([o, s]);
    const se = principal.project([e, s]);
    etiquetaAntes.style.left = `${no.x}px`;
    etiquetaAntes.style.top = `${no.y}px`;
    etiquetaDespues.style.left = `${ne.x}px`;
    etiquetaDespues.style.top = `${ne.y}px`;
    atribucion.style.left = `${(so.x + se.x) / 2}px`;
    atribucion.style.top = `${Math.max(so.y, se.y)}px`;
  }
  principal.on("render", recortar);

  function textoFuente(f: FuenteComparador): string {
    const t = TEXTOS[estado.idioma];
    if (f !== "before" && f !== "after") return t.fuentes[f];
    const v = estado.optical?.[f];
    if (!v || v.tiles.length === 0) return `${t.fuentes[f]} · ${t.sinEscena}`;
    return v.acquiredAt ? `${t.fuentes[f]} · ${formatoFechaUtc(v.acquiredAt).slice(0, 10)}` : t.fuentes[f];
  }

  function rellenarSelector(sel: HTMLSelectElement, lado: Lado, etiqueta: string) {
    const disponibles = fuentesDisponibles(estado);
    const elegida = fuenteValida(lado);
    sel.replaceChildren(
      ...disponibles.map((f) => {
        const o = document.createElement("option");
        o.value = f;
        o.textContent = textoFuente(f);
        o.selected = f === elegida;
        return o;
      }),
    );
    sel.setAttribute("aria-label", etiqueta);
    sel.title = etiqueta;
  }

  function redibujarTextos() {
    const t = TEXTOS[estado.idioma];
    rellenarSelector(selectorAntes.select, "before", t.izquierda);
    rellenarSelector(selectorDespues.select, "after", t.derecha);
    selectorAntes.nombre.textContent = t.izquierdaCorta;
    selectorDespues.nombre.textContent = t.derechaCorta;
    panelFuentes.setAttribute("aria-label", t.deslizador);
    const izq = fuenteValida("before");
    const der = fuenteValida("after");
    etiquetaAntes.textContent = izq ? textoFuente(izq) : t.sinEscena;
    etiquetaDespues.textContent = der ? textoFuente(der) : t.sinEscena;
    asa.setAttribute("aria-label", t.deslizador);
    asa.title = t.ayuda;
    // Licencia Copernicus: siempre junto a la imagen.
    // Solo de las escenas ópticas que se ven en algún lado.
    const vistas = (["before", "after"] as const).map((l) => fuenteValida(l));
    const textos = new Set(
      (["before", "after"] as const)
        .filter((f) => vistas.includes(f))
        .map((l) => estado.optical?.[l]?.attribution)
        .filter((x): x is string => Boolean(x)),
    );
    atribucion.textContent = [...textos].join(" · ");
    atribucion.hidden = textos.size === 0;
  }

  function aplicarPosicion(p: number) {
    estado.posicion = limitarPosicion(p);
    asa.setAttribute("aria-valuenow", String(Math.round(estado.posicion)));
    asa.setAttribute(
      "aria-valuetext",
      `${TEXTOS[estado.idioma].antes} ${Math.round(estado.posicion)} %, ${TEXTOS[estado.idioma].despues} ${Math.round(100 - estado.posicion)} %`,
    );
    recortar();
  }

  // ---- Arrastre y teclado ----
  asa.addEventListener("pointerdown", (ev) => {
    ev.preventDefault();
    asa.setPointerCapture(ev.pointerId);
    asa.classList.add("atlas-ad-arrastrando");
  });
  asa.addEventListener("pointermove", (ev) => {
    if (!asa.hasPointerCapture(ev.pointerId)) return;
    const caja = raiz.getBoundingClientRect();
    const lngLat = principal.unproject([ev.clientX - caja.left, ev.clientY - caja.top]);
    aplicarPosicion(posicionDeLongitud(estado.aoi, lngLat.lng));
  });
  const soltar = (ev: PointerEvent) => {
    if (asa.hasPointerCapture(ev.pointerId)) asa.releasePointerCapture(ev.pointerId);
    asa.classList.remove("atlas-ad-arrastrando");
  };
  asa.addEventListener("pointerup", soltar);
  asa.addEventListener("pointercancel", soltar);
  asa.addEventListener("keydown", (ev) => {
    const p = moverConTecla(estado.posicion, ev.key);
    if (p === null) return;
    ev.preventDefault();
    aplicarPosicion(p);
  });

  redibujarTextos();
  aplicarPosicion(estado.posicion);
  sincronizar();

  return {
    actualizar(c) {
      const cambiaEscena = "optical" in c || "capas" in c || (c.aoi && c.aoi !== estado.aoi);
      Object.assign(estado, c);
      if (cambiaEscena) for (const v of vistas) aplicarEscena(v);
      redibujarTextos();
      recortar();
    },
    destruir() {
      principal.off("move", sincronizar);
      principal.off("resize", alRedimensionar);
      principal.off("render", recortar);
      destruido = true;
      observador?.disconnect();
      for (const v of vistas) {
        v.map.remove();
        v.capa.remove();
      }
      svg.remove();
      etiquetaAntes.remove();
      etiquetaDespues.remove();
      panelFuentes.remove();
      atribucion.remove();
      asa.remove();
      contenedor.classList.remove("atlas-con-antes-despues");
    },
  };
}
