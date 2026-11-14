---
name: verify
description: Portão de qualidade com veredito binário PASSA / NÃO PASSA — roda ruff check, pytest -q e o CLI sobre data/exemplo-validacao.csv, comparando campo a campo com as tabelas da amostra do README. Use antes de propor commit, ao fechar uma fase, ou quando o usuário pedir "verificar", "rodar o portão" ou "está pronto?". NÃO use para diagnosticar defeitos (use audit).
---

# verify — portão binário

## Procedimento

1. **Lint**: `ruff check .` — registrar a saída.
2. **Testes**: `pytest -q` — registrar a saída completa, inclusive a linha de
   resumo com as contagens.
3. **Amostra**: rodar o CLI sobre a amostra de validação.

   ```powershell
   $env:PYTHONPATH = "src"; python -m onfly_report `
     --input data/exemplo-validacao.csv `
     --rates data/taxas_cambio.csv `
     --output output/exemplo.json
   ```

   Registrar também o código de saída (`$LASTEXITCODE`), que precisa ser `0`.
4. **Comparação com o oráculo**:
   - Se existir `tools/conferir_amostra.py` (criado na Fase 2), **usar o script**
     e reportar a saída dele. Não refazer a conferência à mão.
   - Se não existir, comparar manualmente `output/exemplo.json` com as tabelas
     entre `<!-- AMOSTRA:INICIO -->` e `<!-- AMOSTRA:FIM -->` do `README.md`:
     os 7 campos de `summary`, cada linha de `by_month` (`month`, `reservations`,
     `room_nights`, `total_brl`) e cada linha de `top_hotels` (`hotel_id`,
     `hotel_name`, `room_nights`, `total_brl`), **na ordem em que aparecem**.
   - `generated_at` é ignorado na comparação. Todo o resto conta, inclusive a
     ordem das listas e o número de itens.
   - Dinheiro compara como string (`"1200.00"`), não como número.

## Veredito

Começar a saída com uma única linha: `PASSA` ou `NÃO PASSA`.

`PASSA` exige as quatro condições:

- `ruff check .` sem erro;
- `pytest -q` sem falha nem erro;
- CLI com código de saída `0` sobre a amostra;
- zero divergências contra as tabelas do README.

Qualquer uma falhando, o veredito é `NÃO PASSA`. Não existe "passa com
ressalvas", e lint pré-existente não vira exceção: se `ruff check .` acusa, o
portão fecha e o usuário decide o que fazer.

Depois do veredito, listar as divergências, uma por linha, no formato:

```
<caminho do campo>: esperado <X>, obtido <Y>
```

Exemplo: `by_month[0].total_brl: esperado 6684.00, obtido 6584.00`.

Se não houver divergência, escrever `Sem divergências.`

## Pronto quando

- As três execuções foram feitas **nesta sessão**, com as saídas coladas — nunca
  reaproveitar resultado de execução anterior nem presumir que "deve passar".
- O veredito binário está na primeira linha.
- Toda divergência está listada no formato acima, ou consta `Sem divergências.`
