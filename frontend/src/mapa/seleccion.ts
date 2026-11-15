// Selección de punto y serie por píxel (T-ATL-04, RF-ATL-04).
import type { Idioma } from "./textos";
import { TEXTOS } from "./textos";

/** Respuesta de GET /aois/{aoi}/series/{series_id}/pixel (contracts/verdicts.openapi.json). */
export interface SeriePixel {
  aoi: string;
  series: string;
  lon: number;
  lat: number;
  data_kind: "real" | "synthetic";
  values: { date: string; hh_db: number | null; hv_db: number | null }[];
  changes: { pair: string; state: string | null }[];
}

/** Redondea a 5 decimales (constitución V.3), sin el "-0" de los valores muy cercanos a cero. */
export function redondear5(x: number): number {
  const r = Math.round(x * 1e5) / 1e5;
  return r === 0 ? 0 : r;
}

/** Normaliza la longitud al rango [-180, 180] (el mapa puede dar vueltas al mundo) y redondea. */
export function puntoSeleccionado(lng: number, lat: number): { lon: number; lat: number } {
  const lon = ((((lng + 180) % 360) + 360) % 360) - 180;
  return { lon: redondear5(lon), lat: redondear5(lat) };
}

export function urlPixel(base: string, p: { lon: number; lat: number }): string {
  const sep = base.includes("?") ? "&" : "?";
  return `${base}${sep}lon=${p.lon}&lat=${p.lat}`;
}

/** "20260617_20260629" → ["2026-06-17", "2026-06-29"]. Si no tiene esa forma, se devuelve tal cual. */
export function fechasDelPar(id: string): [string, string] | null {
  const m = /^(\d{4})(\d{2})(\d{2})_(\d{4})(\d{2})(\d{2})$/.exec(id);
  return m ? [`${m[1]}-${m[2]}-${m[3]}`, `${m[4]}-${m[5]}-${m[6]}`] : null;
}

export function etiquetaEstado(estado: string | null, idioma: Idioma): string {
  const t = TEXTOS[idioma];
  if (estado === null) return t.sinDato;
  if (estado === "change_probable") return t.cambioProbable;
  if (estado === "no_change" || estado === "no_detectable_change") return t.sinCambio;
  // Cualquier otro estado es una causa de no observable; si es nueva y no tiene texto, su código.
  return `${t.noObservable}: ${t.causas[estado] ?? estado}`;
}

export function formatoValorDb(x: number | null, idioma: Idioma): string {
  if (x === null || !Number.isFinite(x)) return TEXTOS[idioma].sinDato;
  return `${x.toFixed(1).replace("-", "−")} dB`;
}

// ---- Contenido de la ventana -------------------------------------------------

const COLOR_HH = "#1d4ed8";
const COLOR_HV = "#b45309";

export function contenidoCargando(p: { lon: number; lat: number }, idioma: Idioma): HTMLElement {
  const raiz = cabecera(p, idioma);
  raiz.append(el("p", "atlas-serie-nota", TEXTOS[idioma].cargandoSerie));
  return raiz;
}

export function contenidoError(p: { lon: number; lat: number }, mensaje: string, idioma: Idioma) {
  const raiz = cabecera(p, idioma);
  raiz.append(el("p", "atlas-serie-error", mensaje));
  return raiz;
}

export function contenidoSerie(s: SeriePixel, idioma: Idioma): HTMLElement {
  const t = TEXTOS[idioma];
  const raiz = cabecera({ lon: s.lon, lat: s.lat }, idioma);
  raiz.append(el("p", "atlas-serie-nota", `${t.serie} ${s.series}`));
  if (s.data_kind === "synthetic") raiz.append(el("p", "atlas-serie-sintetico", t.sintetico));

  raiz.append(grafica(s, idioma));

  const tabla = el("table", "atlas-serie-tabla");
  tabla.append(el("caption", "", t.valoresPorFecha));
  const cab = el("tr");
  for (const h of [t.fecha, "HH", "HV"]) cab.append(el("th", "", h));
  tabla.append(el("thead"), el("tbody"));
  tabla.tHead!.append(cab);
  for (const v of s.values) {
    const fila = el("tr");
    fila.append(
      el("td", "", v.date),
      el("td", "", formatoValorDb(v.hh_db, idioma)),
      el("td", "", formatoValorDb(v.hv_db, idioma)),
    );
    tabla.tBodies[0].append(fila);
  }

  const cambios = el("table", "atlas-serie-tabla");
  cambios.append(el("caption", "", t.estadoPorPar), el("tbody"));
  for (const c of s.changes) {
    const f = fechasDelPar(c.pair);
    const fila = el("tr");
    fila.append(el("td", "", f ? `${f[0]} → ${f[1]}` : c.pair), el("td", "", etiquetaEstado(c.state, idioma)));
    if (c.state === "change_probable") fila.className = "atlas-serie-cambio";
    cambios.tBodies[0].append(fila);
  }

  const detalle = el("details");
  detalle.append(el("summary", "", t.verTabla), tabla);
  raiz.append(cambios, detalle);
  return raiz;
}

