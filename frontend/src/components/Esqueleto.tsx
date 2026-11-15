/**
 * Esqueletos de carga: la forma de lo que va a llegar, en gris y con un brillo que recorre los bloques
 * (sin movimiento con `prefers-reduced-motion`). El texto de estado va oculto a la vista y lo lee el
 * lector de pantalla, así que el aviso de carga no se pierde.
 */
type Variante = 'tarjeta' | 'lista' | 'bloque' | 'texto'

const anchos = ['92%', '78%', '85%', '64%', '88%', '70%']

export function Esqueleto({
  etiqueta,
  variante = 'tarjeta',
  filas = 3,
  className,
}: {
  etiqueta: string
  variante?: Variante
  filas?: number
  className?: string
}) {
  return (
    // Sin etiqueta es solo forma (otro esqueleto ya anuncia la carga) y no se anuncia dos veces.
    <div
      className={`esqueleto esqueleto-${variante}${className ? ` ${className}` : ''}`}
      role={etiqueta ? 'status' : undefined}
      aria-hidden={etiqueta ? undefined : true}
    >
      {etiqueta && <span className="sr-solo">{etiqueta}</span>}
      <div aria-hidden="true">
        {variante === 'bloque' && <span className="esq esq-bloque" />}
        {variante === 'tarjeta' && (
          <>
            <span className="esq-cabecera">
              <span className="esq esq-marca" />
              <span className="esq esq-titulo" />
            </span>
            {Array.from({ length: filas }, (_, i) => (
              <span key={i} className="esq esq-linea" style={{ width: anchos[i % anchos.length] }} />
            ))}
          </>
        )}
        {variante === 'lista' &&
          Array.from({ length: filas }, (_, i) => (
            <span key={i} className="esq-fila">
              <span className="esq esq-marca" />
              <span className="esq-fila-texto">
                <span className="esq esq-linea" style={{ width: anchos[i % anchos.length] }} />
                <span className="esq esq-linea esq-corta" />
              </span>
            </span>
          ))}
        {variante === 'texto' &&
          Array.from({ length: filas }, (_, i) => (
            <span key={i} className="esq esq-linea" style={{ width: anchos[i % anchos.length] }} />
          ))}
      </div>
    </div>
  )
}
