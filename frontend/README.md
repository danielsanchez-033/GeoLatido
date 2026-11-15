# Frontend

Esta carpeta es del equipo de frontend: framework, estructura y diseño son decisión vuestra. Backend no la toca.

## Arrancar

Vite + React + TypeScript, que genera un sitio estático. Necesita Node 20 o superior y la pila de `docker compose` levantada en `http://localhost:8080`.

```bash
npm install
npm run dev        # http://localhost:5173
npm test           # pruebas (Vitest)
npm run build      # sitio estático en dist/
```

Sin instalar Node: `docker compose up --build` en la raíz levanta también el sitio compilado en `http://localhost:3000` (servicio `frontend`, nginx). Para desarrollar con recarga en caliente, sigue usando `npm run dev`.

Otro origen para la API: copia `.env.example` a `.env.local` y cambia `VITE_API_BASE`.

| Carpeta | Dueño | Qué hay |
|---|---|---|
| `src/mapa/` | Atlas | El mapa. Expone la interfaz de `src/types/map.ts` (`specs/04-atlas/plan.md`) |
| `src/api/` | Faro | Cliente tipado. `verdicts.d.ts` se genera con `npm run gen:types`; una prueba falla si no coincide con el contrato |
| `src/i18n/` | Faro | Textos de interfaz en `es.json` y `en.json`, con las mismas claves (lo comprueba una prueba) |
| `src/components/` | Faro | Tarjeta, consulta de evento, etc. `MapSlot` ocupa el sitio del mapa hasta T-FAR-05 |
| `content/` | Faro | Glosario y explicación del radar |

## Qué tenéis disponible

Con `docker compose up --build` en la raíz, todo se consume desde `http://localhost:8080`, con CORS abierto para desarrollo. Los datos son sintéticos hasta que llegue la serie real, y la forma de las respuestas no cambia.

Documentación interactiva en `/api/verdicts/docs` y `/api/catalog/docs`. Los contratos están en [`../contracts`](../contracts), útiles para generar tipos.

| Necesito | Llamada |
|---|---|
| Zonas con resultados | `GET /api/verdicts/aois` |
| Series y fechas | `GET /api/verdicts/aois/parral/series` |
| Veredictos de una serie | `GET /api/verdicts/aois/parral/series/T048A-F015/verdicts?lang=es` |
| Un veredicto | `GET /api/verdicts/aois/parral/series/T048A-F015/verdicts/20260617_20261015` |
| ¿Se pudo ver un evento? | `GET /api/verdicts/aois/parral/events?date=2026-07-01&persistence_hours=24` |
| Historia de un punto | `GET /api/verdicts/aois/parral/series/T048A-F015/pixel?lon=-105.67&lat=26.93` |

Cada veredicto trae `layers.state`, `layers.change_hh` y `layers.change_hv`: plantillas de tesela `{z}/{x}/{y}` listas para el mapa, añadiendo `http://localhost:8080` delante. La capa `state` lleva una paleta inicial que podéis cambiar con su parámetro `colormap`. Los códigos son 0 sin cambio, 1 cambio probable y 10-15 no observable.

## Lo que la interfaz debe respetar

- Mostrar siempre si el dato es sintético (`receipt.data_kind` o `data_kind`).
- Mostrar `not_observable` como un resultado propio, nunca como "sin cambio".
- Enseñar juntos `summary.detected`, `summary.does_not_prove` y `summary.missing`.
- Presentar `hypotheses` como hipótesis.
- Dejar ver el recibo con los gránulos usados.

Si os falta un dato en la API, abrid un issue o avisad a Back 3 antes de improvisar otra fuente.
