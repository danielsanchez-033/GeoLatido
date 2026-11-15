# Glosario

Cada término lleva un identificador estable (`id`) para enlazarlo desde la interfaz. Los textos no afirman nada que la API no sostenga: si la API cambia, este archivo cambia con ella.

## Las respuestas

<a id="change_probable"></a>
### Cambio probable

La señal de radar cambió entre dos fechas en una parte de la zona mayor que el mínimo que fijamos. Dice **dónde** cambió la señal, no qué lo causó ni si hubo daños. El mínimo es un valor inicial que aún no se ha calibrado con datos reales.

<a id="no_detectable_change"></a>
### Sin cambio detectable

Se observó la zona, pero el cambio no llegó al mínimo. No significa que no pasara nada: un cambio pequeño, o uno que ocurrió y se deshizo entre las dos fechas, puede no verse.

<a id="not_observable"></a>
### No observable

No podemos responder. O no se vio una parte suficiente de la zona, o ninguna pasada coincidió con el evento. Es distinto de «sin cambio»: aquí falta información, no hay una respuesta negativa.

<a id="cause"></a>
### Causa de lo no observable

El motivo por el que no se pudo observar. Puede ser:

- **Fuera de la pasada:** la zona quedó fuera de la franja que barrió el satélite.
- **Datos inválidos o parcialmente enfocados:** el procesado de la misión marcó esos píxeles como no fiables.
- **Anomalía en los datos de entrada:** la misión registró un problema en los datos originales.
- **Muy pocas muestras por píxel:** el valor se calculó con tan pocas medidas que no es fiable.
- **Sin dato utilizable:** el píxel no tiene valor.
- **Relieve:** montañas que ocultan o deforman la señal. Está reservado: los datos GCOV no lo traen y aún no lo calculamos.
- **Ninguna pasada durante el evento:** el satélite no pasó mientras duraba lo que se pregunta.
- **Fuera del periodo con datos:** la fecha cae antes de la primera pasada o después de la última de la serie.

<a id="hypothesis"></a>
### Hipótesis

Una explicación posible del cambio, sacada de cómo variaron HH y HV. Orienta, pero no prueba nada: confirmarla requiere otra fuente o ir al lugar.

<a id="signature"></a>
### Firma por polarización

La combinación de cómo cambiaron HH y HV, por ejemplo «sube HH y HV no cambia». Cada combinación sugiere una hipótesis distinta. Si la firma es mixta, no proponemos ninguna causa.

## La señal

<a id="backscatter"></a>
### Eco o retrodispersión

La parte de la señal de radar que vuelve al satélite. Depende de la rugosidad, la forma y la humedad de lo que toca.

<a id="db"></a>
### Decibelio (dB)

La escala en la que medimos el eco y su cambio. Es logarítmica: subir 3 dB equivale aproximadamente a duplicar la energía del eco.

<a id="hh"></a>
### HH

El satélite emite y recibe con orientación horizontal. Es más sensible al suelo, a la humedad y al agua.

<a id="hv"></a>
### HV

El satélite emite en horizontal y recibe en vertical. El eco crece cuando la señal rebota muchas veces, como dentro de la vegetación.

<a id="l_band"></a>
### Banda L

El tipo de onda que usa el radar de NISAR que analizamos, de unos 24 cm. Una onda tan larga atraviesa en parte la vegetación.

<a id="threshold"></a>
### Umbral

El cambio mínimo, en dB, para marcar un píxel como cambiado. Se ajusta a cada par de fechas y nunca baja de un mínimo fijo. Es un valor inicial, todavía sin calibrar con datos reales.

<a id="observed_fraction"></a>
### Parte observada

Qué porcentaje de la zona tuvo datos válidos en las dos fechas. Si es demasiado baja, la respuesta es «no observable».

<a id="changed_fraction"></a>
### Parte con cambio

Qué porcentaje de la zona **observada** superó el umbral.

## El tiempo

<a id="pass"></a>
### Pasada

Cada vez que el satélite barre la zona y toma una imagen. En la misma serie, las pasadas se repiten cada 12 días.

<a id="interval_days"></a>
### Días entre fechas

Cuántos días separan las dos imágenes que se comparan. Cuantos más días, más cosas pudieron pasar y deshacerse sin quedar registradas.

<a id="pair_kind"></a>
### Par consecutivo y ventana completa

Un par consecutivo compara una pasada con la siguiente. La ventana completa compara la primera y la última fecha de la serie.

<a id="persistence"></a>
### Persistencia supuesta

Cuánto tiempo suponemos que un evento sigue siendo visible, por ejemplo agua encharcada durante 24 horas. Si ninguna pasada cae dentro de ese tiempo, el evento es «no observable». Es un supuesto de la consulta, no un dato medido.

<a id="data_gap"></a>
### Hueco de adquisición

Un periodo sin imágenes. Entre el 27 de julio y el 10 de agosto de 2026 la misión no adquirió datos. Los pares que lo cruzan lo avisan.

<a id="utc"></a>
### UTC

La hora universal. Todas las fechas de la aplicación están en UTC, que en Parral va 6 horas por delante de la hora local.

## Los datos y su origen

<a id="nisar"></a>
### NISAR

Satélite radar de la NASA y la ISRO (la agencia espacial de la India), lanzado el 30 de julio de 2025.

<a id="gcov"></a>
### GCOV

El producto de NISAR que usamos: imágenes del eco de radar ya colocadas sobre el mapa, una por fecha.

<a id="granule"></a>
### Gránulo

Un archivo de datos de una sola pasada. El recibo lista los gránulos exactos de cada respuesta.

<a id="series"></a>
### Serie

Un conjunto de pasadas tomadas con la misma geometría, que se pueden comparar entre sí. Se identifica por su pista, dirección y marco.

<a id="track"></a>
### Pista, dirección y marco

La pista es la órbita que repite el satélite. La dirección dice si iba hacia el norte (ascendente) o hacia el sur (descendente). El marco es el tramo de esa órbita que cubre la zona.

<a id="mode"></a>
### Modo y polarización

La configuración con la que el radar tomó la imagen, por ejemplo el ancho de banda y las orientaciones que emitió y recibió. Solo comparamos fechas con el mismo modo y polarización.

<a id="crid"></a>
### CRID

Código que identifica la versión del procesado de la misión. Solo comparamos fechas con el mismo CRID, para no confundir un cambio de procesado con un cambio real.

<a id="maturity"></a>
### Madurez: provisional o validado

Provisional son datos publicados antes de que la misión termine de validarlos. Validado son datos ya revisados. Nunca mezclamos los dos en una comparación.

<a id="receipt"></a>
### Recibo

El detalle de dónde sale cada respuesta: gránulos, serie, CRID, madurez y avisos. Sirve para que cualquiera pueda comprobarla.

<a id="notices"></a>
### Avisos

Advertencias que acompañan cada respuesta: por ejemplo, que los datos son provisionales, que la serie tiene un hueco de adquisición o que los umbrales se estiman sobre la propia escena.

<a id="data_kind"></a>
### Datos sintéticos o reales

Los datos sintéticos son inventados para probar la aplicación y no describen ningún lugar real. La aplicación siempre indica cuándo un dato es sintético.

<a id="aoi"></a>
### Zona

El área que se analiza, por ejemplo Hidalgo del Parral, en Chihuahua.

<a id="optical"></a>
### Imagen óptica de referencia

Una foto de satélite normal (Sentinel-2, del programa Copernicus) de una fecha cercana. Ayuda a interpretar el mapa, pero puede salir tapada por las nubes.
