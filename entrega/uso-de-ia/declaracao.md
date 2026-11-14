# Declaração de uso de IA

## Ferramenta e modelo

- **Ferramenta:** Claude Code v2.1.325 (CLI da Anthropic), em Windows 11 com
  PowerShell 5.1.
- **Modelo:** Claude Opus 5.
- **Sessões exportadas:** `sessao-01.txt` (sessão principal: baseline, spec,
  auditoria, correção dos seis defeitos, endurecimento e portões) e
  `sessao-02.txt` (sessão de revisão: conferência independente das decisões de
  ambiguidade, da triagem de defeitos e dos testes, e redação desta entrega).

A configuração do assistente está versionada no repositório e faz parte da
investigação: `CLAUDE.md` (regras invioláveis e processo), `.claude/settings.json`
(travas de permissão) e `.claude/skills/` (as skills `audit`, `fix-bug` e
`verify`).

## O que eu fiz

- **Defini o processo e as regras do jogo** antes de qualquer código: diagnóstico
  e conserto como etapas separadas, nenhuma correção sem teste vermelho antes,
  um defeito por commit com parada para revisão, nenhuma mudança colateral, e
  `Decimal` obrigatório em dinheiro. Tudo escrito em `CLAUDE.md`.
- **Travei o que não podia ser tocado** em `.claude/settings.json`: os 5 testes
  fornecidos, o `tests/helpers.py`, o `data/**` e o próprio `README.md`. Quando a
  trava se mostrou larga demais e passou a bloquear a criação de testes novos —
  que o desafio autoriza —, fui eu quem autorizou e definiu a regra nova, por
  arquivo. O assistente tentou afrouxar a própria supervisão e foi barrado; a
  decisão era minha, não dele.
- **Decidi todas as ambiguidades da especificação.** As nove questões A01–A09 e
  as três observações O10–O12 foram decididas por mim, uma a uma, depois de ver a
  medição de impacto de cada leitura. Em particular: a reserva que cruza o mês
  entra inteira no mês do check-in (A01), a média divide o total exato (A03),
  cada bucket arredonda o próprio subtotal mesmo quando a soma não fecha com o
  total (A08) e moeda sem taxa passa a ser erro de entrada com exit 2 (A04).
- **Fiz a triagem dos defeitos**: ordem de correção e severidade. Subi a
  severidade de F04 de média para alta contra a classificação inicial do
  assistente, com o argumento de que medir o risco pelo dataset entregue é
  classificar pela amostra, não pelo defeito. A fronteira de meio centavo
  encontrada depois (0.75 USD × 5,42) confirmou que a reclassificação estava
  certa.
- **Levantei observações que o assistente não tinha visto** — O10 (`hotel_name`
  divergente para o mesmo `hotel_id`), O11 (assimetria de caixa na moeda entre o
  parser e a tabela de taxas) e O12 (mês sem confirmadas sumindo do `by_month`) —
  e aceitei a evidência quando a análise mostrou que O12 não era defeito: contar
  as canceladas quebraria a amostra do README.
- **Pedi os testes que faltavam.** Depois das correções, apontei que F04 e F06
  eram os dois únicos defeitos sem teste vermelho de origem na suíte, e que as
  regras R03, R04, R13, R14, R28 e o contrato inteiro do CLI (R19–R24) estavam
  implementados mas sem cobertura alguma. Os 29 testes novos saíram desse pedido.
- **Revisei e aprovei cada diff**, commit a commit, e escrevi as mensagens de
  commit. Nenhum commit foi feito pelo assistente.
- **Dispensei o `/security-review`** de forma deliberada, com a justificativa
  registrada: CLI local, sem rede, credencial, dado real ou persistência
  compartilhada. A dispensa está declarada neste pacote como dispensa, não como
  portão aprovado.

## O que a IA fez

- **Coletou o baseline** do estado inicial (`docs/baseline/`) e destrinchou o
  `README.md` nas 30 regras numeradas de `docs/SPEC.md`, sempre citando a frase
  de origem e sem decidir nada onde o README calasse.
- **Escreveu o oráculo** `tools/conferir_amostra.py`, que lê a amostra do próprio
  README e compara o JSON gerado campo a campo.
- **Executou a auditoria read-only** (`docs/AUDITORIA.md`), percorrendo as regras
  em vez dos arquivos, e produziu os seis achados com evidência, as 21 regras
  conformes e duas suspeitas que descartou por falta de evidência.
- **Aplicou as correções** que eu autorizei, uma por vez, cada uma com teste
  vermelho antes e patch mínimo, propondo o diff e parando para a minha revisão.
- **Escreveu os 29 testes novos** e verificou cada um nos dois sentidos: verde no
  código corrigido e vermelho num clone com o defeito reintroduzido.
- **Mediu o que eu pedi para medir**: empates no ranking, divergência entre as
  leituras da média, impacto do caminho `float` nas 300 linhas, meses que cruzam
  a virada e a diferença de um centavo entre a soma do `by_month` e o total.
- **Rodou o `/code-review`** e verificou os seis achados em vez de aceitá-los:
  recusou um com teste, corrigiu dois que eram dele e classificou três como
  pendências já conhecidas.
- **Redigiu os documentos** `docs/SPEC.md`, `docs/AUDITORIA.md` e este pacote de
  entrega, a partir do registro do trabalho.

## Resumo honesto da divisão

O assistente foi o executor e o instrumento de medição: leu, mediu, propôs,
corrigiu sob autorização e escreveu os testes e a documentação. As decisões que
mudam o produto — o que é defeito, o que é ambiguidade, como cada ambiguidade se
resolve, em que ordem corrigir, o que entra como mudança de comportamento, o que
fica de fora e o que vai para o commit — foram todas minhas, e estão registradas
com a justificativa de cada uma em `docs/SPEC.md` e nas sessões exportadas.
