// Comparador deslizante radar frente a óptico Sentinel-2 (T-ATL-07, RF-ATL-07).
//
// Un segundo mapa MapLibre, sin interacción propia, pinta la escena óptica y se
// superpone al mapa radar recortado a la derecha del deslizador. Sigue la cámara
// del mapa principal, que es el único que recibe ratón y teclado.
import * as maplibregl from "maplibre-gl";
import type { MapProps } from "../types/map";
import { contornoZona, estiloMapaBase, fuenteDatos } from "./mapaBase";
import {
  describirLado,
  ladoDisponible,
  limitarPosicion,
  moverConTecla,
  POSICION_INICIAL,
  type LadoOptico,
} from "./optico";
import { descargar, ErrorHttp } from "./protocolo";
import { teselaVacia } from "./teselaVacia";
import type { Idioma } from "./textos";
import { TEXTOS } from "./textos";
import type { Bbox } from "./tipos";

const PROTOCOLO = "atlas-optico";

let registrado = false;

/**
 * Plantilla para MapLibre. Fuera de la huella de su tesela MGRS, TiTiler responde 404:
 * es una tesela vacía, no un error, así que se devuelve transparente.
 */
export function plantillaOptica(url: string): string {
  if (!registrado) {
    registrado = true;
    maplibregl.addProtocol(PROTOCOLO, async (params, abort) => {
      const real = params.url.slice(`${PROTOCOLO}://`.length);
      try {
        const blob = await descargar(real, abort.signal);
        return { data: await blob.arrayBuffer() };
      } catch (e) {
        if (e instanceof ErrorHttp && e.status === 404) return { data: await teselaVacia() };
        throw e;
      }
    });
  }
  return `${PROTOCOLO}://${url}`;
}

export interface OpcionesComparador {
  optical: MapProps["optical"];
  idioma: Idioma;
  aoi: Bbox;
}

export interface Comparador {
  actualizar(c: Partial<OpcionesComparador>): void;
  destruir(): void;
}

let contador = 0;

