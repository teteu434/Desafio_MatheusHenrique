---
name: fix-bug
description: Corrige UM defeito F## já triado e autorizado pelo usuário, no ciclo teste vermelho → patch mínimo → verde → suíte → docs/DEFEITOS.md → mensagem de commit proposta. Use quando o usuário mandar corrigir um F## específico da Fase 5. NÃO use para procurar defeitos (use audit) nem sem autorização explícita do F##.
---

# fix-bug — um defeito por vez

## Pré-condições (checar antes de qualquer coisa)

- O usuário nomeou **um** F## e autorizou a correção.
- O F## tem entrada na tabela da auditoria, com R## e evidência.
- A ambiguidade de spec correspondente, se houver, já foi decidida pelo usuário.

Faltando qualquer uma: parar e perguntar. Não corrigir dois defeitos "porque
estão na mesma linha" — se o patch mínimo de F01 não exige tocar F02, não toque.

## Procedimento

1. **Reler** o arquivo que será tocado, inteiro. Não editar de memória.
2. **Teste vermelho primeiro.** Escrever o teste em `tests/test_<assunto>.py`,
   arquivo novo (nunca editar os testes fornecidos). O teste nomeia a regra
   violada na docstring e falha **pelo motivo certo**.
3. **Mostrar o vermelho**: rodar `pytest -q tests/test_<assunto>.py` e colar a
   saída. Se falhar por outro motivo (import, typo, fixture), o teste está
   errado — consertar o teste antes de tocar o código de produção.
4. **Patch mínimo**: a menor mudança em `src/` que faz o teste passar sem violar
   outra regra. Sem refatoração oportunista, sem renomear nada existente, sem
   reformatar, sem arrumar lint fora das linhas corrigidas.
5. **Verde**: rodar o teste novo de novo e colar a saída.
6. **Suíte inteira**: `pytest -q` e `ruff check .`. Colar as saídas. Se algum
   teste que passava quebrou, reverter o patch e reportar — não empilhar
   correções.
7. **Registrar** em `docs/DEFEITOS.md` uma entrada com: F##, R## violada, causa
   raiz em uma frase, teste que cobre, arquivos tocados.
8. **Propor** a mensagem de commit (imperativo, português, assunto ≤ 72
   caracteres, corpo citando F## e R##) e **PARAR**.

## Proibido

- Rodar `git commit`, `git add -p`, `git push` ou `git reset`. O commit é do usuário.
- Editar `tests/` fornecidos ou qualquer coisa em `data/`.
- Mudar nome de campo do relatório, argumento do CLI, exit code ou schema.
- Usar `float` em dinheiro; arredondar antes da serialização.

## Pronto quando

- Existe um teste novo que falhava antes do patch e passa depois, e o vermelho
  e o verde foram mostrados ao usuário.
- `pytest -q` passa inteiro e `ruff check .` não acusa nada nas linhas tocadas.
- `git diff` cobre só o F## autorizado (uma mudança de produção + um teste novo
  + a entrada em `docs/DEFEITOS.md`).
- A mensagem de commit está proposta e a execução parou aguardando revisão.
