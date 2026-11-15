"""Escribe el contrato OpenAPI de este servicio: python -m auth.export_openapi RUTA."""
import json
import sys
import tempfile
from pathlib import Path

from .main import create_app


def main() -> None:
    # Un directorio temporal: exportar el contrato no debe crear claves ni bases de datos de verdad.
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(data_dir=Path(tmp))
        try:
            Path(sys.argv[1]).write_text(
                json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        finally:
            app.state.store.close()  # En Windows, la base abierta impide borrar el directorio temporal.


if __name__ == "__main__":
    main()
