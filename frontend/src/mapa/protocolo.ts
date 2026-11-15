import * as maplibregl from "maplibre-gl";
import { pintarEstado, plantillaCodificada, type ModoEstado } from "./estado";

const PROTOCOLO = "atlas-estado";

type Cargador = (url: string, senal: AbortSignal) => Promise<Blob>;

/** Respuesta HTTP no satisfactoria; guarda el código para poder tratar el 404 aparte. */
export class ErrorHttp extends Error {
  readonly status: number;
  constructor(status: number, url: string) {
    super(`HTTP ${status} en ${url}`);
    this.status = status;
  }
}

const cargadorHttp: Cargador = async (url, senal) => {
  const r = await fetch(url, { signal: senal });
  if (!r.ok) throw new ErrorHttp(r.status, url);
  return r.blob();
};

/** Cargadores alternativos por esquema. Solo los usa el banco de pruebas. */
const cargadores = new Map<string, Cargador>();
export function registrarCargador(esquema: string, cargador: Cargador): void {
  cargadores.set(esquema, cargador);
}

/** Descarga una tesela con el cargador de su esquema, o por HTTP si no hay ninguno. */
export function descargar(url: string, senal: AbortSignal): Promise<Blob> {
  const esquema = url.slice(0, url.indexOf(":"));
  return (cargadores.get(esquema) ?? cargadorHttp)(url, senal);
}

let registrado = false;

function registrarProtocolo(): void {
  if (registrado) return;
  registrado = true;
  maplibregl.addProtocol(PROTOCOLO, async (params, abort) => {
    const resto = params.url.slice(`${PROTOCOLO}://`.length);
    const corte = resto.indexOf("/");
    const modo = resto.slice(0, corte) as ModoEstado;
    const url = resto.slice(corte + 1);
    const blob = await descargar(url, abort.signal);

    // Sin gestión de color ni alfa premultiplicado: el canal rojo es el código.
    const img = await createImageBitmap(blob, {
      premultiplyAlpha: "none",
      colorSpaceConversion: "none",
    });
    const lienzo = new OffscreenCanvas(img.width, img.height);
    const ctx = lienzo.getContext("2d", { willReadFrequently: true })!;
    ctx.drawImage(img, 0, 0);
    img.close();
    const datos = ctx.getImageData(0, 0, lienzo.width, lienzo.height);
    pintarEstado(datos.data, lienzo.width, modo);
    ctx.putImageData(datos, 0, 0);
    const png = await lienzo.convertToBlob({ type: "image/png" });
    return { data: await png.arrayBuffer() };
  });
}

/** Plantilla de tesela para MapLibre a partir de la plantilla `state` de la API. */
export function plantillaEstado(plantillaApi: string, modo: ModoEstado): string {
  registrarProtocolo();
  const interna = /^https?:/.test(plantillaApi) ? plantillaCodificada(plantillaApi) : plantillaApi;
  return `${PROTOCOLO}://${modo}/${interna}`;
}