export function crearComparador(
  contenedor: HTMLElement,
  principal: maplibregl.Map,
  opciones: OpcionesComparador,
): Comparador {
  const id = `atlas-optico-${++contador}`;
  const estado = {
    ...opciones,
    lado: ladoDisponible(opciones.optical, "after") ?? ("after" as LadoOptico),
    posicion: POSICION_INICIAL,
    capas: [] as string[],
  };

  // ---- Mapa óptico superpuesto ----
  const capa = document.createElement("div");
  capa.className = "atlas-optico";
  capa.setAttribute("aria-hidden", "true");
  const lienzo = document.createElement("div");
  lienzo.className = "atlas-lienzo";
  capa.append(lienzo);

  // ---- Deslizador ----
  const divisor = document.createElement("div");
  divisor.className = "atlas-divisor";
  const asa = document.createElement("div");
  asa.className = "atlas-divisor-asa";
  asa.tabIndex = 0;
  asa.setAttribute("role", "slider");
  asa.setAttribute("aria-valuemin", "0");
  asa.setAttribute("aria-valuemax", "100");
  asa.setAttribute("aria-orientation", "horizontal");
  const etiquetaRadar = document.createElement("span");
  etiquetaRadar.className = "atlas-divisor-etiqueta atlas-divisor-radar";
  const etiquetaOptico = document.createElement("span");
  etiquetaOptico.className = "atlas-divisor-etiqueta atlas-divisor-optico";
  divisor.append(etiquetaRadar, asa, etiquetaOptico);

  // ---- Panel: lado, fecha, nubes, aviso y atribución ----
  const panel = document.createElement("section");
  panel.className = "atlas-optico-panel";

  contenedor.append(capa, divisor, panel);

  const optico = new maplibregl.Map({
    container: lienzo,
    style: estiloMapaBase(),
    center: principal.getCenter(),
    zoom: principal.getZoom(),
    interactive: false,
    attributionControl: false,
  });

  function sincronizar() {
    optico.jumpTo({
      center: principal.getCenter(),
      zoom: principal.getZoom(),
      bearing: principal.getBearing(),
      pitch: principal.getPitch(),
    });
  }
  let destruido = false;
  const alRedimensionar = () => {
    if (!destruido) optico.resize();
  };
  principal.on("move", sincronizar);
  principal.on("resize", alRedimensionar);
  // Sin tamaño al crearse, MapLibre se queda en 400 × 300 px: se ajusta cuando el lienzo cambia de tamaño.
  const observador = typeof ResizeObserver === "function" ? new ResizeObserver(alRedimensionar) : null;
  observador?.observe(capa);
  requestAnimationFrame(alRedimensionar);

  function aplicarPosicion() {
    const p = estado.posicion;
    // Se ve el óptico a la derecha del deslizador; a la izquierda, el radar.
    capa.style.clipPath = `inset(0 0 0 ${p}%)`;
    divisor.style.left = `${p}%`;
    asa.setAttribute("aria-valuenow", String(Math.round(p)));
    asa.setAttribute("aria-valuetext", `${Math.round(p)} %`);
  }

  function vistaActual() {
    return estado.optical?.[estado.lado];
  }

  function aplicarEscena() {
    for (const capaId of estado.capas) {
      if (optico.getLayer(capaId)) optico.removeLayer(capaId);
      if (optico.getSource(capaId)) optico.removeSource(capaId);
    }
    estado.capas = [];
    const vista = vistaActual();
    if (!vista) return;
    vista.tiles.forEach((plantilla, i) => {
      const capaId = `${id}-${estado.lado}-${i}`;
      // Acotada a la zona y al zoom del dato (T-ATL-08). Cada tesela MGRS cubre solo una parte de la
      // zona, así que dentro de ella aún se piden algunas fuera de su huella: para quitarlas hace falta
      // la caja de cada tesela, que catalog ya da (T-ANT-19) y verdicts aún no pasa.
      optico.addSource(capaId, fuenteDatos(plantillaOptica(plantilla), estado.aoi));
      optico.addLayer(
        { id: capaId, type: "raster", source: capaId, paint: { "raster-fade-duration": 0 } },
        "aoi-contorno-halo",
      );
      estado.capas.push(capaId);
    });
  }

  function dibujarPanel() {
    const t = TEXTOS[estado.idioma];
    etiquetaRadar.textContent = t.radar;
    etiquetaOptico.textContent = t.optico;
    asa.setAttribute("aria-label", t.deslizador);

    panel.replaceChildren();
    panel.setAttribute("aria-label", t.comparador);

    // La leyenda del grupo hace de título visible del panel.
    const grupo = document.createElement("fieldset");
    grupo.className = "atlas-optico-lados";
    const leyenda = document.createElement("legend");
    leyenda.textContent = t.comparador;
    grupo.append(leyenda);
    for (const lado of ["before", "after"] as LadoOptico[]) {
      const etiqueta = document.createElement("label");
      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = `${id}-lado`;
      radio.value = lado;
      radio.checked = lado === estado.lado;
      radio.disabled = !estado.optical?.[lado];
      etiqueta.append(radio, ` ${lado === "before" ? t.antes : t.despues}`);
      grupo.append(etiqueta);
    }
    panel.append(grupo);

    const vista = vistaActual();
    if (!vista) return;
    const d = describirLado(vista, estado.idioma);
    for (const linea of d.lineas) {
      const p = document.createElement("p");
      p.textContent = linea;
      panel.append(p);
    }
    if (d.aviso) {
      const aviso = document.createElement("p");
      aviso.className = "atlas-optico-aviso";
      aviso.setAttribute("role", "status");
      aviso.textContent = d.aviso;
      panel.append(aviso);
    }
    if (d.atribucion) {
      const atrib = document.createElement("small");
      atrib.className = "atlas-optico-atribucion";
      atrib.textContent = d.atribucion;
      panel.append(atrib);
    }
  }

  panel.addEventListener("change", (ev) => {
    const el = ev.target as HTMLInputElement;
    if (el.name !== `${id}-lado`) return;
    estado.lado = el.value as LadoOptico;
    if (optico.isStyleLoaded()) aplicarEscena();
    dibujarPanel();
    panel.querySelector<HTMLInputElement>("input:checked")?.focus();
  });

  asa.addEventListener("keydown", (e) => {
    const p = moverConTecla(estado.posicion, e.key);
    if (p === null) return;
    e.preventDefault();
    estado.posicion = p;
    aplicarPosicion();
  });

  asa.addEventListener("pointerdown", (e) => {
    asa.setPointerCapture(e.pointerId);
    // preventDefault evita seleccionar texto al arrastrar, pero también el foco: se da a mano.
    e.preventDefault();
    asa.focus();
  });
  asa.addEventListener("pointermove", (e) => {
    if (!asa.hasPointerCapture(e.pointerId)) return;
    const r = contenedor.getBoundingClientRect();
    estado.posicion = limitarPosicion(((e.clientX - r.left) / r.width) * 100);
    aplicarPosicion();
  });

  optico.on("load", () => {
    optico.addSource("aoi", { type: "geojson", data: contornoZona(estado.aoi) });
    optico.addLayer({
      id: "aoi-contorno-halo",
      type: "line",
      source: "aoi",
      layout: { visibility: "none" },
      paint: { "line-color": "#ffffff", "line-width": 4, "line-opacity": 0.9 },
    });
    optico.addLayer({
      id: "aoi-contorno",
      type: "line",
      source: "aoi",
      layout: { visibility: "none" },
      paint: { "line-color": "#000000", "line-width": 2, "line-dasharray": [3, 2] },
    });
    sincronizar();
    aplicarEscena();
  });

  aplicarPosicion();
  dibujarPanel();

  return {
    actualizar(c) {
      if (c.idioma) estado.idioma = c.idioma;
      if (c.aoi) {
        estado.aoi = c.aoi;
        (optico.getSource("aoi") as maplibregl.GeoJSONSource | undefined)?.setData(contornoZona(c.aoi));
      }
      if ("optical" in c) {
        estado.optical = c.optical;
        estado.lado = ladoDisponible(c.optical, estado.lado) ?? estado.lado;
        if (optico.isStyleLoaded()) aplicarEscena();
      }
      dibujarPanel();
    },
    destruir() {
      principal.off("move", sincronizar);
      principal.off("resize", alRedimensionar);
      destruido = true;
      observador?.disconnect();
      optico.remove();
      capa.remove();
      divisor.remove();
      panel.remove();
    },
  };
}
