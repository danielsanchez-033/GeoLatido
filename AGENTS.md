# Instrucciones para agentes y colaboradores

Antes de trabajar, lee en este orden:

1. [specs/constitution.md](specs/constitution.md): principios no negociables.
2. La especificación del rol que vas a tocar, en [specs/](specs/README.md).
3. [MEMORY.md](MEMORY.md): decisiones, hechos verificados y lo que sigue abierto.

## Qué construimos

Una aplicación abierta (Apache-2.0) para el reto NASA/ISRO NISAR. Convierte datos radar GCOV en **veredictos auditables** por zona y par de fechas, con tres estados: `change_probable`, `no_detectable_change` y `not_observable` con su causa. El centro del producto es decir también lo que no se sabe.

## Roles y carpetas

| Rol | Persona | Carpetas | Especificación |
|---|---|---|---|
| Antena: ingesta y tiempo | @KinzzoCS | `services/catalog`, `services/ingest`, `services/auth`, `config/aois` | [01-antena](specs/01-antena/spec.md) |
| Eco: señal y georreferencia | @TakoKami-dev | `services/processor` | [02-eco](specs/02-eco/spec.md) |
| Balanza: interpretación y veracidad | @lospapulindos2-netizen | `services/verdicts`, `gateway`, `docker-compose.yml`, `scripts` | [03-balanza](specs/03-balanza/spec.md) |
| Atlas: mapa y representación web | @Fransomware | Módulo de mapa en `frontend/` | [04-atlas](specs/04-atlas/spec.md) |
| Faro: relato y experiencia | @danielsanchez-033 | Resto de `frontend/` | [05-faro](specs/05-faro/spec.md) |

## Reglas de trabajo para agentes

- Trabaja solo dentro de las carpetas del rol que te pidieron. Para tocar otra, pide la aprobación de su dueño.
- Si el cambio altera lo que el sistema promete, actualiza primero la especificación del rol.
- Cita la tarea (`T-XXX-NN`) en el commit y en el PR, y márcala en `tasks.md` al terminarla.
- Los servicios no importan código entre sí. Se comunican por HTTP o por los contratos de `contracts/`.
- Nunca presentes datos sintéticos como reales ni escribas una afirmación que la API no sostenga.
- No modifiques `frontend/` salvo que el equipo de frontend lo pida.

## Contratos

| Contrato | Dueño | Regenerar o validar |
|---|---|---|
| `contracts/catalog.openapi.json` | Antena | `python -m catalog.export_openapi contracts/catalog.openapi.json` |
| `contracts/gcov-subset.md` | Antena con Eco | Pruebas de `ingest` |
| `contracts/artifact-manifest.schema.json` | Eco con Balanza | Pruebas de `processor` y `verdicts` |
| `contracts/verdicts.openapi.json` | Balanza | `python -m verdicts.export_openapi contracts/verdicts.openapi.json` |
| `contracts/auth.openapi.json` (ola 2, aún no existe) | Antena | `python -m auth.export_openapi contracts/auth.openapi.json` |

Las pruebas fallan si el contrato publicado no coincide con el código. Los contratos **no se congelan**: el proyecto sigue creciendo el 14 y el 15 de noviembre, incluso con cambios radicales, y cualquier cambio de contrato sigue el proceso de la constitución (VI.2).

## Comandos

Cada servicio se prueba por separado desde su carpeta:

```bash
pip install -e ".[dev]"
pytest -q
```

Toda la pila con datos sintéticos, en `http://localhost:8080`:

```bash
docker compose up --build
```

Prueba de humo con la pila levantada:

```bash
bash scripts/smoke.sh
```

## Git

- Ramas `<ámbito>/<tema>` y commits `tipo(ámbito): resumen` en español. Detalle en [CONTRIBUTING.md](CONTRIBUTING.md).
- Validación local: `git config core.hooksPath .githooks`.
- Todo entra a `main` por PR con fusión squash y CI en verde. Lo que está listo (aprobado y con la CI en verde) se fusiona sin esperar a la demo.
- Nunca se suben datos, tokens ni archivos `.env`.

## Orden "verifica y haz commit"

Cuando la persona escriba **"verifica y haz commit"**, sigue estos pasos sin hacer nada más. Su rol es el de la tabla de "Roles y carpetas" que corresponde a su cuenta de git o de `gh`. Fuera de esta orden, no hagas commit sin que te lo pida.

### 1. Clasificar los cambios pendientes

Revisa `git status` y el diff, y decide el dueño de cada archivo con `.github/CODEOWNERS`. Cada cambio cae en uno de estos grupos:

| Grupo | Qué incluye | Qué hacer |
|---|---|---|
| **A. Se envía ya** | Carpetas y especificación del propio rol, `MEMORY.md`, y cambios **aditivos** de un contrato propio (la aprobación llega en la revisión del PR) | Verificar, commit, push y PR |
| **B. Primero confirmación** | Carpetas o especificación de otro rol; `specs/constitution.md`, `specs/00-sistema/` o `AGENTS.md` (aprueban las cinco personas); cambios de contrato que renombran, quitan o cambian algo | No hacer commit. Redactar el mensaje y esperar |
| **Nunca** | `.env`, tokens, datos (`data/`), o un token copiado en un archivo versionado como `.env.example` | Detenerse y avisar. No restaurar ni borrar nada sin permiso |

### 2. Verificar el grupo A antes de enviarlo

- Pruebas de cada servicio tocado (`pytest -q` en su carpeta) y contratos regenerados si cambió una API.
- El diff no contiene tokens, `.env` ni datos.
- Rama `<ámbito>/<tema>`, mensaje con el formato de `CONTRIBUTING.md` (lo valida `.githooks/commit-msg`) y `Refs: T-XXX-NN`.
- PR con la plantilla. Mientras el repositorio sea privado, `CODEOWNERS` no asigna revisores: añádelos a mano con `gh pr edit --add-reviewer`.
- Si algo falla, no se envía. Pasa a la lista de pendientes y se explica.

### 3. Responder siempre con este formato

1. **Enviado:** cada PR con su enlace y lo que contiene.
2. **Mensajes para enviar:** uno por compañero afectado, en un bloque listo para copiar. Cada mensaje dice qué cambió, qué debe hacer paso a paso (revisar, aprobar o cambiar algo), cómo probarlo y la fecha límite si la hay.
3. **Esperando confirmación (grupo B):** cada cambio retenido, de quién es y el mensaje que pide su aprobación. Ahí te detienes hasta que la persona repita "verifica y haz commit" después de conseguirla.

## Actualizar la memoria

Cuando se tome una decisión o se verifique algo que otro necesite, actualiza `MEMORY.md` en la misma rama. Escribe la fecha absoluta y cómo se comprobó. Si algo ya no es cierto, corrígelo en lugar de añadir otra línea.
