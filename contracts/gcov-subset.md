# Contrato: recorte GCOV

Frontera entre `ingest` (Antena, escribe) y `processor` (Eco, lee). Un recorte es un HDF5 con la misma estructura que un gránulo GCOV, limitado a la ventana de la zona.

## Ubicación

`data/raw/real/<aoi>/<serie>/<granuleId>.h5`. Un archivo `.part` es una escritura sin terminar y nadie debe leerlo.

## Contenido

| Ruta | Origen |
|---|---|
| `/science/LSAR/identification/*` | Copia íntegra del gránulo, sin cambiar tipos |
| `/science/LSAR/GCOV/grids/frequencyA/HHHH`, `HVHV` | Ventana de la zona, Float32, potencia gamma-0 |
| `.../mask` | Ventana; 0 inválido, 1-5 subfranja válida, 255 fuera de escena |
| `.../numberOfLooks` | Ventana |
| `.../inputDataExceptionMask` | Ventana, solo si existe en el original |
| `.../xCoordinates`, `.../yCoordinates` | Coordenadas de la ventana, con la orientación original |
| `.../projection` | Copia con su atributo `epsg_code` |
| `/science/LSAR/GCOV/metadata/radarGrid/*` | **Opcional.** Cubos de geometría del radar con forma `(altura, y, x)` sobre nodos cada 500 m (`incidenceAngle`, `losUnitVectorX`, `losUnitVectorY` y los demás que traiga el grupo), con sus `xCoordinates`, `yCoordinates` (descendente, como en el original) y `heightAboveEllipsoid`. Los cubos y las coordenadas se recortan en x e y a los nodos que rodean la ventana más 2 nodos de margen por lado, con todas las alturas. `heightAboveEllipsoid`, `projection` (con su atributo `epsg_code`) y cualquier otro dato que no dependa de x e y se copian enteros. Sin cambiar tipos, valores ni atributos |

Atributos en la raíz: `subset_of` (granuleId original) y `subset_bbox` (oeste, sur, este, norte en grados). Los archivos reales no llevan `data_kind`; los sintéticos llevan `data_kind = "synthetic"`.

## Garantías

- Solo se recortan gránulos cuya pista, dirección y marco coinciden con la serie configurada.
- Nunca se modifica ningún valor: no se filtra, no se convierte a dB y no se reproyecta.
- Las capas obligatorias son `HHHH`, `HVHV`, `mask` y `numberOfLooks`; si falta alguna, el recorte falla.
- `radarGrid` es opcional: si el gránulo no lo trae, el recorte no falla. `processor` lo usa para marcar layover y sombra (T-ECO-05); sin él, no marca relieve y lo avisa en el manifiesto.
