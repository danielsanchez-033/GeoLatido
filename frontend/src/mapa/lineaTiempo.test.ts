import { describe, expect, it, vi } from "vitest";
import {
  crearLineaTiempo,
  describirEstimacion,
  marcasEje,
  modeloLinea,
  serieCorta,
  tramoEvento,
  type EventoLinea,
  type LineaTiempoApi,
} from "./lineaTiempo";
import { TEXTOS_LINEA } from "./lineaTiempoTextos";

const A = "T048A-F015-4005-DHDH-P05023";
const D = "T171D-F075-4005-DHDH-P05023";

// Recorte de la respuesta real de catalog para Parral (2026-11-14).
const DATOS: LineaTiempoApi = {
  aoi: "parral",
  published_at_basis: "cmr_updated",
  passes: [
    { series: A, granule_id: "GA2", acquired_at: "2026-06-29T12:24:34Z", published_at: null, latency_hours: null, contains_aoi: true },
    { series: A, granule_id: "GA1", acquired_at: "2026-06-17T12:24:34Z", published_at: "2026-07-09T03:32:43Z", latency_hours: 519.1, contains_aoi: true },
    { series: D, granule_id: "GD1", acquired_at: "2026-06-26T01:44:36Z", published_at: "2026-07-18T06:15:25Z", latency_hours: 532.5, contains_aoi: false },
  ],
  intervals: [],
  gaps: [{ start: "2026-07-27", end: "2026-08-10", source: "ASF" }],
  next_pass_estimates: [
    {
      series: D,
      expected_at: "2026-11-17T01:44:32Z",
      basis: "12-day cycle",
      observation_plan: { status: "unknown", plan: null, config_id: null, same_config: null, checked_at: null },
    },
  ],
  excluded: [
    {
      id: "GDX",
      date: "2026-08-13",
      acquired_at: "2026-08-13T01:44:33Z",
      reason: "product_defect",
      evidence: "La vista previa de ASF muestra la anomalía.",
      checked_on: "2026-11-12",
      series: D,
    },
  ],
};

const EVENTO: EventoLinea = {
  event_date: "2026-07-01",
  event_time: "18:30:00",
  persistence_hours: 6,
  assumption: {
    persistence_hours: 6,
    source: "event_type",
    event_type: "urban_storm",
    calibrated: false,
    hours_by_event_type: { urban_storm: 6, river_flood: 72, wildfire: 240 },
    text: "Se supone que el evento dura 6 h; no está calibrado.",
  },
};

describe("modelo", () => {
  it("agrupa por serie y ordena cada fila por fecha", () => {
    const m = modeloLinea(DATOS);
    expect(m.filas.map((f) => f.serie)).toEqual([A, D]);
    expect(m.filas[0].pasadas.map((p) => p.granule_id)).toEqual(["GA1", "GA2"]);
    expect(m.filas[1].excluidas).toHaveLength(1);
    expect(m.filas[1].estimaciones).toHaveLength(1);
  });

  it("el eje cubre de la primera pasada a la estimación, con margen", () => {
    const m = modeloLinea(DATOS);
    expect(m.inicio!).toBeLessThan(Date.parse("2026-06-17T12:24:34Z"));
    expect(m.fin!).toBeGreaterThan(Date.parse("2026-11-17T01:44:32Z"));
  });

  it("un hueco con fechas incluidas acaba al final de su último día", () => {
    const [h] = modeloLinea(DATOS).huecos;
    expect(new Date(h.inicio).toISOString()).toBe("2026-07-27T00:00:00.000Z");
    expect(new Date(h.fin).toISOString()).toBe("2026-08-11T00:00:00.000Z");
  });

  it("con serie, deja solo esa fila", () => {
    expect(modeloLinea(DATOS, null, D).filas.map((f) => f.serie)).toEqual([D]);
  });

  it("sin pasadas no hay eje, aunque haya huecos", () => {
    const m = modeloLinea({ ...DATOS, passes: [], excluded: [], next_pass_estimates: [] });
    expect(m.inicio).toBeNull();
    expect(m.filas).toEqual([]);
  });

  it("acorta el nombre de la serie a pista y fotograma", () => {
    expect(serieCorta(A)).toBe("T048A-F015");
    expect(serieCorta("rara")).toBe("rara");
  });
});

