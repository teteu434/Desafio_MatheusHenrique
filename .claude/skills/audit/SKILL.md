---
name: audit
description: Varredura read-only do código de src/onfly_report contra as regras R## de docs/SPEC.md, produzindo achados F## com evidência. Use quando o usuário pedir auditoria, diagnóstico, "onde estão os defeitos", ou ao iniciar a Fase 3. NÃO use para corrigir — a skill é proibida de editar arquivos; para corrigir, use fix-bug.
---

# audit — auditoria read-only contra a SPEC

## Regra número um

Esta skill **não edita arquivo nenhum**. Nem código, nem teste, nem formatação,
nem lint. Se durante a varredura a correção parecer óbvia, ela vai para a tabela
como achado e **nada mais**. Corrigir é trabalho da skill `fix-bug`, depois da
triagem do usuário.

## Procedimento

1. Ler `docs/SPEC.md` inteiro. A auditoria é contra as regras R##, não contra
   a intuição de quem lê o código.
2. Ler todos os arquivos de `src/onfly_report/` do começo ao fim, um por um.
   Não presumir conteúdo; não auditar de memória.
3. Para cada regra R##, perguntar: qual linha de código a implementa, e ela faz
   o que a regra diz? Percorrer as regras, não os arquivos — assim nenhuma regra
   fica sem cobertura e achados não dependem de o código "parecer estranho".
4. Para cada desvio, montar a **evidência concreta**: o trecho exato
   (`arquivo:linha`) e, quando for número errado, a conta que demonstra o erro
   com dados reais de `data/` ou da amostra do README.
   - Evidência de número: entrada → o que o código calcula → o que a regra manda.
   - Evidência de contrato: o trecho + o item do README que ele contradiz.
5. Classificar a severidade:
   - **alta** — produz número errado no relatório;
   - **média** — quebra contrato do CLI ou schema (argumento, exit code, campo);
   - **baixa** — robustez, mensagem, caso de borda que o dataset não exercita.
6. Numerar os achados F01, F02, … na ordem em que forem confirmados.

## Saída

Uma tabela, exatamente com estas colunas:

| F## | R## violada | arquivo:linha | evidência | causa raiz (uma frase) | severidade |

Depois da tabela, uma seção `## Suspeitas`. Vai para lá tudo que não tiver
evidência concreta: cheiro de código, dúvida sobre intenção, caso de borda que
não consegui demonstrar. **Suspeita não entra na tabela** — a tabela é o que
está provado.

Fechar com uma seção `## Cobertura`: quais R## foram verificadas e quais ficaram
sem verificar (e por quê).

## Pronto quando

- Toda regra de `docs/SPEC.md` aparece na seção Cobertura, verificada ou não.
- Todo item da tabela tem `arquivo:linha` e evidência que o usuário consegue
  reproduzir sozinho.
- Nenhum arquivo do repositório foi modificado (confirmar com `git status`
  quando houver repositório).
- A saída termina com: "Aguardando triagem. Nenhuma correção aplicada."
