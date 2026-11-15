"""Órdenes del servicio: `python -m auth seed-accounts [--env-file RUTA]` (T-ANT-15)."""
from __future__ import annotations

import sys

from . import seed


def main(argv: list[str]) -> int:
    if argv[:1] == ["seed-accounts"]:
        return seed.main(argv[1:])
    print("Uso: python -m auth seed-accounts [--env-file RUTA]")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
