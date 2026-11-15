"""Escribe el contrato OpenAPI del servicio: python -m research.export_openapi contracts/research.openapi.json"""
import json
import sys
from pathlib import Path

from .main import create_app
from .pipeline import Deps
from .store import Store


def main(path: str) -> None:
    app = create_app(Store(":memory:"), Deps(cmr=None, verdicts=None, eonet=None))
    Path(path).write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
