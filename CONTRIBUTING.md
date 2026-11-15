# Cómo contribuir

Somos cinco personas trabajando a la vez. Estas reglas existen para que nadie rompa el trabajo de otro.

## Antes de empezar

1. Lee [`specs/constitution.md`](specs/constitution.md) y la especificación de tu rol en [`specs/`](specs/README.md).
2. Lee [`MEMORY.md`](MEMORY.md): decisiones, hechos verificados y lo que sigue abierto.
3. Activa la validación local de commits, una sola vez por clon:

```bash
git config core.hooksPath .githooks
```

## Roles y carpetas

| Rol | Persona | Carpetas |
|---|---|---|
| Antena | @KinzzoCS | `services/catalog`, `services/ingest`, `config/aois` |
| Eco | @TakoKami-dev | `services/processor` |
| Balanza | @lospapulindos2-netizen | `services/verdicts`, `gateway`, `docker-compose.yml`, `scripts` |
| Atlas | @Fransomware | Módulo de mapa en `frontend/` |
| Faro | @danielsanchez-033 | Resto de `frontend/` |

`.github/CODEOWNERS` pide automáticamente la revisión del dueño cuando un PR toca sus carpetas.

## Ramas

`<ámbito>/<tema-en-minusculas>`, por ejemplo `eco/control-calidad` o `faro/tarjeta-veredicto`.

## Commits

Formato [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/) con el resumen en español:

```
<tipo>(<ámbito>)[!]: <resumen en minúsculas, sin punto final, máx. 72 caracteres>

<cuerpo opcional: por qué, no qué>

Refs: T-ECO-03
```

| Tipo | Uso |
|---|---|
| `feat` | Funcionalidad nueva |
| `fix` | Corrección de un error |
| `spec` | Cambio en `specs/` |
| `docs` | Otra documentación |
| `test` | Solo pruebas |
| `refactor` | Cambio interno sin cambiar el comportamiento |
| `perf` | Rendimiento |
| `build` | Dependencias, Docker y empaquetado |
| `ci` | GitHub Actions |
| `chore` | Mantenimiento |
| `revert` | Deshacer un commit |

Ámbitos: `antena`, `eco`, `balanza`, `atlas`, `faro`, `contratos` y `repo`. `!` marca un cambio que rompe un contrato, y el cuerpo lo explica con `BREAKING CHANGE:`.

Ejemplos:

```
feat(eco): añade control de calidad por fecha al manifiesto
fix(antena): reintenta lecturas cortadas por la red
spec(faro): define las tres escenas del modo historia
feat(contratos)!: renombra interval a interval_days
```

## Pull requests

- Todo entra a `main` por PR, con fusión tipo squash. **El título del PR es el commit final**, así que sigue el mismo formato.
- La CI valida el título del PR, el nombre de la rama, las pruebas de cada servicio y la prueba de humo.
- Rellena la plantilla y cita las tareas (`T-XXX-NN`).
- Si cambias un contrato, avisa a quien lo consume y pide su revisión.

## Definición de terminado

Ver la sección VII de la constitución. En resumen: cumple la especificación, tiene pruebas, la CI está en verde, respeta la veracidad y actualiza `MEMORY.md` si hace falta.

## Licencia

Al contribuir aceptas que tu aportación se publica bajo la [licencia Apache 2.0](LICENSE). No añadas dependencias con licencias incompatibles (por ejemplo GPL) ni datos sin su atribución, y añade al archivo [NOTICE](NOTICE) toda fuente de datos nueva.
