import { describe, expect, it } from "vitest";
import { avisoEscena, normalizarAvisoEscena } from "./escena";

describe("aviso de desplazamiento de toda la escena", () => {
  it("sin desplazamiento por encima del umbral, o sin datos, no hay aviso", () => {
    expect(avisoEscena(null)).toBe("ninguno");
    expect(avisoEscena(undefined)).toBe("ninguno");
    expect(avisoEscena({ exceeds_threshold: false, corrected: false })).toBe("ninguno");
    expect(avisoEscena({ exceeds_threshold: false, corrected: true })).toBe("ninguno");
  });

  it("si Eco ya lo descontó (PR 42), es una nota, no el aviso de cambio no local", () => {
    expect(avisoEscena({ exceeds_threshold: true, corrected: true })).toBe("corregido");
  });

  it("si no se descontó, o la API aún no trae corrected (PR 37), avisa", () => {
    expect(avisoEscena({ exceeds_threshold: true, corrected: false })).toBe("sin_corregir");
    expect(avisoEscena({ exceeds_threshold: true })).toBe("sin_corregir");
  });

  it("acepta el booleano del PR 32 por compatibilidad", () => {
    expect(normalizarAvisoEscena(true)).toBe("sin_corregir");
    expect(normalizarAvisoEscena(false)).toBe("ninguno");
    expect(normalizarAvisoEscena(undefined)).toBe("ninguno");
    expect(normalizarAvisoEscena("corregido")).toBe("corregido");
  });
});
