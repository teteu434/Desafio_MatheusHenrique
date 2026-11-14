# Entrega — onfly-report

Consolidador de reservas de hotel em JSON. O CLI entregue parte do commit
inicial `5bb6367`, onde **seis defeitos** produziam números errados, e chega a um
relatório que bate campo a campo com a amostra de validação do `README.md`.

| | antes (commit `5bb6367`) | depois |
|-|-|-|
| `pytest -q` | 5 failed | **34 passed** |
| `ruff check .` | All checks passed | All checks passed |
| Amostra do README | 22 divergências em 35 campos | **SEM DIVERGENCIAS (35 campos)** |
| `data/reservas_hoteis.csv` | 200 reservas, −1393 noites, R$ 193.218,53 | **300 reservas, 1347 noites, R$ 396.170,00** |

Relatório final do dataset completo:

```json
{
  "total_reservations": 300, "confirmed_reservations": 235,
  "cancelled_reservations": 31, "no_show_reservations": 34,
  "total_room_nights": 1347, "total_amount_brl": "396170.00",
  "average_nightly_rate_brl": "294.11"
}
```

---

## 1. Resultado do `pytest`

```
34 passed
```

| arquivo | testes | origem |
|-|-|-|
| `tests/test_currency.py` | 1 | fornecido |
| `tests/test_nights.py` | 1 | fornecido |
| `tests/test_regression_report.py` | 1 | fornecido |
| `tests/test_status_rules.py` | 1 | fornecido |
| `tests/test_top_hotels.py` | 1 | fornecido |
| `tests/test_leitura_completa.py` | 1 | novo — R08 |
| `tests/test_cambio_exatidao.py` | 2 | novo — R12 e R13 |
| `tests/test_regras_extras.py` | 9 | novo — R03, R04, R13, R14, R18, R28 |
| `tests/test_contrato.py` | 10 | novo — R19 a R24 |
| `tests/test_moedas.py` | 7 | novo — A04 e O11 |

Os **5 testes fornecidos estão inalterados** — a trava em `.claude/settings.json`
nomeia os 6 arquivos entregues (os 5 testes mais `helpers.py`) e nega `Edit`,
`Write` e `MultiEdit` em cada um. Os 29 testes novos vivem em arquivos novos,
como o `README.md` do desafio autoriza.

## 2. Como validar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

pytest -q                 # 34 passed
ruff check .              # All checks passed!

# amostra de validação do README
$env:PYTHONPATH = "src"; python -m onfly_report `
  --input data/exemplo-validacao.csv --rates data/taxas_cambio.csv `
  --output output/exemplo.json
python tools/conferir_amostra.py output/exemplo.json
# SEM DIVERGENCIAS (35 campos conferidos, generated_at ignorado)

# dataset completo
$env:PYTHONPATH = "src"; python -m onfly_report `
  --input data/reservas_hoteis.csv --rates data/taxas_cambio.csv `
  --output output/report.json
