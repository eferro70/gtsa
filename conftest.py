"""Garante que o pacote ``gtsa`` (layout src/) seja importável nos testes
mesmo sem instalação editável."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
