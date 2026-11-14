# onfly-report — instruções do projeto

CLI que consolida reservas de hotel em JSON. `README.md` é a especificação;
`docs/SPEC.md` é a spec destrinchada em regras R##.

## Ambiente e comandos canônicos (PowerShell 5.1, Windows)

```powershell
python -m venv .venv                 # criar o venv
.\.venv\Scripts\Activate.ps1         # ativar
pip install -r requirements-dev.txt  # pytest 8.3.4 + ruff 0.8.4

pytest -q                            # pythonpath=["src"] já vem do pyproject
ruff check .
ruff format --check .                # só se solicitado; não formatar em massa

$env:PYTHONPATH = "src"; python -m onfly_report `
  --input data/reservas_hoteis.csv `
  --rates data/taxas_cambio.csv `
  --output output/report.json
```

PowerShell 5.1 não tem `&&`, `||`, `?:` nem `??`. Encadear: `A; if ($?) { B }`.

## Invioláveis

- Não editar `tests/**` nem `data/**` (trava em `.claude/settings.json`).
  Teste fornecido que pareça errado: reportar ao usuário, nunca contornar.
- Não mudar comando, argumentos, códigos de saída, schema nem semântica do relatório.
- Nunca renomear campos do relatório nem identificadores já existentes.
- Dinheiro: `Decimal` sempre, `float` nunca. Arredondar só na serialização,
  2 casas, `ROUND_HALF_UP`.

## Processo

- Diagnóstico e conserto são etapas separadas. A auditoria não edita nada.
- Nenhuma correção sem teste vermelho antes, falhando pelo motivo certo.
- Um defeito por vez: diff + mensagem de commit propostos, e PARAR para revisão.
- Nunca rodar `git commit`, `git push` nem `git reset`. O commit é do usuário.
- Ambiguidade na spec: listar as leituras possíveis e esperar a decisão do usuário.
- Antes de agir, ler o arquivo. Não presumir conteúdo.
- Discordar com evidência quando o usuário estiver errado.
- Sem mudança colateral: não reformatar, não arrumar lint fora das linhas corrigidas.

## Convenções de código

- Python 3.11+, type hints em tudo que for novo ou tocado.
- `from __future__ import annotations` no topo de arquivo novo ou tocado.
- ruff: `line-length = 120`, regras `E`, `F`, `I` (já no `pyproject.toml`).
- Português em docs, skills, comentários, docstrings e identificadores NOVOS.
  O que já existe em inglês permanece como está.

## Skills

- `audit` — varredura read-only do código contra `docs/SPEC.md`.
- `fix-bug` — corrige UM F## já triado pelo usuário.
- `verify` — portão binário: ruff + pytest + amostra do README.
