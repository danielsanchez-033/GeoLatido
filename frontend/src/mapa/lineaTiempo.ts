// Línea de tiempo de pasadas, huecos y eventos (T-ATL-06, RF-ATL-06).
// Pinta GET /api/catalog/aois/{aoi}/timeline tal cual; Faro hace la petición, como con el óptico.
// Cada tipo de marca tiene su forma, así que nada depende solo del color, y debajo va todo en texto.
import type { EventVerdict } from "../api/client";
import type { components } from "./catalogo";
import { formatoFechaUtc } from "./optico";
import "./lineaTiempo.css";
import { TEXTOS_LINEA } from "./lineaTiempoTextos";
import type { Idioma } from "./textos";

type Esquemas = components["schemas"];
export type LineaTiempoApi = Esquemas["TimelineOut"];
export type PasadaApi = Esquemas["TimelinePass"];
export type ExcluidaApi = Esquemas["ExcludedPass"];
export type EstimacionApi = Esquemas["NextPassEstimate"];

/** Lo que la línea usa de `EventVerdict` (GET /api/verdicts/aois/{aoi}/events). */
export type EventoLinea = Pick<
  EventVerdict,
  "event_date" | "event_time" | "persistence_hours" | "assumption"
>;

const HORA = 3_600_000;
const DIA = 24 * HORA;

export interface FilaSerie {
  serie: string;
  pasadas: PasadaApi[];
  excluidas: ExcluidaApi[];
  estimaciones: EstimacionApi[];
}

export interface TramoEvento {
  inicio: number;
  fin: number;
  /** Sin `event_time`, el evento puede empezar en cualquier momento de su día. */
  inicioIncierto: boolean;
}

export interface ModeloLinea {
  /** Extremos del eje en ms UTC; null si no hay nada que pintar. */
  inicio: number | null;
  fin: number | null;
  filas: FilaSerie[];
  /** Fechas incluidas convertidas a [inicio del primer día, fin del último). */
  huecos: { inicio: number; fin: number; gap: Esquemas["TimelineGap"] }[];
  evento: TramoEvento | null;
}

/** "T048A-F015-4005-DHDH-P05023" → "T048A-F015": pista y fotograma. */
export function serieCorta(id: string): string {
  const partes = id.split("-");
  return partes.length > 2 ? partes.slice(0, 2).join("-") : id;
}

function diaUtc(fecha: string): number {
  return Date.parse(`${fecha}T00:00:00Z`);
}

/** Hora UTC "HH:MM" o "HH:MM:SS", con o sin "Z", a "HH:MM:SS". */
function horaUtc(hora: string): string {
  const h = hora.replace(/Z$/i, "");
  return h.length === 5 ? `${h}:00` : h.slice(0, 8);
}

export function tramoEvento(e: EventoLinea): TramoEvento {
  const horas = e.persistence_hours * HORA;
  if (e.event_time) {
    const inicio = Date.parse(`${e.event_date}T${horaUtc(e.event_time)}Z`);
    if (!Number.isNaN(inicio)) return { inicio, fin: inicio + horas, inicioIncierto: false };
  }
  const dia = diaUtc(e.event_date);
  return { inicio: dia, fin: dia + DIA + horas, inicioIncierto: true };
}

function porTiempo<T>(lista: T[], t: (x: T) => string): T[] {
  return [...lista].sort((a, b) => Date.parse(t(a)) - Date.parse(t(b)));
}

/** Ordena lo que llega de la API por serie y calcula el eje. `serie` deja solo esa fila. */
export function modeloLinea(
  datos: LineaTiempoApi,
  evento?: EventoLinea | null,
  serie?: string,
): ModeloLinea {
  const vale = (s: string) => !serie || s === serie;
  const ids = new Set<string>();
  for (const l of [datos.passes, datos.excluded, datos.next_pass_estimates]) {
    for (const x of l) if (vale(x.series)) ids.add(x.series);
  }
  const filas = [...ids].sort().map((s) => ({
    serie: s,
    pasadas: porTiempo(datos.passes.filter((p) => p.series === s), (p) => p.acquired_at),
    excluidas: porTiempo(datos.excluded.filter((p) => p.series === s), (p) => p.acquired_at),
    estimaciones: porTiempo(
      datos.next_pass_estimates.filter((p) => p.series === s),
      (p) => p.expected_at,
    ),
  }));
  const huecos = datos.gaps.map((gap) => ({
    inicio: diaUtc(gap.start),
    fin: diaUtc(gap.end) + DIA,
    gap,
  }));
  const tramo = evento ? tramoEvento(evento) : null;

  const tiempos: number[] = [];
  for (const f of filas) {
    for (const p of f.pasadas) tiempos.push(Date.parse(p.acquired_at));
    for (const p of f.excluidas) tiempos.push(Date.parse(p.acquired_at));
    for (const p of f.estimaciones) tiempos.push(Date.parse(p.expected_at));
  }
  // Los huecos solo amplían el eje si hay pasadas: sin ellas no hay nada que situar.
  if (tiempos.length) for (const h of huecos) tiempos.push(h.inicio, h.fin);
  if (tramo) tiempos.push(tramo.inicio, tramo.fin);
  const validos = tiempos.filter((t) => !Number.isNaN(t));
  if (!validos.length) return { inicio: null, fin: null, filas, huecos, evento: tramo };

  const min = Math.min(...validos);
  const max = Math.max(...validos);
  const margen = Math.max(DIA, (max - min) * 0.03);
  return { inicio: min - margen, fin: max + margen, filas, huecos, evento: tramo };
}

