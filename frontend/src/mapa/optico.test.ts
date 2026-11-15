import { describe, expect, it } from "vitest";
import type { VistaOptica } from "../types/map";
import {
  describirLado,
  formatoFechaUtc,
  formatoPorcentaje,
  ladoDisponible,
  limitarPosicion,
  moverConTecla,
} from "./optico";

const DESPEJADA: VistaOptica = {
  status: "clear",
  tiles: ["http://localhost:8080/tiles/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url=a"],
  attribution: "Contiene datos modificados de Copernicus Sentinel 2026",
  cloudCover: 26.6,
  acquiredAt: "2026-06-28T17:46:21Z",
  daysFromRadar: -1,
  coversAoi: true,
};

describe("lado disponible", () => {
  it("usa el preferido si existe", () => {
    expect(ladoDisponible({ before: DESPEJADA, after: DESPEJADA }, "before")).toBe("before");
  });
  it("cae al otro lado si el preferido falta", () => {
    expect(ladoDisponible({ before: DESPEJADA }, "after")).toBe("before");
  });
  it("devuelve null sin datos ópticos: no se monta el comparador", () => {
    expect(ladoDisponible(undefined, "after")).toBeNull();
    expect(ladoDisponible({}, "after")).toBeNull();
  });
});

describe("deslizador", () => {
  it("se queda entre 0 y 100", () => {
    expect(limitarPosicion(-10)).toBe(0);
    expect(limitarPosicion(140)).toBe(100);
    expect(limitarPosicion(Number.NaN)).toBe(50);
  });
  it("se mueve con flechas, Re Pág/Av Pág, Inicio y Fin", () => {
    expect(moverConTecla(50, "ArrowLeft")).toBe(45);
    expect(moverConTecla(50, "ArrowRight")).toBe(55);
    expect(moverConTecla(50, "PageUp")).toBe(75);
    expect(moverConTecla(10, "PageDown")).toBe(0);
    expect(moverConTecla(50, "Home")).toBe(0);
    expect(moverConTecla(50, "End")).toBe(100);
    expect(moverConTecla(50, "Enter")).toBeNull();
  });
});

describe("formato", () => {
  it("fecha y hora siempre en UTC, sin segundos", () => {
    expect(formatoFechaUtc("2026-06-28T17:46:21Z")).toBe("2026-06-28 17:46");
    expect(formatoFechaUtc("2026-06-28T11:46:21-06:00")).toBe("2026-06-28 17:46");
    expect(formatoFechaUtc("sin fecha")).toBe("sin fecha");
  });
  it("porcentaje con coma decimal en español", () => {
    expect(formatoPorcentaje(26.6, "es")).toBe("26,6");
    expect(formatoPorcentaje(26.6, "en")).toBe("26.6");
  });
});

describe("descripción de un lado", () => {
  it("escena despejada: fecha, distancia al radar, nubes de la tesela y atribución, sin aviso", () => {
    const d = describirLado(DESPEJADA, "es");
    expect(d.conImagen).toBe(true);
    expect(d.lineas).toEqual([
      "Escena del 2026-06-28 17:46 UTC",
      "1 día antes de la pasada de radar",
      "Nubes: 26,6 % de la tesela completa, no de la zona",
    ]);
    expect(d.aviso).toBeNull();
    expect(d.atribucion).toBe(DESPEJADA.attribution);
  });

  it("escena nublada: avisa", () => {
    const d = describirLado({ ...DESPEJADA, status: "cloudy", cloudCover: 39 }, "es");
    expect(d.aviso).toMatch(/nublada/);
  });

  it("escena 'clear' que no cubre la zona: también avisa", () => {
    const d = describirLado({ ...DESPEJADA, coversAoi: false }, "en");
    expect(d.aviso).toBe("The scene does not cover the whole area");
  });

  it("sin escena: dice por qué y no hay nada que pintar", () => {
    const ninguna = describirLado({ status: "none_in_window", tiles: [] }, "es");
    expect(ninguna).toEqual({
      conImagen: false,
      lineas: [],
      aviso: "No hay escena Sentinel-2 cercana a esta fecha",
      atribucion: null,
    });
    const caido = describirLado({ status: "catalog_unavailable", tiles: [] }, "en");
    expect(caido.aviso).toBe("The optical image catalog did not respond");
  });

  it("días respecto al radar en singular, plural y mismo día", () => {
    expect(describirLado({ ...DESPEJADA, daysFromRadar: 0 }, "es").lineas[1]).toBe(
      "el mismo día que la pasada de radar",
    );
    expect(describirLado({ ...DESPEJADA, daysFromRadar: 3 }, "en").lineas[1]).toBe(
      "3 days after the radar pass",
    );
  });
});
