// Textos de la línea de tiempo (T-ATL-06). Las fechas van en ISO y UTC, igual que en la API.
import type { Idioma } from "./textos";

type EstadoPlan = "planned" | "partial" | "not_planned" | "no_plan" | "unknown";

export interface TextosLinea {
  titulo: string;
  graficaAria: (pasadas: number, series: number, desde: string, hasta: string) => string;
  sinPasadas: string;
  pasada: string;
  excluida: string;
  estimada: string;
  hueco: string;
  evento: string;
  hoy: string;
  /** published_at_basis = cmr_updated. */
  notaPublicacion: string;
  pasadaDe: (fecha: string, serie: string) => string;
  latencia: (horas: string) => string;
  sinPublicar: string;
  noContieneZona: string;
  excluidaDe: (fecha: string, serie: string, motivo: string) => string;
  comprobada: (fecha: string) => string;
  /** Códigos de ExcludedPass.reason; si llega otro, se muestra el código. */
  motivos: Record<string, string>;
  estimadaDe: (fecha: string, serie: string) => string;
  /** basis = "12-day cycle". */
  baseEstimacion: string;
  planes: Record<EstadoPlan, string>;
  planConsultado: (fecha: string) => string;
  planSinConsultar: string;
  planNoGarantiza: string;
  huecoDe: (desde: string, hasta: string, fuente: string) => string;
  eventoDe: (inicio: string, horas: number) => string;
  eventoSinHora: (fecha: string, horas: number) => string;
  verLista: string;
  pasadasDeSerie: (serie: string) => string;
  seleccionarPasada: (fecha: string, serie: string) => string;
}

export const TEXTOS_LINEA: Record<Idioma, TextosLinea> = {
  es: {
    titulo: "Pasadas de radar sobre la zona",
    graficaAria: (p, s, d, h) =>
      `Línea de tiempo: ${p} ${p === 1 ? "pasada" : "pasadas"} de ${s} ${s === 1 ? "serie" : "series"} entre ${d} y ${h}. La lista completa va debajo.`,
    sinPasadas: "El catálogo no tiene pasadas de esta zona.",
    pasada: "Pasada adquirida",
    excluida: "Pasada excluida",
    estimada: "Próxima pasada estimada",
    hueco: "Hueco sin adquisiciones",
    evento: "Evento consultado",
    hoy: "Hoy",
    notaPublicacion:
      "La publicación es aproximada: es la última actualización del gránulo en CMR.",
    pasadaDe: (f, s) => `${f} UTC, serie ${s}`,
    latencia: (h) => `publicada unas ${h} h después`,
    sinPublicar: "sin fecha de publicación",
    noContieneZona: "no cubre toda la zona",
    excluidaDe: (f, s, m) => `Pasada del ${f} UTC (serie ${s}) excluida: ${m}.`,
    comprobada: (f) => `Comprobado el ${f}.`,
    motivos: {
      product_defect: "fallo en el producto publicado",
    },
    estimadaDe: (f, s) => `Próxima pasada de la serie ${s}: hacia el ${f} UTC.`,
    baseEstimacion:
      "Es una estimación (última pasada más ciclos de 12 días), no un plan de observación.",
    planes: {
      planned: "El plan diario de NISAR incluye esa hora.",
      partial: "El plan diario de NISAR cubre esa hora solo en parte.",
      not_planned: "El plan diario de NISAR no incluye esa hora.",
      no_plan: "No hay plan diario de NISAR publicado para esa hora.",
      unknown: "No se sabe si el plan diario de NISAR incluye esa hora.",
    },
    planConsultado: (f) => `Plan consultado el ${f} UTC.`,
    planSinConsultar: "El plan no se ha consultado.",
    planNoGarantiza: "Un plan no garantiza que se adquiera.",
    huecoDe: (d, h, f) => `Sin adquisiciones del ${d} al ${h}, ambos incluidos (fuente: ${f}).`,
    eventoDe: (i, h) => `Evento desde el ${i} UTC, durante ${h} h supuestas.`,
    eventoSinHora: (f, h) =>
      `Evento del ${f}, sin hora: puede empezar en cualquier momento de ese día y durar ${h} h supuestas.`,
    verLista: "Ver todas las pasadas",
    pasadasDeSerie: (s) => `Serie ${s}`,
    seleccionarPasada: (f, s) => `Pasada del ${f} UTC, serie ${s}`,
  },
  en: {
    titulo: "Radar passes over the area",
    graficaAria: (p, s, d, h) =>
      `Timeline: ${p} ${p === 1 ? "pass" : "passes"} from ${s} ${s === 1 ? "series" : "series"} between ${d} and ${h}. The full list is below.`,
    sinPasadas: "The catalog has no passes for this area.",
    pasada: "Acquired pass",
    excluida: "Excluded pass",
    estimada: "Estimated next pass",
    hueco: "Gap with no acquisitions",
    evento: "Queried event",
    hoy: "Today",
    notaPublicacion:
      "Publication time is approximate: it is the granule's last update in CMR.",
    pasadaDe: (f, s) => `${f} UTC, series ${s}`,
    latencia: (h) => `published about ${h} h later`,
    sinPublicar: "no publication date",
    noContieneZona: "does not cover the whole area",
    excluidaDe: (f, s, m) => `Pass of ${f} UTC (series ${s}) excluded: ${m}.`,
    comprobada: (f) => `Checked on ${f}.`,
    motivos: {
      product_defect: "defect in the published product",
    },
    estimadaDe: (f, s) => `Next pass of series ${s}: around ${f} UTC.`,
    baseEstimacion:
      "This is an estimate (last pass plus 12-day cycles), not an observation plan.",
    planes: {
      planned: "The NISAR daily plan includes that time.",
      partial: "The NISAR daily plan only partly covers that time.",
      not_planned: "The NISAR daily plan does not include that time.",
      no_plan: "No NISAR daily plan is published for that time.",
      unknown: "It is not known whether the NISAR daily plan includes that time.",
    },
    planConsultado: (f) => `Plan checked on ${f} UTC.`,
    planSinConsultar: "The plan has not been checked.",
    planNoGarantiza: "A plan does not guarantee an acquisition.",
    huecoDe: (d, h, f) => `No acquisitions from ${d} to ${h}, both included (source: ${f}).`,
    eventoDe: (i, h) => `Event from ${i} UTC, lasting an assumed ${h} h.`,
    eventoSinHora: (f, h) =>
      `Event on ${f}, no time given: it may start at any moment that day and last an assumed ${h} h.`,
    verLista: "Show all passes",
    pasadasDeSerie: (s) => `Series ${s}`,
    seleccionarPasada: (f, s) => `Pass of ${f} UTC, series ${s}`,
  },
};
