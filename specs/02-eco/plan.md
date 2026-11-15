# Eco — plan técnico

## Diseño

- **Por pares.** Hoy `process_series` carga todas las escenas. Pasará a leer cada fecha una vez, escribir su COG en dB y comparar solo dos escenas a la vez. El par de ventana completa compara la primera y la última fecha.
- **Control de calidad.** Por fecha se calculan: fracción válida según `mask`, `numberOfLooks` e `inputDataExceptionMask`; mediana en dB de HH y HV sobre píxeles válidos; y desviación respecto a la mediana de la serie. Bandera `radiometric_outlier` si la desviación supera 1,5 dB. Ese umbral es inicial y se calibrará.
- **Layover y sombra.** Con el DEM GLO-30 remuestreado a la malla, y los ángulos de incidencia y de mirada de la geometría del producto, se calcula la pendiente hacia el sensor. Si los metadatos de geometría no bastan, se aproxima con el ángulo de incidencia medio y se declara como aproximación.
- **Georreferencia.** Se compara la orilla de la presa La Boquilla en radar con su posición en Sentinel-2 y se anota el desplazamiento en MEMORY.

## Interfaces y contratos

Cambio aditivo del manifiesto: `dates[].qa` con `valid_fraction`, `median_hh_db`, `median_hv_db`, `deviation_hh_db`, `deviation_hv_db` y `flags[]`. Requiere aprobación de Balanza.

## Datos

- Malla nativa UTM; no se reproyecta antes de calcular.
- COG con compresión DEFLATE y vistas reducidas: promedio para dB y vecino más cercano para estados.

## Pruebas

- Escena sintética con una fecha desplazada +3 dB, que debe quedar marcada.
- Medición de memoria con 10 fechas sintéticas a resolución real.
- Pendiente artificial que debe dar estado 15.

## Riesgos

- Sin metadatos de geometría precisos, el layover será aproximado y se declarará así.
- La desviación de la mediana puede ser un cambio real de toda la escena, como una lluvia general. Por eso es una bandera, no una exclusión.
