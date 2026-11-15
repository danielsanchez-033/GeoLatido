import type { Bbox } from "./tipos";

/**
 * Georreferencia de la vista previa `_LATLON.png` de ASF (2026-11-15).
 *
 * La imagen está en latitud/longitud (placa carré), pero es mayor que la escena: el radar ocupa una parte y el resto
 * es negro (en un gránulo de Groenlandia, el 83 % de 1947 × 1954 píxeles). Estirarla entera sobre la caja de la huella
 * encogía y desplazaba la escena. Como la rejilla es lineal en lon y lat, basta casar los bordes del contenido (primer
 * y último píxel con dato en cada eje) con los de la huella: de ahí salen grados por píxel y la caja de la imagen
 * entera. Comprobado a mano con ese gránulo: los cuatro vértices de la huella caen a menos de 0,003° de los extremos
 * del contenido.
 */

/** Caja de píxeles con dato: [x0, y0, x1, y1], ambos extremos incluidos. */
export type CajaPx = [number, number, number, number];

/** Esquinas de la imagen entera para una fuente `image` de MapLibre: NO, NE, SE, SO. */
export function esquinasImagen(ancho: number, alto: number, contenido: CajaPx, huella: Bbox): [number, number][] {
  const [x0, y0, x1, y1] = contenido;
  const [o, s, e, n] = huella;
  // Los píxeles tienen tamaño: el borde del contenido es el lado exterior del primer y del último píxel.
  const gradoX = (e - o) / (x1 - x0 + 1);
  const gradoY = (n - s) / (y1 - y0 + 1);
  const oeste = o - x0 * gradoX;
  const este = oeste + ancho * gradoX;
  const norte = n + y0 * gradoY;
  const sur = norte - alto * gradoY;
  return [
    [oeste, norte],
    [este, norte],
    [este, sur],
    [oeste, sur],
  ];
}

/** Caja de los píxeles con dato (valor > 0 en algún canal y no transparentes). null si la imagen está vacía. */
export function cajaContenido(datos: Uint8ClampedArray, ancho: number, alto: number): CajaPx | null {
  let x0 = ancho;
  let y0 = alto;
  let x1 = -1;
  let y1 = -1;
  for (let y = 0; y < alto; y++) {
    for (let x = 0; x < ancho; x++) {
      const i = (y * ancho + x) * 4;
      if (datos[i + 3] === 0 || datos[i] + datos[i + 1] + datos[i + 2] === 0) continue;
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    }
  }
  return x1 < 0 ? null : [x0, y0, x1, y1];
}

/** Negro puro (sin dato) a transparente, para que el mapa se vea alrededor de la escena. */
export function negroATransparente(datos: Uint8ClampedArray): void {
  for (let i = 0; i < datos.length; i += 4) {
    if (datos[i] + datos[i + 1] + datos[i + 2] === 0) datos[i + 3] = 0;
  }
}

const LADO_MAX = 1024;

/**
 * Descarga la vista previa (ASF la sirve con CORS abierto), la reduce a 1024 px como mucho, quita el negro y calcula
 * sus esquinas. null si no se puede (sin canvas, sin CORS o vacía): entonces el mapa no la pinta antes que mal.
 */
export async function prepararVistaPrevia(url: string, huella: Bbox): Promise<{ url: string; coordinates: [number, number][] } | null> {
  if (typeof document === "undefined") return null;
  const img = new Image();
  img.crossOrigin = "anonymous";
  img.src = url;
  try {
    await img.decode();
  } catch {
    return null;
  }
  const escala = Math.min(1, LADO_MAX / Math.max(img.naturalWidth, img.naturalHeight));
  const ancho = Math.max(1, Math.round(img.naturalWidth * escala));
  const alto = Math.max(1, Math.round(img.naturalHeight * escala));
  const lienzo = document.createElement("canvas");
  lienzo.width = ancho;
  lienzo.height = alto;
  const ctx = lienzo.getContext("2d", { willReadFrequently: true });
  if (!ctx) return null;
  ctx.drawImage(img, 0, 0, ancho, alto);
  let pixeles: ImageData;
  try {
    pixeles = ctx.getImageData(0, 0, ancho, alto);
  } catch {
    return null; // lienzo contaminado: el servidor no dio CORS
  }
  const caja = cajaContenido(pixeles.data, ancho, alto);
  if (!caja) return null;
  negroATransparente(pixeles.data);
  ctx.putImageData(pixeles, 0, 0);
  return { url: lienzo.toDataURL("image/png"), coordinates: esquinasImagen(ancho, alto, caja, huella) };
}
