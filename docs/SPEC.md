# SPEC — regras derivadas do README

Fonte única: `README.md`. Este documento só **reorganiza** o README em regras
numeradas e verificáveis; onde o README cala, a lacuna vai para "Ambiguidades",
não para uma decisão minha.

Legenda de "como verificar": `[fornecido]` = teste já existente em `tests/`;
`[amostra]` = tabelas entre `<!-- AMOSTRA:INICIO -->` e `<!-- AMOSTRA:FIM -->`;
`[criar]` = precisa de teste novo.

---

## Status

### R01 — Só `CONFIRMED` é faturável

> "Só `CONFIRMED` é faturável."

Módulo: `services/status_policy.py` (`is_billable`).
Verificar: `[fornecido]` `tests/test_status_rules.py`; `[amostra]` EX-05 é
`NO_SHOW` de 300.00 BRL e 1 noite e **não** aparece nos totais.

### R02 — Não faturáveis contam só nas contagens

> "`CANCELLED` e `NO_SHOW` contam em `total_reservations` e nas contagens por
> status, mas não entram em noites, valores, `by_month` nem `top_hotels`."

Módulo: `services/report_builder.py` (contagem antes do filtro).
Verificar: `[fornecido]` `tests/test_status_rules.py`; `[amostra]` 12 reservas,
9 confirmadas, e `by_month`/`top_hotels` só somam as 9.

---

## Noites

### R03 — Fórmula de `room_nights`

> "`room_nights = (checkout_date - checkin_date).days * rooms`"

Módulo: `services/stay_calculator.py` (`calculate_room_nights`).
Verificar: `[amostra]` EX-03, 2025-01-28 para 2025-02-02 com 2 quartos = 5 x 2 =
10 noites; `[criar]` para `rooms > 1` isolado.

### R04 — Diferença não inclusiva, válida na virada de mês/ano

> "A diferença é não inclusiva: check-in 10/01 e check-out 13/01 = 3 noites.
> Vale também na virada de mês/ano."

Módulo: `services/stay_calculator.py`.
Verificar: `[fornecido]` `tests/test_nights.py` (01-30 para 02-02 = 3);
`[criar]` virada de ano (2024-12-30 para 2025-01-02 = 3).

---

## Câmbio

### R05 — `amount` está na moeda de `currency`

> "`amount` está na moeda de `currency`."

Módulo: `services/row_parser.py`.

### R06 — Conversão é multiplicação

> "Converta com `amount * rate_to_brl`, usando a tabela `data/taxas_cambio.csv`."

Módulo: `services/currency_converter.py` (`convert_to_brl`).
Verificar: `[fornecido]` `tests/test_currency.py` (100 BRL + 100 USD = 642.00);
`[amostra]` EX-02, 200 USD x 5.42 = 1084.00.

### R07 — Toda moeda do dataset tem taxa

> "Todas as moedas do dataset têm taxa."

Módulo: `repositories/csv_rate_repository.py`.
Confirmado nos dados: `reservas_hoteis.csv` usa BRL, EUR e USD; as três estão em
`taxas_cambio.csv`. Moeda ausente é, portanto, erro de arquivo — não linha a
descartar (ver A04).

---

## Totais

### R08 — `total_reservations` conta o arquivo inteiro

> "`total_reservations` = número de reservas no arquivo."

Módulo: `repositories/csv_reservation_repository.py` + `report_builder`.
Verificar: `[amostra]` 12; `[criar]` `data/reservas_hoteis.csv` tem 300 linhas
de dados e o relatório precisa refletir as 300.

### R09 — Contagens por status

> "`confirmed_reservations`, `cancelled_reservations` e `no_show_reservations` =
> contagens por status."

Módulo: `services/report_builder.py`.
Verificar: `[fornecido]` `tests/test_status_rules.py`; `[amostra]` 9 / 2 / 1.

### R10 — Agregados financeiros só com `CONFIRMED`

> "`total_room_nights`, `total_amount_brl` e `average_nightly_rate_brl` usam
> apenas `CONFIRMED`."

Módulo: `services/report_builder.py`.
Verificar: `[fornecido]` `tests/test_regression_report.py`; `[amostra]` 28 /
7566.00 / 270.21.

---

## Ordem do processamento

### R11 — Pipeline fixo

> "`ler -> converter tipos -> contar status -> filtrar CONFIRMED -> agregar`"

Módulo: `services/report_builder.py` (`build`).
Consequência verificável: a contagem por status enxerga **todas** as linhas, e a
agregação enxerga só as confirmadas.

---

## Exatidão

### R12 — `Decimal` sempre, `float` nunca

> "Use `Decimal`, nunca `float`, no dinheiro."