describe("tramo del evento", () => {
  it("con hora, dura las horas supuestas desde esa hora UTC", () => {
    const t = tramoEvento(EVENTO);
    expect(new Date(t.inicio).toISOString()).toBe("2026-07-01T18:30:00.000Z");
    expect(new Date(t.fin).toISOString()).toBe("2026-07-02T00:30:00.000Z");
    expect(t.inicioIncierto).toBe(false);
  });

  it("acepta HH:MM y la Z final", () => {
    expect(tramoEvento({ ...EVENTO, event_time: "18:30" }).inicio).toBe(Date.parse("2026-07-01T18:30:00Z"));
    expect(tramoEvento({ ...EVENTO, event_time: "18:30:00Z" }).inicio).toBe(Date.parse("2026-07-01T18:30:00Z"));
  });

  it("sin hora, puede empezar en cualquier momento del día", () => {
    const t = tramoEvento({ ...EVENTO, event_time: null });
    expect(new Date(t.inicio).toISOString()).toBe("2026-07-01T00:00:00.000Z");
    expect(new Date(t.fin).toISOString()).toBe("2026-07-02T06:00:00.000Z");
    expect(t.inicioIncierto).toBe(true);
  });
});

describe("eje", () => {
  it("marca el día 1 de cada mes en ejes largos", () => {
    const m = marcasEje(Date.parse("2026-06-15T00:00:00Z"), Date.parse("2026-09-02T00:00:00Z"));
    expect(m.map((t) => new Date(t).toISOString().slice(0, 10))).toEqual(["2026-07-01", "2026-08-01", "2026-09-01"]);
  });

  it("marca cada 7 días en ejes cortos", () => {
    const m = marcasEje(Date.parse("2026-07-01T00:00:00Z"), Date.parse("2026-07-20T00:00:00Z"));
    expect(m).toHaveLength(3);
  });
});

describe("próxima pasada (compromiso del PR 41)", () => {
  it("dice que es una estimación y que el plan no se consultó", () => {
    const l = describirEstimacion(DATOS.next_pass_estimates[0], "es");
    expect(l).toContain(TEXTOS_LINEA.es.baseEstimacion);
    expect(l).toContain(TEXTOS_LINEA.es.planes.unknown);
    expect(l).toContain(TEXTOS_LINEA.es.planSinConsultar);
  });

  it("con plan, da la fecha de consulta y avisa de que no garantiza la adquisición", () => {
    const p = {
      ...DATOS.next_pass_estimates[0],
      observation_plan: { status: "planned" as const, plan: "P", config_id: "C", same_config: true, checked_at: "2026-11-13T10:00:00Z" },
    };
    const l = describirEstimacion(p, "en");
    expect(l).toContain(TEXTOS_LINEA.en.planNoGarantiza);
    expect(l).toContain(TEXTOS_LINEA.en.planConsultado("2026-11-13 10:00"));
  });
});

function montar(opciones: Partial<Parameters<typeof crearLineaTiempo>[1]> = {}) {
  const c = document.createElement("div");
  const linea = crearLineaTiempo(c, { timeline: DATOS, ahora: Date.parse("2026-11-14T00:00:00Z"), ...opciones });
  return { c, linea };
}

