"""Testes novos: leitura integral da exportação (R08, defeito F06)"""

from __future__ import annotations

from pathlib import Path

from helpers import run_cli

TOTAL_DE_LINHAS = 250


def test_le_todas_as_linhas_acima_do_limite_de_200(tmp_path: Path) -> None:
    """R08: `total_reservations` é o número de reservas do arquivo, sem teto."""
    linhas = [{"reservation_id": f"R-{indice:04d}", "amount": "100.00"} for indice in range(1, TOTAL_DE_LINHAS)]
    linhas.append(
        {
            "reservation_id": f"R-{TOTAL_DE_LINHAS:04d}",
            "hotel_id": "H99",
            "hotel_name": "Hotel da Última Linha",
            "amount": "9999.00",
        }
    )

    report = run_cli(tmp_path, linhas)

    assert report["summary"]["total_reservations"] == TOTAL_DE_LINHAS
    assert report["summary"]["confirmed_reservations"] == TOTAL_DE_LINHAS
    assert report["summary"]["total_room_nights"] == TOTAL_DE_LINHAS
    assert report["summary"]["total_amount_brl"] == "34899.00"
    assert [hotel["hotel_id"] for hotel in report["top_hotels"]] == ["H01", "H99"]
    assert report["top_hotels"][1]["total_brl"] == "9999.00"