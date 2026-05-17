"""
Ponto de entrada para `streamlit run app.py` (Streamlit Cloud — branch main).

Importar `src.app` só corre o módulo na primeira vez; nos reruns o import fica em cache
e `main()` deixa de correr (página em branco). Por isso fazemos `reload` a cada execução.

`runpy.run_path` não é usado: no Cloud ele prepende `src/` ao sys.path e quebra
`from src.database...` (ImportError / ModuleNotFoundError).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_ROOT_STR = str(_ROOT)
_SRC_STR = str(_ROOT / "src")

if _ROOT_STR not in sys.path:
    sys.path.insert(0, _ROOT_STR)

# `runpy` e alguns runners colocam `.../src` na path — impede o pacote `src.*`.
while _SRC_STR in sys.path:
    sys.path.remove(_SRC_STR)

import src.app as _beaba_app

importlib.reload(_beaba_app)
