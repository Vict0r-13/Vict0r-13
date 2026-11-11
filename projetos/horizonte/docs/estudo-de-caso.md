# Horizonte Estudo de caso

## Contexto

Queria uma ferramenta para organizar minhas finanças e apoiar decisões antes de gastar. Além de registrar despesas, precisava entender se meu saldo chegaria ao próximo pagamento, quais compromissos consumiriam esse dinheiro e quanto poderia gastar por dia.

## Processo de construção com IA

Construí o Horizonte por vibe coding, usando IA para gerar e adaptar código a partir das necessidades que descrevi. Minha participação incluiu definição do problema, funcionalidades, regras de negócio, preferências de interface e feedback após testar versões.

No histórico do projeto, pedi melhor relação entre lançamentos e saldo, alertas de orçamento, análise dos principais gastos, simulações e uma experiência financeira mais fácil de compreender. Também relatei falhas, como a leitura de uma nota fiscal fotografada. A evolução passou a priorizar controle financeiro e planejamento entre recebimentos.

## Produto e contribuição pessoal

Uso o aplicativo no meu planejamento financeiro. Consigo apresentar a necessidade que originou o produto, as funcionalidades que solicitei e as regras de negócio que orientaram a experiência. O desenvolvimento teve apoio de IA; minha contribuição não é descrita como programação independente de todos os componentes.

O núcleo publicado é Python, com SQLite e interface HTML/CSS/JavaScript. Os fontes foram recuperados do pacote Android 5.0 enviado por mim e organizados nesta pasta. O projeto Android nativo completo e o processo de empacotamento dos instaladores não foram reconstruídos nesta etapa.

## Demonstração para entrevista

Use `python demo.py` para iniciar uma base fictícia. Mostre saldo, próximo recebimento e despesas programadas. Acrescente uma despesa e observe como ela modifica a capacidade de gasto. Explique o que acontece se uma conta vence antes do salário e por que renda prevista não equivale a dinheiro disponível hoje.

Depois, mostre `cashflow.py`, `spending.py` e os testes. Diferencie o que consigo explicar como regra do produto dos detalhes técnicos que ainda estou aprofundando.

## Resultado verificável e limites

Há um aplicativo de uso pessoal relatado pelo responsável, código recuperado e uma demonstração local preparada com dados fictícios. Nesta preparação, oito testes das regras centrais passaram e o servidor iniciou. A conexão do navegador de automação a localhost foi bloqueada, portanto não houve verificação visual completa da interface.

Não há uso por terceiros, economia de horas ou resultado financeiro mensurado demonstrado. As projeções são determinísticas; não são um modelo de IA próprio. A geração de software com IA faz parte do processo de construção, e não deve ser confundida com um modelo generativo funcionando dentro do aplicativo.