describe("dibujo", () => {
  it("pinta cada tipo de marca con su forma", () => {
    const { c } = montar();
    expect(c.querySelectorAll("circle.atlas-linea-pasada")).toHaveLength(3 + 1); // 3 pasadas + leyenda
    expect(c.querySelector(".atlas-linea-pasada-parcial")).not.toBeNull(); // GD1 no contiene la zona
    expect(c.querySelectorAll("path.atlas-linea-excluida").length).toBeGreaterThanOrEqual(1);
    expect(c.querySelectorAll("circle.atlas-linea-estimada").length).toBeGreaterThanOrEqual(1);
    expect(c.querySelectorAll("rect.atlas-linea-hueco").length).toBeGreaterThanOrEqual(1);
    expect(c.querySelector(".atlas-linea-hoy")).not.toBeNull();
  });

  it("la pasada excluida enseña su motivo y su evidencia a la vista (compromiso del PR 40)", () => {
    const nota = montar().c.querySelector(".atlas-linea-nota-excluida");
    expect(nota?.textContent).toContain(TEXTOS_LINEA.es.motivos.product_defect);
    expect(nota?.textContent).toContain("La vista previa de ASF muestra la anomalía.");
    expect(nota?.textContent).toContain("2026-11-12");
  });

  it("un motivo desconocido se muestra con su código", () => {
    const { c } = montar({ timeline: { ...DATOS, excluded: [{ ...DATOS.excluded[0], reason: "otro_motivo" }] } });
    expect(c.querySelector(".atlas-linea-nota-excluida")?.textContent).toContain("otro_motivo");
  });

  it("la próxima pasada va como estimación, a la vista", () => {
    const nota = montar().c.querySelector(".atlas-linea-nota-estimada");
    expect(nota?.textContent).toContain("2026-11-17 01:44");
    expect(nota?.textContent).toContain(TEXTOS_LINEA.es.baseEstimacion);
  });

  it("el evento lleva su banda y el texto del supuesto (compromiso del PR 33)", () => {
    const { c } = montar({ evento: EVENTO });
    expect(c.querySelector("rect.atlas-linea-evento:not(.atlas-linea-evento-incierto)")).not.toBeNull();
    expect(c.querySelector(".atlas-linea-supuesto")?.textContent).toContain(EVENTO.assumption.text);
  });

  it("sin hora, la banda del evento lleva borde discontinuo", () => {
    const { c } = montar({ evento: { ...EVENTO, event_time: null } });
    expect(c.querySelector(".atlas-linea-evento-incierto")).not.toBeNull();
    expect(c.querySelector(".atlas-linea-nota-evento")?.textContent).toContain("sin hora");
  });

  it("la lista en texto tiene todas las pasadas", () => {
    const items = montar().c.querySelectorAll(".atlas-linea-lista li");
    expect(items).toHaveLength(3);
    expect(items[0].textContent).toContain("519 h");
  });

  it("sin datos de catalog solo queda el título", () => {
    const { c } = montar({ timeline: null });
    expect(c.querySelector("svg")).toBeNull();
    expect(c.querySelector("h3")?.textContent).toBe(TEXTOS_LINEA.es.titulo);
  });

  it("dice que no hay pasadas en lugar de pintar un eje vacío", () => {
    const { c } = montar({ timeline: { ...DATOS, passes: [], excluded: [], next_pass_estimates: [] } });
    expect(c.querySelector(".atlas-linea-vacia")?.textContent).toBe(TEXTOS_LINEA.es.sinPasadas);
  });

  it("actualizar cambia el idioma sin recrear el contenedor", () => {
    const { c, linea } = montar();
    const raiz = c.firstElementChild;
    linea.actualizar({ idioma: "en" });
    expect(c.firstElementChild).toBe(raiz);
    expect(c.querySelector("h3")?.textContent).toBe(TEXTOS_LINEA.en.titulo);
  });

  it("sin onPassSelected las pasadas no son botones", () => {
    expect(montar().c.querySelector("[role=button]")).toBeNull();
  });

  it("con onPassSelected, clic y Enter eligen la pasada", () => {
    const elegida = vi.fn();
    const { c } = montar({ onPassSelected: elegida });
    const botones = c.querySelectorAll<SVGElement>("[role=button]");
    expect(botones).toHaveLength(3);
    botones[0].dispatchEvent(new MouseEvent("click", { bubbles: true }));
    botones[1].dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(elegida.mock.calls.map(([p]) => p.granule_id)).toEqual(["GA1", "GA2"]);
    expect(elegida.mock.calls[0][0]).toEqual({ series: A, granule_id: "GA1", acquired_at: "2026-06-17T12:24:34Z" });
  });

  it("destruir quita la línea", () => {
    const { c, linea } = montar();
    linea.destruir();
    expect(c.childElementCount).toBe(0);
  });
});