# Reservas: 300 | Confirmadas: 235 | Noites: 1347 | Total BRL: 396170.00
```

`tools/conferir_amostra.py` é um oráculo escrito **antes** de qualquer correção:
ele lê as tabelas do próprio `README.md`, entre os marcadores
`AMOSTRA:INICIO`/`AMOSTRA:FIM`, e compara com o JSON gerado campo a campo,
inclusive o tipo de cada um — inteiro JSON contra string de dinheiro, por R26.
Nada é transcrito à mão: se a amostra do README mudasse, a conferência
acompanharia sozinha. `generated_at` é ignorado, conforme R16.

Ambiente usado: Windows 11 com PowerShell 5.1, venv com **Python 3.13.14** (a
3.11 não estava disponível na máquina; o `pyproject.toml` pede `>=3.11` e o CLI
usa apenas a biblioteca padrão), pytest 8.3.4 e ruff 0.8.4.

## 3. Defeitos corrigidos

Um commit por defeito, na ordem em que foram corrigidos, com a causa raiz em uma
frase:

| # | Regra violada | Onde | Causa raiz | Commit |
|-|-|-|-|-|
| F06 | R08 | `repositories/csv_reservation_repository.py:47` | A leitura tinha um limite fixo de 200 linhas que truncava o arquivo em silêncio. | `384912d` |
| F02 | R03, R04 | `services/stay_calculator.py:10` | Subtraía o campo `.day` de cada data em vez da diferença entre as datas. | `5b13185` |
| F03 | R06 | `services/currency_converter.py:11` | A conversão dividia pela taxa onde o README manda multiplicar. | `ee76aab` |
| F04 | R12 | `services/currency_converter.py:11` | O dinheiro saía do domínio `Decimal` e voltava via `str(float)`, perdendo exatidão antes do arredondamento. | `a28197b` |
| F01 | R01, R02, R10 | `services/status_policy.py:8` | O predicado de faturabilidade negava apenas `CANCELLED` em vez de afirmar `CONFIRMED`, deixando `NO_SHOW` entrar nos totais. | `dbd655e` |
| F05 | R18 | `services/report_builder.py:91` | A chave de ordenação não invertia o valor, publicando o ranking do menor para o maior. | `50b3cb9` |

A ordem não foi arbitrária. **F06 veio primeiro** porque era o único que mudava o
conjunto de dados sob todos os outros: enquanto 100 linhas estivessem fora, os
números dos demais defeitos seriam instáveis. Os outros cinco são independentes
entre si.

### F06 — leitura truncada em 200 linhas

`data/reservas_hoteis.csv` tem 300 linhas de dados; 100 reservas, 82 delas
`CONFIRMED`, nunca chegavam ao agregador, e o CLI saía com código 0 sem avisar.
Correção: remoção das duas linhas do limite. Depois do patch as contagens fecham
com o arquivo — 235 + 31 + 34 = 300.

### F02 — noites calculadas pelo dia do mês

`.day` é o dia do mês, de 1 a 31, então a conta só acertava quando check-in e
check-out caíam no mesmo mês. Para 2025-01-30 → 2025-02-02 dava `(2 − 30) × 1 =
−28`. No dataset, **93 das 300 linhas cruzam mês**, o que explica como um defeito
tão grave sobrevivia com um único teste vermelho. Como o total ficava negativo,
ele caía no guarda `total_nights > 0` e a média era publicada como `"0.00"` — um
segundo campo errado de tabela. Correção: `(checkout - checkin).days * rooms`.

### F03 — câmbio dividia pela taxa

100 USD com taxa 5,42 viravam `18.45` em vez de `542.00`. Moedas com taxa
`1.000000` (BRL) passavam ilesas, o que mascarava o defeito em qualquer teste que
só usasse reais. Correção: multiplicar.

### F04 — dinheiro passava por `float`

Corrigido em commit separado do F03, embora na **mesma linha**, porque viola outra
regra e exige outra evidência. Com a multiplicação já certa, 19 das 235 linhas
`CONFIRMED` ainda divergiam do `Decimal` exato. A evidência decisiva é um caso de
fronteira de meio centavo, com uma reserva só:

```
0.75 USD × 5.42 = 4.065 exatos        →  half-up: "4.07"
caminho do float: 4.0649999999999995  →  half-up: "4.06"
```

Correção: `amount * rate`, direto em `Decimal`. Não resta nenhuma ocorrência de
`float` em `src/`.

### F01 — `NO_SHOW` entrava nos totais

A regra tem **dois** status não faturáveis e o predicado excluía só um. As
contagens por status nunca estiveram erradas, porque o pipeline conta antes de
filtrar, conforme R11; o defeito estava apenas no filtro. Correção:
`status == "CONFIRMED"` — afirmar o faturável em vez de negar os não faturáveis,
o que também resolve o caso de status desconhecido (decisão A05).

### F05 — ranking invertido

Como `top_hotels` é truncado em `--top` itens, o relatório publicava os hotéis de
**menor** faturamento e omitia os maiores. Correção: `key=(-amount, hotel_id)`.
**`reverse=True` não serviria**: inverteria junto o desempate, e R18 pede valor
decrescente com `hotel_id` ascendente.

| chave | H01=100, H02=200, H03=100 | veredito |
|-|-|-|
| `(amount, id)` (defeito) | `[H01, H03, H02]` | valor ascendente: errado |
| `(amount, id)` + `reverse=True` | `[H02, H03, H01]` | empate descendente: errado |
| `(-amount, id)` (adotada) | `[H02, H01, H03]` | correto |

## 4. Mudanças de comportamento (não são defeitos)

Separadas dos F## de propósito, em commits próprios: nenhuma corrige violação de
regra nos dados fornecidos e **nenhuma altera um número entregue** — a amostra
segue `SEM DIVERGENCIAS` e o dataset completo segue em R$ 396.170,00.

**A04 — moeda fora da tabela de câmbio passa a ser erro de entrada.** Medi o CLI
com cada campo malformado: `checkin_date`, `rooms` e `amount` inválidos saíam com
2 e diagnóstico claro; `currency` sem taxa saía com **1** e traceback cru, porque
a consulta da taxa acontecia fora do `try` do `RowParser`. Agora `convert_to_brl`
levanta `InputFileError` e o `ReportBuilder` acrescenta a linha física, que o
conversor não conhece:

```
antes:  erro inesperado ao gerar o relatório + KeyError: 'GBP'                    (exit 1)
depois: falha ao ler a entrada: linha 2: moeda 'GBP' sem taxa na tabela de câmbio (exit 2)
```

A validação vive na conversão, que só alcança reservas `CONFIRMED` — uma reserva
cancelada com moeda exótica não derruba o relatório, porque por R02 ela não entra
em valor nenhum. Coberto por teste.

**O11 — `currency` normalizada simetricamente.** `CsvRateRepository` indexa a
tabela com `.strip().upper()`, mas o `RowParser` lia a moeda só com `.strip()`:
`usd` procurava a chave `'usd'` numa tabela indexada por `'USD'`. O espaço já
funcionava; só a caixa quebrava. Decidi normalizar a moeda e **manter o `status`
sem `.upper()`** — moeda é chave de busca numa tabela que o próprio programa
normaliza, enquanto status é literal de domínio definido pelo README, com o caso
desconhecido já resolvido em A05.

## 5. Decisões sobre os pontos omissos do README

O `README.md` é a especificação, mas cala em alguns pontos. Em vez de escolher em
silêncio, cada lacuna foi listada com as leituras possíveis, medida contra os
dados e decidida explicitamente, com registro em `docs/SPEC.md`.

| # | Questão | Decisão | Impacto medido |
|-|-|-|-|
| A01 | Estadia que cruza o mês | Reserva inteira no mês do check-in | Fechada pela amostra: só assim EX-03 produz 6684.00 / 882.00 |
| A02 | Empate em `top_hotels`: valor exato ou arredondado | Valor exato | Nenhum: os 12 hotéis têm 12 totais distintos; a menor distância no top 6 é R$ 123,76 |
| A03 | Média sobre o total exato ou o arredondado | Exato, por R13 | Nenhum: 294.11 nas duas leituras |
| A04 | Moeda sem taxa | Erro de entrada, exit 2 | Só robustez; o dataset não exercita |
| A05 | Status fora dos três conhecidos | Conta em `total_reservations`, em nenhum bucket | Só robustez; o dataset tem 235 / 31 / 34 |
| A06 | `--top` maior que o nº de hotéis | Truncar em silêncio | É o que R28 já manda |
| A07 | `--top` inválido | `0`, `-1` e `abc` todos com exit 2 e mensagem em stderr | Já era o comportamento; virou teste |
| A08 | Arredondar cada bucket ou forçar a soma fechar | Cada bucket independente, por R13 | Ver "Limites conhecidos" |
| A09 | `generated_at` | Relógio real com offset fixo `-03:00` | Nenhum; o campo é ignorado na comparação |

Três observações sobre o código não viraram defeito, e o porquê está medido:

- **O10** — o `hotel_name` publicado é o da última linha daquele hotel. Latente:
  os 12 `hotel_id` do dataset têm exatamente um nome cada.
- **O11** — a assimetria de caixa na moeda. Virou mudança de comportamento (seção 4).
- **O12** — um mês só com reservas canceladas sumiria do `by_month`. **Não é
  defeito: é o que R02 exige.** A amostra prova numericamente — `exemplo-validacao.csv`
  tem 11 check-ins em janeiro, três deles não confirmados, e o README manda
  `reservations: 8`. Contar os 11 quebraria a validação; "corrigir" aqui seria
  introduzir um defeito.

## 6. Como investiguei

O princípio do processo foi um só: **diagnóstico e conserto são etapas
separadas**, e nada é corrigido sem antes existir um teste vermelho falhando pelo
motivo certo.

1. **Baseline antes de tocar em qualquer coisa** (`docs/baseline/`): saída do CLI,
   JSON gerado, `pytest`, `ruff` e códigos de saída do commit inicial. Sem isso,
   "melhorou" seria opinião.
2. **Spec destrinchada** (`docs/SPEC.md`): o README virou 30 regras numeradas
   R01–R30, cada uma com a citação de origem, o módulo responsável e como
   verificar. Onde o README calava, a lacuna virou item de ambiguidade — para
   decisão explícita, não escolha silenciosa.
3. **Oráculo** (`tools/conferir_amostra.py`), escrito antes das correções, lendo a
   amostra do próprio README.
4. **Auditoria read-only** (`docs/AUDITORIA.md`): varredura percorrendo as
   **regras**, não os arquivos, para que nenhuma ficasse sem cobertura. Saldo: 6
   defeitos, 21 regras conformes, nenhuma sem cobertura, mais duas suspeitas que
   não viraram achado por falta de evidência (BOM no CSV de entrada; `strftime`
   contra `isoformat`). Nenhum arquivo foi modificado nesta fase.
5. **Triagem**: ordem dos consertos e severidade. A severidade de F04 subiu de
   média para alta — o argumento de que `float` e `Decimal` serializam igual
   *neste* dataset classifica pela amostra, não pelo defeito, e o README avisa que
   testes adicionais são considerados. A fronteira de meio centavo encontrada
   depois (0.75 USD) confirmou a reclassificação.
6. **Correção, um defeito por commit**, cada um com teste vermelho antes, patch
   mínimo, suíte verde e conferência na amostra.
7. **Endurecimento** (A04 e O11) e cobertura das regras que funcionavam mas não
   tinham teste algum — R03, R04, R13, R14, R18, R28 e o contrato do CLI inteiro.
8. **Portões**: `ruff`, `pytest`, oráculo da amostra e `/code-review`.

### O que o `/code-review` devolveu

Seis achados, cada um verificado em vez de aceito de cara:

- **A validação mais forte** foi o revisor reimplementar o pipeline inteiro de
  forma independente e comparar com `output/report.json` nas 300 linhas:
  `summary`, `by_month` e `top_hotels` batem exatamente.
- **Um achado não procedia** e foi recusado com teste: alegava que a trava de
  permissão por arquivo perdia a grafia `./tests/...`; as duas grafias foram
  tentadas e ambas recusadas pelo matcher.
- **Dois eram legítimos e foram corrigidos**: faltava teste para o desempate de
  R18 — uma regressão com `reverse=True` passaria nos 26 testes de então, porque
  nem a amostra nem o dataset têm empate — e o oráculo tinha um ramo morto que
  deixava passar `"total_reservations": "12"` como string, furando R26.
- **Três eram pendências já conhecidas e registradas**: A04/O11, este
  `README-ENTREGA.md` e um commit faltante.

## 7. Limites conhecidos

Honestidade vale mais que uma lista limpa:

- **O `by_month` do dataset completo soma R$ 396.170,01 contra os R$ 396.170,00 de
  `total_amount_brl`.** Um centavo. É consequência direta da decisão A08: por R13,
  cada bucket arredonda o próprio subtotal exato e nada é arredondado antes.
  Forçar o fechamento exigiria escolher arbitrariamente um mês para absorver a
  diferença, o que contraria R13 e inventa semântica que o README não pede. Na
  amostra o conflito não existe: 6684.00 + 882.00 = 7566.00.
- **Nenhuma varredura de segurança foi executada.** Dispensa deliberada, não
  portão que passou: o CLI não tem rede, credencial, sessão, dado real nem
  persistência compartilhada — lê dois CSV, grava um JSON e encerra. A superfície
  que resta é o contrato do próprio CLI, coberta por `tests/test_contrato.py`. A
  dispensa vale para este desafio e não deve ser reaproveitada em código que ganhe
  rede ou dados reais.
- **O10 segue latente**: se o mesmo `hotel_id` aparecesse com nomes diferentes, o
  nome publicado dependeria da ordem das linhas. Não ocorre nos dados fornecidos.

## 8. Mapa dos arquivos de apoio

| caminho | conteúdo |
|-|-|
| `docs/SPEC.md` | As 30 regras R## derivadas do README e as decisões A01–A09 / O10–O12, cada uma com a análise que levou a ela |
| `docs/AUDITORIA.md` | A auditoria read-only: 6 achados com evidência, 21 regras conformes, suspeitas descartadas |
| `docs/baseline/` | Estado inicial completo do commit `5bb6367`, para comparação |
| `tools/conferir_amostra.py` | Oráculo que confere o JSON gerado contra a amostra do README |
| `entrega/uso-de-ia/` | Export das sessões e declaração de uso de IA |
