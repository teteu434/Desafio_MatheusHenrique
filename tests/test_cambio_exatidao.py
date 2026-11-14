"""Testes novos: exatidão decimal do câmbio (R12 e R13, defeito F04)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from helpers import run_cli

from onfly_report.services.currency_converter import convert_to_brl

TAXAS: dict[str, Decimal] = {
    "BRL": Decimal("1.000000"),
    "USD": Decimal("5.420000"),
    "EUR": Decimal("5.880000"),
}


def test_convert_to_brl_devolve_o_decimal_exato() -> None:
    """R12: a conversão é aritmética de Decimal, sem passagem por float."""
    casos = [
        (Decimal("0.75"), "USD", Decimal("4.06500000")),
        (Decimal("1457.41"), "USD", Decimal("7899.16220000")),
        (Decimal("233.79"), "EUR", Decimal("1374.68520000")),
    ]
    for valor, moeda, esperado in casos:
        obtido = convert_to_brl(valor, moeda, TAXAS)
        assert obtido == esperado
        assert obtido == valor * TAXAS[moeda]


def test_centavo_de_fronteira_sobrevive_ate_a_serializacao(tmp_path: Path) -> None:
    """R13: 0.75 USD x 5.42 = 4.065 exatos, que o half-up da serialização sobe para 4.07.

    Pelo caminho do float o produto vira 4.0649999999999995 e desce para 4.06.
    """
    report = run_cli(
        tmp_path,
        [{"reservation_id": "R-1", "currency": "USD", "amount": "0.75"}],
    )

    assert report["summary"]["total_amount_brl"] == "4.07"
    assert report["summary"]["average_nightly_rate_brl"] == "4.07"
    assert report["by_month"][0]["total_brl"] == "4.07"
    assert report["top_hotels"][0]["total_brl"] == "4.07"