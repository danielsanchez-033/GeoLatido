import { afterEach, describe, expect, it, vi } from "vitest";
import { reiniciarTeselaVacia, teselaVacia } from "./teselaVacia";

/** Imita a Chrome: convertToBlob() falla si no se pidió antes un contexto. */
class LienzoFalso {
  static creados = 0;
  static fallar = false;
  private conContexto = false;
  constructor() {
    LienzoFalso.creados++;
  }
  getContext() {
    this.conContexto = true;
    return {};
  }
  convertToBlob(): Promise<Blob> {
    if (!this.conContexto) {
      return Promise.reject(new DOMException("The OffscreenCanvas has no rendering context.", "InvalidStateError"));
    }
    if (LienzoFalso.fallar) return Promise.reject(new Error("fallo puntual"));
    return Promise.resolve(new Blob([new Uint8Array([137, 80, 78, 71])], { type: "image/png" }));
  }
}

describe("tesela vacía", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    reiniciarTeselaVacia();
    LienzoFalso.creados = 0;
    LienzoFalso.fallar = false;
  });

  it("pide un contexto antes de convertToBlob, así que no lanza InvalidStateError", async () => {
    vi.stubGlobal("OffscreenCanvas", LienzoFalso);
    const png = await teselaVacia();
    expect(png.byteLength).toBeGreaterThan(0);
  });

  it("crea el PNG una sola vez y lo reutiliza", async () => {
    vi.stubGlobal("OffscreenCanvas", LienzoFalso);
    await teselaVacia();
    await teselaVacia();
    expect(LienzoFalso.creados).toBe(1);
  });

  it("si falla, no se queda con la promesa rechazada: el siguiente intento funciona", async () => {
    vi.stubGlobal("OffscreenCanvas", LienzoFalso);
    LienzoFalso.fallar = true;
    await expect(teselaVacia()).rejects.toThrow("fallo puntual");
    LienzoFalso.fallar = false;
    const png = await teselaVacia();
    expect(png.byteLength).toBeGreaterThan(0);
    expect(LienzoFalso.creados).toBe(2);
  });
});
