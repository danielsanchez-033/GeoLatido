// Capa de estado: códigos de services/processor/src/processor/change.py.
//
// La API sirve `state` como PNG con una paleta (parámetro `colormap` de TiTiler).
// Atlas la sustituye por una paleta que guarda el código en el canal rojo y
// después pinta cada píxel en el navegador. Así lo no observable lleva una trama
// diagonal, que se distingue sin depender del color (constitución IX.2).
// La capa `state` usa remuestreo "nearest" en sus vistas generales, por lo que
// los códigos llegan intactos a cualquier zoom.

export const SIN_CAMBIO = 0;
export const CAMBIO_PROBABLE = 1;

/**
 * Códigos conocidos de lo no observable con su clave de causa en la API (`cause`).
 * No es la lista cerrada: cualquier código en el rango reservado cuenta como no observable,
 * para que una causa nueva de Eco nunca se vea como «sin cambio».
 */
export const CAUSAS_NO_OBSERVABLE: Record<number, string> = {
  10: "outside_scene",
  11: "invalid_or_partial",
  12: "input_exception",
  13: "low_looks",
  14: "no_data",
  15: "terrain",
};

/** Rango reservado para lo no observable. Hoy Eco usa del 10 al 15. */
export const PRIMER_CODIGO_NO_OBSERVABLE = 10;
export const ULTIMO_CODIGO_NO_OBSERVABLE = 63;

export function esNoObservable(codigo: number): boolean {
  return codigo >= PRIMER_CODIGO_NO_OBSERVABLE && codigo <= ULTIMO_CODIGO_NO_OBSERVABLE;
}

/** Paleta que codifica cada estado en el canal rojo, con alfa 255. "Sin cambio" es transparente. */
export function paletaCodificada(): Record<string, string> {
  const hex = (n: number) => n.toString(16).padStart(2, "0");
  const paleta: Record<string, string> = { [SIN_CAMBIO]: "#00000000" };
  paleta[CAMBIO_PROBABLE] = `#${hex(CAMBIO_PROBABLE)}0000ff`;
  // Todo el rango reservado, no solo las causas conocidas: si TiTiler no encuentra un código
  // en la paleta lo deja transparente, y una causa nueva se leería como «sin cambio».
  for (let c = PRIMER_CODIGO_NO_OBSERVABLE; c <= ULTIMO_CODIGO_NO_OBSERVABLE; c++) {
    paleta[c] = `#${hex(c)}0000ff`;
  }
  return paleta;
}

/** Reescribe el parámetro `colormap` de una plantilla de la API sin tocar nada más. */
export function plantillaCodificada(plantilla: string): string {
  const [base, consulta = ""] = plantilla.split("?");
  const params = new URLSearchParams(consulta);
  params.set("colormap", JSON.stringify(paletaCodificada()));
  // URLSearchParams codifica las llaves y no altera {z}/{x}/{y}, que están en la ruta.
  return `${base}?${params.toString()}`;
}

/**
 * "cambio": solo el cambio probable, en color sólido.
 * "trama": solo lo no observable, con trama. Va en su propia capa, siempre visible y
 * con una opacidad mínima, para que lo no observable no se pierda al bajar la opacidad
 * ni al cambiar de capa.
 */
export type ModoEstado = "cambio" | "trama";

// Blanco y negro (diseño del 2026-11-14): el cambio probable es relleno en tinta y lo no
// observable, trama negra sobre blanco. El mapa base va en grises (mapaBase.ts), así que
// los dos se leen por la forma, no por el color.
export const COLOR_CAMBIO: [number, number, number] = [0x00, 0x00, 0x00]; // tinta
const TRAMA_OSCURA: [number, number, number, number] = [0x00, 0x00, 0x00, 235];
const TRAMA_CLARA: [number, number, number, number] = [0xff, 0xff, 0xff, 170];
/** Periodo de la trama en píxeles. Divide a 256, así que las rayas continúan entre teselas. */
export const PERIODO_TRAMA = 8;

/** Opacidad mínima de la capa de trama, aunque la persona baje la opacidad de las capas radar. */
export const OPACIDAD_MINIMA_TRAMA = 0.7;

/** Pinta in situ un RGBA decodificado con `paletaCodificada`, según el modo. */
export function pintarEstado(rgba: Uint8ClampedArray, ancho: number, modo: ModoEstado): void {
  for (let i = 0; i < rgba.length; i += 4) {
    const codigo = rgba[i + 3] === 0 ? SIN_CAMBIO : rgba[i];
    const p = i / 4;
    const x = p % ancho;
    const y = (p - x) / ancho;
    if (esNoObservable(codigo) && modo === "trama") {
      const c = (x + y) % PERIODO_TRAMA < 3 ? TRAMA_OSCURA : TRAMA_CLARA;
      rgba.set(c, i);
    } else if (codigo === CAMBIO_PROBABLE && modo === "cambio") {
      rgba.set([...COLOR_CAMBIO, 255], i);
    } else {
      rgba.set([0, 0, 0, 0], i);
    }
  }
}