/** Marcas del eje: el día 1 de cada mes, o cada 7 días si el eje dura menos de 45 días. */
export function marcasEje(inicio: number, fin: number): number[] {
  const marcas: number[] = [];
  if (fin - inicio < 45 * DIA) {
    for (let t = Math.ceil(inicio / DIA) * DIA; t <= fin; t += 7 * DIA) marcas.push(t);
    return marcas;
  }
  const d = new Date(inicio);
  let t = Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1);
  while (t <= fin) {
    marcas.push(t);
    const m = new Date(t);
    t = Date.UTC(m.getUTCFullYear(), m.getUTCMonth() + 1, 1);
  }
  return marcas;
}

function etiquetaMarca(t: number, idioma: Idioma, semanal: boolean): string {
  const d = new Date(t);
  if (semanal) return d.toISOString().slice(5, 10);
  const mes = new Intl.DateTimeFormat(idioma, { month: "short", timeZone: "UTC" }).format(d);
  return d.getUTCMonth() === 0 ? `${mes} ${d.getUTCFullYear()}` : mes;
}

/** Latencia en horas enteras, con separador de miles del idioma (1.234 h o 1,234 h). */
function formatoHoras(h: number, idioma: Idioma): string {
  return Math.round(h).toLocaleString(idioma === "es" ? "es-MX" : "en-US");
}

// ---- Dibujo ----

export interface PasadaSeleccionada {
  series: string;
  granule_id: string;
  acquired_at: string;
}

export interface OpcionesLineaTiempo {
  /** Respuesta de GET /api/catalog/aois/{aoi}/timeline. null mientras carga o si falló. */
  timeline: LineaTiempoApi | null;
  /** Evento consultado (GET /api/verdicts/aois/{aoi}/events): banda y supuesto de duración. */
  evento?: EventoLinea | null;
  /** Deja solo la fila de esa serie. Por defecto, todas. */
  serie?: string;
  /** Por defecto, "es". */
  idioma?: Idioma;
  /** Momento actual en ms UTC, para la línea de "hoy". Por defecto, Date.now(). */
  ahora?: number;
  /** Con esto, cada pasada adquirida es un botón (clic o Enter). */
  onPassSelected?: (p: PasadaSeleccionada) => void;
}

export type CambiosLinea = Partial<Omit<OpcionesLineaTiempo, "onPassSelected">>;

export interface LineaTiempoAtlas {
  actualizar(cambios: CambiosLinea): void;
  destruir(): void;
}

const SVG = "http://www.w3.org/2000/svg";
const ANCHO = 960;
const IZQ = 16;
const DER = 16;
const ARRIBA = 18;
const ALTO_FILA = 44;
const ALTO_EJE = 26;

let contador = 0;

function el<K extends keyof SVGElementTagNameMap>(
  nombre: K,
  atributos: Record<string, string | number>,
  padre?: Element,
): SVGElementTagNameMap[K] {
  const n = document.createElementNS(SVG, nombre);
  for (const [k, v] of Object.entries(atributos)) n.setAttribute(k, String(v));
  padre?.append(n);
  return n;
}

function titulo(padre: Element, texto: string) {
  el("title", {}, padre).textContent = texto;
}

function html<K extends keyof HTMLElementTagNameMap>(
  nombre: K,
  clase: string,
  texto?: string,
): HTMLElementTagNameMap[K] {
  const n = document.createElement(nombre);
  if (clase) n.className = clase;
  if (texto !== undefined) n.textContent = texto;
  return n;
}

