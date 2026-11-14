"""Testes novos: contrato do CLI (R19 a R24).

`helpers.run_cli` afirma `returncode == 0`, então não serve para checar códigos
de saída de erro. Este módulo traz um executor próprio que devolve o processo
inteiro, sem tocar nos arquivos fornecidos.
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


def _preparar_entradas(tmp_path: Path) -> tuple[Path, Path]:
    """Grava um CSV de reservas mínimo e a tabela de câmbio; devolve os caminhos."""
    caminho_reservas = tmp_path / "reservas.csv"
    with caminho_reservas.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUMNS, lineterminator="\n")
        escritor.writeheader()
        escritor.writerow({**BASE, "reservation_id": "R-1"})

    caminho_taxas = tmp_path / "rates.csv"
    caminho_taxas.write_text(TAXAS, encoding="utf-8")
    return caminho_reservas, caminho_taxas


def _executar(tmp_path: Path, *argumentos: str) -> subprocess.CompletedProcess[str]:
    """Roda o CLI com `cwd` no diretório temporário e devolve o processo.

    O `cwd` temporário é proposital: assim o padrão de `--output` resolve para
    dentro do `tmp_path` e o teste não escreve nada no repositório.
    """
    ambiente = os.environ.copy()
    ambiente["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + ambiente.get("PYTHONPATH", "")
    ambiente["PYTHONDONTWRITEBYTECODE"] = "1"

    return subprocess.run(
        [sys.executable, "-m", "onfly_report", *argumentos],
        cwd=str(tmp_path),
        env=ambiente,
        capture_output=True,
        text=True,
        timeout=60,
    )


# --- R22: sucesso --------------------------------------------------------------


def test_sucesso_retorna_zero(tmp_path: Path) -> None:
    """R22: 0 em caso de sucesso."""
    reservas, taxas = _preparar_entradas(tmp_path)
    saida = tmp_path / "relatorio.json"

    processo = _executar(tmp_path, "--input", str(reservas), "--rates", str(taxas), "--output", str(saida))

    assert processo.returncode == 0, processo.stderr
    assert saida.is_file()


# --- R20 e R23: saída ----------------------------------------------------------


def test_output_tem_padrao_output_report_json(tmp_path: Path) -> None:
    """R20: sem `--output`, o relatório vai para `output/report.json`."""
    reservas, taxas = _preparar_entradas(tmp_path)

    processo = _executar(tmp_path, "--input", str(reservas), "--rates", str(taxas))

    assert processo.returncode == 0, processo.stderr
    assert (tmp_path / "output" / "report.json").is_file()


def test_cli_cria_o_diretorio_de_saida(tmp_path: Path) -> None:
    """R23: o CLI cria o diretório do relatório, em qualquer profundidade."""
    reservas, taxas = _preparar_entradas(tmp_path)
    saida = tmp_path / "um" / "dois" / "tres" / "relatorio.json"
    assert not saida.parent.exists()

    processo = _executar(tmp_path, "--input", str(reservas), "--rates", str(taxas), "--output", str(saida))

    assert processo.returncode == 0, processo.stderr
    assert saida.is_file()
    assert json.loads(saida.read_text(encoding="utf-8"))["report_version"] == "1.0"


# --- R24: resumo no stdout -----------------------------------------------------


def test_resumo_vai_para_stdout(tmp_path: Path) -> None:
    """R24: o resumo é impresso no stdout; o stdout não carrega o JSON nem o log."""
    reservas, taxas = _preparar_entradas(tmp_path)
    saida = tmp_path / "relatorio.json"

    processo = _executar(tmp_path, "--input", str(reservas), "--rates", str(taxas), "--output", str(saida))

    assert processo.returncode == 0, processo.stderr
    assert "Reservas:" in processo.stdout
    assert "Total BRL:" in processo.stdout
    assert "report_version" not in processo.stdout


# --- R19: argumentos obrigatórios ----------------------------------------------


def test_input_e_rates_sao_obrigatorios(tmp_path: Path) -> None:
    """R19 e R22: faltando argumento obrigatório, o CLI recusa com 2."""
    reservas, taxas = _preparar_entradas(tmp_path)

    sem_input = _executar(tmp_path, "--rates", str(taxas))
    sem_rates = _executar(tmp_path, "--input", str(reservas))

    assert sem_input.returncode == 2
    assert sem_rates.returncode == 2


# --- R21 e R22: validação de --top ---------------------------------------------


def test_top_zero_e_recusado_com_exit_2(tmp_path: Path) -> None:
    """R21: `--top` é inteiro >= 1; R22: argumento inválido sai com 2."""
    reservas, taxas = _preparar_entradas(tmp_path)

    processo = _executar(
        tmp_path, "--input", str(reservas), "--rates", str(taxas), "--top", "0"
    )

    assert processo.returncode == 2
    assert processo.stdout == ""
    assert processo.stderr != ""


def test_top_negativo_e_recusado_com_exit_2(tmp_path: Path) -> None:
    """R21: `--top` menor que 1 é inválido, inclusive negativo."""
    reservas, taxas = _preparar_entradas(tmp_path)

    processo = _executar(
        tmp_path, "--input", str(reservas), "--rates", str(taxas), "--top", "-1"
    )

    assert processo.returncode == 2


def test_top_nao_inteiro_e_recusado_com_exit_2(tmp_path: Path) -> None:
    """R21: `--top` precisa ser inteiro; texto é argumento inválido."""
    reservas, taxas = _preparar_entradas(tmp_path)

    processo = _executar(
        tmp_path, "--input", str(reservas), "--rates", str(taxas), "--top", "abc"
    )

    assert processo.returncode == 2
    assert processo.stderr != ""


# --- R22: entrada inválida -----------------------------------------------------


def test_input_inexistente_retorna_exit_2(tmp_path: Path) -> None:
    """R22: 2 para entrada inválida — arquivo de reservas ausente."""
    _, taxas = _preparar_entradas(tmp_path)
    ausente = tmp_path / "nao-existe.csv"
    assert not ausente.exists()

    processo = _executar(tmp_path, "--input", str(ausente), "--rates", str(taxas))

    assert processo.returncode == 2
    assert processo.stdout == ""


def test_rates_inexistente_retorna_exit_2(tmp_path: Path) -> None:
    """R22: 2 para entrada inválida — tabela de câmbio ausente."""
    reservas, _ = _preparar_entradas(tmp_path)
    ausente = tmp_path / "sem-taxas.csv"
    assert not ausente.exists()

    processo = _executar(tmp_path, "--input", str(reservas), "--rates", str(ausente))

    assert processo.returncode == 2