Módulos: `services/currency_converter.py`, `services/report_builder.py`,
`services/row_parser.py`.
Verificar: `[criar]` valor cuja ida e volta por `float` perde precisão.

### R13 — Soma exata, arredondamento só na serialização

> "Some os valores exatos e arredonde **só na serialização**, para 2 casas, com
> half-up."

Módulo: `services/report_builder.py` (`format_money`).
Verificar: `[criar]` dois valores que, arredondados antes, dariam outro total.

### R14 — Média e o caso sem noites

> "`average_nightly_rate_brl = total_amount_brl / total_room_nights`; sem noites,
> `"0.00"`."

Módulo: `services/report_builder.py`.
Verificar: `[fornecido]` `tests/test_regression_report.py` (308.40);
`[amostra]` 7566 / 28 = 270.2142... para 270.21; `[criar]` zero noites.

### R15 — Datas civis

> "Check-in/check-out são datas civis (`YYYY-MM-DD`)."

Módulo: `services/row_parser.py` (`date.fromisoformat`).
Sem fuso, sem hora: a aritmética de noites é de calendário.

### R16 — `generated_at`

> "`generated_at` usa offset fixo `-03:00` e é ignorado na comparação."

Módulo: `services/report_builder.py` (`FIXED_OFFSET`).

---

## Ordenação

### R17 — `by_month` por `month` ascendente

> "`by_month`: `month` ascendente."

Módulo: `services/report_builder.py`.
Verificar: `[amostra]` 2025-01 antes de 2025-02.

### R18 — `top_hotels` por `total_brl` decrescente, empate por `hotel_id` ascendente

> "`top_hotels`: `total_brl` decrescente; empate por `hotel_id` ascendente."

Módulo: `services/report_builder.py`.
Verificar: `[fornecido]` `tests/test_top_hotels.py`; `[amostra]` H01 1200,
H02 1084, H12 1000, H10 900, H09 882, nessa ordem; `[criar]` empate (ver A02).

---

## Contrato do CLI

### R19 — Comando e argumentos imutáveis

> "O comando e os argumentos do CLI." (seção "O que não pode mudar")

Módulo: `cli.py` (`build_parser`).
`--input` e `--rates` obrigatórios; `--output` e `--top` opcionais.

### R20 — Padrão de `--output`

> Tabela do contrato: `--output` | não | `output/report.json`

Módulo: `cli.py`.

### R21 — `--top` padrão 5, inteiro >= 1

> Tabela do contrato: `--top` | não | `5` (inteiro >= 1)

Módulo: `cli.py`.
Verificar: `[criar]` `--top 0` e `--top -1` recusados (ver A07).

### R22 — Códigos de saída

> "Códigos de saída: `0` sucesso, `2` entrada/argumento inválido, `1` erro
> inesperado."

Módulo: `cli.py` (`main`).
Verificar: `[criar]` arquivo inexistente para 2; `--top 0` para 2; sucesso para 0.

### R23 — O CLI cria o diretório de saída

> "O relatório é gravado em `output/report.json`; o CLI cria o diretório."

Módulo: `cli.py`.
Verificar: `[criar]` `--output` em diretório inexistente.

### R24 — Resumo no stdout

> "Um resumo é impresso no stdout."

Módulo: `cli.py`. Log vai para stderr (`logging_config.py`), stdout fica para o
resumo.

---

## Schema do relatório

### R25 — Estrutura exata

> Bloco JSON do README: `report_version`, `generated_at`, `summary` (7 campos),
> `by_month[]` (`month`, `reservations`, `room_nights`, `total_brl`),
> `top_hotels[]` (`hotel_id`, `hotel_name`, `room_nights`, `total_brl`).

Módulo: `services/report_builder.py` (`build`).

### R26 — Dinheiro é string com 2 casas

> "Dinheiro é string com exatamente 2 casas (`"1234.50"`), sem separador de
> milhar."

Módulo: `services/report_builder.py` (`format_money`).
Contagens (`reservations`, `room_nights`, `total_reservations`...) são inteiros
JSON, não strings.

### R27 — `report_version` é sempre `"1.0"`

> "`report_version` é sempre `"1.0"`."

### R28 — Tamanho de `top_hotels`

> "`top_hotels` tem `--top` itens (ou menos, se houver menos hotéis)."

Verificar: `[fornecido]` `tests/test_top_hotels.py` com `top=3`; `[criar]`
`--top` maior que o número de hotéis (ver A06).

### R29 — `by_month` usa o mês do check-in

> "`by_month` usa o mês do check-in."

Verificar: `[amostra]` EX-03 (check-in 2025-01-28, check-out 2025-02-02) cai
inteira em 2025-01 (ver A01).

