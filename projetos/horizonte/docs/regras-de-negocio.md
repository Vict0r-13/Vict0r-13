# Regras de negócio do Horizonte

## Saldo disponível e recebimento previsto

O saldo informado representa o dinheiro disponível conforme o cadastro. Uma receita futura programada pertence à projeção e não é dinheiro já recebido. A projeção temporal considera a receita na data prevista; o limite de gastos atual não pode simplesmente antecipá-la.

`cashflow.cycle` identifica o recebimento programado mais próximo, até o horizonte de busca implementado. O período de proteção vai até o dia anterior ao recebimento. Sem renda futura cadastrada, o período usa o fim do mês. Uma renda informada apenas como referência no perfil não gera automaticamente depósitos futuros nessa função.

## Contas protegidas e insuficiência

Despesas e investimentos programados consomem capacidade financeira conforme seus vencimentos. Custos fixos ainda sem lançamento podem ser representados na projeção segundo as regras de calendário. A linha do tempo também simula consumo do orçamento variável.

Se o saldo projetado ficar negativo, a primeira data de insuficiência é exposta. Isso descreve o cenário cadastrado, sem garantir o que acontecerá na conta bancária real. Contas que vencem no mesmo dia de um recebimento merecem atenção porque a ordem intradiária não é garantida.

## Limite diário

`spending.overview` começa pelo saldo, compromissos, orçamento variável restante e reserva protegida configurada. A capacidade também é restringida pelos compromissos do ciclo até o próximo recebimento. O limite diário divide a capacidade calculada pelos dias restantes do mês, incluindo o dia de referência.

Saldo ausente, orçamento incompleto, falta de conferência, parcelas sem calendário ou outros conflitos podem gerar avisos e impedir que a estimativa seja apresentada como planejamento pronto. A divisão usa centavos inteiros; não é salário dividido pelos dias até receber.

## Simulações

Uma simulação de compra ou decisão trabalha com um cenário alternativo, preservando os dados de entrada. Compra à vista, parcelas e assinaturas têm efeitos de calendário diferentes. A simulação não realiza pagamento, operação bancária ou contratação.

Os resultados dependem das regras e informações registradas. Não se deve afirmar que uma compra é segura apenas porque um número cabe em uma projeção incompleta.

## Evidências nesta preparação

Oito verificações reproduzíveis em `tests/test_cashflow.py` conferem regras centrais e o esquema do cenário fictício. São verificações focadas, não certificação contábil ou cobertura integral do aplicativo. O teste de aumento do recebimento futuro confere que esse aumento não cria limite disponível hoje; o teste de despesa adicional confere a redução de capacidade diária.
