# Fase 0 — Baseline do estado inicial

Registro do comportamento do CLI **antes de qualquer correção**. Nada foi
corrigido nesta fase. O lint pré-existente também só foi registrado.

Data da coleta: 2026-11-14.

## Ambiente

| Item | Valor |
|-|-|
| SO | Windows 11 Home Single Language 10.0.26200 |
| Shell | Windows PowerShell 5.1 |
| Python do venv | 3.13.14 (`.venv`) |
| pytest | 8.3.4 |
| ruff | 0.8.4 |
| Commit | `5bb6367` ("First commit"), árvore limpa |

Python 3.11 não está disponível nesta máquina (só 3.13.14 e 3.14). Por decisão
do usuário, o venv usa o 3.13.14, que satisfaz o `requires-python = ">=3.11"` do
`pyproject.toml`. O CLI usa apenas a biblioteca padrão.

## Comandos exatos

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m ruff check .

$env:PYTHONPATH = "src"
& .\.venv\Scripts\python.exe -m onfly_report `
  --input data/exemplo-validacao.csv `
  --rates data/taxas_cambio.csv `
  --output docs/baseline/amostra.json

& .\.venv\Scripts\python.exe -m onfly_report `
  --input data/reservas_hoteis.csv `
  --rates data/taxas_cambio.csv `
  --output docs/baseline/completo.json
```

Os relatórios gerados ficam nesta pasta: `amostra.json` e `completo.json`.
Saídas de terminal, stderr e códigos de saída estão transcritos abaixo.

## Resultados

### `pytest -q`

**5 falharam, 0 passaram.** Exit code 1. É o esperado pelo README ("No início,
todos falham").

| Teste | Esperado | Obtido |
|-|-|-|
| `test_currency_conversion_to_brl` | `total_amount_brl == "642.00"` | `"118.45"` |
| `test_nights_across_month_boundary` | `total_room_nights == 3` | `-28` |
| `test_regression_report_on_sample` | `1542.00` / `308.40` | `1018.45` / `203.69` |
| `test_status_rules_exclude_cancelled_and_no_show` | `total_amount_brl == "100.00"` | `"120.00"` |
| `test_top_hotels_are_ranked_descending` | `[H01, H02, H03]` | `[H04, H03, H02]` |

As demais asserções de `test_status_rules` (as quatro contagens) e as cinco
chaves restantes de `test_regression_report` já passam.

### `ruff check .`

**`All checks passed!`**, exit code 0. Não há lint pré-existente; qualquer
apontamento futuro do ruff será introduzido por mim e deve ser tratado como tal.

### CLI sobre `data/exemplo-validacao.csv` → `amostra.json`

Exit code **0**, stderr vazio.

- stdout: `Reservas: 12 | Confirmadas: 9 | Noites: -33 | Total BRL: 5962.41`

### CLI sobre `data/reservas_hoteis.csv` → `completo.json`

Exit code **0**, stderr vazio.

- stdout: `Reservas: 200 | Confirmadas: 153 | Noites: -1393 | Total BRL: 193218.53`

O arquivo tem **300 linhas de dados** (301 com o cabeçalho), mas o relatório
informa `total_reservations: 200`. O `by_month` traz 7 meses e o `top_hotels`,
5 itens.

O CLI não quebrava em nenhum dos dois arquivos: terminava com sucesso e
entregava números errados.

## Divergências da amostra contra as tabelas do README

Comparação de `amostra.json` contra as tabelas entre `<!-- AMOSTRA:INICIO -->`
e `<!-- AMOSTRA:FIM -->` do README. `generated_at` ignorado.

### `summary` — 3 de 7 campos divergem

| Campo | Esperado | Obtido | Bate? |
|-|-|-|-|
| `total_reservations` | 12 | 12 | sim |
| `confirmed_reservations` | 9 | 9 | sim |
| `cancelled_reservations` | 2 | 2 | sim |
| `no_show_reservations` | 1 | 1 | sim |
| `total_room_nights` | 28 | **-33** | não |
| `total_amount_brl` | 7566.00 | **5962.41** | não |
| `average_nightly_rate_brl` | 270.21 | **0.00** | não |

A média sai `0.00` porque o total de noites é negativo, e o código só divide
quando `total_nights > 0`.

### `by_month` — 4 divergências

| Linha | Campo | Esperado | Obtido |
|-|-|-|-|
| 2025-01 | `reservations` | 8 | **9** |
| 2025-01 | `room_nights` | 25 | **-36** |
| 2025-01 | `total_brl` | 6684.00 | **5936.90** |
| 2025-02 | `reservations` | 1 | 1 |
| 2025-02 | `room_nights` | 3 | 3 |
| 2025-02 | `total_brl` | 882.00 | **25.51** |

### `top_hotels` — as 5 posições divergem

| Pos. | Esperado | Obtido |
|-|-|-|
| 1 | H01 · Hotel Aurora Paulista · 3 · 1200.00 | **H09 · Hotel Lisboa, Centro · 3 · 25.51** |
| 2 | H02 · Hotel Mirante · 2 · 1084.00 | **H02 · Hotel Mirante · 2 · 36.90** |
| 3 | H12 · Hotel Miami Beach · 1 · 1000.00 | **H05 · Hotel Recife Plaza · 1 · 300.00** |
| 4 | H10 · Hotel Madrid, Gran Vía · 4 · 900.00 | **H08 · Hotel Iguazu Falls · 1 · 400.00** |
| 5 | H09 · Hotel Lisboa, Centro · 3 · 882.00 | **H07 · Hotel Brasília Tower · 2 · 600.00** |

Os valores obtidos estão em ordem **crescente**, e H05 (Hotel Recife Plaza) é a
reserva `NO_SHOW` da amostra, que não deveria aparecer no ranking.

## Observação sobre acentuação (não é defeito)

O console exibe "Hotel BrasÃ­lia Tower" ao abrir o JSON com `Get-Content` sem
`-Encoding utf8`. Conferi os bytes no arquivo: `c3 ad`, que é `í` em UTF-8
correto. O CLI grava com `encoding="utf-8"` e `ensure_ascii=False`. **A
acentuação do arquivo está certa**; o que distorce é a leitura em cp1252 do
PowerShell 5.1. Registrado aqui para não virar falso positivo na auditoria.

## Estado

Fase 0 encerrada. Nenhum arquivo de `src/`, `tests/` ou `data/` foi tocado.