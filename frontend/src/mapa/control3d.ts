// Botón 2D/3D (T-ATL-10, RF-INT-11): un control de MapLibre con aria-pressed.
import type { IControl } from "maplibre-gl";
import { TEXTOS, type Idioma } from "./textos";

export interface EstadoControl3d {
  /** Se pidió el 3D (aunque el mapa haya quedado en 2D por un motivo que ya se avisa). */
  pulsado: boolean;
  idioma: Idioma;
}

export class Control3d implements IControl {
  private caja: HTMLDivElement;
  private boton: HTMLButtonElement;

  constructor(alPulsar: () => void) {
    this.caja = document.createElement("div");
    this.caja.className = "maplibregl-ctrl maplibregl-ctrl-group atlas-control-3d";
    this.boton = document.createElement("button");
    this.boton.type = "button";
    this.boton.className = "atlas-boton-3d";
    this.boton.addEventListener("click", alPulsar);
    this.caja.append(this.boton);
  }

  dibujar(e: EstadoControl3d) {
    const t = TEXTOS[e.idioma];
    this.boton.textContent = "3D";
    this.boton.setAttribute("aria-pressed", String(e.pulsado));
    this.boton.setAttribute("aria-label", t.boton3d);
    this.boton.title = e.pulsado ? t.boton3dQuitar : t.boton3dPoner;
  }

  onAdd(): HTMLElement {
    return this.caja;
  }

  onRemove(): void {
    this.caja.remove();
  }
}
