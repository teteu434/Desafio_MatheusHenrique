# Defeitos corrigidos

Um registro por defeito, na ordem em que foram corrigidos. A triagem e a ordem
são do usuário; a análise completa está em `docs/AUDITORIA.md`.

---

## F06 — leitura truncada em 200 linhas

| | |
|-|-|
| **Regra violada** | R08 — `total_reservations` = número de reservas no arquivo |
| **Severidade** | alta |
| **Causa raiz** | A leitura tinha um limite fixo de 200 linhas que truncava o arquivo silenciosamente. |
| **Arquivos tocados** | `src/onfly_report/repositories/csv_reservation_repository.py` |
| **Teste** | `tests/test_leitura_completa.py::test_le_todas_as_linhas_acima_do_limite_de_200` |

### O que acontecia

`CsvReservationRepository.read()` interrompia o laço ao chegar em 200 linhas:

```python
rows.append(RawRow(line_number=reader.line_num, values=values))
if len(rows) == 200:
    break
```

`data/reservas_hoteis.csv` tem **300** linhas de dados, então 100 reservas não
chegavam ao `ReportBuilder`. O corte era silencioso: sem aviso, sem erro, e o
CLI saía com código 0. Todos os agregados herdavam o erro — contagens por
status, noites, valores, `by_month` e `top_hotels`.

### Evidência

Antes (baseline da Fase 0, `docs/baseline/completo.stdout.txt`):

```
Reservas: 200 | Confirmadas: 153 | Noites: -1393 | Total BRL: 193218.53
```

Depois:

```
Reservas: 300 | Confirmadas: 235 | Noites: -2068 | Total BRL: 284908.26
```

As contagens batem com o dataset: 235 `CONFIRMED`, 31 `CANCELLED` e 34
`NO_SHOW`, somando 300.

As noites e os valores continuam errados — são F02, F03 e F04, ainda abertos
neste ponto da correção.

### Correção

Remoção das duas linhas do limite. Nada mais foi tocado: sem refatoração, sem
reformatação, sem lint fora do trecho.

```diff
                  rows: list[RawRow] = []
                  for values in reader:
                      rows.append(RawRow(line_number=reader.line_num, values=values))
 -                    if len(rows) == 200:
 -                        break
                  return rows
```

### Verificação

- Teste novo: vermelho `assert 200 == 250` antes, verde depois.
- `ruff check .`: `All checks passed!`
- `pytest -q`: 5 falhas remanescentes, todas de F01–F05, ainda abertos. Nenhum
  teste que passava antes quebrou.

---

## F02 — noites calculadas pelo dia do mês

| | |
|-|-|
| **Regra violada** | R03 e R04 — `(checkout_date - checkin_date).days * rooms`, não inclusiva, válida na virada de mês/ano |
| **Severidade** | alta |
| **Causa raiz** | Subtraía o campo `.day` de cada data em vez da diferença entre as datas. |
| **Arquivos tocados** | `src/onfly_report/services/stay_calculator.py` |
| **Teste** | `tests/test_nights.py::test_nights_across_month_boundary` (fornecido) |

### O que acontecia

```python
return (checkout.day - checkin.day) * rooms
```

`.day` é o dia do mês, de 1 a 31. A conta só acertava quando check-in e
check-out caíam no **mesmo mês**; em qualquer travessia de mês ou de ano o
resultado era negativo ou absurdo. Para 2025-01-30 → 2025-02-02: `(2 - 30) * 1
= -28`, quando o certo são 3 noites.

Como `total_room_nights` saía negativo, a média caía no ramo
`total_nights > 0` do `report_builder` e era publicada como `"0.00"` — um
segundo campo errado por tabela.

### Evidência

O teste fornecido `tests/test_nights.py` já cobria exatamente esta regra e
falhava com `assert -28 == 3`. **Nenhum teste novo foi criado**: o vermelho já
existia na suíte entregue.

Conferência das duas regras direto na função, após o patch:

| caso | esperado | obtido |
|-|-|-|
| 10/01 → 13/01, 1 quarto (exemplo do README) | 3 | 3 |
| 30/01 → 02/02, 1 quarto (virada de mês) | 3 | 3 |
| 30/12/2024 → 02/01/2025, 1 quarto (virada de ano, R04) | 3 | 3 |
| 28/01 → 02/02, 2 quartos (amostra EX-03) | 10 | 10 |
| 10/01 → 11/01, 3 quartos (R03) | 3 | 3 |

### Correção

```diff
-    return (checkout.day - checkin.day) * rooms
+    return (checkout - checkin).days * rooms
```

