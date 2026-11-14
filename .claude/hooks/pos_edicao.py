"""Hook PostToolUse: roda ruff e pytest depois de editar um arquivo .py.

Informa, não bloqueia — durante o loop de correção o vermelho é esperado.
Lê o JSON do hook no stdin (sem jq) e só age quando o arquivo tocado é .py.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

LIMITE_SEGUNDOS = 180


def _raiz_do_projeto() -> Path:
    bruto = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(bruto) if bruto else Path.cwd()


def _interpretador(raiz: Path) -> str:
    """Prefere o Python do venv do projeto; cai no que estiver rodando o hook."""
    for relativo in ("Scripts/python.exe", "bin/python"):
        candidato = raiz / ".venv" / relativo
        if candidato.is_file():
            return str(candidato)
    return sys.executable


def _rodar(comando: list[str], raiz: Path) -> tuple[int, str]:
    try:
        processo = subprocess.run(
            comando,
            cwd=str(raiz),
            capture_output=True,
            text=True,
            timeout=LIMITE_SEGUNDOS,
        )
    except FileNotFoundError:
        return 127, f"comando não encontrado: {comando[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"tempo esgotado após {LIMITE_SEGUNDOS}s"
    saida = (processo.stdout or "") + (processo.stderr or "")
    return processo.returncode, saida.strip()


def _ultimas_linhas(texto: str, quantas: int = 25) -> str:
    linhas = [linha for linha in texto.splitlines() if linha.strip()]
    return "\n".join(linhas[-quantas:])


def _forcar_utf8() -> None:
    """No Windows o padrão é cp1252 e os acentos chegariam corrompidos."""
    for fluxo in (sys.stdin, sys.stdout):
        reconfigurar = getattr(fluxo, "reconfigure", None)
        if reconfigurar is not None:
            reconfigurar(encoding="utf-8", errors="replace")


def main() -> int:
    _forcar_utf8()
    try:
        evento = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    entrada = evento.get("tool_input") or {}
    caminho = entrada.get("file_path") or entrada.get("notebook_path") or ""
    if not str(caminho).endswith(".py"):
        return 0

    raiz = _raiz_do_projeto()
    python = _interpretador(raiz)

    partes: list[str] = []
    for rotulo, comando in (
        ("ruff check", [python, "-m", "ruff", "check", "."]),
        ("pytest -q", [python, "-m", "pytest", "-q"]),
    ):
        codigo, saida = _rodar(comando, raiz)
        marca = "ok" if codigo == 0 else f"falhou (codigo {codigo})"
        partes.append(f"[{rotulo}] {marca}")
        if codigo != 0 and saida:
            partes.append(_ultimas_linhas(saida))

    relatorio = "\n".join(partes)
    print(
        json.dumps(
            {
                "systemMessage": f"Verificação pós-edição:\n{relatorio}",
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        "Verificação automática após editar um .py "
                        "(informativa; vermelho é esperado durante o loop de correção):\n"
                        f"{relatorio}"
                    ),
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
