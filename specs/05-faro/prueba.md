# Faro — prueba rápida con personas (T-FAR-20, antes T-FAR-10)

Cierra RF-FAR-09. Propuesta de Faro, 2026-11-14.

**Fuera del hackathon (decisión de Faro, 2026-11-14):** las sesiones no se hicieron antes de la demo. La prueba pasa a la ola 2 como T-FAR-20 y este protocolo sigue valiendo tal cual.

## Para qué

La misión de Faro es que cualquier persona entienda en menos de un minuto qué pasó, qué no sabemos y por qué confiar en la respuesta. Esta prueba comprueba eso con personas reales antes de la demo. **No mide si les gusta la app: mide si la entienden bien.** El fallo más grave es que alguien saque una conclusión que la API no sostiene, por ejemplo que "no observable" significa "no pasó nada" o que una hipótesis es la causa.

## Criterios de aceptación

- [ ] De 3 a 5 personas sin formación en radar ni en teledetección, que no sean del equipo. Al menos una tiene que ser ajena a la informática.
- [ ] Cada sesión sigue el protocolo de abajo, con las mismas tareas y en la pila local con la serie `real`.
- [ ] Los resultados se anotan en la tabla de "Resultados" con un código (P1 a P5) y un perfil general. Sin nombres, contactos, grabaciones ni capturas con datos de la persona.
- [ ] Cada problema se clasifica por gravedad (ver abajo) y se decide qué se ajusta.
- [ ] Se corrigen todos los problemas de gravedad alta que estén en los textos o la interfaz de Faro, y los de gravedad media que vieron dos personas o más.
- [ ] Lo que dependa de los textos del veredicto (Balanza) o del mapa (Atlas) se le pasa a su dueño como propuesta, con lo que dijo la persona. Faro no lo cambia.
- [ ] Ningún ajuste hace que un texto afirme más que la API (constitución II.4).

Fuera de esta prueba: medir con muchas personas, comparar versiones, la prueba con lector de pantalla y la versión en inglés.

## Protocolo (unos 10 minutos por persona)

Lo lleva una persona del equipo, que **no explica ni ayuda** salvo que la persona se atasque más de un minuto. Si ayuda, se anota.

### Antes

- [ ] Pila levantada con `docker compose up --build` y `http://localhost:3000` abierto y cargado (la primera carga puede tardar más de 40 s).
- [ ] Serie `real`, idioma español y la escena 1 seleccionada arriba del todo.
- [ ] Decirle a la persona: "Probamos la app, no a ti. No hay respuestas malas. Piensa en voz alta. No grabamos nada ni apuntamos tu nombre." Y preguntarle si está de acuerdo.
- [ ] Preguntar solo el perfil general (por ejemplo "estudiante de derecho", "docente", "trabaja en Protección Civil") y si ha usado imágenes de satélite alguna vez.

### Tareas

Se leen tal cual, una a una. Se cronometra la tarea 1.

| # | Qué se le pide | Se cumple si | Error que más importa |
|---|---|---|---|
| 1 | "El 1 de julio de 2026 hubo una tormenta fuerte en Parral. Con esta página, ¿el satélite la vio?" | Dice que no se pudo observar porque el satélite no pasó durante la tormenta, en menos de 1 minuto | Decir que no hubo cambio o que la tormenta no dejó huella |
| 2 | "¿Esto prueba que la tormenta no hizo daños?" | Dice que no | Decir que sí |
| 3 | "Ve a la segunda escena. ¿Qué pasó entre esas dos fechas de agosto?" | Dice el estado que muestra la pantalla y que es en una parte de la zona | Contar una posible explicación como la causa |
| 4 | "¿Sabemos qué lo causó?" | Dice que no, o que hay posibles explicaciones sin comprobar | Afirmar una causa |
| 5 | "Ve a la tercera escena. ¿Cambió algo en ese punto?" | Dice que el radar no detectó cambio en esos pares | Decir que está demostrado que no cambió nada |
| 6 | "Si quisieras comprobar de dónde sale esta respuesta, ¿dónde mirarías?" | Abre el recibo | No encontrarlo |

### Al final

- "¿Qué fue lo más confuso?"
- "¿Hubo alguna palabra que no entendieras?"
- "Explícale en una frase a un amigo qué hace esta página."

## Gravedad

| Gravedad | Cuándo | Qué se hace |
|---|---|---|
| Alta | La persona saca una conclusión que la API no sostiene (tareas 1, 2, 4 o 5) o no puede terminar una tarea | Se corrige siempre |
| Media | Tarda más de 1 minuto en la tarea 1, necesita ayuda o no entiende una palabra | Se corrige si les pasó a dos personas o más |
| Baja | Duda, comentario de aspecto o una preferencia | Se anota y no se toca antes de la demo |

## Resultados

| Código | Fecha | Perfil general | Ha usado imágenes de satélite | Tarea 1 (tiempo) | Tareas cumplidas | Problemas observados | Frase final |
|---|---|---|---|---|---|---|---|
| P1 | | | | | | | |
| P2 | | | | | | | |
| P3 | | | | | | | |
| P4 | | | | | | | |
| P5 | | | | | | | |

## Ajustes

| Problema | Personas | Gravedad | Dueño | Decisión | PR |
|---|---|---|---|---|---|
| | | | | | |