A subtração entre dois `date` devolve um `timedelta`, cujo `.days` é a diferença
de calendário — não inclusiva por construção, e indiferente a mês e ano.

### Verificação

- `tests/test_nights.py`: vermelho `assert -28 == 3` antes, `1 passed` depois.
- `pytest -q`: de 5 falhas para **4**. As restantes são F01, F03, F04 e F05.
- `ruff check .`: `All checks passed!`
- Amostra: `total_room_nights` saiu de `-33` para **29**. O alvo é 28; o `+1`
  restante é a EX-05 (`NO_SHOW`, 1 noite), que só sai com **F01**. O mesmo em
  2025-01: 26 contra 25 esperados, a mesma reserva.
- Dataset completo: `Noites: -2068` virou `Noites: 1554`.

---

## F03 — conversão de moeda dividia pela taxa

| | |
|-|-|
| **Regra violada** | R06 — "Converta com `amount * rate_to_brl`" |
| **Severidade** | alta |
| **Causa raiz** | A conversão invertia a operação da taxa, dividindo onde deveria multiplicar. |
| **Arquivos tocados** | `src/onfly_report/services/currency_converter.py` |
| **Teste** | `tests/test_currency.py::test_currency_conversion_to_brl` (fornecido) |

### O que acontecia

```python
return Decimal(str(float(amount) / float(rate)))
```

Cada valor em moeda estrangeira era **dividido** pela taxa. 100 USD com taxa
5.42 viravam `100 / 5.42 = 18.45` em vez de `542.00` — um erro de quase 30x no
sentido oposto. Moedas com taxa `1.000000` (BRL) passavam ilesas, o que
mascarava o defeito em qualquer teste que só usasse reais.

### Evidência

Teste fornecido `tests/test_currency.py`, com uma linha em BRL e outra em USD de
100.00 cada: esperava `"642.00"` (100 + 542) e obtinha `"118.45"`
(100 + 18.45). **Nenhum teste novo foi criado**: o vermelho já existia.

### Correção

```diff
-    return Decimal(str(float(amount) / float(rate)))
+    return Decimal(str(float(amount) * float(rate)))
```

O `float` foi **mantido de propósito**. Ele é o defeito F04, violação de R12,
e será corrigido em commit separado para que cada um tenha sua própria
evidência. Trocar as duas coisas de uma vez tornaria impossível demonstrar qual
delas causava qual desvio.

### Verificação

- `tests/test_currency.py`: vermelho `assert '118.45' == '642.00'`, depois verde.
- `tests/test_regression_report.py` também ficou verde: era o outro teste
  fornecido que dependia de câmbio.
- `pytest -q`: de 4 falhas para **2**. Restam F01 e F05.
- `ruff check .`: `All checks passed!`
- Amostra: `total_amount_brl` saiu de `5962.41` para **7866.00**, contra
  7566.00 esperados. A diferença é exatamente `300.00`, a EX-05 (`NO_SHOW`),
  que só sai com **F01**. As noites seguem em 29 contra 28 pela mesma reserva, e
  o ranking continua ascendente por **F05**.

### F04 confirmado ainda vermelho, pelo motivo de F04

Com a multiplicação já correta, `convert_to_brl` continua **não** devolvendo o
`Decimal` exato — o que isola o defeito do `float`:

| amount | moeda | exato | obtido via `float` | iguais |
|-|-|-|-|-|
| 1457.41 | USD | `7899.16220000` | `7899.162200000001` | não |
| 2116.06 | USD | `11469.04520000` | `11469.045199999999` | não |


---

## F04 — dinheiro passava por `float`

| | |
|-|-|
| **Regra violada** | R12 — "Use `Decimal`, nunca `float`, no dinheiro" |
| **Severidade** | alta (reclassificada de média na triagem — ver `docs/AUDITORIA.md`) |
| **Causa raiz** | O valor saía do domínio `Decimal` e voltava via `str(float)`, perdendo exatidão antes do arredondamento. |
| **Arquivos tocados** | `src/onfly_report/services/currency_converter.py` |
| **Teste** | **pendente** — ver "Pendência" abaixo |

### O que acontecia

```python
return Decimal(str(float(amount) * float(rate)))
```

Com F03 já corrigido, a operação estava certa e o resultado **ainda** vinha
errado: o produto era calculado em binário de precisão dupla e só então
reconvertido para `Decimal`. O erro é minúsculo por linha, mas entra na soma
antes do arredondamento, que é justamente onde R13 manda preservar exatidão.

### Evidência 1 — a conversão não devolvia o valor exato

