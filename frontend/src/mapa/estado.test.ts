import { describe, expect, it } from "vitest";
import {
  CAUSAS_NO_OBSERVABLE,
  esNoObservable,
  PRIMER_CODIGO_NO_OBSERVABLE,
  ULTIMO_CODIGO_NO_OBSERVABLE,
  COLOR_CAMBIO,
  OPACIDAD_MINIMA_TRAMA,
  PERIODO_TRAMA,
  paletaCodificada,
  pintarEstado,
  plantillaCodificada,
} from "./estado";
import { formatoDb, limitarOpacidad, rangoReescalado } from "./leyenda";

// Plantilla con la forma exacta que genera services/verdicts (_tile_url + _layers).
const PLANTILLA_API =
  "http://localhost:8080/tiles/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png" +
  "?url=file%3A%2F%2F%2Fdata%2Fartifacts%2Fparral%2Fpairs%2Fa_b%2Fstate.tif" +
  "&colormap=%7B%220%22%3A%22%2300000000%22%2C%221%22%3A%22%23e4572eff%22%7D";

/** RGBA de una fila de `n` píxeles con los códigos dados, como llegan con la paleta codificada. */
function fila(codigos: (number | null)[]): Uint8ClampedArray {
  const a = new Uint8ClampedArray(codigos.length * 4);
  codigos.forEach((c, i) => a.set(c === null || c === 0 ? [0, 0, 0, 0] : [c, 0, 0, 255], i * 4));
  return a;
}

const px = (a: Uint8ClampedArray, i: number) => Array.from(a.slice(i * 4, i * 4 + 4));

describe("paleta codificada", () => {
  it("cubre 0, 1 y todo el rango reservado de no observable, no solo los 10-15 actuales", () => {
    const codigos = Object.keys(paletaCodificada()).map(Number).sort((a, b) => a - b);
    expect(codigos.slice(0, 2)).toEqual([0, 1]);
    expect(codigos.slice(2)).toEqual(
      Array.from({ length: ULTIMO_CODIGO_NO_OBSERVABLE - PRIMER_CODIGO_NO_OBSERVABLE + 1 }, (_, i) => PRIMER_CODIGO_NO_OBSERVABLE + i),
    );
    for (const c of Object.keys(CAUSAS_NO_OBSERVABLE).map(Number)) expect(codigos).toContain(c);
  });

  it("una causa nueva de Eco (p. ej. 16) se pinta con trama, nunca como «sin cambio»", () => {
    expect(esNoObservable(16)).toBe(true);
    expect(paletaCodificada()["16"]).toBe("#100000ff");
    const a = fila([16]);
    pintarEstado(a, 1, "trama");
    expect(px(a, 0)[3]).toBeGreaterThan(0);
    expect(esNoObservable(1)).toBe(false);
    expect(esNoObservable(0)).toBe(false);
  });

  it("guarda el código en el canal rojo con alfa opaco", () => {
    expect(paletaCodificada()["13"]).toBe("#0d0000ff");
    expect(paletaCodificada()["0"]).toBe("#00000000");
  });

  it("solo sustituye colormap y conserva url y las marcas {z}/{x}/{y}", () => {
    const nueva = plantillaCodificada(PLANTILLA_API);
    expect(nueva.startsWith("http://localhost:8080/tiles/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?")).toBe(true);
    const p = new URLSearchParams(nueva.split("?")[1]);
    expect(p.get("url")).toBe("file:///data/artifacts/parral/pairs/a_b/state.tif");
    expect(JSON.parse(p.get("colormap")!)).toEqual(paletaCodificada());
  });
});

describe("pintar el estado", () => {
  it("modo cambio: cambio en color sólido; el resto transparente", () => {
    const a = fila([1, 0, null, 13]);
    pintarEstado(a, 4, "cambio");
    expect(px(a, 0)).toEqual([...COLOR_CAMBIO, 255]);
    expect(px(a, 1)).toEqual([0, 0, 0, 0]);
    expect(px(a, 2)).toEqual([0, 0, 0, 0]);
    expect(px(a, 3)).toEqual([0, 0, 0, 0]); // lo pinta la capa de trama
  });

  it("modo trama: todas las causas de no observable se pintan, nunca transparentes", () => {
    const codigos = Object.keys(CAUSAS_NO_OBSERVABLE).map(Number);
    const a = fila(codigos);
    pintarEstado(a, codigos.length, "trama");
    codigos.forEach((_, i) => expect(px(a, i)[3]).toBeGreaterThan(0));
  });

  it("modo trama: deja transparentes el cambio probable y el sin cambio", () => {
    const a = fila([1, 0]);
    pintarEstado(a, 2, "trama");
    expect(px(a, 0)[3]).toBe(0);
    expect(px(a, 1)[3]).toBe(0);
  });

  it("la capa de trama no baja de su opacidad mínima", () => {
    expect(OPACIDAD_MINIMA_TRAMA).toBeGreaterThanOrEqual(0.7);
  });

  it("dibuja rayas diagonales que no dependen del color", () => {
    const ancho = PERIODO_TRAMA * 2;
    const a = fila(Array(ancho * 2).fill(13));
    pintarEstado(a, ancho, "trama");
    const tonos = new Set(Array.from({ length: ancho * 2 }, (_, i) => px(a, i).join()));
    expect(tonos.size).toBe(2); // dos tonos alternos: es una trama, no un relleno
    // Diagonal: el píxel (x+1, y) es igual que el (x, y+1).
    expect(px(a, 1)).toEqual(px(a, ancho));
  });

  it("la trama continúa entre teselas vecinas de 256 px", () => {
    expect(256 % PERIODO_TRAMA).toBe(0);
  });
});

describe("leyenda", () => {
  it("lee el rango de rescale de la plantilla de cambio", () => {
    expect(rangoReescalado("http://h/t/{z}/{x}/{y}.png?url=x&rescale=-10,10&colormap_name=rdbu")).toEqual([-10, 10]);
    expect(rangoReescalado("http://h/t/{z}/{x}/{y}.png?url=x")).toBeNull();
  });

  it("escribe los dB con signo", () => {
    expect(formatoDb(-10)).toBe("−10 dB");
    expect(formatoDb(10)).toBe("+10 dB");
    expect(formatoDb(0)).toBe("0 dB");
  });

  it("limita la opacidad entre 0,2 y 1", () => {
    expect(limitarOpacidad(0)).toBe(0.2);
    expect(limitarOpacidad(1.5)).toBe(1);
    expect(limitarOpacidad(0.5)).toBe(0.5);
    expect(limitarOpacidad(Number.NaN)).toBe(1);
  });
});
