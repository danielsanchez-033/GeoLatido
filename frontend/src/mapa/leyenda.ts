import type { AvisoEscena } from "./escena";
import { COLOR_CAMBIO } from "./estado";
import type { Idioma } from "./textos";
import { TEXTOS } from "./textos";
import type { CapaRadar } from "./tipos";

// Paradas de la paleta "rdbu" de TiTiler (RdBu de matplotlib): rojo en el mínimo, azul en el máximo.
export const RDBU = [
  "#67001f", "#b2182b", "#d6604d", "#f4a582", "#fddbc7", "#f7f7f7",
  "#d1e5f0", "#92c5de", "#4393c3", "#2166ac", "#053061",
];

/** Tramos de la capa de cambio en dB de −10 a +10 (`CHANGE_DB_BINS` en verdicts), como paradas de un degradado. */
export const TRAMOS_DB = [
  "#b2182b 0% 20%", "#d6604d 20% 35%", "#f4a582 35% 42.5%", "transparent 42.5% 57.5%",
  "#92c5de 57.5% 65%", "#4393c3 65% 80%", "#2166ac 80% 100%",
];

/** Por debajo de este valor una capa radar casi desaparece y lo no observable dejaría de verse. */
export const OPACIDAD_MINIMA = 0.2;

export function limitarOpacidad(o: number): number {
  if (!Number.isFinite(o)) return 1;
  return Math.min(1, Math.max(OPACIDAD_MINIMA, o));
}

/** Lee `rescale=min,max` de una plantilla de cambio de la API. */
export function rangoReescalado(plantilla: string): [number, number] | null {
  const consulta = plantilla.split("?")[1] ?? "";
  const valor = new URLSearchParams(consulta).get("rescale");
  if (!valor) return null;
  const [a, b] = valor.split(",").map(Number);
  return Number.isFinite(a) && Number.isFinite(b) ? [a, b] : null;
}

export function formatoDb(x: number): string {
  const s = String(x).replace("-", "−");
  return `${x > 0 ? "+" : ""}${s} dB`;
}

export interface EstadoLeyenda {
  idioma: Idioma;
  capa: CapaRadar;
  capasDisponibles: boolean;
  opacidad: number;
  rango: [number, number] | null;
  causa?: string;
  /** Cambio de nivel de toda la escena en este par (ver escena.ts). */
  avisoEscena?: AvisoEscena;
  /** El mapa está en 3D: la leyenda documenta las teclas de giro e inclinación (RF-INT-15). */
  teclas3d?: boolean;
}

interface Manejadores {
  alCambiarCapa: (c: CapaRadar) => void;
  alCambiarOpacidad: (o: number) => void;
}

let contador = 0;

