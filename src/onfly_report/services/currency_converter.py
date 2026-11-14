"""Conversão de valores para BRL."""

from __future__ import annotations

from decimal import Decimal

from ..exceptions import InputFileError


def convert_to_brl(amount: Decimal, currency: str, rates: dict[str, Decimal]) -> Decimal:
    """Converte um valor na moeda informada para BRL usando a taxa da tabela.

    Moeda ausente da tabela é erro do arquivo de entrada (decisão A04), não erro
    inesperado: o CLI precisa sair com 2, como já faz para data, `rooms` e
    `amount` malformados.
    """
    try:
        rate = rates[currency]
    except KeyError as err:
        raise InputFileError(f"moeda {currency!r} sem taxa na tabela de câmbio") from err
    return amount * rate
