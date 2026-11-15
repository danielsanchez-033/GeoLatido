import { describe, expect, it } from "vitest";
import { cajaContenido, esquinasImagen, negroATransparente } from "./vistaPrevia";

describe("vista previa LATLON de ASF", () => {
  it("casa los bordes del contenido con los de la huella y extiende la caja a la imagen entera", () => {
    // Medidas reales del gránulo de Groenlandia del 2026-10-20 (1947 × 1954 px, contenido de x 138-1268 e y 143-1413).
    const huella: [number, number, number, number] = [-40.29844, 64.53893, -34.86097, 67.08163];
    const [no, ne, se, so] = esquinasImagen(1947, 1954, [138, 143, 1268, 1413], huella);
    expect(no[0]).toBeCloseTo(-40.962, 2);
    expect(no[1]).toBeCloseTo(67.368, 2);
    expect(ne[0]).toBeCloseTo(-31.597, 1);
    expect(se[1]).toBeCloseTo(63.458, 1);
    expect(so).toEqual([no[0], se[1]]);
    // El contenido vuelve a caer exactamente en la huella.
    const gradoX = (ne[0] - no[0]) / 1947;
    expect(no[0] + 138 * gradoX).toBeCloseTo(huella[0], 6);
  });

  it("encuentra el contenido y vuelve transparente el negro", () => {
    const datos = new Uint8ClampedArray(4 * 4 * 4); // 4 × 4, todo negro opaco
    for (let i = 3; i < datos.length; i += 4) datos[i] = 255;
    const pix = (x: number, y: number) => (y * 4 + x) * 4;
    datos[pix(1, 2)] = 90;
    datos[pix(2, 1)] = 200;
    expect(cajaContenido(datos, 4, 4)).toEqual([1, 1, 2, 2]);
    negroATransparente(datos);
    expect(datos[pix(0, 0) + 3]).toBe(0);
    expect(datos[pix(1, 2) + 3]).toBe(255);
  });

  it("sin contenido no hay caja", () => {
    expect(cajaContenido(new Uint8ClampedArray(16), 2, 2)).toBeNull();
  });
});