/** Panel con selector de capa, opacidad y leyenda. Devuelve una función para redibujarlo. */
export function crearLeyenda(contenedor: HTMLElement, m: Manejadores) {
  const id = `atlas-${++contador}`;
  const panel = document.createElement("section");
  panel.className = "atlas-panel";
  contenedor.append(panel);

  panel.addEventListener("change", (ev) => {
    const el = ev.target as HTMLInputElement;
    if (el.name === `${id}-capa`) m.alCambiarCapa(el.value as CapaRadar);
  });
  panel.addEventListener("input", (ev) => {
    const el = ev.target as HTMLInputElement;
    if (el.type === "range") m.alCambiarOpacidad(Number(el.value) / 100);
  });

  return function dibujar(e: EstadoLeyenda | null) {
    // Conserva el foco del teclado al redibujar (por ejemplo, tras elegir una capa).
    const enfocado = document.activeElement as HTMLInputElement | null;
    const foco = enfocado && panel.contains(enfocado) ? enfocado.type : null;
    panel.replaceChildren();
    panel.hidden = e === null;
    if (!e) return;
    const t = TEXTOS[e.idioma];
    panel.setAttribute("aria-label", t.leyenda);

    if (e.capasDisponibles) {
      const grupo = el("fieldset", "atlas-capas");
      grupo.append(el("legend", "", t.capa));
      for (const c of ["state", "change_hh", "change_hv"] as CapaRadar[]) {
        const etiqueta = el("label");
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = `${id}-capa`;
        radio.value = c;
        radio.checked = c === e.capa;
        etiqueta.append(radio, ` ${t.capas[c]}`);
        grupo.append(etiqueta);
      }
      panel.append(grupo);

      const opac = el("label", "atlas-opacidad");
      const rango = document.createElement("input");
      rango.type = "range";
      rango.min = "20";
      rango.max = "100";
      rango.step = "5";
      rango.value = String(Math.round(e.opacidad * 100));
      opac.append(`${t.opacidad} `, rango);
      panel.append(opac);
    }

    const lista = el("ul", "atlas-leyenda");
    // Va junto a lo que muestra cambio (el estado o la escala en dB), nunca suelto.
    const aviso =
      e.avisoEscena === "sin_corregir"
        ? el("small", "atlas-aviso-escena", t.avisoEscena)
        : e.avisoEscena === "corregido"
          ? el("small", "atlas-aviso-escena atlas-aviso-escena-corregido", t.notaEscenaCorregida)
          : null;
    if (e.capa === "subsidence") {
      const li = el("li", "atlas-escala");
      const barra = el("div", "atlas-degradado");
      // Mismos tramos que `subsidence_colormap` de verdicts: desde el umbral de la zona, 1,5 y 2 veces el umbral.
      barra.style.background =
        "linear-gradient(to right, transparent 0% 25%, #fec44f 25% 50%, #ec7014 50% 75%, #993404 75% 100%)";
      const marcas = el("div", "atlas-marcas");
      marcas.append(el("span", "", t.hundeMenos), el("span", "", t.hundeMas));
      li.append(barra, marcas, el("small", "", t.escalaHundimiento));
      lista.append(li);
    } else if (e.capa === "state") {
      const cambio = entrada("atlas-muestra-cambio", t.cambioProbable);
      if (aviso) cambio.querySelector(".atlas-entrada")!.append(aviso);
      lista.append(cambio, entrada("atlas-muestra-vacia", t.sinCambio, t.sinCambioNota));
    } else {
      const li = el("li", "atlas-escala");
      const barra = el("div", "atlas-degradado");
      // Mismos tramos que `CHANGE_DB_BINS` de verdicts: rojo si bajó, azul si subió y, entre −1,5 y +1,5 dB,
      // nada (se ve el mapa, como en la trama de cuadros).
      barra.style.background = `linear-gradient(to right, ${TRAMOS_DB.join(", ")})`;
      const marcas = el("div", "atlas-marcas");
      const [min, max] = e.rango ?? [Number.NaN, Number.NaN];
      marcas.append(
        el("span", "", e.rango ? `${t.bajo} ${formatoDb(min)}` : t.bajo),
        el("span", "", e.rango ? `${t.subio} ${formatoDb(max)}` : t.subio),
      );
      li.append(barra, marcas, el("small", "", t.escalaDb));
      if (aviso) li.append(aviso);
      lista.append(li);
    }
    const noObs = entrada("atlas-muestra-trama", t.noObservable, t.noObservableNota);
    if (e.causa) {
      noObs
        .querySelector(".atlas-entrada")!
        .append(el("small", "atlas-causa", `${t.causaPrincipal}: ${e.causa}`));
    }
    lista.append(noObs);
    panel.append(lista);
    if (e.teclas3d) panel.append(el("p", "atlas-teclas-3d", t.teclas3d));

    if (foco === "radio") panel.querySelector<HTMLInputElement>("input[type=radio]:checked")?.focus();
    if (foco === "range") panel.querySelector<HTMLInputElement>("input[type=range]")?.focus();
  };
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, clase = "", texto?: string) {
  const n = document.createElement(tag);
  if (clase) n.className = clase;
  if (texto !== undefined) n.textContent = texto;
  return n;
}

function entrada(claseMuestra: string, nombre: string, nota?: string) {
  const li = el("li");
  const muestra = el("span", `atlas-muestra ${claseMuestra}`);
  muestra.setAttribute("aria-hidden", "true");
  if (claseMuestra === "atlas-muestra-cambio") {
    muestra.style.background = `rgb(${COLOR_CAMBIO.join(",")})`;
  }
  const texto = el("span", "atlas-entrada");
  texto.append(el("strong", "", nombre));
  if (nota) texto.append(el("small", "", nota));
  li.append(muestra, texto);
  return li;
}
