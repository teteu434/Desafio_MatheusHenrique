"""Testes novos: tratamento de moeda (decisões A04 e O11).

Não são testes de defeito: cobrem mudanças de comportamento deliberadas,
decididas em `docs/SPEC.md`. O dataset fornecido só traz `BRL`, `USD` e `EUR`
maiúsculos, então nada aqui altera os números entregues.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

from helpers import BASE, COLUMNS, SRC_DIR

TAXAS = "currency,rate_to_brl\nBRL,1.000000\nUSD,5.420000\nEUR,5.880000\n"


def _executar_com_moeda(
    tmp_path: Path, moeda: str, status: str = "CONFIRMED"
) -> tuple[subprocess.CompletedProcess[str], Path]:
    """Roda o CLI sobre uma única reserva com a moeda informada."""
    reservas = tmp_path / "reservas.csv"
    with reservas.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUMNS, lineterminator="\n")
        escritor.writeheader()
        escritor.writerow({**BASE, "reservation_id": "M-01", "currency": moeda, "status": status})

    taxas = tmp_path / "rates.csv"
    taxas.write_text(TAXAS, encoding="utf-8")
    saida = tmp_path / "relatorio.json"

    ambiente = os.environ.copy()
    ambiente["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + ambiente.get("PYTHONPATH", "")
    ambiente["PYTHONDONTWRITEBYTECODE"] = "1"

    processo = subprocess.run(
        [
            sys.executable, "-m", "onfly_report",
            "--input", str(reservas),
            "--rates", str(taxas),
            "--output", str(saida),
        ],
        cwd=str(tmp_path), env=ambiente, capture_output=True, text=True, timeout=60,
    )
    return processo, saida


# --- A04: moeda sem taxa é erro de entrada -------------------------------------


def test_moeda_sem_taxa_sai_com_exit_2(tmp_path: Path) -> None:
    """A04 e R22: moeda ausente da tabela é entrada inválida, não erro inesperado.

    Antes desta decisão o `KeyError` escapava para o `except Exception` do CLI e
    saía com 1, enquanto data, `rooms` e `amount` malformados já saíam com 2.
    """
    processo, saida = _executar_com_moeda(tmp_path, "GBP")

    assert processo.returncode == 2
    assert not saida.exists()
    assert "Traceback" not in processo.stderr
    assert "GBP" in processo.stderr


def test_mensagem_de_moeda_sem_taxa_cita_a_linha(tmp_path: Path) -> None:
    """A04: o diagnóstico nomeia a linha do CSV, como já faz o RowParser."""
    processo, _ = _executar_com_moeda(tmp_path, "GBP")

    assert "linha 2" in processo.stderr


def test_moeda_vazia_sai_com_exit_2(tmp_path: Path) -> None:
    """A04: moeda em branco também é entrada inválida."""
    processo, _ = _executar_com_moeda(tmp_path, "")

    assert processo.returncode == 2
    assert "Traceback" not in processo.stderr


def test_moeda_sem_taxa_em_reserva_nao_faturavel_nao_interrompe(tmp_path: Path) -> None:
    """A04 com R02: linha não faturável nunca é convertida, então não há taxa a buscar.

    Decisão de escopo: a validação acontece na conversão, que só alcança as
    reservas `CONFIRMED`. Uma reserva `CANCELLED` com moeda exótica não afeta
    nenhum total e não derruba o relatório.
    """
    processo, saida = _executar_com_moeda(tmp_path, "GBP", status="CANCELLED")

    assert processo.returncode == 0, processo.stderr
    relatorio = json.loads(saida.read_text(encoding="utf-8"))
    assert relatorio["summary"]["total_reservations"] == 1
    assert relatorio["summary"]["cancelled_reservations"] == 1
    assert relatorio["summary"]["total_amount_brl"] == "0.00"


# --- O11: normalização simétrica de currency -----------------------------------


def test_moeda_minuscula_e_aceita(tmp_path: Path) -> None:
    """O11: `CsvRateRepository` indexa com `.strip().upper()`; o parser precisa casar.

    100.00 `usd` x 5.42 = 542.00.
    """
    processo, saida = _executar_com_moeda(tmp_path, "usd")

    assert processo.returncode == 0, processo.stderr
    relatorio = json.loads(saida.read_text(encoding="utf-8"))
    assert relatorio["summary"]["total_amount_brl"] == "542.00"


def test_moeda_com_espacos_continua_aceita(tmp_path: Path) -> None:
    """O11: o `.strip()` já funcionava antes da mudança; guarda contra regressão."""
    processo, saida = _executar_com_moeda(tmp_path, "  USD  ")

    assert processo.returncode == 0, processo.stderr
    relatorio = json.loads(saida.read_text(encoding="utf-8"))
    assert relatorio["summary"]["total_amount_brl"] == "542.00"


def test_moeda_com_caixa_mista_e_espacos(tmp_path: Path) -> None:
    """O11: caixa e espaço normalizados juntos."""
    processo, saida = _executar_com_moeda(tmp_path, " Usd ")

    assert processo.returncode == 0, processo.stderr
    relatorio = json.loads(saida.read_text(encoding="utf-8"))
    assert relatorio["summary"]["total_amount_brl"] == "542.00"