| amount | moeda | exato | obtido via `float` |
|-|-|-|-|
| 1457.41 | USD | `7899.16220000` | `7899.162200000001` |
| 2116.06 | USD | `11469.04520000` | `11469.045199999999` |

### Evidência 2 — o `float` mudava um centavo **entregue**

É esta que sustenta a severidade alta. Varrendo todos os valores de 2 casas
contra as taxas do próprio `data/taxas_cambio.csv`, há casos em que o
`ROUND_HALF_UP` da serialização cai para o lado errado:

```
0.75 USD x 5.42 = 4.065          (produto exato)
   half-up sobre o exato : 4.07
   half-up via float     : 4.06  <-- um centavo a menos
```

Confirmado **ponta a ponta pelo CLI**, com um CSV de uma linha só:

| | `total_amount_brl` |
|-|-|
| antes do patch | `4.06` |
| depois do patch | `4.07` |
| exigido por R13 | `4.07` |

Outros casos na mesma faixa: 8.25, 18.25, 22.75, 26.75 e 30.25 USD. Nenhum
depende de valor exótico — são quantias de 2 casas com a taxa do projeto.

### Correção

```diff
-    return Decimal(str(float(amount) * float(rate)))
+    return amount * rate
```

`amount` e `rate` já são `Decimal`; a multiplicação direta é exata por
construção. Não resta **nenhuma** ocorrência de `float` em `src/`
(`grep -rn "float" src/` não retorna nada).

### Verificação

- `convert_to_brl` passou a devolver o `Decimal` exato nos 4 casos da tabela.
- Varredura repetida após o patch, mesma faixa: **0** casos de centavo divergente
  (antes havia pelo menos 6).
- `pytest -q`: **2 failed, 3 passed** — igual a antes. Nenhum teste fornecido
  cobre este defeito, o que é exatamente o motivo da pendência abaixo.
- `ruff check .`: `All checks passed!`
- Amostra: **inalterada** (7866.00). Honestamente: os valores da amostra não
  tocam a fronteira de meio centavo, então ela não demonstra este defeito nem
  antes nem depois. A prova é a Evidência 2.
- Dataset completo: `Total BRL: 460058.83`, ainda com as `NO_SHOW` dentro por
  causa de **F01**. Previsão: quando F01 fechar, o total deve cair para
  **396170.00**, que é a soma exata só das `CONFIRMED`.

### Pendência — teste de regressão

F04 é o único defeito sem teste fornecido que o cubra, porque o erro só aparece
no `Decimal` **antes** da serialização. Por decisão do usuário, os testes novos
entram na etapa final; este defeito está corrigido mas **sem rede de proteção**.

O teste a criar deve, em dois níveis:

1. chamar `convert_to_brl` e comparar com `Decimal(amount) * Decimal(rate)`
   usando igualdade exata, não arredondada;
2. rodar o CLI sobre uma reserva de `0.75 USD` e exigir
   `total_amount_brl == "4.07"`, que é o caso de fronteira.

Um teste que só olhe o valor serializado de quantias comuns passa com `float` e
não prova nada.

---

## F01 — `NO_SHOW` entrava nos totais financeiros

| | |
|-|-|
| **Regra violada** | R01, R02 e R10 — só `CONFIRMED` é faturável |
| **Severidade** | alta |
| **Causa raiz** | O predicado negava apenas um dos dois status não faturáveis, em vez de afirmar `CONFIRMED`. |
| **Arquivos tocados** | `src/onfly_report/services/status_policy.py` |
| **Teste** | `tests/test_status_rules.py::test_status_rules_exclude_cancelled_and_no_show` (fornecido) |

### O que acontecia

```python
return status != "CANCELLED"
```

A regra tem **dois** status não faturáveis, `CANCELLED` e `NO_SHOW`, e o
predicado excluía só o primeiro. Toda reserva `NO_SHOW` era tratada como
faturável e entrava em `total_room_nights`, `total_amount_brl`,
`average_nightly_rate_brl`, `by_month` e `top_hotels` — exatamente os cinco
lugares que R02 proíbe.

As contagens por status nunca estiveram erradas: `report_builder` conta antes de
filtrar, conforme R11, então `no_show_reservations` já saía certo. O defeito
estava só no filtro.

### Evidência

Teste fornecido, com uma reserva de cada status (100.00 / 50.00 / 20.00):
esperava `total_amount_brl == "100.00"` e obtinha `"120.00"` — os 20.00 da linha
`NO_SHOW`. A linha `CANCELLED` já era excluída corretamente, o que explica por
que só 20.00 vazavam. **Nenhum teste novo foi criado.**

