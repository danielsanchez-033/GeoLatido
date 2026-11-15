// PNG transparente para las teselas ópticas vacías (404 de TiTiler fuera de la huella MGRS).

let vacia: Promise<ArrayBuffer> | null = null;

/** PNG transparente de 1 × 1 para las teselas vacías. Se crea una vez y se reutiliza. */
export function teselaVacia(): Promise<ArrayBuffer> {
  if (!vacia) {
    const lienzo = new OffscreenCanvas(1, 1);
    // Sin un contexto, convertToBlob() lanza InvalidStateError ("has no rendering context").
    lienzo.getContext("2d");
    vacia = lienzo
      .convertToBlob({ type: "image/png" })
      .then((b) => b.arrayBuffer())
      .catch((e: unknown) => {
        // No se guarda una promesa fallida: el siguiente 404 vuelve a intentarlo.
        vacia = null;
        throw e;
      });
  }
  return vacia;
}

/** Solo para pruebas: olvida el PNG guardado. */
export function reiniciarTeselaVacia(): void {
  vacia = null;
}
