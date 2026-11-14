"""Testes novos: regras sem cobertura na suíte fornecida (R03, R04, R13, R14, R28)."""

from __future__ import annotations

from pathlib import Path

import pytest
from helpers import run_cli


def test_soma_exata_antes_de_arredondar(tmp_path: Path) -> None:
    """R13: some os valores exatos e arredonde só na serialização.

    0.75 USD x 5.42 = 4.065 exatos. Duas linhas somam 8.13 e serializam "8.13".
    Se cada linha fosse arredondada antes da soma, daria 4.07 + 4.07 = "8.14".
    O valor entregue distingue as duas implementações.
    """
    relatorio = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "currency": "USD", "amount": "0.75"},
            {"reservation_id": "R-2", "currency": "USD", "amount": "0.75"},
        ],
    )

    assert relatorio["summary"]["total_amount_brl"] == "8.13"
    assert relatorio["by_month"][0]["total_brl"] == "8.13"
    assert relatorio["top_hotels"][0]["total_brl"] == "8.13"

    # 8.13 / 2 noites = 4.065, que o half-up sobe para 4.07.
    assert relatorio["summary"]["average_nightly_rate_brl"] == "4.07"


def test_sem_noites_a_media_e_zero(tmp_path: Path) -> None:
    """R14: sem noites, `average_nightly_rate_brl` é "0.00".

    Só reservas não faturáveis: nada entra em noites, valores, by_month nem
    top_hotels, mas as contagens por status continuam valendo (R02).
    """
    relatorio = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "status": "CANCELLED", "amount": "500.00"},
            {"reservation_id": "R-2", "status": "NO_SHOW", "amount": "300.00"},
        ],
    )

    resumo = relatorio["summary"]
    assert resumo["total_reservations"] == 2
    assert resumo["confirmed_reservations"] == 0
    assert resumo["cancelled_reservations"] == 1
    assert resumo["no_show_reservations"] == 1
    assert resumo["total_room_nights"] == 0
    assert resumo["total_amount_brl"] == "0.00"
    assert resumo["average_nightly_rate_brl"] == "0.00"

    assert relatorio["by_month"] == []
    assert relatorio["top_hotels"] == []


def test_noites_na_virada_de_ano(tmp_path: Path) -> None:
    """R04: a diferença não inclusiva vale também na virada de ano.

    30/12/2024 a 02/01/2025 são 3 noites, e o mês do relatório é o do check-in.
    """
    relatorio = run_cli(
        tmp_path,
        [
            {
                "reservation_id": "R-1",
                "checkin_date": "2024-12-30",
                "checkout_date": "2025-01-02",
                "rooms": "1",
            }
        ],
    )

    assert relatorio["summary"]["total_room_nights"] == 3
    assert [mes["month"] for mes in relatorio["by_month"]] == ["2024-12"]
    assert relatorio["by_month"][0]["room_nights"] == 3


@pytest.mark.parametrize(("quartos", "noites_esperadas"), [(1, 3), (2, 6), (3, 9), (4, 12)])
def test_noites_multiplicam_pelo_numero_de_quartos(
    tmp_path: Path, quartos: int, noites_esperadas: int
) -> None:
    """R03: room_nights = (checkout - checkin).days * rooms.

    Mesmas datas (3 noites) com número de quartos crescente.
    """
    relatorio = run_cli(
        tmp_path,
        [
            {
                "reservation_id": "R-1",
                "checkin_date": "2025-01-10",
                "checkout_date": "2025-01-13",
                "rooms": str(quartos),
            }
        ],
    )

    assert relatorio["summary"]["total_room_nights"] == noites_esperadas


def test_top_maior_que_a_quantidade_de_hoteis(tmp_path: Path) -> None:
    """R28: top_hotels tem --top itens, ou menos se houver menos hotéis.

    `--top 50` com 2 hotéis devolve 2 itens, na ordem de R18, e sem erro.
    """
    relatorio = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "hotel_id": "H01", "hotel_name": "Hotel A", "amount": "100.00"},
            {"reservation_id": "R-2", "hotel_id": "H02", "hotel_name": "Hotel B", "amount": "200.00"},
        ],
        top=50,
    )

    assert len(relatorio["top_hotels"]) == 2
    assert [hotel["hotel_id"] for hotel in relatorio["top_hotels"]] == ["H02", "H01"]
    assert [hotel["total_brl"] for hotel in relatorio["top_hotels"]] == ["200.00", "100.00"]