/** Símbolo de una marca: lo usan la gráfica y la leyenda, para que coincidan. */
function simbolo(tipo: "pasada" | "excluida" | "estimada", x: number, y: number, padre: Element) {
  if (tipo === "pasada") return el("circle", { cx: x, cy: y, r: 6, class: "atlas-linea-pasada" }, padre);
  if (tipo === "estimada")
    return el("circle", { cx: x, cy: y, r: 6, class: "atlas-linea-estimada" }, padre);
  return el(
    "path",
    { d: `M${x - 5} ${y - 5}L${x + 5} ${y + 5}M${x + 5} ${y - 5}L${x - 5} ${y + 5}`, class: "atlas-linea-excluida" },
    padre,
  );
}

function iconoLeyenda(clase: string, dibujar: (svg: SVGSVGElement) => void): SVGSVGElement {
  const svg = el("svg", { viewBox: "0 0 20 14", width: 20, height: 14, "aria-hidden": "true", class: clase });
  dibujar(svg);
  return svg;
}

export function crearLineaTiempo(
  contenedor: HTMLElement,
  opciones: OpcionesLineaTiempo,
): LineaTiempoAtlas {
  const id = `atlas-linea-${++contador}`;
  let estado: OpcionesLineaTiempo = { ...opciones };

  const raiz = html("section", "atlas-linea");
  raiz.setAttribute("aria-labelledby", `${id}-titulo`);
  contenedor.append(raiz);

  raiz.addEventListener("click", (ev) => elegir(ev.target));
  raiz.addEventListener("keydown", (ev) => {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    if (elegir(ev.target)) ev.preventDefault();
  });

  function elegir(objetivo: EventTarget | null): boolean {
    const marca = (objetivo as Element | null)?.closest?.("[data-granulo]");
    if (!marca || !estado.onPassSelected) return false;
    estado.onPassSelected({
      series: marca.getAttribute("data-serie") ?? "",
      granule_id: marca.getAttribute("data-granulo") ?? "",
      acquired_at: marca.getAttribute("data-adquirida") ?? "",
    });
    return true;
  }

  function dibujar() {
    const idioma = estado.idioma ?? "es";
    const t = TEXTOS_LINEA[idioma];
    raiz.replaceChildren();
    raiz.lang = idioma;

    const h = html("h3", "atlas-linea-titulo", t.titulo);
    h.id = `${id}-titulo`;
    raiz.append(h);

    if (!estado.timeline) return;
    const m = modeloLinea(estado.timeline, estado.evento, estado.serie);
    const pasadas = m.filas.reduce((n, f) => n + f.pasadas.length, 0);
    if (m.inicio === null || m.fin === null || !m.filas.length) {
      raiz.append(html("p", "atlas-linea-vacia", t.sinPasadas));
      dibujarNotas(m, idioma);
      return;
    }

    const inicio = m.inicio;
    const fin = m.fin;
    const x = (ms: number) => IZQ + ((ms - inicio) / (fin - inicio)) * (ANCHO - IZQ - DER);
    const altoFilas = m.filas.length * ALTO_FILA;
    const alto = ARRIBA + altoFilas + ALTO_EJE;

    const svg = el("svg", {
      viewBox: `0 0 ${ANCHO} ${alto}`,
      class: "atlas-linea-grafica",
      role: "group",
      "aria-labelledby": `${id}-aria`,
    });
    const aria = el("title", { id: `${id}-aria` }, svg);
    aria.textContent = t.graficaAria(
      pasadas,
      m.filas.length,
      new Date(inicio).toISOString().slice(0, 10),
      new Date(fin).toISOString().slice(0, 10),
    );

    const defs = el("defs", {}, svg);
    const trama = el(
      "pattern",
      { id: `${id}-trama`, width: 8, height: 8, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" },
      defs,
    );
    el("rect", { width: 8, height: 8, class: "atlas-linea-trama-fondo" }, trama);
    el("line", { x1: 0, y1: 0, x2: 0, y2: 8, class: "atlas-linea-trama-raya" }, trama);

    // Eje
    const semanal = fin - inicio < 45 * DIA;
    const eje = el("g", { class: "atlas-linea-eje", "aria-hidden": "true" }, svg);
    const yEje = ARRIBA + altoFilas;
    el("line", { x1: IZQ, x2: ANCHO - DER, y1: yEje, y2: yEje }, eje);
    for (const marca of marcasEje(inicio, fin)) {
      el("line", { x1: x(marca), x2: x(marca), y1: ARRIBA - 8, y2: yEje + 4, class: "atlas-linea-guia" }, eje);
      el("text", { x: x(marca), y: yEje + 18, "text-anchor": "middle" }, eje).textContent =
        etiquetaMarca(marca, idioma, semanal);
    }

    // Huecos y evento, a lo alto de todas las filas
    for (const hueco of m.huecos) {
      const r = el(
        "rect",
        {
          x: x(hueco.inicio),
          y: ARRIBA - 8,
          width: Math.max(2, x(hueco.fin) - x(hueco.inicio)),
          height: altoFilas + 8,
          fill: `url(#${id}-trama)`,
          class: "atlas-linea-hueco",
        },
        svg,
      );
      titulo(r, t.huecoDe(hueco.gap.start, hueco.gap.end, hueco.gap.source));
    }
    if (m.evento && estado.evento) {
      const e = m.evento;
      const r = el(
        "rect",
        {
          x: x(e.inicio),
          y: ARRIBA - 8,
          width: Math.max(3, x(e.fin) - x(e.inicio)),
          height: altoFilas + 8,
          class: e.inicioIncierto ? "atlas-linea-evento atlas-linea-evento-incierto" : "atlas-linea-evento",
        },
        svg,
      );
      titulo(r, textoEvento(estado.evento, idioma));
    }

    const ahora = estado.ahora ?? Date.now();
    if (ahora >= inicio && ahora <= fin) {
      const g = el("g", { class: "atlas-linea-hoy", "aria-hidden": "true" }, svg);
      el("line", { x1: x(ahora), x2: x(ahora), y1: ARRIBA - 12, y2: yEje }, g);
      el("text", { x: x(ahora) + 4, y: ARRIBA - 4 }, g).textContent = t.hoy;
    }

    // Filas
    m.filas.forEach((f, i) => {
      const y = ARRIBA + i * ALTO_FILA + ALTO_FILA / 2 + 6;
      const g = el("g", { class: "atlas-linea-fila" }, svg);
      el("text", { x: IZQ, y: y - 14, class: "atlas-linea-serie" }, g).textContent = serieCorta(f.serie);
      el("line", { x1: IZQ, x2: ANCHO - DER, y1: y, y2: y, class: "atlas-linea-pista" }, g);
      const corta = serieCorta(f.serie);
      for (const p of f.pasadas) {
        const fecha = formatoFechaUtc(p.acquired_at);
        const c = simbolo("pasada", x(Date.parse(p.acquired_at)), y, g);
        if (!p.contains_aoi) c.classList.add("atlas-linea-pasada-parcial");
        titulo(c, describirPasada(p, idioma));
        if (estado.onPassSelected) {
          c.setAttribute("tabindex", "0");
          c.setAttribute("role", "button");
          c.setAttribute("aria-label", t.seleccionarPasada(fecha, corta));
          c.setAttribute("data-granulo", p.granule_id);
          c.setAttribute("data-serie", p.series);
          c.setAttribute("data-adquirida", p.acquired_at);
        }
      }
      for (const p of f.excluidas) {
        const c = simbolo("excluida", x(Date.parse(p.acquired_at)), y, g);
        titulo(c, describirExcluida(p, idioma));
      }
      for (const p of f.estimaciones) {
        const c = simbolo("estimada", x(Date.parse(p.expected_at)), y, g);
        titulo(c, describirEstimacion(p, idioma).join(" "));
      }
    });
    // En pantallas estrechas la gráfica no se encoge hasta ser ilegible: se desplaza en horizontal.
    const marco = html("div", "atlas-linea-desplazable");
    marco.tabIndex = 0;
    marco.setAttribute("role", "region");
    // Nombre propio (la descripción de la gráfica): con el mismo título que la sección, axe lo marca como
    // región duplicada (landmark-unique, prueba de uso del 2026-11-14).
    marco.setAttribute("aria-labelledby", `${id}-aria`);
    marco.append(svg);
    raiz.append(marco);

    // Leyenda: forma y nombre de cada marca
    const leyenda = html("ul", "atlas-linea-leyenda");
    const entrada = (icono: SVGSVGElement, texto: string) => {
      const li = html("li", "");
      li.append(icono, html("span", "", texto));
      leyenda.append(li);
    };
    entrada(iconoLeyenda("", (s) => simbolo("pasada", 10, 7, s)), t.pasada);
    if (m.filas.some((f) => f.excluidas.length)) entrada(iconoLeyenda("", (s) => simbolo("excluida", 10, 7, s)), t.excluida);
    if (m.filas.some((f) => f.estimaciones.length)) entrada(iconoLeyenda("", (s) => simbolo("estimada", 10, 7, s)), t.estimada);
    if (m.huecos.length)
      entrada(
        iconoLeyenda("", (s) => el("rect", { x: 1, y: 1, width: 18, height: 12, fill: `url(#${id}-trama)`, class: "atlas-linea-hueco" }, s)),
        t.hueco,
      );
    if (m.evento) entrada(iconoLeyenda("", (s) => el("rect", { x: 1, y: 1, width: 18, height: 12, class: "atlas-linea-evento" }, s)), t.evento);
    raiz.append(leyenda);

    dibujarNotas(m, idioma);

    // Lista completa de pasadas: la alternativa en texto de la gráfica
    const detalles = html("details", "atlas-linea-lista");
    detalles.append(html("summary", "", `${t.verLista} (${pasadas})`));
    for (const f of m.filas) {
      detalles.append(html("h4", "", t.pasadasDeSerie(f.serie)));
      const ol = html("ol", "");
      for (const p of f.pasadas) ol.append(html("li", "", describirPasada(p, idioma)));
      detalles.append(ol);
    }
    raiz.append(detalles);
  }

  /** Lo que la gráfica no puede dejar solo en un título emergente: va siempre a la vista. */
  function dibujarNotas(m: ModeloLinea, idioma: Idioma) {
    const t = TEXTOS_LINEA[idioma];
    const notas = html("ul", "atlas-linea-notas");
    if (estado.evento && m.evento) {
      const li = html("li", "atlas-linea-nota-evento", textoEvento(estado.evento, idioma));
      // assumption.text ya viene redactado en el idioma pedido, con su «Supuesto:» delante.
      li.append(html("p", "atlas-linea-supuesto", estado.evento.assumption.text));
      notas.append(li);
    }
    for (const f of m.filas)
      for (const p of f.estimaciones) {
        const [primera, ...resto] = describirEstimacion(p, idioma);
        const li = html("li", "atlas-linea-nota-estimada", primera);
        li.append(html("small", "", ` ${resto.join(" ")}`));
        notas.append(li);
      }
    for (const f of m.filas)
      for (const p of f.excluidas) {
        const li = html("li", "atlas-linea-nota-excluida", describirExcluida(p, idioma));
        li.append(html("small", "", ` ${p.evidence} ${t.comprobada(p.checked_on)}`));
        notas.append(li);
      }
    for (const h of m.huecos) notas.append(html("li", "atlas-linea-nota-hueco", t.huecoDe(h.gap.start, h.gap.end, h.gap.source)));
    if (m.filas.some((f) => f.pasadas.length))
      notas.append(html("li", "atlas-linea-nota-publicacion", t.notaPublicacion));
    if (notas.childElementCount) raiz.append(notas);
  }

  dibujar();

  return {
    actualizar(cambios) {
      estado = { ...estado, ...cambios };
      dibujar();
    },
    destruir() {
      raiz.remove();
    },
  };
}

export function describirPasada(p: PasadaApi, idioma: Idioma): string {
  const t = TEXTOS_LINEA[idioma];
  const partes = [t.pasadaDe(formatoFechaUtc(p.acquired_at), serieCorta(p.series))];
  partes.push(p.latency_hours === null ? t.sinPublicar : t.latencia(formatoHoras(p.latency_hours, idioma)));
  if (!p.contains_aoi) partes.push(t.noContieneZona);
  return partes.join("; ");
}

export function describirExcluida(p: ExcluidaApi, idioma: Idioma): string {
  const t = TEXTOS_LINEA[idioma];
  return t.excluidaDe(formatoFechaUtc(p.acquired_at), serieCorta(p.series), t.motivos[p.reason] ?? p.reason);
}

/** Primera línea: cuándo; el resto: que es una estimación y qué dice el plan, con su fecha de consulta. */
export function describirEstimacion(p: EstimacionApi, idioma: Idioma): string[] {
  const t = TEXTOS_LINEA[idioma];
  const plan = p.observation_plan;
  const lineas = [t.estimadaDe(formatoFechaUtc(p.expected_at), serieCorta(p.series)), t.baseEstimacion, t.planes[plan.status]];
  if (plan.status === "planned" || plan.status === "partial") lineas.push(t.planNoGarantiza);
  lineas.push(plan.checked_at ? t.planConsultado(formatoFechaUtc(plan.checked_at)) : t.planSinConsultar);
  return lineas;
}

export function textoEvento(e: EventoLinea, idioma: Idioma): string {
  const t = TEXTOS_LINEA[idioma];
  const tramo = tramoEvento(e);
  return tramo.inicioIncierto
    ? t.eventoSinHora(e.event_date, e.persistence_hours)
    : t.eventoDe(formatoFechaUtc(new Date(tramo.inicio).toISOString()), e.persistence_hours);
}