Na amostra, a EX-05 (Hotel Recife Plaza, `NO_SHOW`, 300.00 BRL, 1 noite)
aparecia no `top_hotels` e inflava janeiro em uma reserva e uma noite.

### Correção

```diff
-    return status != "CANCELLED"
+    return status == "CONFIRMED"
```

Afirmar o status faturável, em vez de negar os não faturáveis, também resolve o
caso de status desconhecido conforme a decisão **A05**: um status fora dos três
conhecidos conta em `total_reservations` e em nenhum agregado.

### Verificação

- `tests/test_status_rules.py`: vermelho `assert '120.00' == '100.00'`, depois verde.
- `pytest -q`: de 2 falhas para **1**. Resta apenas F05.
- `ruff check .`: `All checks passed!`
- **Amostra: `summary` e `by_month` agora batem campo a campo com o README.**
  `total_room_nights` = 28, `total_amount_brl` = 7566.00,
  `average_nightly_rate_brl` = 270.21, 2025-01 com 8 / 25 / 6684.00 e 2025-02
  com 1 / 3 / 882.00. As 15 divergências que restam estão **todas** em
  `top_hotels`, que é F05.
- Dataset completo: `Total BRL: 460058.83` caiu para **396170.00**, confirmando
  exatamente a previsão registrada na entrada de F04 — a soma exata só das 235
  reservas `CONFIRMED`. As noites foram de 1554 para 1347.

---

## F05 — ranking de hotéis em ordem crescente

| | |
|-|-|
| **Regra violada** | R18 — `top_hotels` por `total_brl` decrescente, empate por `hotel_id` ascendente |
| **Severidade** | alta |
| **Causa raiz** | A chave de ordenação não invertia o valor, então o ranking saía do menor para o maior. |
| **Arquivos tocados** | `src/onfly_report/services/report_builder.py` |
| **Teste** | `tests/test_top_hotels.py::test_top_hotels_are_ranked_descending` (fornecido) |

### O que acontecia

```python
ranked_hotels = sorted(hotels.items(), key=lambda item: (item[1]["amount"], item[0]))
```

Ordenação ascendente. Como `top_hotels` é truncado em `--top` itens, o relatório
publicava os hotéis de **menor** faturamento e omitia os maiores — o oposto de
um ranking.

### Evidência

Teste fornecido com quatro hotéis de 1000, 900, 800 e 700 e `--top 3`: esperava
`[H01, H02, H03]` e obtinha `[H04, H03, H02]`. **Nenhum teste novo foi criado.**

### Correção

```diff
-        ranked_hotels = sorted(hotels.items(), key=lambda item: (item[1]["amount"], item[0]))
+        ranked_hotels = sorted(hotels.items(), key=lambda item: (-item[1]["amount"], item[0]))
```

**`reverse=True` não resolveria.** Inverter a ordenação inteira inverteria
também o desempate, e R18 pede valor decrescente com `hotel_id` **ascendente**.
Negar só o valor na chave mantém os dois critérios em sentidos opostos, como a
regra exige:

| chave | H01=100, H02=200, H03=100 | veredito |
|-|-|-|
| `(amount, id)` (antes) | `[H01, H03, H02]` | valor ascendente: errado |
| `(amount, id)` + `reverse=True` | `[H02, H03, H01]` | empate descendente: errado |
| `(-amount, id)` (adotada) | `[H02, H01, H03]` | correto |

A negação opera sobre o `Decimal` exato, conforme a decisão **A02**, e não sobre
o valor arredondado. Verificado com valores sub-centavo: com
H05=100.004, H04=100.001, H02=200 e H01=H03=100, o ranking sai
`[H02, H05, H04, H01, H03]` — valor exato decrescente, e o único empate real
desempatado por `hotel_id` ascendente.

### Verificação

- `tests/test_top_hotels.py`: vermelho `['H04','H03','H02']`, depois verde.
- `pytest -q`: **5 passed**. Toda a suíte fornecida passa.
- `ruff check .`: `All checks passed!`
- **Oráculo: `SEM DIVERGENCIAS (35 campos conferidos)`.** A amostra bate campo a
  campo com o README, incluindo a ordem e os nomes do `top_hotels`.
- Verificação cruzada no dataset completo: o `top_hotels` do CLI
  (H06 45165.46, H10 45041.69, H12 41647.69, H07 39920.52, H11 37455.69) é
  idêntico ao ranking calculado de forma independente na Fase 3, antes de
  qualquer correção.
