import { describe, expect, it } from "vitest";
import { crearMapa } from "./mapa";
import { TEXTOS } from "./textos";

// jsdom no tiene WebGL: es justo el caso de un navegador sin WebGL 2.
describe("sin WebGL 2", () => {
  it("no rompe: dice que no puede dibujar el mapa y deja la zona en texto", () => {
    const c = document.createElement("div");
    const mapa = crearMapa(c, {
      aoi: [-105.95, 26.7, -105.4, 27.15],
      nombreZona: "Parral",
      dataKind: "synthetic",
      modo3d: true,
    });
    expect(c.querySelector(".atlas-aviso-sin-mapa")?.textContent).toBe(TEXTOS.es.sinMapa);
    expect(c.querySelector(".atlas-extension")?.textContent).toContain("Parral");
    expect(c.querySelector(".atlas-extension")?.textContent).toContain("105.95");
    const sello = c.querySelector<HTMLElement>(".atlas-sintetico");
    expect(sello?.hidden).toBe(false);

    mapa.actualizar({ idioma: "en", dataKind: "real" });
    expect(c.querySelector(".atlas-aviso-sin-mapa")?.textContent).toBe(TEXTOS.en.sinMapa);
    expect(sello?.hidden).toBe(true);

    mapa.destruir();
    expect(c.childElementCount).toBe(0);
  });
});
