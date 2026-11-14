"""Oráculo da Fase 2: confere o relatório contra a amostra de validação do README.

A fonte da verdade é o próprio `README.md`, lido entre os marcadores
`<!-- AMOSTRA:INICIO -->` e `<!-- AMOSTRA:FIM -->`. Nada é transcrito à mão aqui:
se a amostra do README mudar, a checagem acompanha sozinha.

Uso:

    python tools/conferir_amostra.py output/exemplo.json

Saída: `SEM DIVERGENCIAS` e código 0, ou a lista de divergências e código 1.
`generated_at` é ignorado, conforme R16.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
README = RAIZ / "README.md"

MARCADOR_INICIO = "<!-- AMOSTRA:INICIO -->"
MARCADOR_FIM = "<!-- AMOSTRA:FIM -->"

# O README escapa underscores e acentos em markdown; desfazemos para comparar.
_ESCAPES = re.compile(r"\\([\\_*`\[\]])")


def _limpar(celula: str) -> str:
    """Remove crases, escapes de markdown e espaços de uma célula da tabela."""
    texto = celula.strip().strip("|").strip()
    texto = _ESCAPES.sub(r"\1", texto)
    return texto.replace("`", "").strip()


def _linhas_de_tabela(bloco: str) -> list[list[str]]:
    """Extrai as linhas de dados de todas as tabelas markdown do bloco."""
    linhas: list[list[str]] = []
    for linha in bloco.splitlines():
        crua = linha.strip()
        if not crua.startswith("|"):
            continue
        celulas = [_limpar(c) for c in crua.strip("|").split("|")]
        if all(set(c) <= {"-", ":"} and c for c in celulas):
            continue  # separador de cabeçalho
        linhas.append(celulas)
    return linhas


def ler_amostra_do_readme(caminho: Path = README) -> dict:
    """Devolve o esperado da amostra: summary, by_month e top_hotels."""
    texto = caminho.read_text(encoding="utf-8")
    try:
        bloco = texto.split(MARCADOR_INICIO, 1)[1].split(MARCADOR_FIM, 1)[0]
    except IndexError as err:
        raise SystemExit(f"marcadores da amostra não encontrados em {caminho}") from err

    linhas = _linhas_de_tabela(bloco)

    summary: dict[str, str] = {}
    by_month: list[dict[str, str]] = []
    top_hotels: list[dict[str, str]] = []

    for celulas in linhas:
        if celulas[:2] == ["Campo", "Valor esperado"]:
            continue
        if celulas[:2] == ["month", "reservations"] or celulas[:2] == ["hotel_id", "hotel_name"]:
            continue
        if len(celulas) == 2:
            summary[celulas[0]] = celulas[1]
        elif len(celulas) == 4 and re.fullmatch(r"\d{4}-\d{2}", celulas[0]):
            by_month.append(
                {
                    "month": celulas[0],
                    "reservations": celulas[1],
                    "room_nights": celulas[2],
                    "total_brl": celulas[3],
                }
            )
        elif len(celulas) == 4:
            top_hotels.append(
                {
                    "hotel_id": celulas[0],
                    "hotel_name": celulas[1],
                    "room_nights": celulas[2],
                    "total_brl": celulas[3],
                }
            )

    if not summary or not by_month or not top_hotels:
        raise SystemExit("amostra do README incompleta: não consegui ler as três tabelas")
    return {"summary": summary, "by_month": by_month, "top_hotels": top_hotels}


CAMPOS_INTEIROS = {
    "total_reservations",
    "confirmed_reservations",
    "cancelled_reservations",
    "no_show_reservations",
    "total_room_nights",
    "reservations",
    "room_nights",
}


def _normalizar(campo: str, valor) -> str:
    """Dinheiro compara como string de 2 casas; contagem compara como inteiro."""
    if campo in CAMPOS_INTEIROS:
        return str(valor).strip()
    return str(valor).strip()


def comparar(esperado: dict, obtido: dict) -> list[str]:
    """Devolve a lista de divergências, uma string por campo."""
    divergencias: list[str] = []

    resumo_obtido = obtido.get("summary") or {}
    for campo, valor_esperado in esperado["summary"].items():
        if campo not in resumo_obtido:
            divergencias.append(f"summary.{campo}: esperado {valor_esperado}, obtido <ausente>")
            continue
        valor_obtido = _normalizar(campo, resumo_obtido[campo])
        if valor_obtido != valor_esperado:
            divergencias.append(f"summary.{campo}: esperado {valor_esperado}, obtido {valor_obtido}")

    for nome, chaves in (
        ("by_month", ("month", "reservations", "room_nights", "total_brl")),
        ("top_hotels", ("hotel_id", "hotel_name", "room_nights", "total_brl")),
    ):
        lista_esperada = esperado[nome]
        lista_obtida = obtido.get(nome) or []
        if len(lista_obtida) != len(lista_esperada):
            divergencias.append(
                f"{nome}: esperado {len(lista_esperada)} itens, obtido {len(lista_obtida)}"
            )
        for indice, item_esperado in enumerate(lista_esperada):
            if indice >= len(lista_obtida):
                divergencias.append(f"{nome}[{indice}]: esperado {item_esperado}, obtido <ausente>")
                continue
            item_obtido = lista_obtida[indice]
            for chave in chaves:
                valor_esperado = item_esperado[chave]
                valor_obtido = _normalizar(chave, item_obtido.get(chave, "<ausente>"))
                if valor_obtido != valor_esperado:
                    divergencias.append(
                        f"{nome}[{indice}].{chave}: esperado {valor_esperado}, obtido {valor_obtido}"
                    )

    return divergencias


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Confere um relatório contra a amostra do README.")
    parser.add_argument("relatorio", help="caminho do JSON gerado pelo CLI")
    parser.add_argument("--readme", default=str(README), help="caminho do README.md")
    args = parser.parse_args(argv)

    esperado = ler_amostra_do_readme(Path(args.readme))
    obtido = json.loads(Path(args.relatorio).read_text(encoding="utf-8"))

    divergencias = comparar(esperado, obtido)

    total_campos = (
        len(esperado["summary"]) + len(esperado["by_month"]) * 4 + len(esperado["top_hotels"]) * 4
    )
    if divergencias:
        print(f"DIVERGENCIAS: {len(divergencias)} (de {total_campos} campos conferidos)")
        for item in divergencias:
            print(f"  {item}")
        return 1

    print(f"SEM DIVERGENCIAS ({total_campos} campos conferidos, generated_at ignorado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