function cabecera(p: { lon: number; lat: number }, idioma: Idioma): HTMLElement {
  const t = TEXTOS[idioma];
  const raiz = el("div", "atlas-serie");
  raiz.append(
    el("h2", "", t.puntoSeleccionado),
    // Nombre del lugar (2026-11-15): lo rellena `rotularPunto` cuando llega de la geocodificación inversa.
    el("p", "atlas-serie-lugar", ""),
    el("p", "atlas-serie-coord", `${t.lon} ${String(p.lon).replace("-", "−")}° · ${t.lat} ${String(p.lat).replace("-", "−")}°`),
  );
  return raiz;
}

/** Gráfica mínima en SVG de HH y HV por fecha. Los huecos (null) cortan la línea. */
function grafica(s: SeriePixel, idioma: Idioma): Element {
  const t = TEXTOS[idioma];
  const W = 240;
  const H = 96;
  const M = { izq: 34, der: 6, arr: 6, aba: 16 };
  const tiempos = s.values.map((v) => Date.parse(v.date));
  const numeros = s.values.flatMap((v) => [v.hh_db, v.hv_db]).filter((x): x is number => x !== null);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("class", "atlas-serie-grafica");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", t.graficaAria);
  if (numeros.length === 0 || tiempos.length === 0) return svg;

  let [min, max] = [Math.min(...numeros), Math.max(...numeros)];
  if (min === max) [min, max] = [min - 1, max + 1];
  const [t0, t1] = [Math.min(...tiempos), Math.max(...tiempos)];
  const x = (tm: number) => M.izq + (t1 === t0 ? 0.5 : (tm - t0) / (t1 - t0)) * (W - M.izq - M.der);
  const y = (v: number) => M.arr + (1 - (v - min) / (max - min)) * (H - M.arr - M.aba);

  const svgEl = (tag: string, attrs: Record<string, string | number>, texto?: string) => {
    const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
    if (texto) n.textContent = texto;
    svg.append(n);
    return n;
  };

  svgEl("line", { x1: M.izq, x2: W - M.der, y1: H - M.aba, y2: H - M.aba, stroke: "#9ca3af" });
  svgEl("text", { x: M.izq - 4, y: y(max) + 4, "text-anchor": "end" }, formatoNum(max));
  svgEl("text", { x: M.izq - 4, y: y(min) + 4, "text-anchor": "end" }, formatoNum(min));
  svgEl("text", { x: M.izq, y: H - 3 }, s.values[0].date.slice(5));
  svgEl("text", { x: W - M.der, y: H - 3, "text-anchor": "end" }, s.values.at(-1)!.date.slice(5));

  for (const [clave, color, discontinua] of [
    ["hh_db", COLOR_HH, false],
    ["hv_db", COLOR_HV, true],
  ] as const) {
    let d = "";
    let abierto = false;
    s.values.forEach((v, i) => {
      const val = v[clave];
      if (val === null) {
        abierto = false;
        return;
      }
      d += `${abierto ? "L" : "M"}${x(tiempos[i]).toFixed(1)},${y(val).toFixed(1)}`;
      abierto = true;
      svgEl("circle", { cx: x(tiempos[i]), cy: y(val), r: 2.2, fill: color });
    });
    // HV discontinua: las dos series se distinguen sin depender del color.
    svgEl("path", {
      d,
      fill: "none",
      stroke: color,
      "stroke-width": 1.6,
      ...(discontinua ? { "stroke-dasharray": "4 3" } : {}),
    });
  }
  svgEl("text", { x: W - M.der, y: M.arr + 8, "text-anchor": "end", fill: COLOR_HH }, "— HH");
  svgEl("text", { x: W - M.der, y: M.arr + 18, "text-anchor": "end", fill: COLOR_HV }, "- - HV");
  return svg;
}

function formatoNum(x: number) {
  return x.toFixed(0).replace("-", "−");
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, clase = "", texto?: string) {
  const n = document.createElement(tag);
  if (clase) n.className = clase;
  if (texto !== undefined) n.textContent = texto;
  return n;
}
