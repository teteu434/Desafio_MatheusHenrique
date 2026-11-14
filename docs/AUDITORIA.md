# Fase 3 — Auditoria read-only

Varredura de `src/onfly_report/` contra as regras R01–R30 de `docs/SPEC.md`.
Percorri as **regras**, não os arquivos, para que nenhuma ficasse sem cobertura.

Data: 2026-11-14. Commit auditado: `5bb6367`, `git status --short src` vazio.
**Nenhum arquivo foi modificado nesta fase.**

## Achados

| F## | R## violada | arquivo:linha | evidência | causa raiz | severidade |
|-|-|-|-|-|-|
| F01 | R01, R02, R10 | `services/status_policy.py:8` | `return status != "CANCELLED"` deixa `NO_SHOW` passar. `tests/test_status_rules.py` espera `total_amount_brl == "100.00"` e obtém `"120.00"` — os 20.00 da linha `NO_SHOW`. Na amostra, H05 (Hotel Recife Plaza, `NO_SHOW`, 300.00) aparece no `top_hotels` do baseline, e 2025-01 conta 9 reservas em vez de 8. | O predicado de faturabilidade nega só um dos dois status não faturáveis, em vez de afirmar `CONFIRMED`. | alta |
| F02 | R03, R04 | `services/stay_calculator.py:10` | `(checkout.day - checkin.day) * rooms` compara **dia do mês**, não datas. Para 2025-01-30 → 2025-02-02: `(2 - 30) * 1 = -28`, e `tests/test_nights.py` exige `3`. Na amostra o total dá `-33` contra os 28 do README. | Subtrai o campo `.day` de cada data em vez da diferença entre as datas. | alta |
| F03 | R06 | `services/currency_converter.py:11` | `float(amount) / float(rate)` **divide** onde R06 manda multiplicar. 100 USD com taxa 5.42 vira `100/5.42 = 18.4501…` em vez de `542.00`; `tests/test_currency.py` espera `"642.00"` e obtém `"118.45"` (= 100 + 18.45). | A conversão inverte a operação da taxa. | alta |
| F04 | R12 | `services/currency_converter.py:11` | O mesmo trecho passa por `float`, que R12 proíbe explicitamente ("Use `Decimal`, nunca `float`"). Medido no dataset **já com a multiplicação correta**: 19 das 235 linhas `CONFIRMED` dão resultado diferente do `Decimal` exato (ex.: o acumulado fecha em `396169.99939999999932` contra `396169.99940000` exato). | O valor sai do domínio `Decimal` e volta via `str(float)`, perdendo exatidão. | alta |
| F05 | R18 | `services/report_builder.py:91` | `sorted(hotels.items(), key=lambda item: (item[1]["amount"], item[0]))` ordena **ascendente**. `tests/test_top_hotels.py` espera `[H01, H02, H03]` e obtém `[H04, H03, H02]`; o baseline da amostra sai de 25.51 a 600.00, crescente. | A chave de ordenação não inverte o valor, então o ranking sai do menor para o maior. | alta |
| F06 | R08 | `repositories/csv_reservation_repository.py:47-48` | `if len(rows) == 200: break` corta a leitura. `data/reservas_hoteis.csv` tem 300 linhas de dados e o baseline informa `total_reservations: 200` — 100 reservas somem de todos os agregados. | A leitura tem um limite fixo de 200 linhas que trunca o arquivo silenciosamente. | alta |

### Nota sobre F03 e F04

Os dois vivem na mesma linha e um único patch resolve ambos
(`amount * rates[currency]`, sem `float`). Estão separados porque violam regras
diferentes e têm impacto diferente, e a decisão de tratá-los como um ou dois
commits é da triagem.

### Severidade de F04: alta

Minha classificação inicial foi **média**, com o argumento de que, corrigida a
divisão, `float` e `Decimal` exato serializam igual neste dataset
(`396170.00`), apesar de 19 das 235 linhas `CONFIRMED` diferirem internamente.

**Reclassificado para alta na triagem de 2026-11-14, e o usuário está certo.**
A severidade mede **risco**, não o efeito observado neste arquivo:

- R12 é proibição textual do README ("Use `Decimal`, nunca `float`"), não
  preferência de estilo.
- O erro do `float` não depende deste dataset. Com outros valores ele pode cair
  numa **fronteira de meio centavo**, e aí o `ROUND_HALF_UP` da serialização
  arredonda para o lado errado — virando número errado no relatório, que é
  exatamente o critério de severidade alta.
- O README diz que "testes adicionais são considerados", ou seja, o avaliador
  pode rodar o CLI sobre dados que não são os nossos. Classificar pelo que este
  arquivo expõe seria classificar pela amostra, não pelo defeito.

Que os 19 casos medidos somem no arredondamento é sorte deste dataset, não
propriedade do código.

## Suspeitas

Sem evidência concreta de defeito; não entram na tabela.

- **S01 — BOM no CSV de entrada.** Os repositórios abrem com `encoding="utf-8"`,
  não `"utf-8-sig"`. Um arquivo com BOM faria a primeira coluna virar
  `﻿reservation_id` e a validação de colunas obrigatórias acusaria ausência,
  terminando em exit 2. Os arquivos fornecidos não têm BOM (o CLI lê os dois com
  exit 0), então **não consegui demonstrar falha**. Robustez, fora de escopo.
