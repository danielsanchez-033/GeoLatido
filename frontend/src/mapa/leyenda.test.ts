import { describe, expect, it } from "vitest";
import { crearLeyenda, type EstadoLeyenda } from "./leyenda";
import { TEXTOS } from "./textos";

const BASE: EstadoLeyenda = {
  idioma: "es",
  capa: "state",
  capasDisponibles: true,
  opacidad: 0.85,
  rango: null,
};

function dibujar(e: EstadoLeyenda): HTMLElement {
  const contenedor = document.createElement("div");
  crearLeyenda(contenedor, { alCambiarCapa: () => {}, alCambiarOpacidad: () => {} })(e);
  return contenedor;
}

describe("aviso de desplazamiento de toda la escena (scene_shift, PR 37 y 42)", () => {
  it("no aparece si el par no lo trae", () => {
    expect(dibujar(BASE).querySelector(".atlas-aviso-escena")).toBeNull();
    expect(dibujar({ ...BASE, avisoEscena: "ninguno" }).querySelector(".atlas-aviso-escena")).toBeNull();
  });

  it("va junto a «Cambio probable» en la capa de estado", () => {
    const c = dibujar({ ...BASE, avisoEscena: "sin_corregir" });
    const aviso = c.querySelector(".atlas-aviso-escena");
    expect(aviso?.textContent).toBe(TEXTOS.es.avisoEscena);
    expect(aviso?.closest("li")?.textContent).toContain(TEXTOS.es.cambioProbable);
  });

  it("va junto a la escala en dB en las capas de cambio", () => {
    const c = dibujar({ ...BASE, capa: "change_hh", rango: [-10, 10], avisoEscena: "sin_corregir", idioma: "en" });
    const aviso = c.querySelector(".atlas-aviso-escena");
    expect(aviso?.textContent).toBe(TEXTOS.en.avisoEscena);
    expect(aviso?.closest("li")?.classList.contains("atlas-escala")).toBe(true);
  });

  it("si ya se descontó, enseña la nota y no dice que pueda no ser local", () => {
    const c = dibujar({ ...BASE, avisoEscena: "corregido" });
    const nota = c.querySelector(".atlas-aviso-escena");
    expect(nota?.classList.contains("atlas-aviso-escena-corregido")).toBe(true);
    expect(nota?.textContent).toBe(TEXTOS.es.notaEscenaCorregida);
    expect(c.textContent).not.toContain(TEXTOS.es.avisoEscena);
  });
});

describe("teclas de 3D (RF-INT-15)", () => {
  it("solo aparecen en 3D", () => {
    expect(dibujar(BASE).querySelector(".atlas-teclas-3d")).toBeNull();
    expect(dibujar({ ...BASE, teclas3d: true }).querySelector(".atlas-teclas-3d")?.textContent).toBe(
      TEXTOS.es.teclas3d,
    );
  });
});
