"""
Ponto de entrada para `streamlit run app.py`.

Importar `src.app` só corre o módulo na primeira vez; nos reruns do Streamlit
o ficheiro raiz volta a executar mas o import fica em cache — `main()` deixa
de ser chamado e a página fica em branco. Por isso usamos `runpy.run_path`
para executar `src/app.py` completo em cada rerun.
"""

import sys
from pathlib import Path

import runpy

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

runpy.run_path(str(_ROOT / "src" / "app.py"), run_name="__main__")
