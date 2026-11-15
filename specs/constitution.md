# Constitución del proyecto

Principios que valen para todo el código, la documentación y la demo. Cambiarlos requiere un PR `spec(repo): ...` aprobado por las cinco personas.

## I. Propósito

Convertimos datos radar NISAR en **veredictos auditables** por zona y par de fechas, con tres estados: `change_probable`, `no_detectable_change` y `not_observable` con su causa. Decir lo que no se sabe es parte del producto, no un fallo.

## II. Veracidad

1. Solo se comparan fechas con la misma pista, dirección, marco, modo, polarización y CRID. Nunca se mezclan PROVISIONAL y VALIDATED.
2. `data_kind` viaja en cada respuesta y en cada pantalla. Lo sintético nunca se presenta como real.
3. Un píxel no observable se conserva con su causa. Nunca se borra ni se cuenta como "sin cambio".
4. Toda afirmación visible para el usuario sale de un campo de la API, y ese campo se rastrea hasta gránulos concretos.
5. Las hipótesis se redactan como hipótesis. No afirmamos causas, daños ni que NISAR supere a otro sistema sin una medición propia.
6. Ninguna cifra se inventa ni se redondea para que luzca mejor. Las fuentes externas se citan.
7. Los umbrales sin calibrar se declaran como tales.

## III. Señal

1. Solo se usan los términos diagonales `HHHH` y `HVHV`.
2. GCOV está en potencia gamma-0: se promedia en lineal y después se convierte a dB.
3. Ningún valor se modifica en la ingesta. Todo procesamiento ocurre en `processor`.

## IV. Tiempo

1. Todas las fechas y horas se expresan en UTC con formato ISO 8601.
2. Los intervalos se dan en días, y cada veredicto dice cuántos días separan sus fechas.
3. Los huecos de adquisición, la latencia de publicación y la persistencia supuesta de un evento son datos explícitos, nunca supuestos ocultos.

## V. Georreferencia

1. Todo raster declara su CRS. Los cálculos se hacen en la malla nativa, sin reproyectar antes.
2. La API usa WGS84 (EPSG:4326) para coordenadas y extensiones.
3. Las coordenadas que ve el usuario se muestran con la precisión que el dato sostiene: 5 decimales como máximo.

## VI. Contratos y trabajo en paralelo

1. Los servicios no importan código entre sí. Se comunican por HTTP o por los artefactos de `contracts/`.
2. Cambiar un contrato requiere avisar a quien lo consume, actualizarlo en el mismo PR y conseguir la aprobación de los dueños indicados en `CODEOWNERS`.
3. Los contratos no se congelan. El proyecto sigue creciendo durante el evento (14 y 15 de noviembre), incluso con cambios radicales si hacen falta. Cualquier cambio de contrato, aditivo o no, sigue el proceso del punto 2. Lo que está listo (con sus aprobaciones y la CI en verde) se fusiona sin esperar a la demo. Decisión del 2026-11-14, que sustituye al congelamiento acordado el 2026-11-12.
4. Cada rol trabaja en sus carpetas. Tocar las de otro rol requiere su aprobación.

## VII. Calidad: definición de terminado

Un cambio está terminado cuando:

1. Cumple los criterios de aceptación de su especificación.
2. Tiene pruebas automáticas que fallarían sin el cambio.
3. La CI está en verde, incluidas las pruebas de contrato y la prueba de humo.
4. Respeta las reglas de veracidad de esta constitución.
5. Actualiza `MEMORY.md` si decidió o verificó algo que otro necesita.

## VIII. Código abierto

1. El proyecto se publica bajo **Apache-2.0** (cambio aprobado en persona por las cinco personas el 2026-11-15; antes, GPL-3.0-only). Toda dependencia debe tener una licencia compatible, y los créditos de los datos van en `NOTICE`.
2. Se atribuyen siempre las fuentes de datos: NASA/ISRO NISAR, NASA OPERA, Copernicus (Sentinel-2 y DEM) y el mapa base que se use.
3. Nunca se suben datos, tokens ni archivos `.env`.
4. Cualquier persona debe poder reproducir los resultados con los comandos documentados.

## IX. Personas usuarias

1. La interfaz funciona en español e inglés.
2. Cumple WCAG 2.1 AA: contraste suficiente, uso con teclado y estados que no dependen solo del color.
3. El lenguaje es llano: un término técnico solo aparece si se explica.

## X. Perfiles y acceso

1. Los perfiles (público general, estudiante e investigador) cambian la profundidad, las herramientas y las cuotas; nunca la verdad. El estado, `data_kind`, lo que el veredicto no prueba, lo que falta, la causa de lo no observable y el recibo con los gránulos son visibles para cualquier persona, con o sin cuenta.
2. Un permiso solo puede añadir rutas, filtros, exportaciones o explicaciones. Nunca oculta ni altera un campo de una respuesta.
3. El perfil lo declara la persona y no se verifica; ninguna pantalla lo presenta como verificado.
4. Las contraseñas, las claves de firma y los tokens siguen la regla VIII.3: nunca entran en el repositorio.