### R30 — Nomes, tipos e semântica dos campos são imutáveis

> "Não altere nomes, tipos ou semântica dos campos."

---

# Ambiguidades

Nenhuma decidida por mim. As resolvidas pela amostra vêm com a conta e ficam
marcadas para confirmação; as demais aguardam decisão.

### A01 — Estadia que cruza o mês: mês do check-in ou rateio por noite?

Leituras: (a) a reserva inteira entra no mês do check-in; (b) as noites são
rateadas entre os meses que a estadia ocupa.

Conta: EX-03 tem check-in 2025-01-28, check-out 2025-02-02, 2 quartos, 800.00
BRL, 10 noites. Na leitura (a), 2025-01 fica com 25 noites e 6684.00 e 2025-02
com 3 noites e 882.00 — **exatamente o que o README manda**. Na leitura (b),
2025-01 ficaria com 8 noites da EX-03 (28 a 31) e 2025-02 com 2, mudando as duas
linhas da tabela.

**Resolvida pela amostra — confirmar: leitura (a).** R29 já reflete isso.

### A02 — Empate em `top_hotels`: sobre o valor exato ou o arredondado?

Leituras: (a) desempatar quando os `Decimal` exatos forem iguais; (b) desempatar
quando as strings de 2 casas forem iguais.

Impacto: dois hotéis separados por menos de um centavo (por exemplo 1000.004 e
1000.001) saem na ordem de valor em (a) e na ordem de `hotel_id` em (b). A
amostra não tem empate algum. **Aguardando decisão.**

Observação: o dataset real pode ou não produzir empate exato — vou medir isso na
auditoria, antes de a decisão custar alguma coisa.

### A03 — A média divide o total exato ou o total já arredondado?

Leituras: (a) `total_amount_brl` exato dividido pelas noites, arredondando só no
fim; (b) o total já arredondado para 2 casas dividido pelas noites.

R13 ("arredonde só na serialização") favorece (a), mas a frase de R14 cita o
nome do campo serializado, o que dá margem a (b).

Impacto na amostra: nenhum — 7566 é exato nas duas leituras, e 7566/28 =
270.2142... vira 270.21 de qualquer jeito. Separar as leituras exige um caso cujo
total tenha mais de 2 casas decimais.

**Aguardando decisão** (recomendo (a), por R13).

### A04 — Linha com moeda fora da tabela de câmbio

R07 garante que não acontece no dataset, e o docstring de `RowParser` diz que
"falhas de formato são erro de arquivo, não dado a ser descartado". Leituras:
(a) erro de entrada, exit 2; (b) ignorar a linha; (c) estourar erro inesperado,
exit 1. Afeta só robustez, nunca os números do dataset fornecido.

**Aguardando decisão** (recomendo (a), coerente com o docstring e com R22).

### A05 — Status fora de `CONFIRMED` / `CANCELLED` / `NO_SHOW`

O dataset só tem os três (confirmei: 235 / 31 / 34 em 300 linhas) e a amostra
também. Leituras: (a) conta em `total_reservations` e em nenhum bucket; (b) erro
de entrada, exit 2. O README diz que `total_reservations` é "o número de reservas
no arquivo", o que sustenta (a). **Aguardando decisão.**

### A06 — `--top` maior que o número de hotéis

R28 diz "ou menos, se houver menos hotéis", então a lista encurta. O que fica em
aberto é se vale truncar em silêncio ou avisar em stderr. Sem impacto no schema.

**Aguardando decisão** (recomendo truncar em silêncio).

### A07 — `--top` inválido: qual exit code e por qual caminho?

R21 exige inteiro >= 1 e R22 manda exit 2 para argumento inválido. `--top abc` e
`--top 0` precisam ambos sair com 2. O README não diz se a mensagem vai para
stderr nem se o texto importa.

**Aguardando decisão** (recomendo: ambos exit 2, mensagem em stderr, texto livre).

### A08 — Arredondamento por bucket contra soma dos buckets

Cada linha de `by_month` e `top_hotels` arredonda seu próprio subtotal, então a
soma das linhas pode diferir do `total_amount_brl` em centavos. Leituras:
(a) arredondar cada bucket de forma independente (o que R13 implica); (b) forçar
que a soma feche com o total. Na amostra não há conflito: 6684.00 + 882.00 =
7566.00.

**Aguardando decisão** (recomendo (a)).

### A09 — `generated_at`: relógio real ou valor fixo?

R16 fixa o offset `-03:00` e manda ignorar o campo na comparação, mas não diz se
o horário é o de execução. Sem impacto na avaliação automática.

**Aguardando decisão** (recomendo o relógio real com offset fixo, como já está).
