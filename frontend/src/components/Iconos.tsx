import type { ButtonHTMLAttributes, ReactNode } from 'react'

/**
 * Iconos de línea del sistema en blanco y negro (2026-11-14): trazo de 1,75 en una caja de 24, extremos
 * redondeados y color heredado. Son decorativos: el nombre del botón va en `aria-label`.
 */
const TRAZOS: Record<string, ReactNode> = {
  buscar: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="M16 16l4.5 4.5" />
    </>
  ),
  ver: (
    <>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
      <circle cx="12" cy="12" r="2.75" />
    </>
  ),
  guardar: <path d="M6.5 3.5h11v17l-5.5-3.75-5.5 3.75z" />,
  mapa: (
    <>
      <path d="M3.5 6.5l5.5-2.5 6 2.5 5.5-2.5v13.5l-5.5 2.5-6-2.5-5.5 2.5z" />
      <path d="M9 4v13.5M15 6.5V20" />
    </>
  ),
  historia: (
    <>
      <path d="M12 6.5c-1.8-1.5-4.4-2-8-2v13c3.6 0 6.2.5 8 2 1.8-1.5 4.4-2 8-2v-13c-3.6 0-6.2.5-8 2z" />
      <path d="M12 6.5v13" />
    </>
  ),
  evento: (
    <>
      <rect x="3.5" y="5" width="17" height="15.5" rx="2" />
      <path d="M3.5 10h17M8 3v4M16 3v4M12 13.5v3l2 1" />
    </>
  ),
  interprete: (
    <>
      <path d="M4 20h4.5L19.5 9a2.1 2.1 0 0 0-3-3L5.5 17z" />
      <path d="M14.5 8l3 3M13 20h7" />
    </>
  ),
  comunidad: (
    <>
      <circle cx="9" cy="8.5" r="3.25" />
      <path d="M3 19.5c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5" />
      <path d="M15.5 5.5a3.25 3.25 0 0 1 0 6.25M17.5 14.3c2 .7 3.5 2.6 3.5 5.2" />
    </>
  ),
  descargar: <path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19.5h14" />,
  abrir: <path d="M13.5 4.5H19.5V10.5M19.5 4.5l-8.5 8.5M17.5 14v5a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-11a1 1 0 0 1 1-1h5" />,
  borrar: <path d="M4.5 7h15M10 11v6M14 11v6M6.5 7l1 13h9l1-13M9.5 7V4.5h5V7" />,
  cerrar: <path d="M6.5 6.5l11 11M17.5 6.5l-11 11" />,
  quitar: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M9.25 9.25l5.5 5.5M14.75 9.25l-5.5 5.5" />
    </>
  ),
  entrar: <path d="M14.5 4h4.5v16h-4.5M9.5 8l4 4-4 4M13.5 12H4" />,
  salir: <path d="M9.5 4H5v16h4.5M15 8l4 4-4 4M19 12H9.5" />,
  anterior: <path d="M14.5 6l-6 6 6 6" />,
  siguiente: <path d="M9.5 6l6 6-6 6" />,
  volver: <path d="M9.5 7L5 11.5 9.5 16M5 11.5h9.5a4.5 4.5 0 0 1 0 9H12" />,
  comparar: (
    <>
      <rect x="3.5" y="4.5" width="17" height="15" rx="1.5" />
      <path d="M12 3v18" />
    </>
  ),
  sol: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" />
    </>
  ),
  luna: <path d="M19.5 14.5A7.5 7.5 0 1 1 9.5 4.5a6 6 0 0 0 10 10z" />,
  // Rediseño de vidrio (T-FAR-21)
  hallazgos: <path d="M12 3l1.9 5.6L19.5 10.5l-5.6 1.9L12 18l-1.9-5.6L4.5 10.5l5.6-1.9zM18.5 15.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z" />,
  filtros: <path d="M4 5h16l-6.25 7.5v5.5l-3.5 2v-7.5z" />,
  satelite: (
    <>
      <path d="M9.5 9.5l5 5M7 12l5-5 5 5-5 5z" />
      <path d="M4.5 9.5l2.5-2.5M2.5 7.5l2.5-2.5 2 2-2.5 2.5zM14.5 19.5l2.5-2.5M17 21.5l2.5-2.5 2 2-2.5 2.5zM15.5 4.5a4 4 0 0 1 4 4" />
    </>
  ),
  cubo: (
    <>
      <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z" />
      <path d="M4 7.5l8 4.5 8-4.5M12 12v9" />
    </>
  ),
  plano: <path d="M3 19.5l5.5-10 4 6 2.5-3.5 6 7.5z" />,
  centrar: (
    <>
      <circle cx="12" cy="12" r="6.5" />
      <circle cx="12" cy="12" r="1.75" />
      <path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3" />
    </>
  ),
  capas: (
    <>
      <path d="M12 3.5l9 4.75-9 4.75-9-4.75z" />
      <path d="M3 12.5l9 4.75 9-4.75M3 16.5l9 4.75 9-4.75" />
    </>
  ),
  pantalla: <path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5M9 9l6 6M15 9l-6 6" />,
  reproducir: <path d="M7.5 4.5v15l12-7.5z" />,
  pausa: <path d="M8 5v14M16 5v14" />,
  ubicacion: (
    <>
      <path d="M12 21s-6.5-6.2-6.5-11a6.5 6.5 0 0 1 13 0c0 4.8-6.5 11-6.5 11z" />
      <circle cx="12" cy="10" r="2.25" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 11v5.5M12 7.75v.01" />
    </>
  ),
  subir: <path d="M12 20V9M7.5 13.5L12 9l4.5 4.5M5 4.5h14" />,
  estrella: <path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z" />,
  llave: (
    <>
      <circle cx="8" cy="15.5" r="3.5" />
      <path d="M10.5 13L19 4.5M16 7.5l2.5 2.5M13.75 9.75l2 2" />
    </>
  ),
  nube: <path d="M7 18.5h10a4 4 0 0 0 .5-7.97A5.5 5.5 0 0 0 7 9.5a4.5 4.5 0 0 0 0 9z" />,
  recibo: <path d="M6 3.5h12v17l-2-1.25-2 1.25-2-1.25-2 1.25-2-1.25-2 1.25zM9 8h6M9 11.5h6M9 15h4" />,
  arriba: <path d="M6 14.5l6-6 6 6" />,
  abajo: <path d="M6 9.5l6 6 6-6" />,
  cuenta: (
    <>
      <circle cx="12" cy="8" r="3.75" />
      <path d="M4.5 20.5c0-4.1 3.4-6.5 7.5-6.5s7.5 2.4 7.5 6.5" />
    </>
  ),
}

export type NombreIcono = keyof typeof TRAZOS

export function Icono({ nombre, tamano = 20 }: { nombre: NombreIcono; tamano?: number }) {
  return (
    <svg
      className="icono"
      viewBox="0 0 24 24"
      width={tamano}
      height={tamano}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {TRAZOS[nombre]}
    </svg>
  )
}

/**
 * Botón solo con icono. El nombre accesible es `etiqueta` (aria-label) y la misma etiqueta sale como
 * descripción emergente (`title`), para quien usa ratón y no reconoce el icono.
 */
export function BotonIcono({
  icono,
  etiqueta,
  className,
  type = 'button',
  ...resto
}: { icono: NombreIcono; etiqueta: string } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button {...resto} type={type} className={`boton-icono${className ? ` ${className}` : ''}`} aria-label={etiqueta} title={etiqueta}>
      <Icono nombre={icono} />
    </button>
  )
}