- **S02 — `strftime("%Y-%m")` em `report_builder.py:68`.** Funciona e passa na
  amostra; `isoformat()[:7]` seria mais direto. Sem evidência de erro: não é
  achado, é preferência.

## Já registrado em `docs/SPEC.md` (não é achado novo)

- **O10** — `hotel_name` é o da última linha do hotel. Latente: os 12 `hotel_id`
  têm um nome cada.
- **O11** — `currency` com `.strip()` no parser contra `.strip().upper()` no
  repositório de taxas. Latente: o dataset só traz `BRL`/`USD`/`EUR` maiúsculos.
- **O12** — `by_month` só com confirmadas. **Não é defeito, e nada a mudar.**
  R02 exige literalmente que `CANCELLED` e `NO_SHOW` não entrem em `by_month`, e
  a amostra fecha a conta: `exemplo-validacao.csv` tem 11 check-ins em 2025-01,
  três deles não confirmados (EX-04, EX-05, EX-06), e o README manda
  `reservations: 8`. Contar as 11 quebraria a validação — alterar aqui seria
  **introduzir** um defeito. Levantado pelo usuário, discutido e **resolvido na
  triagem de 2026-11-14 a favor de R02 + amostra**. O único resíduo é que um mês
  com zero confirmadas não gera linha, o que também decorre de R02 e não ocorre
  no dataset (todo mês tem entre 21 e 39 confirmadas).
- **A04** — moeda sem taxa estoura `KeyError` e sai com 1 em vez de 2. Decidido
  como **mudança de comportamento**, Fase 6, não defeito.

## Cobertura

Todas as 30 regras foram verificadas.

**Violadas (6 achados):** R01, R02, R03, R04, R06, R08, R10, R12, R18.

**Verificadas e conformes (21 regras):**

| Regra | Onde | Situação |
|-|-|-|
| R05 | `row_parser.py:34` | `amount` lido na moeda de `currency` (ver O11) |
| R07 | `csv_rate_repository.py:25-47` | valida colunas, taxa positiva e tabela não vazia |
| R09 | `report_builder.py:45-47` | as três contagens somam sobre **todas** as linhas |
| R11 | `report_builder.py:42-61` | ler → parsear → contar → filtrar → agregar, nessa ordem |
| R13 | `report_builder.py:20-22` | acumula em `Decimal` e só `quantize` com `ROUND_HALF_UP` na saída |
| R14 | `report_builder.py:77-79` | divide pelo total de noites; `Decimal("0")` quando não há noites |
| R15 | `row_parser.py:30-31` | `date.fromisoformat`, data civil sem fuso |
| R16 | `report_builder.py:17,102,106` | `timezone(timedelta(hours=-3))` + `isoformat(timespec="seconds")` |
| R17 | `report_builder.py:88` | `sorted(monthly.items())` ordena o mês ascendente |
| R19 | `cli.py:24-27` | `--input`/`--rates` obrigatórios, `--output`/`--top` opcionais |
| R20 | `cli.py:26` | padrão `output/report.json` |
| R21 | `cli.py:27,36-37` | `type=int`, `default=5`, recusa `< 1` |
| R22 | `cli.py:36-37,45-50` | `parser.error` → 2; `InputFileError` → 2; `Exception` → 1; sucesso → 0 |
| R23 | `cli.py:54` | `mkdir(parents=True, exist_ok=True)` |
| R24 | `cli.py:64-71` + `logging_config.py:13` | resumo no stdout, log no stderr |
| R25 | `report_builder.py:104-118` | as chaves e o aninhamento batem com o README |
| R26 | `report_builder.py:20-22` | dinheiro serializa como string de 2 casas; contagens ficam `int` |
| R27 | `report_builder.py:105` | `"report_version": "1.0"` fixo |
| R28 | `report_builder.py:99` | `[: self._top_n]` encurta sem estourar |
| R29 | `report_builder.py:68` | mês vem do `checkin` |
| R30 | — | nenhum campo renomeado |

**Sem cobertura: nenhuma.**

## Detalhe para a correção de F05

`reverse=True` **não** resolve sozinho. Com a chave atual, inverter a ordenação
inverte também o desempate, e R18 pede valor decrescente com `hotel_id`
**ascendente**. Demonstração com H01=100, H02=200, H03=100:

| chave | resultado | veredito |
|-|-|-|
| `(amount, id)` (hoje) | `[H01, H03, H02]` | valor ascendente: errado |
| `(amount, id)` + `reverse=True` | `[H02, H03, H01]` | empate descendente: errado |
| `(-amount, id)` | `[H02, H01, H03]` | correto |

## Ordem sugerida para a Fase 5

Sugestão, não decisão — a triagem é do usuário. F06 primeiro, porque é o único
que muda o **conjunto de dados** sob os outros e deixaria os números de todos os
demais instáveis enquanto estivesse aberto. Depois F02, F03+F04, F01 e F05, que
são independentes entre si.

Aguardando triagem. Nenhuma correção aplicada.
