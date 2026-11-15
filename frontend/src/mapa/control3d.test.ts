import { describe, expect, it, vi } from "vitest";
import { Control3d } from "./control3d";
import { TEXTOS } from "./textos";

describe("botón 2D/3D (RF-INT-11)", () => {
  it("es un botón con aria-pressed y nombre accesible en el idioma del mapa", () => {
    const c = new Control3d(() => {});
    const caja = c.onAdd();
    const boton = caja.querySelector("button")!;
    c.dibujar({ pulsado: false, idioma: "es" });
    expect(boton.getAttribute("aria-pressed")).toBe("false");
    expect(boton.getAttribute("aria-label")).toBe(TEXTOS.es.boton3d);
    expect(boton.title).toBe(TEXTOS.es.boton3dPoner);

    c.dibujar({ pulsado: true, idioma: "en" });
    expect(boton.getAttribute("aria-pressed")).toBe("true");
    expect(boton.getAttribute("aria-label")).toBe(TEXTOS.en.boton3d);
    expect(boton.title).toBe(TEXTOS.en.boton3dQuitar);
  });

  it("avisa al pulsarlo", () => {
    const pulsar = vi.fn();
    const c = new Control3d(pulsar);
    c.onAdd().querySelector("button")!.click();
    expect(pulsar).toHaveBeenCalledTimes(1);
  });
});
