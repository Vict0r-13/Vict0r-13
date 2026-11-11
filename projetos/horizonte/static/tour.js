const guideBaseForm=openForm;let guideTour=null,guideTourIndex=0,guideTourFocus=null;let guideSettings=null;
// Short, contextual explanations: purpose, what to enter, and effect of the action.
const guideCopy={
home:'Comece conferindo o saldo em conta e os avisos. Saldo é o dinheiro registrado; “pode gastar” desconta compromissos e proteções. Abra a próxima ação para corrigir informações pendentes antes de decidir uma compra.',
cashflow:'O calendário mostra como seu saldo pode mudar a cada dia. Contas previstas reduzem a projeção; recebimentos previstos só entram na data indicada. A linha sem novas receitas mostra o risco de o depósito atrasar. Nenhuma previsão confirma um pagamento.',
setup:'Cadastre uma informação de cada vez: prioridade, saldo, renda, contas fixas e cartões. Você pode deixar dados pendentes e continuar depois. Salvar uma etapa guarda as respostas; informar uma renda não significa que o dinheiro já entrou.',
review:'Compare os registros com seu banco, confira os pagamentos e veja as próximas contas. Marque cada conferência somente depois de realizá-la. Concluir registra a revisão; não paga contas nem corrige valores sozinho.',
ledger:'Este é o extrato dos movimentos que você registrou. Receita recebida aumenta o saldo; despesa paga o reduz. Um item previsto só entra no calendário. Para a fatura de um cartão já cadastrado, confirme o pagamento na tela Cartões.',
budget:'Separe contas que se repetem, como aluguel, dos limites para gastos variáveis, como lazer. Cadastrar um limite não tira dinheiro da conta. Pagar uma conta fixa atualiza o saldo; atingir seu valor esperado não é, por si só, um excesso de gasto variável.',
fixed:'Uma conta fixa é um compromisso que se repete nos meses definidos. Informe valor, vencimento e uma categoria exclusiva, como Aluguel. O app considera a obrigação na projeção; o dinheiro só sai ao registrar o pagamento.',
cards:'Aqui ficam os cartões e suas faturas. Compras no cartão são valores a pagar, sem diminuir a conta agora. Confirmar uma fatura registra sua saída do banco uma única vez. Não cadastre o total de uma fatura que já tem todas as compras lançadas.',
goals:'Uma meta é um valor que você quer juntar para um objetivo. Defina o preço, quanto já tem e o prazo. Você pode associar parte dos investimentos à meta. Essa associação serve para acompanhar o progresso e não move dinheiro.',
debts:'Veja contratos e faturas distribuídos no tempo e simule pagamentos adicionais. Vincule pagamentos já existentes para evitar contar a mesma dívida duas vezes. Simular mostra uma possibilidade; não altera contratos nem faz pagamentos.',
holdings:'Cadastre o que você já possui. Ações usam quantidade e preço por cota; aplicações como Tesouro ou CDB podem usar saldo em reais. Registrar um aporte é diferente de apenas atualizar um saldo: confira o efeito explicado antes de salvar.',
market:'Digite o código do ativo para consultar preços e indicadores disponíveis. Dados podem estar incompletos ou atrasados. Os campos são editáveis para conferência; calcular gera referências e cenários, sem comprar ações nem garantir retorno.',
compare:'Compare aplicações com o mesmo valor inicial, aporte mensal e prazo. Informe as taxas de cada alternativa. Calcular só simula: não aplica dinheiro. O maior valor projetado também depende das hipóteses, dos custos e dos riscos informados.',
sim:'Estime quanto acumular e quanto guardar por mês para buscar a renda desejada. Retorno e inflação são hipóteses. Os aportes da simulação não saem da conta; registre separadamente as transferências que realmente fizer.',
house:'Controle produtos, quantidades, lotes e validades. Cada compra pode ter uma validade diferente. Receitas calculam o custo da parte usada; planejar uma refeição não baixa estoque. A baixa ocorre ao registrar que a refeição foi preparada.',
shopping:'Monte seu carrinho enquanto compra ou importe uma nota para conferência. Quantidades e preços precisam bater com o documento. A leitura pode falhar: revise os itens antes de confirmar. Só a confirmação da compra registra estoque e a opção financeira escolhida.',
reports:'Escolha os assuntos e a frequência dos relatórios. Para envio por e-mail, configure neste aparelho a conta que enviará e o endereço que receberá. Criar um agendamento não envia imediatamente; a execução depende do aparelho e, no envio, da internet.',
research:'Pesquise preços online ou estabelecimentos próximos. São duas buscas diferentes: uma loja próxima pode não ter o preço ou o estoque mostrado na internet. Confira a embalagem, o preço final e a disponibilidade antes de decidir.',
power:'Poder de compra é quanto seu dinheiro consegue comprar depois da inflação. Compare valores no mesmo período. O IPCA é um índice médio do Brasil; sua cesta pode variar. A inflação divulgada é histórica e não garante o que acontecerá no futuro.',
onepage:'Reúna seus indicadores em um relatório. O gráfico da carteira contra a inflação exige fechamentos mensais conferidos e registro de aportes e retiradas. Crescimento do saldo por novos depósitos não é rendimento do investimento.',
spending:'Informe uma compra para testar se ela cabe no planejamento registrado. O app preserva compromissos, limites e valores protegidos. O resultado depende de informações completas; fazer o teste não registra a compra nem reserva o valor.',
payroll:'Informe o salário bruto para estimar descontos CLT ou use o líquido que você já conhece. Divida os recebimentos nas datas reais. Calcular apenas mostra a estimativa; salvar cria previsões. Confirme cada depósito para ele entrar no saldo.',
balance:'Compare o saldo do app com o saldo disponível no banco e veja as alterações registradas. Se falta uma despesa ou receita, lance-a no extrato. Ajustar saldo guarda uma explicação da diferença, sem inventar uma entrada ou saída.',
modules:'Ative os assuntos que deseja acompanhar. Casa inclui estoque, receitas e compras; Investimentos inclui carteira e simuladores. Mostrar ou ocultar um módulo muda a navegação e preserva os dados já cadastrados.',
settings:'Atualize seus dados e faça uma cópia de segurança. Exportar backup guarda seus registros em um arquivo; restaurar substitui os dados deste aparelho pelos dados do arquivo. PC e celular mantêm bases separadas nesta versão.',
startplan:'A sugestão usa sua renda líquida para propor limites iniciais. Ajuste os valores e desmarque categorias que não usa. Aplicar cria os limites selecionados; não faz pagamentos nem transfere a margem para uma reserva.',
analytics:'Escolha o período para comparar entradas, saídas e categorias. Os gráficos usam seus lançamentos registrados. Amplie os detalhes para descobrir quais gastos explicam os totais; filtros não alteram o extrato.',
learn:'Consulte explicações para entender os termos e os cálculos do app. Exemplos são educativos. Para planejar sua realidade, use seus valores nas telas de orçamento, dívidas e simulações.'
};
const guideFields={
username:'SMTP é o serviço que envia os e-mails. Aqui entra o login da conta que vai enviar seus relatórios, geralmente o e-mail completo, como nome@gmail.com. Se deixar vazio, o app usa o endereço remetente.',
provider:'Escolha o serviço da conta que enviará os relatórios: Gmail ou Outlook. O app usa essa escolha para definir a conexão de envio. A conta precisa permitir o método de acesso oferecido aqui.',
sender:'Digite o endereço completo da conta que enviará os relatórios, por exemplo nome@gmail.com. Use uma conta à qual você tenha acesso e uma credencial compatível com ela.',
recipient:'Digite o e-mail completo em que quer receber os relatórios. Pode ser o mesmo do remetente. Confira as letras: um endereço errado pode impedir a entrega ou enviar suas informações a outra pessoa.',
password:'Use a senha de aplicativo ou credencial de envio aceita pelo seu provedor. No Gmail, gere uma senha de aplicativo se a conta permitir; ela é diferente da senha de acesso comum. A credencial fica neste aparelho e não entra no backup.',
key:'API é uma forma de um serviço fornecer dados ao app. Cole sua chave de acesso da brapi, se tiver uma. É opcional, fica na memória desta sessão e não entra no backup. Salvar vazio remove a chave da sessão.',
gross:'É o salário mensal antes dos descontos. Copie o valor bruto do contracheque, por exemplo 5376,81. Não use só a parcela da quinzena. O cálculo estima os descontos CLT disponíveis no app.',
net:'É o total mensal que chega à conta depois dos descontos. Se recebe em duas datas, some os dois depósitos. Use este modo quando já sabe o líquido real do mês.',
income:'Informe sua renda líquida mensal total, depois dos descontos. Se recebe por quinzena, some as duas partes. É uma referência do orçamento; preencher aqui não confirma depósitos nem aumenta o saldo.',
dependents:'Informe a quantidade de dependentes considerada no seu imposto de renda mensal. Exemplo: 1 para um dependente. Se não tem, use 0. Esse número participa da estimativa do IRRF, o imposto retido no salário.',
pension:'Informe o valor mensal da pensão judicial descontada na folha. Use 0 se não houver. O cálculo usa o valor informado para estimar o líquido e as deduções aplicáveis.',
other:'Some outros descontos da folha, como plano de saúde e consignado. Não repita INSS, imposto de renda ou adiantamento. Use 0 se não houver. Esse valor reduz a estimativa do que você recebe.',
mode:'Escolha CLT para estimar o líquido a partir do bruto ou “Já sei meu líquido” para informar o total recebido. A escolha muda quais campos entram no cálculo.',
twice:'Marque se o salário chega em duas partes no mesmo mês. Informe o dia e a divisão da primeira parte; a segunda fica no último dia do mês. Desmarcado, o recebimento fica somente no fim do mês.',
firstDay:'Informe o dia da primeira parte do salário, de 1 a 28, por exemplo 15. A segunda parte fica no último dia do mês. Se a empresa antecipar, ajuste a data real no extrato.',
split:'Escolha como sua empresa calcula a primeira parte: percentual do líquido, percentual do bruto ou valor fixo. A segunda parte será o líquido mensal menos esse adiantamento. Confira no contracheque.',
percent:'Informe só o número do percentual da primeira parte. Exemplo: 50 significa 50%. Ele será aplicado ao bruto ou ao líquido conforme a opção “Como dividir?”.',
advance:'Digite quanto recebe na primeira data do mês, em reais. Exemplo: 2000,00. O restante do líquido estimado fica para a última data. Este campo só é usado na divisão por valor fixo.',
link1:'Se a primeira parcela deste salário já está no extrato do mês inicial, selecione esse lançamento. Assim a programação aproveita o registro existente. Deixe sem vínculo somente se precisar de uma previsão nova.',
link2:'Se a última parcela deste salário já está no extrato do mês inicial, selecione esse lançamento. O vínculo evita criar outra previsão para o mesmo recebimento.',
reviewed:'Marque depois de conferir os dados e os compromissos indicados no texto ao lado. É uma confirmação sua, sem consulta automática ao banco. Confira novamente se suas informações mudarem.',
cash:'Informe o dinheiro disponível na conta hoje, sem somar reserva ou investimentos. Exemplo: 850,25. Zero significa saldo conferido e zerado; se não sabe, use a opção de conferir depois.',
cashReal:'Copie o saldo disponível agora na conta que você acompanha. Não some limite do cartão, cheque especial disponível, reserva nem investimentos. Salvar define a referência usada nos cálculos do app.',
bank:'Abra seu banco e copie o saldo atual da conta em reais. Não inclua limite de crédito. Ao salvar, o Horizonte ajusta o saldo para esse valor e guarda a justificativa, sem criar uma receita ou despesa.',
reason:'Explique o que conferiu ou a origem da diferença, por exemplo “Comparei com o banco; faltava o saldo inicial”. A explicação fica no histórico do ajuste para você entender depois.',
unknown:'Marque se ainda não conferiu seu saldo. O app deixa a informação pendente; não interpreta isso como zero. Se já existe um saldo registrado, ele é preservado até sua conferência.',
nextDate:'Selecione o dia em que espera o próximo depósito. Esta é uma previsão única, não uma programação de todos os meses. O valor só entra no saldo após a confirmação de recebimento.',
nextAmount:'Informe o valor líquido esperado apenas para esse próximo depósito. Se o salário é quinzenal, use só a parte que vai chegar nessa data. Não repita um recebimento já registrado.',
paidDate:'Informe a data em que o dinheiro realmente entrou ou saiu da conta. Use depois de conferir o banco. Confirmar um item com essa data atualiza o saldo; vencimento e pagamento podem ser em dias diferentes.',
status:'Escolha Previsto se ainda vai receber ou pagar: o saldo atual não muda. Escolha Pago/Recebido somente se o dinheiro já saiu/entrou. Isso atualiza o saldo da conta.',
cardId:'Selecione o cartão usado nesta despesa. A compra fica associada à fatura. Se pagou por Pix, dinheiro ou débito na conta, deixe sem cartão. Não escolha cartão para uma receita.',
closeDay:'É o dia em que o banco encerra as compras de uma fatura. Exemplo: fecha dia 5 e vence dia 10. Não é a data do pagamento; confira essa informação no aplicativo do cartão.',
dueDay:'É o dia do mês em que a fatura precisa ser paga, por exemplo 10. Confira no aplicativo do cartão. Cadastrar o vencimento não confirma que você já pagou.',
limit:'É o limite de crédito disponibilizado pelo banco para este cartão. Exemplo: 3000,00. É um dado de referência, não é dinheiro na conta nem autorização para gastar todo esse valor.',
count:'Informe em quantas parcelas a compra foi dividida. Exemplo: 10 para uma compra em dez vezes. O app distribui o total entre os vencimentos e preserva os centavos.',
first:'Escolha o vencimento da primeira parcela na fatura. As demais serão distribuídas mensalmente a partir dela. Use a data da primeira cobrança, não necessariamente o dia da compra.',
allocate:'Use apenas se já existe um saldo de parcelas antigas sem calendário e esta compra faz parte dele. Marcado, reduz esse saldo sem calendário ao criar as parcelas datadas. Para uma compra nova, deixe desmarcado.',
pendingInstallments:'É o total de parcelas futuras antigas que você ainda não distribuiu em datas. Não inclua valores já cadastrados nas faturas. Se todas as parcelas estão no calendário, use 0.',
confirmDuplicate:'Marque só depois de conferir que um registro com mesmo nome, valor e data representa outra movimentação real. Isso permite salvar mesmo com o aviso de possível repetição.',
confirmSimilar:'Marque somente se você conferiu que o gasto parecido já existente é outra compra. A opção permite prosseguir apesar do alerta; ela não apaga nem combina os dois registros.',
essential:'Marque se esta despesa é necessária na sua rotina, como moradia ou alimentação básica. Serve para identificar prioridades no planejamento; não registra nem paga a conta.',
day:'Informe o dia do mês do vencimento, de 1 a 31. Exemplo: 10 para uma conta que vence todo dia 10. Se o mês não tiver esse dia, o app usa o último dia disponível.',
frequency:'Escolha com que frequência o relatório será gerado: todo dia, uma vez por semana ou uma vez por mês. Depois confira o horário e o dia correspondente à opção escolhida.',
weekday:'Informe o dia da semana para o relatório semanal: 0 segunda, 1 terça, 2 quarta, 3 quinta, 4 sexta, 5 sábado ou 6 domingo. Só é usado na frequência semanal.',
time:'Escolha o horário local deste aparelho, por exemplo 19:00. O aparelho precisa conseguir executar a tarefa; no Android, o sistema pode adiar a execução em segundo plano.',
channel:'Escolha para onde vai o relatório. E-mail usa a conta configurada neste aparelho; local apenas guarda o resumo. WhatsApp automático exige o conector no PC e não funciona sozinho no celular.',
enabled:'Marque para ativar esta configuração neste aparelho. Desmarcado, ela fica desativada. Confirme também os outros campos: ativar, por si só, não garante que o envio esteja configurado.',
expiry:'Selecione a validade escrita nesta embalagem. Confira dia, mês e ano; se houver prazo após abertura, considere as instruções do rótulo. Sem data, o item fica pendente e não gera aviso por vencimento.',
location:'Escreva onde o produto fica guardado, por exemplo “Geladeira” ou “Armário de cima”. É uma referência para encontrar o lote em casa, não a localização do celular.',
store:'Informe o nome do estabelecimento onde comprou, por exemplo “Mercantil do bairro”. O nome ajuda a identificar a compra; não confirma preços nem vincula a uma loja online.',
stockQuantity:'Informe o conteúdo total comprado na unidade escolhida para o estoque. Exemplo: 2 pacotes de 1 kg equivalem a 2000 g. Esse total é o que ficará disponível para uso nas receitas.',
stockUnit:'Escolha como vai controlar o conteúdo: g para gramas, ml para mililitros ou un para unidades. Use a mesma unidade da quantidade total. Exemplo: 2000 com g, não 2 com g para dois quilos.',
unit:'Escolha a unidade em que a quantidade está expressa. Gramas medem peso, mililitros medem volume e unidades contam itens. Exemplo: 1 kg equivale a 1000 g; 1 litro equivale a 1000 ml.',
productId:'Escolha qual produto cadastrado vai receber esta entrada ou será usado como ingrediente. Confira o nome e a unidade. Uma entrada soma estoque desse produto; um ingrediente apenas compõe a receita.',
recipeId:'Escolha a receita que deseja preparar nesse dia. O planejamento usa os ingredientes e as quantidades dessa receita para estimar as necessidades de compra.',
servings:'Informe para quantas porções a receita inteira rende ou quantas pretende preparar, conforme o título. Exemplo: se a receita inteira serve duas pessoas em uma porção cada, o rendimento é 2.',
meal:'Escolha em qual refeição do dia vai usar a receita, por exemplo Almoço ou Lanche. Essa escolha organiza o cardápio; não retira ingredientes do estoque.',
minimum:'Informe a menor quantidade que quer manter em casa, na unidade do produto. Exemplo: aveia em gramas com mínimo 200. Quando o estoque ficar abaixo da referência, a reposição aparece no planejamento.',
expectedItems:'Copie a quantidade de linhas de produtos da nota, ou conte essas linhas. Não é a soma das quantidades compradas. Exemplo: três linhas com produtos diferentes são 3 itens, mesmo que uma linha tenha duas unidades.',
receiptCount:'Confira quantas linhas de produtos existem na nota. Use a contagem para perceber se a leitura esqueceu algum item. Não some o número de unidades de todas as linhas.',
fiscalTotal:'Copie o valor final a pagar impresso na nota, já considerando descontos ou acréscimos. Esse valor será comparado à soma dos itens para ajudar na conferência.',
text:'Cole o conteúdo pedido neste formulário, sem resumir os dados do documento. Você pode revisar o texto antes de salvar ou tentar a leitura. A extração pode falhar; confira os valores encontrados.',
url:'Cole o endereço completo da página, incluindo http:// ou https://, conforme a origem. Em notas, use o link gerado pelo QR fiscal. Consultar exige internet e o portal pode pedir uma confirmação.',
value:'Cole o link completo aberto ao ler o QR da nota fiscal, não apenas a sequência numérica. Use o portal oficial da nota. A consulta pode pedir internet, captcha ou conferência manual.',
query:'Digite produto, marca e tamanho da embalagem, por exemplo “arroz Camil 1 kg”. Uma descrição específica ajuda a comparar itens equivalentes. A busca envia esse texto às fontes consultadas.',
lat:'Latitude é uma das coordenadas do local de busca. Prefira “Usar localização do aparelho” para preenchê-la. Se informar manualmente, use graus decimais e o sinal, como -3,88.',
lon:'Longitude é a outra coordenada do local de busca. Use junto com a latitude do mesmo lugar. O botão de localização pode preencher ambas; não informe um endereço escrito neste campo.',
radius:'Informe até quantos quilômetros ao redor do local quer buscar lojas, de 1 a 10. Exemplo: 3 para um raio de 3 km. A distância encontrada é em linha reta, não o percurso da rua.',
ticker:'Ticker é o código do investimento na bolsa, como MDIA3 ou MXRF11. Digite o código do ativo que quer consultar. A disponibilidade de indicadores depende da fonte e pode variar por ativo.',
sector:'Escolha se a empresa é financeira/seguradora ou de outro setor. Alguns critérios de análise de empresas não financeiras não se aplicam da mesma forma a bancos e seguradoras.',
eps:'LPA é o lucro por ação: o lucro da empresa dividido pelo número de ações. Informe o valor em reais dos últimos 12 meses, conforme uma fonte conferida. Se não sabe, deixe vazio; ausência não é zero.',
eps3:'Informe a média do lucro por ação dos últimos três anos, em reais. Some os três LPAs anuais e divida por 3. Essa média é usada na referência de Graham; o LPA de 12 meses não a substitui.',
book:'VPA é o valor patrimonial por ação ou cota. Informe o patrimônio por unidade em reais, conforme o balanço/fonte. Não é a cotação na bolsa. Se desconhecido, deixe vazio.',
dividend:'Informe quanto o ativo distribuiu por ação/cota em um ano, em reais. Não informe a porcentagem do rendimento nem o total recebido por toda a carteira. O histórico não garante pagamentos futuros.',
margin:'Informe o desconto adicional desejado sobre a referência calculada. Exemplo: 30 significa buscar uma referência 30% menor. É uma margem escolhida por você, não proteção garantida contra perdas.',
currentRatio:'Liquidez corrente é o ativo circulante dividido pelo passivo circulante. Use a razão publicada, por exemplo 1,5, sem sinal de %. Se o dado não estiver disponível, deixe vazio.',
longDebt:'Informe a dívida de longo prazo em milhões de reais. Exemplo: R$ 250 milhões vira 250. Use a mesma escala do capital de giro para o app comparar os valores.',
workingCapital:'Capital de giro é o ativo circulante menos o passivo circulante. Informe em milhões de reais, na mesma escala da dívida de longo prazo. Se não sabe o dado, deixe vazio.',
profitYears:'Informe quantos anos consecutivos a empresa apresentou lucro, conforme o histórico conferido. Exemplo: 10. Não use a idade total da empresa nem presuma que ausência de dado significa zero.',
dividendYears:'Informe quantos anos seguidos houve distribuição de dividendos, conforme histórico conferido. Isso descreve o passado e não garante as próximas distribuições.',
growth10:'Informe a variação percentual do lucro por ação em dez anos. Exemplo: 40 para crescimento de 40% no período inteiro. Não use a taxa anual nesse campo.',
sales:'Informe a receita anual da empresa em milhões de reais. Exemplo: R$ 1,2 bilhão vira 1200. Use uma fonte e um período conferidos.',
salesFloor:'Defina sua referência mínima de receita anual, em milhões de reais, para o critério de porte. É um parâmetro escolhido por você, não um mínimo universal para investir.',
years:'Informe o prazo da simulação em anos completos. Exemplo: 10 representa dez anos. O resultado usa esse prazo e as taxas informadas, sem registrar movimentações reais.',
lowGrowth:'Informe sua hipótese de crescimento anual do LPA no cenário adverso. Exemplo: -5 significa queda de 5% ao ano. É uma hipótese editável, não uma previsão do app.',
baseGrowth:'Informe sua hipótese de crescimento anual do LPA no cenário central. Exemplo: 3 significa alta de 3% ao ano. O cenário usa a mesma hipótese a cada ano.',
highGrowth:'Informe sua hipótese de crescimento anual do LPA no cenário favorável. Mesmo um cenário favorável é uma simulação e pode não acontecer.',
lowPE:'P/L é preço dividido pelo lucro por ação. Informe o múltiplo que imagina no fim do cenário adverso, por exemplo 8. Não é uma porcentagem.',
basePE:'Informe o múltiplo preço/lucro esperado ao fim do cenário central, por exemplo 12. Ele será aplicado ao lucro por ação projetado para estimar o preço final.',
highPE:'Informe o múltiplo preço/lucro esperado ao fim do cenário favorável. Quanto maior o múltiplo escolhido, maior tende a ser o preço simulado; isso não garante valorização.',
annual:'Informe uma hipótese de retorno líquido anual, já considerando custos e impostos. Exemplo: 8 significa 8% ao ano. Não é retorno garantido e este campo não consulta automaticamente seu investimento.',
inflation:'Informe uma hipótese de aumento anual dos preços. Exemplo: 4 significa 4% ao ano. Nas simulações, essa taxa não é uma promessa nem a inflação futura conhecida.',
futureMode:'Escolha repetir o IPCA recente apenas como hipótese constante ou informar sua própria hipótese. No primeiro modo, o campo de inflação personalizada é ignorado.',
futureInflation:'Informe a hipótese de inflação anual, por exemplo 4 para 4% ao ano. Esse valor só é usado quando a opção de inflação futura for “Informar minha hipótese”.',
initial:'Informe o saldo ou valor que tinha no mês inicial escolhido, em reais. O app o corrige pela inflação do período para comparar poder de compra.',
final:'Informe o saldo ou valor no mês final escolhido. A comparação desconta a inflação, mas o crescimento desse saldo pode incluir depósitos e não representa, sozinho, rendimento.',
oldIncome:'Informe o total líquido mensal que recebia no mês inicial. Se eram dois depósitos, some ambos. O app compara esse valor com a renda final depois da inflação.',
newIncome:'Informe o total líquido mensal recebido no mês final. Use o mesmo tipo de renda considerado no mês inicial para a comparação fazer sentido.',
netReturn:'Informe a rentabilidade líquida do mesmo período escolhido, em %. Exemplo: 12 para 12% no período inteiro. Não use o crescimento do saldo causado por novos aportes.',
capital:'Informe quanto já tem aplicado ou reservado no começo da simulação, em reais. Esse é o ponto de partida; não inclui os futuros aportes mensais.',
contribution:'Informe quanto pretende adicionar todo mês, em reais. A simulação considera esse aporte no fim de cada mês. Use 0 para simular sem aportes; não há débito automático.',
monthly:'Informe quanto pretende guardar por mês, em reais. Exemplo: 300,00. É uma hipótese do planejamento; salvar não transfere dinheiro nem cadastra pagamentos mensais.',
months:'Informe o prazo em meses. Exemplo: 24 equivale a dois anos. Em metas com uma data desejada preenchida, a data é que define o prazo do cálculo.',
priority:'Escolha a importância desta meta para sua organização: Alta, Média ou Baixa. Isso ajuda a ordenar seus objetivos; não move dinheiro nem altera a rentabilidade.',
saved:'Informe o dinheiro já reservado manualmente para esta meta. Se vincular investimentos, o progresso passa a usar a parcela vinculada e ignora este valor manual, para não somar duas vezes.',
investmentLinks:'Defina qual percentual de cada investimento pertence à meta. Exemplo: 25 destina um quarto daquela posição ao objetivo. É uma associação para acompanhamento; não faz resgate nem transferência.',
holdingId:'Escolha a posição da carteira que receberá a compra. Se não houver uma posição correspondente, o app oferece criar uma. Salvar registra a compra real informada; não envia ordem à corretora.',
fees:'Informe o total de taxas e custos desta compra, em reais. Use 0 se não houve custos. Esse valor será incluído no custo da operação e no cálculo do custo médio.',
reserve:'Informe quanto já existe na sua reserva de emergência, em reais. Não repita aqui valores da carteira. Atualizar uma referência de saldo é diferente de registrar uma transferência para a reserva.',
reserveMonths:'Informe quantos meses de despesas quer cobrir com a reserva. Exemplo: 6 para seis meses. É sua meta de proteção, não o tempo para chegar ao valor.',
portfolio:'Informe investimentos que ainda não detalhou na carteira. Não repita posições já cadastradas nem a reserva. É uma referência patrimonial, não uma nova receita.',
snapshotDate:'Selecione a data em que conferiu esses saldos. O app usa essa referência no histórico; ela não importa movimentações antigas do banco.',
birth:'Informe sua data de nascimento se quiser cálculos que usam sua idade. É opcional. Confira dia, mês e ano; deixar vazio não impede organizar suas finanças.',
salaryDay:'Informe o dia de referência do salário. Para receber em duas datas e criar previsões mensais, use a tela “Salário e receitas”. Este campo sozinho não programa a quinzena.',
distrato:'Se precisar acompanhar um distrato, descreva sua situação. É uma anotação opcional; não registra recebimento nem soma um reembolso ao saldo.',
buffer:'Informe quanto quer preservar além dos compromissos e limites já considerados. Exemplo: 200,00. Esse valor reduz a margem sugerida para compras, mas não transfere nem bloqueia dinheiro no banco.',
opening:'Copie o saldo da carteira no início do mês encerrado. Use a mesma carteira e a mesma abrangência do saldo final. O app precisa desses saldos e dos fluxos para estimar o rendimento.',
closing:'Copie o saldo da mesma carteira no fim do mês encerrado. Registre também todos os aportes e retiradas do mês para que depósitos não sejam confundidos com rentabilidade.',
confirmed:'Marque apenas depois de conferir os saldos e movimentos ou os vínculos descritos ao lado. É sua confirmação dos registros; o app não verifica automaticamente o extrato do banco.',
coveredByCard:'Escolha se este contrato avulso também está representado por uma fatura de cartão. O vínculo evita somar o mesmo saldo duas vezes na visão de dívidas. Confira se a cobertura é completa.',
confirmedCoverage:'Marque somente se o calendário do cartão escolhido representa toda esta obrigação. Se faltam parcelas, complete o calendário antes de confirmar a cobertura.',
paymentCategory:'Informe a categoria dos lançamentos que serão reconhecidos como pagamentos desta dívida. Use uma categoria exclusiva para não associar despesas de outro compromisso.',
scope:'Escolha se quer associar um lançamento específico ou todos os da categoria informada. O vínculo usa pagamentos que já existem; não cria uma segunda despesa.',
transactionId:'Selecione um lançamento que já representa o pagamento desta dívida. Confira valor, data e situação antes de associar. O vínculo não paga nem duplica o lançamento.',
monthlyExtra:'Informe quanto poderia pagar a mais por mês, além do calendário atual. Esse valor é usado apenas no cenário de quitação; não cria pagamentos no extrato.',
lump:'Informe um valor extra disponível para antecipar dívidas uma única vez. Exemplo: 1000,00. A simulação o usa no mês escolhido; não retira dinheiro da conta.',
lumpMonth:'Escolha em qual mês o pagamento extra único estaria disponível. O cenário só usa esse valor nessa data, sem modificar o calendário original.',
discount:'Informe o desconto percentual que conseguiu ou quer testar na antecipação. Exemplo: 10 para 10%. É uma hipótese; o credor precisa confirmar o desconto real.',
order:'Escolha a prioridade usada no cenário de antecipação. A simulação reorganiza os pagamentos conforme a estratégia, sem negociar dívidas nem alterar seus lançamentos.',
respectCash:'Marque para limitar o cenário ao caixa projetado com os dados cadastrados. Receitas incertas ou despesas ausentes podem mudar o resultado; confira seu planejamento.',
strategy:'Avalanche prioriza as maiores taxas de juros; bola de neve prioriza os menores saldos. Escolha a estratégia para comparar o plano de quitação. Nenhum pagamento é feito pela simulação.',
notes:'Acrescente detalhes que ajudem a reconhecer este registro depois, como origem do valor ou condições combinadas. É uma anotação; escrever um valor aqui não o inclui nos cálculos.',
tags:'Digite palavras para organizar o lançamento, separadas por vírgula, por exemplo “viagem, trabalho”. Depois você pode filtrar por essas tags. Elas não substituem a categoria do orçamento.'
};
const guideActions={
'life-expense':'Abre um formulário para registrar um gasto. Você vai informar valor, categoria, situação e data. O saldo só muda ao salvar como pago; no cartão, a compra fica na fatura a pagar.',
'life-income':'Abre um formulário para registrar dinheiro recebido ou previsto. Confirme como recebido apenas depois do depósito; salvar uma previsão não aumenta o saldo atual.',
'life-reconcile':'Abre a comparação com o banco. Você informa o saldo real e uma justificativa. Ao confirmar, o app ajusta o saldo e guarda a diferença sem criar uma receita ou despesa fictícia.',
'life-undo':'Após sua confirmação, desfaz a última alteração financeira disponível neste aparelho. Confira os registros depois. Não desfaz mensagens de relatórios que já tenham sido enviadas.',
'life-invoice-add':'Abre o cadastro do total de uma fatura ainda sem compras lançadas. Não use se a mesma fatura já está detalhada no extrato: isso contaria a despesa duas vezes.',
'spend-review':'Abre o saldo adicional que deseja preservar e a confirmação de conferência do mês. Esse valor reduz a margem para compras; não é transferido ou bloqueado no banco.',
'ux-palette':'Abre a busca de telas, ações e lançamentos. Você pode digitar gasto Uber 22,50 para abrir um formulário de revisão. Nenhum comando salva valores sem sua confirmação.',
'ux-toggle-menu':'Recolhe ou expande o menu lateral para dar espaço à tela. Isso muda apenas a navegação visual e não altera dados.',
'ux-events':'Consulta o histórico local de alterações salvas. Ele ajuda a entender mudanças, mas não é extrato bancário nem substitui uma cópia de segurança.',
'life-invoice-pay':'Abre a confirmação do pagamento da fatura existente. Depois de conferir o banco e salvar, baixa os itens da fatura e reduz o saldo sem criar outra despesa.',
'life-card-items':'Abre o extrato filtrado para este cartão e mês, para conferir as compras que compõem a fatura. Abrir a lista não registra pagamentos.',
'life-check-cards':'Registra que você conferiu os cartões ou não usa cartão. Não paga faturas nem consulta o banco. Use depois de revisar os valores e as datas.',
'life-check-bills':'Registra que você conferiu as contas fixas. Não paga contas nem cria despesas. Confira valor, vencimento e vigência antes de marcar.',
'life-adapt':'Mostra uma confirmação para ajustar o limite desta categoria à média registrada. Aplicar aumenta o espaço previsto para ela a partir deste mês; não reduz seus gastos nem muda meses anteriores.',
'life-module':'Mostra ou oculta este módulo na navegação. Os registros existentes são preservados; você pode ativar o módulo novamente depois.',
'life-clean-models':'Pede confirmação para remover arquivos dos modelos de IA das versões anteriores e liberar espaço. Não remove seus dados financeiros nem as cópias de segurança.',
'life-export-metrics':'Baixa um arquivo CSV com indicadores de uso deste aparelho. Ele serve para avaliar o teste do app; não reúne dados de outros usuários nem sincroniza informações.',
'life-setup':'Abre o cadastro guiado para conferir prioridade, saldo, renda, contas fixas e cartões. Seus dados existentes são usados nas etapas e só mudam conforme você salva.',
'life-receipt-manual':'Abre a conferência da nota para você preencher o total e os dados que a leitura não encontrou. O gasto só será criado depois de revisar e confirmar.',
'fixed-new':'Abre o cadastro de uma conta que se repete, com valor, vencimento e meses de vigência. Criar a conta fixa inclui o compromisso no planejamento; ainda não confirma o pagamento.',
'fixed-edit':'Abre o cadastro para corrigir valor, vencimento e vigência da conta fixa. Salvar muda a referência nos meses de vigência e preserva os pagamentos já registrados.',
'fixed-pay':'Abre a confirmação da data real de pagamento. Ao salvar, baixa o que já estava previsto e registra apenas a diferença que faltar, reduzindo o saldo uma vez.',
'fixed-convert':'Abre os dados para transformar esta categoria em compromisso fixo com vencimento. Confira valor e período antes de salvar; isso não confirma pagamentos.',
'fixed-end':'Abre a escolha do último mês de cobrança. Salvar encerra a repetição após esse mês e mantém os pagamentos e as referências anteriores.',
'fixed-delete39':'Pede confirmação para excluir a definição deste custo fixo de todos os meses. Pagamentos e lançamentos existentes permanecem. Para preservar a referência histórica e só parar a cobrança futura, use Encerrar recorrência.',
'new-card':'Abre o cadastro do cartão: nome, limite, fechamento e vencimento. Cadastrar um cartão não cria compras nem acrescenta dinheiro ao saldo.',
'purchase':'Abre o cadastro de uma compra parcelada. Você informa o valor total, o número de parcelas e o primeiro vencimento. Salvar cria cobranças futuras no cartão, sem pagar a fatura agora.',
'new-budget':'Abre o cadastro de um limite mensal para uma categoria. O limite orienta os avisos e o planejamento, sem criar despesa nem bloquear dinheiro no banco.',
'guide-budget':'Calcula sugestões iniciais de limites usando sua renda líquida de referência. Você pode alterar os valores e escolher o que aplicar antes de criar categorias.',
'salary-open':'Abre a programação salarial. Você pode calcular o líquido CLT, informar um líquido conhecido e dividir o recebimento em duas datas. Nada é depositado automaticamente.',
'salary-receive':'Abre a confirmação de um depósito salarial já recebido. Informe o valor real e a data. Salvar aumenta o saldo uma única vez e atualiza a previsão restante desse mês.',
'salary-pause':'Após confirmação, pausa a programação e cancela as previsões salariais ainda não recebidas. Os depósitos que você já confirmou permanecem no extrato.',
'salary-remove':'Após confirmação, remove a programação salarial e cancela as previsões pendentes. Recebimentos já confirmados são preservados.',
'salary-refresh':'Atualiza as previsões da programação salarial ativa. Não consulta sua conta bancária e não confirma depósitos; os recebimentos continuam previstos até você conferir.',
'spend-open':'Abre o teste de uma compra e as proteções do planejamento. Informe o valor para estimar seu efeito no orçamento. Simular não registra o gasto nem movimenta o banco.',
'email-config':'Abre a configuração da conta que enviará seus relatórios. Você informa remetente, destinatário e credencial de envio. Salvar configura este aparelho; use Enviar teste para verificar.',
'email-test':'Pede confirmação e tenta enviar uma mensagem de teste ao destinatário configurado. Exige internet. A aceitação pelo serviço não comprova entrega; confira também a caixa de spam.',
'email-remove':'Pede confirmação para apagar deste aparelho a credencial de envio por e-mail. Os relatórios locais permanecem, mas novos e-mails precisam de uma configuração válida.',
'email-retry':'Pede confirmação para tentar enviar este relatório novamente. Confira antes sua caixa de entrada: se o envio anterior ficou incerto, a nova tentativa pode gerar uma mensagem repetida.',
'report-new':'Abre um agendamento. Escolha os assuntos, a frequência, o horário e o destino. Salvar não envia na hora; o relatório será processado quando o agendamento vencer e o aparelho executar a tarefa.',
'report-edit':'Abre este agendamento para alterar frequência, horário, conteúdos ou destino. As novas configurações valem a partir de agora; não modificam relatórios já gerados.',
'report-delete':'Pede confirmação para remover este agendamento. Ele deixa de gerar novos relatórios, mas os resumos já gerados permanecem no histórico.',
'report-preview':'Gera uma amostra do texto com os dados atuais. Serve para conferir o conteúdo antes de usar o agendamento; esta prévia não envia uma mensagem.',
'report-check':'Verifica quais agendamentos já venceram e processa os relatórios devidos. Se o destino for e-mail e estiver configurado, essa verificação pode iniciar um envio.',
'report-open':'Mostra o texto deste relatório já gerado. Abrir o resumo não envia novamente nem muda seus registros financeiros.',
'report-download':'Baixa o resumo exibido como arquivo de texto, para guardar ou compartilhar. Não altera dados e não configura envio automático.',
'report-share':'Abre o compartilhamento do relatório exibido. Você escolhe o destinatário e confirma o envio no aplicativo externo. Este botão não é o agendamento automático.',
'research-location':'Pede acesso à localização para preencher coordenadas aproximadas. Depois use Buscar lojas próximas. Não ativa rastreamento contínuo nem garante preço ou estoque nas lojas.',
'research-product':'Inicia uma pesquisa online com o nome deste produto. A descrição é enviada aos catálogos consultados; preços e embalagens precisam ser conferidos.',
'shop-photo':'Abre a câmera para fotografar a nota e tentar extrair seus itens. A leitura pode falhar. Confira nomes, quantidades e valores antes de registrar a compra.',
'shop-gallery':'Abre a seleção de uma foto da nota para tentar ler os produtos. Escolher a imagem ainda não registra estoque nem despesa; revise o resultado.',
'shop-qr':'Abre o leitor de QR fiscal no aparelho compatível. O portal oficial pode exigir internet ou conferência. Revise os itens encontrados antes de registrar.',
'shop-file':'Abre a escolha de um arquivo XML ou texto da nota. XML é o documento com dados estruturados. Os produtos vão para conferência no carrinho; não são salvos como compra imediatamente.',
'shop-paste':'Abre um campo para colar o XML ou texto da nota. O app tenta separar os produtos no carrinho. Confira o resultado antes de confirmar a compra.',
'shop-link':'Abre o campo para colar o endereço do QR fiscal. O app valida o portal e abre a consulta oficial; o portal pode exigir uma ação manual.',
'shop-checkout':'Abre a revisão final do carrinho. Ao confirmar, registra os itens no estoque e o efeito financeiro escolhido: pago, cartão a pagar ou somente estoque se a despesa já existe.',
'shop-clear':'Pede confirmação para esvaziar o carrinho atual. Não use para estornar uma compra já concluída; para isso, confira o histórico de compras.',
'shop-adjust':'Abre a conferência do total final da nota. Após conferir todos os produtos, o ajuste distribui proporcionalmente a diferença entre os itens. Não recupera linhas que a leitura deixou de encontrar.',
'shop-receipt-meta':'Abre o total final e a contagem de itens da nota. Copie os números do documento para comparar com o carrinho. Alterar a contagem não cria os produtos que faltam.',
'shop-read-text':'Mostra o texto que o leitor reconheceu para você corrigir e tentar a extração novamente. Não adivinhe dados ilegíveis: confira a nota ou refaça a foto.',
'shop-expiry':'Inicia a leitura das validades na sequência dos produtos. Aponte para a data da embalagem e confirme o resultado. Se não for reconhecida, informe a data manualmente.',
'shop-stock-expiry':'Abre a leitura de validade dos lotes pendentes. Confira a embalagem correspondente a cada produto antes de aceitar a data encontrada.',
'shop-date':'Abre a data de validade deste lote para correção manual. Salvar atualiza os avisos desse lote e não altera a data da compra.',
'shop-reverse':'Abre a confirmação para desfazer esta compra, conforme os vínculos e usos já registrados. Leia eventuais impedimentos antes de prosseguir; confira estoque e financeiro após a operação.',
'shop-budget':'Define um limite apenas para o carrinho desta compra. Ele ajuda a acompanhar o total no mercado e não substitui o orçamento mensal.',
'shop-store':'Abre o nome da loja para identificar o carrinho e a compra. Informar uma loja não consulta preços nem vincula estoque físico.',
'receipt-open310':'Abre as opções de ler uma nota para registrar o gasto no extrato. Você poderá usar QR, foto, arquivo ou preenchimento manual. O gasto só é criado após sua conferência.',
'receipt-photo310':'Abre a câmera para ler o total e os dados da nota. Não registra a despesa imediatamente. Confira o valor final, a data e como foi pago antes de confirmar.',
'receipt-gallery310':'Abre uma foto salva da nota para leitura. Se faltar algum dado, você pode completá-lo manualmente na conferência.',
'receipt-qr310':'Abre o leitor do QR da nota para consultar os dados fiscais. Exige um portal aceito e pode depender da internet; ainda será necessário conferir o registro.',
'receipt-url310':'Abre um campo para colar o link completo do QR fiscal. Consultar tenta trazer os dados do portal oficial; não registra automaticamente um gasto sem revisão.',
'receipt-file310':'Abre a escolha de XML, HTML ou texto da nota. Esses formatos podem trazer os dados fiscais sem fotografar o papel. Revise o resultado antes de salvar.',
'receipt-text310':'Abre um campo para colar o conteúdo da nota. O app tenta identificar o total e a data; complete o que faltar na conferência.',
'receipt-review310':'Abre o formulário final da despesa. Confirme valor, data, categoria e pagamento. Ao salvar como pago, o valor sai do saldo; no cartão, fica a pagar na fatura.',
'receipt-discard310':'Descarta a leitura que está em revisão. Não deve ser usado para excluir uma despesa já salva; registros salvos são gerenciados no extrato.',
'receipt-close310':'Fecha o painel de leitura de notas. Fechar o painel não confirma o lançamento da despesa.',
'receipt-portal310':'Abre a consulta fiscal oficial no navegador. É uma página externa, que pode pedir uma confirmação. Confira os dados antes de voltar e registrar.',
'new-product':'Abre o cadastro de um produto, com nome, unidade e estoque mínimo. Cadastrar o produto não informa uma quantidade comprada; depois registre uma entrada.',
'edit-product':'Abre o cadastro deste produto para corrigir nome e referências de controle. Confira a unidade antes de salvar, pois receitas e quantidades dependem dela.',
'new-lot':'Abre uma entrada de produto: quantidade, custo, local e validade daquela compra. Se o gasto já existe no extrato, escolha a opção sem novo lançamento para não duplicá-lo.',
'edit-lot':'Abre a validade, o local de armazenamento e as observações desta entrada. Cada lote pode ter uma data diferente; confira a embalagem certa.',
'use-lot':'Abre o registro da quantidade consumida ou descartada. Ao salvar, reduz o estoque e apura o custo de uso. Não cria outra despesa no extrato.',
'undo-use':'Estorna uma baixa de uso ou descarte para devolver sua quantidade ao estoque. Confira o item selecionado e o resultado depois da confirmação.',
'new-recipe':'Abre o cadastro de uma receita. Informe rendimento e somente as quantidades de ingredientes usadas. O app calcula o custo proporcional; cadastrar a receita não consome estoque.',
'edit-recipe':'Abre esta receita para ajustar ingredientes, quantidades, unidades e porções. A estimativa de custo muda conforme os dados salvos; o estoque só baixa ao registrar o preparo.',
'ingredient-add':'Acrescenta uma linha para mais um ingrediente na receita. Escolha o produto e a quantidade usada na receita inteira. Essa linha não é uma nova compra.',
'plan-meal':'Abre o planejamento de uma refeição com dia, receita e porções. Salvar organiza o cardápio e a necessidade de ingredientes, sem baixar o estoque.',
'prepare-meal':'Abre a confirmação de que a refeição foi preparada. Ao salvar, baixa os ingredientes dos lotes disponíveis por validade. Se faltar ingrediente, o preparo é bloqueado sem baixa parcial.',
'house-settings':'Abre quantos dias antes quer ver avisos de validade e as opções do Windows. Permissões e execução do aparelho são necessárias para notificações externas.',
'house-alerts':'Mostra os produtos que precisam de atenção no estoque ou na validade. Confira cada lote no rótulo antes de decidir o uso.',
'export-shopping':'Baixa a lista de reposição em CSV, um arquivo que pode abrir em planilhas. Não registra compras nem muda o estoque.',
'new-goal':'Abre uma meta para definir valor, prazo e aporte mensal hipotético. Você pode vincular investimentos existentes. Salvar a meta não aplica nem transfere dinheiro.',
'goal-project39':'Calcula o prazo estimado e o aporte necessário com os valores da meta. É uma simulação com taxas informadas; não cria transferências mensais.',
'new-debt':'Abre um contrato avulso para acompanhar saldo, taxa e pagamento de referência. Não repita saldos já representados pelos cartões sem indicar a cobertura.',
'db-link-payment':'Abre o vínculo entre uma dívida e pagamentos já existentes. Isso permite acompanhar a quitação sem criar uma segunda despesa.',
'db-edit-contract':'Abre os dados do contrato para corrigir saldo, juros e cobertura por cartão. Use informações do credor; alterações mudam as projeções, sem fazer pagamentos.',
'db-unlink':'Remove a associação deste pagamento com o contrato. O lançamento continua no extrato; apenas deixa de compor este vínculo de dívida.',
'db-refresh':'Recalcula o cenário de dívidas com os parâmetros preenchidos. Não altera o calendário original nem registra antecipações reais.',
'db-reset':'Restaura os parâmetros da simulação e volta ao calendário original. Não apaga contratos nem desfaz pagamentos efetivos.',
'db-export':'Baixa a projeção de dívidas em CSV para abrir em uma planilha. O arquivo é uma cópia dos resultados; não muda seu extrato.',
'new-holding':'Abre uma posição de investimento para informar o que você já possui. Quantidade, custo médio e preço atual têm funções diferentes. O cadastro de posição não é uma ordem de compra.',
'new-simple-asset':'Abre uma aplicação controlada por saldo, como Tesouro ou CDB. Informe total aplicado e saldo atual em reais. Atualizar a posição não substitui o registro de um aporte efetivo.',
'asset-deposit':'Abre o registro de um aporte já realizado nesta aplicação. Ao confirmar, transfere o valor da conta para o investimento no controle do app; não executa uma aplicação no banco.',
'reserve-deposit':'Abre uma transferência da conta para a reserva de emergência. Salvar reduz o saldo da conta e aumenta a reserva no app, sem enviar dinheiro ao banco.',
'asset-buy39':'Abre o registro de uma compra deste ativo, com quantidade, preço efetivo e custos. Salvar atualiza carteira e saldo no app; não compra na corretora.',
'market-buy39':'Abre o registro de uma compra do ativo consultado. Use o preço que realmente pagou e as taxas reais. A consulta e este botão não executam ordens na bolsa.',
'refresh-holding':'Consulta online o preço deste ativo e atualiza a cotação da posição quando os dados são válidos. Não muda a quantidade nem registra uma compra.',
'market-key':'Abre uma chave opcional de acesso à brapi, um dos serviços de consulta. A chave não é sua senha bancária; fica somente na sessão e não garante cobertura de todos os dados.',
'save-analysis':'Calcula os dados informados e abre o nome e a fonte para salvar uma cópia da análise. Os valores ficam associados à data de salvamento; não viram compra.',
'load-analysis':'Abre as premissas desta análise salva e recalcula suas referências. Para dados de mercado novos, faça outra consulta; abrir uma análise antiga não a atualiza automaticamente.',
'sync-portfolio':'Pede confirmação para substituir a carteira manual do perfil pelo total das posições cadastradas. Não soma esse total novamente e não inclui a reserva.',
'add-product':'Acrescenta mais uma alternativa na comparação de aplicações. Preencha taxa, custos e condições dessa alternativa antes de comparar.',
'remove-product':'Remove esta alternativa apenas da simulação comparativa. Não resgata dinheiro nem exclui investimentos da sua carteira.',
'override':'Abre um aporte diferente para um mês específico da simulação. O valor informado substitui o aporte regular daquele mês; não se soma a ele. Use 0 para simular uma pausa.',
'remove-override':'Remove o aporte personalizado deste mês da simulação. O mês volta a seguir as regras regulares do cenário; nenhum movimento real é alterado.',
'save-scenario':'Abre um nome para guardar as premissas da simulação atual e poder revê-las depois. Isso não cria aportes nem muda os saldos reais.',
'load-scenario':'Carrega os parâmetros deste cenário salvo para a simulação. Confira os valores antes de recalcular; não aplica dinheiro.',
'power-refresh':'Busca a divulgação de inflação mais recente disponível nas fontes oficiais. Exige internet. O IPCA é mensal; a consulta de hoje não mede uma inflação diária.',
'power-save':'Guarda os parâmetros desta comparação para você continuar depois. Não altera seu saldo, salário nem metas cadastradas.',
'power-reset':'Pede confirmação para limpar os parâmetros desta comparação. Seus lançamentos, saldos e metas permanecem como estavam.',
'power-use-goal':'Copia o valor-alvo e o saldo da meta escolhida para esta simulação. Confira prazo, aportes e taxas. Simular não altera a meta original.',
'op-close-new':'Abre um fechamento de um mês já encerrado. Você informa os saldos inicial e final e confere aportes e retiradas para estimar a rentabilidade separada dos depósitos.',
'op-close-edit':'Abre os dados deste fechamento mensal. Corrigir saldos ou movimentos muda o histórico de rendimento estimado, sem alterar sua conta bancária.',
'op-close-delete':'Pede confirmação para excluir este fechamento do histórico de rentabilidade. Confira o mês; a exclusão pode interromper a série comparável do gráfico.',
'op-flow-add':'Abre uma movimentação de entrada ou saída da carteira no mês. Registre aportes e resgates para que não sejam confundidos com rendimento. Não é o cadastro de uma nova despesa doméstica.',
'op-flow-import':'Traz aportes já vinculados no extrato para o histórico da carteira. Confira se todas as entradas e saídas do período estão representadas antes de confirmar o fechamento.',
'op-export':'Baixa o relatório como arquivo HTML, que pode ser aberto no navegador. É uma cópia dos indicadores exibidos; guarde-a como informação financeira pessoal.',
'op-print':'Abre a impressão do relatório. Se o sistema oferecer, escolha Salvar como PDF para gerar um arquivo. Não altera seus registros.',
'op-refresh':'Busca uma atualização do índice de inflação usado na comparação do relatório. A divulgação é mensal e pode ainda não cobrir o mês do fechamento.',
'backup':'Baixa uma cópia dos seus dados em JSON, formato usado pelo Horizonte para restaurar registros. Guarde em local seguro. Esse arquivo não inclui a senha de envio de e-mail.',
'import':'Abre a escolha de um backup JSON. Restaurar substitui a base deste aparelho pelos dados do arquivo, após a confirmação. Exporte o estado atual antes se quiser poder voltar.',
'edit-profile':'Abre seus dados e as referências de saldo. Confira o significado de cada valor e não repita investimentos ou reserva. Salvar uma referência não importa extratos do banco.',
'export-ledger':'Baixa os lançamentos selecionados em CSV para abrir em planilhas. Isso é uma exportação para análise, não o backup completo de restauração.',
'export-projection':'Baixa a projeção calculada em CSV. Os resultados são hipóteses da simulação; o arquivo não cria aportes nem altera a carteira.',
'pay':'Abre a confirmação da data real de pagamento ou recebimento dos itens selecionados. Ao salvar, muda sua situação e atualiza o saldo sem criar um segundo lançamento.',
'pay-card':'Abre a baixa dos itens pendentes deste cartão e mês. Confirme somente o que já foi pago no banco; a baixa reduz o saldo da conta.',
'generate-month':'Cria previsões do mês a partir das referências cadastradas. Confira os itens já existentes para não repetir obrigações. Uma previsão não confirma pagamento.',
'reset3':'Abre a confirmação de zerar os dados financeiros e começar do início. É uma ação de exclusão; exporte um backup antes se quiser preservar o estado atual.',
'new-note':'Abre uma anotação de decisão financeira. Descreva a decisão e o motivo para consultar depois. A anotação não registra pagamentos nem muda os cálculos.',
'life-help':'Inicia uma explicação dos itens desta tela. Você pode avançar, voltar ou pular. O tutorial não aciona botões, não preenche campos e não salva valores.',
'guide-editor-help':'Explica os campos e botões deste formulário. Leia os exemplos e o efeito de salvar. O tutorial preserva tudo o que você já digitou.',
'life-help-skip':'Fecha o convite de ajuda desta tela por enquanto. Você pode rever pelo botão Ajuda desta tela. Seus dados e as demais telas não mudam.',
'close':'Fecha este formulário sem enviar os valores que ainda não foram salvos. Para confirmar alterações, use o botão Salvar.',
'quit':'Solicita encerrar o aplicativo. Salve o que está preenchendo antes. Com o serviço encerrado no PC, tarefas locais não são executadas.',
'ux-accept-category':'Preenche a categoria sugerida para este lançamento. Confira se ela corresponde ao gasto antes de salvar; a sugestão não confirma um pagamento.'
};

async function guidePreference(p){guideSettings=await api('guidance/settings',p);return guideSettings;}
function guideVisible(el){
 if(el.hidden||el.closest('[hidden]')||el.closest('#guide-tour-dialog')||!el.getClientRects().length||getComputedStyle(el).visibility==='hidden')return false;
 for(let p=el.parentElement;p;p=p.parentElement){if(p.tagName==='DETAILS'&&!p.open&&el!==p.querySelector(':scope > summary')&&!p.querySelector(':scope > summary')?.contains(el))return false;if(p.tagName==='DIALOG'&&!p.open)return false;}
 return true;
}
function guideStartIntro(){guideStart([{title:'Seu Horizonte, no seu ritmo',text:'O Horizonte usa os valores que você registra para organizar seu dinheiro. Comece pelo cadastro em cinco etapas: saldo da conta, renda, contas fixas e cartões. Uma previsão não é dinheiro já recebido; confira no banco antes de confirmar.'},{target:()=>$('#life-help'),title:'Ajuda quando precisar',text:'Use Ajuda desta tela para percorrer os botões e saber o que fazem. Nos formulários, há exemplos junto aos campos e o botão Explicar os campos. Você pode voltar, pular e rever. O tutorial não preenche nem salva nada.'}], 'intro');}
function guideStart(steps,key){if(guideTour)guideEnd(false);guideTourFocus=document.activeElement;guideTour={steps,key};guideTourIndex=0;$('#guide-screen-invite')?.remove();let d=$('#guide-tour-dialog');if(!d){document.body.insertAdjacentHTML('beforeend','<dialog id="guide-tour-dialog" aria-labelledby="guide-tour-title" aria-describedby="guide-tour-text"><div id="guide-spot" aria-hidden="true"></div><section id="guide-tour-panel"><div class="split-heading"><small id="guide-tour-count"></small><button type="button" class="quiet" id="guide-tour-skip">Pular tutorial</button></div><h3 id="guide-tour-title"></h3><p id="guide-tour-text"></p><div class="actions"><button type="button" class="secondary" id="guide-tour-back">Voltar</button><button type="button" class="primary" id="guide-tour-next">Próximo</button></div></section></dialog>');d=$('#guide-tour-dialog');$('#guide-tour-back').onclick=()=>{guideTourIndex=Math.max(0,guideTourIndex-1);guideDraw();};$('#guide-tour-next').onclick=()=>{if(guideTourIndex===guideTour.steps.length-1)guideEnd(true);else{guideTourIndex++;guideDraw();}};$('#guide-tour-skip').onclick=()=>guideEnd(false);d.addEventListener('cancel',e=>{e.preventDefault();guideEnd(false);});d.addEventListener('keydown',e=>{if(e.key==='Tab'){const a=[...d.querySelectorAll('button:not(:disabled)')],first=a[0],last=a.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}});}d.showModal();guideDraw();$('#guide-tour-next').focus();}
function guideDraw(){if(!guideTour)return;const step=guideTour.steps[guideTourIndex];$('#guide-tour-title').textContent=step.title;$('#guide-tour-text').textContent=step.text;$('#guide-tour-count').textContent=`${guideTourIndex+1} de ${guideTour.steps.length}`;$('#guide-tour-back').disabled=guideTourIndex===0;$('#guide-tour-next').textContent=guideTourIndex===guideTour.steps.length-1?'Concluir':'Próximo';const target=step.target?.();if(target?.isConnected)target.scrollIntoView({block:'center',behavior:'instant'});requestAnimationFrame(guidePosition);}
function guidePosition(){if(!guideTour)return;const target=guideTour.steps[guideTourIndex].target?.(),spot=$('#guide-spot'),panel=$('#guide-tour-panel'),vw=innerWidth,vh=innerHeight,rect=target?.isConnected&&guideVisible(target)?target.getBoundingClientRect():null;spot.hidden=!rect;if(rect){Object.assign(spot.style,{left:Math.max(4,rect.left-5)+'px',top:Math.max(4,rect.top-5)+'px',width:Math.min(vw-8,rect.width+10)+'px',height:Math.min(vh-8,rect.height+10)+'px'});}const w=Math.min(380,vw-24),h=panel.getBoundingClientRect().height;let left=Math.max(12,Math.min(vw-w-12,rect?rect.left:((vw-w)/2))),top=(vh-h)/2;if(rect){top=rect.bottom+14;if(top+h>vh-12)top=rect.top-h-14;if(top<12)top=vh-h-12;}Object.assign(panel.style,{width:w+'px',left:left+'px',top:Math.max(12,top)+'px',maxHeight:(vh-24)+'px'});}
async function guideEnd(done){if(!guideTour)return;const key=guideTour.key;guideTour=null;$('#guide-tour-dialog')?.close();if(guideTourFocus?.isConnected)guideTourFocus.focus();try{if(key!=='editor')await guidePreference({action:'tour',screen:key,status:done?'done':'skipped'});}catch(e){toast('Não foi possível salvar a preferência do tutorial. '+e.message);}guideDecorate();}
openForm=function(...args){guideBaseForm(...args);if(!$('#guide-editor-help'))$('#modal .dialog-actions').insertAdjacentHTML('afterbegin','<button type="button" class="quiet" id="guide-editor-help" data-action="guide-editor-help">? Explicar os campos</button>');};
window.addEventListener('resize',()=>requestAnimationFrame(guidePosition));window.addEventListener('scroll',()=>requestAnimationFrame(guidePosition),true);

function guideLabel(el){
 const label=el.closest('label')||[...(document.querySelectorAll('label[for]'))].find(l=>l.htmlFor===el.id&&el.id);
 let text='';if(label){const copy=label.cloneNode(true);copy.querySelectorAll('input,select,textarea,button,small,.guide-field-copy').forEach(x=>x.remove());text=copy.textContent;}
 return (text||el.getAttribute('aria-label')||el.getAttribute('title')||el.textContent||el.name||'Controle').replace(/\s+/g,' ').trim().slice(0,150);
}
Object.assign(guideActions,{
 'new-tx':guideActions['life-expense'],'ux-new-expense':guideActions['life-expense'],'ux-new-income':guideActions['life-income'],
 'shop-edit':'Abre este item do carrinho para conferir nome, quantidade, unidade e custo total. Corrigir o carrinho não registra a compra; confirme a compra somente depois de revisar todos os itens.',
 'shop-remove':'Remove este item do carrinho atual. Confira a nota para não deixar um produto de fora. Isso não estorna uma compra já concluída.',
 'shop-add':'Abre o cadastro de um item no carrinho. Informe quantidade e preço para acompanhar a soma enquanto compra. A despesa só é registrada na confirmação final.',
 'shop-tab':'Mostra a seção escolhida do carrinho ou histórico de compras. Trocar de seção não confirma compra nem altera estoque.',
 'house-tab':'Mostra a seção escolhida de estoque, cardápio ou receitas. Abrir uma seção não baixa produtos nem cria despesas.',
 'delete-product':'Pede confirmação para excluir o cadastro deste produto. Lotes e receitas vinculados podem impedir a operação; leia o aviso e confira o produto antes de prosseguir.',
 'delete-recipe':'Pede confirmação para excluir esta receita. Confira os planejamentos vinculados e os avisos; a exclusão não desfaz preparos que já foram registrados.',
 'remove-lot':'Pede confirmação para excluir esta entrada de estoque. Usos já registrados podem impedir a operação; se a entrada criou uma despesa vinculada, confira o efeito informado antes de confirmar.',
 'remove-plan':'Remove esta refeição do planejamento após a confirmação apresentada. Não use para estornar ingredientes de um preparo já realizado.',
 'op-open':'Abre o relatório que reúne os indicadores financeiros e o gráfico da carteira contra a inflação. A consulta usa os registros disponíveis e não altera saldos.'
});
function guideContext(el){return [el.closest('#modal')?$('#modal-title')?.textContent:'',el.closest('form')?.id||'',typeof view!=='undefined'?view:''].join(' ').toLowerCase();}
Object.assign(guideFields,{
 type:'Escolha Receita para dinheiro que entra, Despesa para gastos ou Investimento para um aporte. A situação define se já aconteceu. Confira antes de salvar: um movimento confirmado pode alterar o saldo.',
 budget:'Informe o total que consegue destinar por mês às dívidas deste simulador, em reais. Esse valor deve caber depois das despesas essenciais. Calcular não registra nenhum pagamento.',
 delay:'Informe quantos meses quer esperar antes de começar os aportes regulares da simulação. Use 0 para começar sem adiamento. Aportes específicos de um mês continuam valendo conforme cadastrados.',
 growth:'Informe a variação anual do aporte mensal, em %. Exemplo: 4 aumenta o valor guardado em 4% a cada ano; 0 mantém o mesmo valor. Isso é uma hipótese, sem reajuste automático de transferências.',
 spending:'Informe a renda mensal que deseja ter no futuro, em poder de compra de hoje. Exemplo: 4000,00. A simulação considera a inflação para estimar quanto seria necessário no futuro.',
 withdrawal:'Informe a fração anual hipotética que pretende retirar do patrimônio, em %. Exemplo: 3,5 significa 3,5% ao ano. Não é rentabilidade nem garantia de que o dinheiro durará para sempre.',
 costCents:'Informe o total já aplicado nesta posição, em reais. Exemplo: 1000,00. É o custo de aquisição acumulado; o saldo atual, que inclui rendimentos ou perdas, é informado separadamente.',
 source:'Anote de onde veio o preço ou o dado, como extrato da corretora ou balanço de uma data. Isso permite conferir a análise depois. O texto não faz uma consulta automática.',
 desktop:'Marque para permitir os avisos do Horizonte no Windows enquanto o serviço estiver em execução. A permissão do sistema também é necessária. O app não avisa com o computador desligado.',
 lumpMonth:'Informe a posição do mês na simulação: 1 é o mês atual, 2 é o próximo, 3 o seguinte. O pagamento extra único é considerado apenas nesse mês. Não digite um ano ou uma data aqui.'
});
const guideFieldIds={
 'ux-tx-query':'Digite parte da descrição, categoria ou tag para encontrar lançamentos. A busca filtra os registros exibidos; não altera nem apaga os que ficam fora do resultado.',
 'ux-date-basis':'Escolha Vencimento para organizar pela data prevista ou Pagamento para usar a data real dos movimentos confirmados. A escolha muda a consulta, sem mudar as datas registradas.',
 'ux-status':'Filtre todos os lançamentos, só os previstos ou só os realizados. Filtrar não confirma pagamentos nem muda a situação dos registros.',
 'ux-account':'Escolha todos os movimentos, somente conta/Pix ou um cartão específico. A escolha muda a lista consultada e não transfere dinheiro entre origens.',
 'ux-tag':'Escolha uma tag para ver somente lançamentos marcados com ela. Para voltar a ver os demais, selecione Todas. Tags são palavras de organização que você cadastra nos registros.',
 'db-horizon':'Escolha quantos meses a partir do mês atual quer analisar: por exemplo, 12 para um ano. Isso muda a janela da projeção e não exclui parcelas mais distantes.',
 'range3':'Escolha quantos meses quer comparar nas análises. O gráfico usa seus registros do período selecionado; meses sem dados podem não representar toda sua movimentação.'
};
function guideFieldText(el){
 const label=guideLabel(el),l=label.toLowerCase(),ctx=guideContext(el),raw=el.name||el.id||'',name=raw.replace(/^p\d+_/,''),inModal=!!el.closest('#modal');
 if(el.dataset.guideText)return el.dataset.guideText;
 if(guideFieldIds[el.id])return guideFieldIds[el.id];
 if(el.hasAttribute('data-f-date'))return 'Informe a data real da entrada ou saída de dinheiro da carteira, dentro do mês do fechamento. A data ajuda a separar o efeito do aporte do rendimento.';
 if(el.hasAttribute('data-f-kind'))return 'Escolha Aporte externo para dinheiro novo que entrou na carteira ou Retirada externa para dinheiro que saiu dela. Compras e vendas dentro da própria carteira não são fluxos externos.';
 if(el.hasAttribute('data-f-amount'))return 'Informe o valor positivo da entrada ou retirada externa, em reais. A opção de movimentação define o sentido. Esse registro analítico não cria outra despesa no extrato.';
 if(ctx.includes('life-review')&&name==='balance')return 'Marque depois de comparar o saldo do app com o banco. Se houver diferença, use Conferir ou ajustar saldo. Marcar esta caixa não corrige o saldo sozinho.';
 if(ctx.includes('db-scenario')&&name==='cardId')return 'Escolha quais faturas entram na simulação de antecipação: todos os cartões ou apenas um. Isso não exclui as outras dívidas nem paga nenhuma fatura.';
 if(name==='goal'&&ctx.includes('ux-goal'))return 'Selecione a meta cujo prazo quer simular. O app considera o valor que falta e o aporte mensal informado. Selecionar não muda o saldo da meta.';
 if(el.hasAttribute('data-goal-holding'))return guideFields.investmentLinks;
 if(el.closest('.ingredient-row')){
  if(el.matches('select'))return el.hasAttribute('data-ing-unit')?'Escolha a unidade da quantidade usada na receita. Para usar 200 g de um pacote, selecione g. A unidade precisa ser compatível com o produto e o conteúdo da embalagem.':'Escolha o produto cadastrado que entra nesta receita. Confira a unidade e o conteúdo da embalagem para calcular somente a parte consumida.';
  if(el.hasAttribute('data-ing-per'))return 'Informe o conteúdo de uma embalagem na unidade escolhida. Exemplo: pacote de 1 kg contém 1000 g. Esse fator permite calcular o custo de apenas 200 g, em vez do pacote inteiro.';
  return 'Informe a quantidade deste ingrediente usada na receita inteira. Exemplo: 200 com unidade g para 200 g de aveia; 0,5 com unidade un para meia maçã. Não use a quantidade total do estoque.';
 }
 if(/^use\d+$/.test(raw))return 'Marque para incluir esta categoria no orçamento sugerido. Desmarque se ela não faz parte da sua rotina. A categoria só será criada quando você aplicar a seleção.';
 if(/^amount\d+$/.test(raw))return 'Informe o limite mensal que faz sentido para esta categoria, em reais. Exemplo: 600,00 para alimentação. Aplicar o limite não lança gastos nem transfere dinheiro.';
 if(el.id==='month')return 'Escolha o mês que quer consultar. A mudança filtra as telas que usam mês de referência; não muda as datas dos seus lançamentos.';
 if(el.id==='power-goal')return 'Escolha uma meta cadastrada e depois toque em Trazer valor e saldo. A escolha prepara a cópia dos dados para a simulação; não muda a meta original.';
 if(/bank|smtp/.test(l)&&name==='username')return guideFields.username;
 if(name==='name'){
  if(/perfil/.test(ctx)||l==='seu nome')return 'Digite como quer ser identificado no aplicativo, por exemplo seu primeiro nome. Esse campo personaliza o cadastro e não altera saldos nem dados bancários.';
  if(/fixo/.test(ctx))return 'Use um nome exclusivo para esta conta, por exemplo Aluguel. Lançamentos com essa mesma categoria cumprem o compromisso do mês. Não junte duas contas diferentes no mesmo nome.';
  if(/receita e custo/.test(ctx))return 'Dê um nome à preparação, por exemplo Iogurte com maçã. Aqui “receita” significa prato ou refeição, não dinheiro recebido. Ingredientes e porções serão informados abaixo.';
  if(/meta/.test(ctx))return 'Escreva o objetivo que quer alcançar, como Reserva de emergência ou Notebook. O nome ajuda a reconhecer a meta; o valor e o prazo são preenchidos nos outros campos.';
  if(/fatura|cartão/.test(ctx))return 'Dê um nome que permita reconhecer o cartão, por exemplo Nubank pessoal. Não digite número completo, código de segurança ou senha do cartão.';
  if(/agendamento/.test(ctx))return 'Dê um nome ao relatório, por exemplo Gastos da semana. Esse nome identifica o agendamento no histórico; o conteúdo é escolhido nas opções abaixo.';
  if(/produto/.test(ctx))return 'Informe um nome que identifique o produto e a embalagem, por exemplo Aveia 1 kg. A quantidade de estoque e o custo são preenchidos separadamente.';
  if(/dívida|contrato/.test(ctx))return 'Informe um nome para reconhecer o contrato e o credor, por exemplo Empréstimo banco X. Confira separadamente saldo e juros; o nome não calcula encargos.';
  if(/salário|salary/.test(ctx))return 'Dê um nome ao recebimento, por exemplo Salário empresa. Esse texto aparece nas previsões e no extrato; o valor mensal e as datas são definidos separadamente.';
  if(/cenário|análise/.test(ctx))return 'Dê um nome que ajude a reconhecer esta simulação depois, por exemplo Meta em dez anos. Salvar guarda as premissas, sem movimentar dinheiro.';
  return 'Descreva o movimento ou cadastro de forma fácil de reconhecer, por exemplo Mercado do bairro ou Trabalho extra. O nome não define valor nem confirma pagamento; confira os outros campos.';
 }
 if(name==='amount'||name==='total'){
  if(/fatura/.test(l)||/total de uma fatura/.test(ctx))return 'Copie o total desta fatura em reais, por exemplo 700,00. Use somente se essa fatura ainda não tem as compras lançadas no app. O total fica a pagar até você confirmar o pagamento.';
  if(/orçamento|budget|limite/.test(ctx+' '+l))return 'Informe o valor máximo planejado para essa categoria ou compra, em reais. Exemplo: 300,00. Um limite orienta a previsão e os alertas; não é uma despesa nem um bloqueio na conta.';
  if(/substituto|aporte de um mês/.test(ctx+' '+l))return 'Informe o aporte total desejado neste mês, em reais. Ele substitui o aporte regular da simulação, não se soma a ele. Use 0 para simular uma pausa nesse mês.';
  if(/aporte|reserva|transferência/.test(ctx))return 'Informe o valor que você realmente transferiu para esta aplicação ou reserva, em reais. Salvar registra a transferência no app e reduz o saldo da conta; não envia dinheiro ao banco.';
  if(/recebimento salarial/.test(ctx))return 'Copie o valor líquido que realmente caiu no banco nesta data. Se foi só uma parte do salário, informe apenas essa parte. Salvar confirma o depósito e aumenta o saldo uma vez.';
  if(/parcelas/.test(ctx))return 'Informe o valor total da compra, somando todas as parcelas, em reais. Exemplo: compra de 1000,00 em dez vezes deve ter total 1000,00. O app fará a divisão.';
  if(/nota|compra/.test(ctx))return 'Copie o valor final da compra em reais, já com descontos e acréscimos. Exemplo: 65,54. Confira com a nota; a forma de pagamento escolhida define quando o gasto afeta o saldo.';
  return 'Informe o valor deste movimento em reais, sem sinal de R$. Exemplo: 22,50. Use um valor positivo; receita ou despesa e a situação de pagamento determinam o efeito no saldo.';
 }
 if(name==='payment'){
  if(/registrar gasto|registrar recebimento/.test(ctx))return 'Escolha se já pagou/recebeu, se ainda é previsto ou se comprou no cartão. Pago/recebido muda a conta ao salvar; previsto fica no calendário; cartão entra na fatura a pagar.';
  if(el.tagName==='SELECT')return 'Escolha como tratar o gasto: pago agora reduz o saldo; cartão cria um item a pagar na fatura; já lançado/somente estoque evita outra despesa se o pagamento já existe. Confira o cartão e o vencimento quando aplicável.';
  return 'Informe como costuma pagar, por exemplo Conta / Pix. É uma referência do cadastro; escrever uma forma de pagamento não confirma que a conta foi paga.';
 }
 if(name==='date'){
  if(/validade/.test(ctx+' '+l))return guideFields.expiry;
  if(/confirmar pagamento|pagar |confirmar recebimento|preparo/.test(ctx))return 'Escolha a data em que o pagamento, recebimento ou preparo realmente aconteceu, conforme este formulário. Salvar confirma a operação descrita; não use apenas a data em que pretende realizá-la.';
  if(/registrar gasto|registrar recebimento/.test(ctx))return 'Para um movimento pago/recebido, use o dia real da movimentação. Para previsto, use a data esperada. Para compra no cartão, use o vencimento da fatura, como indicado neste formulário.';
  if(/fatura/.test(l))return 'Escolha a data de vencimento desta fatura. Ela define quando o compromisso aparece no calendário. Informar o vencimento não confirma o pagamento.';
  if(/compra|entrada/.test(l))return 'Selecione o dia da compra ou da entrada indicado no documento. Se for cartão, informe o vencimento da fatura no campo próprio. Confira a data antes de confirmar o registro.';
  if(/preço|saldo/.test(l))return 'Informe o dia em que conferiu este preço ou saldo no extrato da aplicação. É a referência do valor cadastrado, não a previsão de um rendimento futuro.';
  if(/planejar refeição/.test(ctx))return 'Escolha o dia em que pretende preparar esta refeição. Salvar cria o planejamento; o estoque só muda ao registrar que você preparou.';
  return 'Escolha dia, mês e ano relativos ao registro indicado no título do formulário. Em previsões, use a data esperada; confirme como pago somente depois da movimentação real.';
 }
 if(name==='due')return /meta/.test(ctx)?'Opcional: escolha até quando quer alcançar a meta. Quando preenchida, essa data define o prazo usado no cálculo. Se deixar vazio, o app usa o prazo em meses informado.':'Escolha o vencimento da fatura associada a esta compra. Use quando a forma de pagamento for cartão. Essa data vai para o calendário, sem confirmar que você já pagou.';
 if(name==='start')return /power/.test(ctx)?'Escolha o mês inicial da comparação histórica. O cálculo compara o fim dos meses escolhidos: exclui a inflação do mês inicial e inclui a do mês final.':'Escolha o primeiro mês em que este cadastro deve valer. Exemplo: novembro de 2026. Na programação salarial, isso define o início das previsões; em contas e limites, define a vigência.';
 if(name==='end')return /power/.test(ctx)?'Escolha o mês final já divulgado para comparar com o inicial. Não use um mês anterior ao início. A inflação futura ainda não foi medida.':'Opcional: escolha o último mês em que este cadastro deve valer. Deixe vazio se não há fim definido. Preencher encerra a referência após esse mês; não apaga pagamentos antigos.';
 if(name==='month')return /fechamento|onepage/.test(ctx)?'Escolha um mês que já terminou para conferir os saldos e os fluxos da carteira. O app compara o rendimento estimado com o IPCA do mesmo mês quando o índice estiver disponível.':'Escolha o mês ao qual este registro ou simulação pertence. Mudar o mês de uma simulação não altera a data dos seus pagamentos reais.';
 if(name==='category')return /produto|comprada|estoque/.test(ctx)?'Escolha o grupo do produto, como Alimentação, Limpeza ou Higiene. Isso organiza o estoque e as análises; não altera a quantidade comprada.':/posição|aplicação|registrar compra ·/.test(ctx)?'Escolha a classe deste investimento, como Ações, FIIs ou Renda fixa. Ela organiza a carteira e a distribuição por classe; não determina sozinha o risco.':'Escolha a categoria que descreve este movimento, como Alimentação ou Transporte. Ela relaciona a despesa ao orçamento. Para uma conta fixa, use exatamente a categoria do compromisso cadastrado.';
 if(name==='kind')return /analysis/.test(ctx)?'Escolha Ação, FII, ETF ou BDR conforme o ativo. Cada categoria tem critérios diferentes; a referência de Graham não é aplicada a FIIs e ETFs.':/baixa de/.test(ctx)?'Escolha Consumo/uso se utilizou o produto ou Descarte/perda se o jogou fora. Ambos reduzem estoque e registram o motivo, sem criar outra despesa.':'Escolha o formato real do documento ou tipo do registro entre as opções. O app usa essa escolha para interpretar os dados; não altere o formato só porque a leitura falhou.';
 if(name==='quantity')return /posição|compra ·/.test(ctx)?'Informe quantas ações ou cotas comprou ou possui, conforme o título. Exemplo: 10 ações. O app multiplica a quantidade pelo preço por unidade; não coloque o valor em reais aqui.':/produto|lote|conferir produto|entrada|baixa de/.test(ctx)?'Informe a quantidade na unidade indicada. Exemplo: 1000 para 1 kg se o produto é controlado em g. Em uma baixa, informe apenas o que foi consumido ou descartado.':'Informe a quantidade deste item na unidade selecionada. Confira se está em unidades, gramas ou mililitros; 200 g deve usar quantidade 200 com unidade g.';
 if(name==='costCents')return guideFields.costCents;
 if(name==='cost')return /posição/.test(ctx)?'Informe o custo médio de aquisição por ação/cota. Exemplo: comprou 10 cotas por 100,00 cada, custo médio 100,00. Em aplicação por saldo, use o total aplicado conforme o formulário.':'Informe o custo total desta entrada ou item, em reais, não o preço de uma única unidade. Exemplo: 2 pacotes por 8,00 cada custaram 16,00. O app calcula o custo proporcional a partir desse total.';
 if(name==='price'||name==='priceCents')return /saldo atual/.test(l)?'Copie o saldo atual desta aplicação, em reais, como aparece no extrato. Esse valor pode diferir do total aplicado por rendimentos e perdas. Atualizar o saldo não registra um novo aporte.':'Informe o preço em reais por uma ação ou cota. Se estiver registrando uma compra, use o preço que realmente pagou; para acompanhar a posição, use o preço de referência conferido.';
 if(name==='target')return /peso/.test(l)?'Informe qual percentual da carteira deseja concentrar neste ativo, de 0 a 100. Exemplo: 10 para 10%. É sua referência de distribuição; o app não compra ou vende para ajustá-la.':'Informe quanto custa hoje o objetivo que quer alcançar, em reais. Exemplo: 5000,00 para um notebook. O preço futuro pode mudar; confira a hipótese de aumento de preços na simulação.';
 if(name==='balance')return 'Copie o saldo ainda devido neste contrato, em reais, conforme informação do credor. Não use o limite do cartão e não repita uma obrigação já integralmente representada nas faturas.';
 if(name==='rate')return /compare/.test(ctx)?'Informe a taxa bruta anual desta alternativa em %. Exemplo: 10 significa 10% ao ano. Não digite 110 para representar 110% do CDI; converta para uma hipótese anual antes de comparar.':'Informe a taxa de juros mensal do contrato, em %. Exemplo: 2 significa 2% ao mês. Consulte a fatura ou o credor; se não sabe e o campo permite, deixe vazio em vez de presumir zero.';
 if(name==='minimum')return /dívida|contrato/.test(ctx)?'Informe o pagamento mensal de referência ou mínimo exigido pelo credor, em reais. Isso ajuda na simulação e não é uma recomendação de pagar apenas o mínimo.':guideFields.minimum;
 if(name==='day'&&/agendamento/.test(ctx))return 'Informe o dia do mês para o relatório mensal, de 1 a 31. Se o mês não tiver esse dia, o app usa o último. Esse campo só vale para a frequência mensal.';
 if(name==='days')return /avisos/.test(ctx)?'Informe com quantos dias de antecedência quer ver o aviso de validade. Exemplo: 3 inclui itens que vencem nos próximos três dias; 0 avisa a partir do dia de vencimento.':'Escolha de 1 a 90 dias. Gastos consideram esse número de dias passados, incluindo hoje; compras e contas consideram os próximos dias, também incluindo hoje.';
 if(name==='overdue')return 'Marque se este saldo está em atraso conforme o credor. É uma identificação manual; não calcula sozinho multas ou juros extras e não registra um pagamento.';
 if(['tax','fee','liquidity','risk'].includes(name))return {tax:'Informe a alíquota percentual de imposto sobre o ganho nesta simulação. Exemplo: 15 para 15%. O modelo aplica a taxa informada ao ganho e não calcula a regra tributária individual de cada aporte.',fee:'Informe o custo percentual anual da aplicação, como taxa de administração. Exemplo: 0,5 para 0,5% ao ano. Use 0 se não houver; não informe um valor em reais aqui.',liquidity:'Informe em quantos dias espera receber o dinheiro após pedir o resgate. Exemplo: 1. É uma informação para comparar acesso ao dinheiro; confira carências e regras reais do produto.',risk:'Descreva os riscos que quer considerar, como oscilação de preço, emissor e prazo. Esse texto ajuda a comparar; o app não verifica garantias nem mede todos os riscos.'}[name];
 if(['balance','transactions','upcoming'].includes(name)&&ctx.includes('life-review'))return {balance:'Marque depois de comparar o saldo do app com o banco. Se houver diferença, use Conferir ou ajustar saldo. Marcar esta caixa não corrige o saldo sozinho.',transactions:'Marque depois de conferir no extrato se os recebimentos e os pagamentos foram registrados corretamente. Não confirma os movimentos automaticamente.',upcoming:'Marque depois de revisar as próximas contas e faturas e suas datas. Isso confirma que fez a conferência; não paga nem agenda um Pix.'}[name];
 if(name==='goal')return 'Escolha o que quer priorizar agora: organizar o mês, sair das dívidas ou começar uma reserva. Isso orienta seu cadastro inicial, sem excluir dados ou movimentar dinheiro.';
 if(name==='checked')return 'Marque depois de fazer a conferência descrita ao lado: compare o documento, o banco ou seus registros. O app depende dessa confirmação sua; marcar não significa que houve uma consulta automática.';
 if(el.type==='checkbox'&&typeof reportTopics35!=='undefined'&&reportTopics35[name])return 'Marque para incluir “'+reportTopics35[name]+'” no relatório. Desmarque para não incluir. O resumo usa os dados registrados e o período definido neste agendamento.';
 if(guideFields[name])return guideFields[name];
 if(el.type==='file')return 'Escolha um arquivo do tipo indicado neste controle. A seleção inicia a leitura ou a preparação descrita na tela; confira os dados e as confirmações antes de concluir uma importação.';
 if(el.tagName==='SELECT')return 'Escolha '+label.toLowerCase()+' entre as opções disponíveis. A seleção define qual informação esta tela usa; confira o resultado antes de salvar. Opções: '+[...el.options].map(o=>o.textContent.trim()).slice(0,6).join('; ')+'.';
 if(el.type==='checkbox')return 'Marque se a opção “'+label+'” se aplica a você. Desmarque para não usá-la. Confira o aviso do formulário antes de salvar.';
 return (el.type==='number'?'Digite o valor de “'+label+'” na unidade indicada, sem acrescentar o símbolo da moeda ou %.':'Informe “'+label+'” conforme o cadastro que está fazendo.')+(el.required?' Este campo precisa ser preenchido para confirmar.':' É opcional; deixe vazio se não tiver essa informação.');
}
function guideControlText(el){
 if(el.matches('input,select,textarea'))return guideFieldText(el);
 const label=guideLabel(el),a=el.dataset.action||'',ctx=guideContext(el);
 if(el.tagName==='A')return 'Abre o destino “'+label+'”. '+(el.getAttribute('href')?.startsWith('/')?'Se for um arquivo ou guia do Horizonte, ele será aberto ou baixado.':'É um link externo: você pode precisar de internet e sair do Horizonte para consultar a fonte.')+' Abrir o link não confirma compras nem pagamentos.';
 if(a==='op-window')return 'Mostra até '+el.dataset.n+' meses no gráfico de rentabilidade. O trecho pode ser menor se faltarem fechamentos ou inflação divulgada. Não inventa meses ausentes nem altera registros.';
 if(a==='db-chart')return 'Mostra no gráfico “'+label+'” ao longo dos meses: saldo devedor é o que resta dever; pagamentos são as saídas previstas; caixa é o saldo projetado. Trocar a curva não faz pagamentos.';
 if(a==='op-flow-remove')return 'Remove esta entrada ou retirada do fechamento que você está editando. A mudança só é confirmada ao salvar o formulário; não exclui lançamentos do extrato.';
 if(a==='ingredient-remove')return 'Retira este ingrediente da receita em edição e atualiza a prévia de custo. Salve a receita para confirmar. Não remove o produto nem seu estoque.';
 if(el.tagName==='SUMMARY')return 'Abre ou recolhe a seção “'+label+'”. Abra para ver os campos e explicações adicionais; depois você pode rever a ajuda para percorrê-los. Abrir esta seção não salva nem altera seus dados.';
 if(el.dataset.guideText)return el.dataset.guideText;
 if(a==='delete')return 'Pede confirmação para excluir este registro de '+({transactions:'extrato',budgets:'orçamento',cards:'cartão',holdings:'investimento',goals:'meta',debts:'dívida',scenarios:'cenário',analyses:'análise',notes:'anotação'}[el.dataset.table]||'cadastro')+'. Se for um movimento pago ou um aporte, sua exclusão pode recalcular os saldos. Leia a confirmação e confira o resultado antes de continuar.';
 if(a==='edit')return 'Abre este registro para corrigir os dados. Nada muda até salvar. Se alterar valor ou situação de um lançamento pago, o saldo pode ser recalculado.';
 if(guideActions[a])return guideActions[a];
 if(a.startsWith('go-')){const dest=a.slice(3);return 'Abre a tela “'+(uxNames[dest]||dest)+'”. '+(guideCopy[dest]||'Você poderá consultar e organizar os registros desse assunto. Abrir a tela não altera valores.');}
 if(a==='life-step')return 'Volta ou avança para outra etapa do cadastro inicial. Para guardar uma resposta que acabou de mudar, use Salvar e continuar antes de trocar de etapa.';
 if(a==='life-budget-tab'||a==='shop-tab'||a==='house-tab')return 'Mostra a seção “'+label+'” dentro desta tela. Trocar de seção não confirma compras nem pagamentos; salve primeiro um formulário que esteja preenchendo.';
 if(a==='life-refresh'||/retry$/.test(a))return 'Tenta carregar novamente os dados desta tela após uma falha. Se a informação depende de uma fonte online, é preciso internet. Não inventa dados quando a fonte não responde.';
 if(el.type==='submit'||(el.tagName==='BUTTON'&&!el.hasAttribute('type')&&el.closest('form'))){
  const id=el.closest('form')?.id;
  const texts={
   'salary-form':el.value==='preview'?'Calcula uma estimativa do líquido e mostra as datas com os valores preenchidos. Não salva a programação nem registra depósitos.':'Salva a programação salarial e cria receitas previstas. Atualiza a renda de referência pelo líquido. O saldo atual só aumenta quando você confirmar cada recebimento.',
   'life-setup-form':'Salva as respostas desta etapa e avança no cadastro. Na última etapa, abre o diagnóstico. Renda prevista não é depósito; o saldo inicial só é definido conforme a sua resposta.',
   'life-review-form':'Registra que você concluiu as três conferências desta semana. É preciso marcar cada uma depois de revisar. O saldo e os pagamentos não são corrigidos automaticamente.',
   'guide-budget-form':'Cria os limites das categorias selecionadas com os valores preenchidos. Não cria despesas nem transfere dinheiro para a margem. Os limites existentes são preservados.',
   'quote-form':'Consulta online o código digitado e preenche os dados disponíveis. Os campos ausentes ficam para conferência; consultar não compra o ativo.',
   'analysis-form':'Calcula indicadores e cenários com os dados preenchidos. As taxas e os múltiplos dos cenários são hipóteses, sem compra ou recomendação automática.',
   'compare-form':'Compara os resultados das alternativas com capital inicial, aportes e taxas informados. Não movimenta dinheiro; o ranking vale apenas para essas hipóteses.',
   'db-scenario-form':'Compara as faturas atuais com uma hipótese de pagamentos extras e desconto. Não altera os lançamentos; o desconto e a possibilidade de antecipar precisam ser confirmados com o banco.',
   'debt3-form':'Simula a quitação dos contratos avulsos com o valor mensal e a estratégia escolhidos. A simulação não registra pagamentos nem substitui o calendário real das faturas.',
   'ux-goal-form':'Estima o prazo da meta com o valor mensal informado, sem rendimentos, inflação ou novos saques. Não modifica o saldo da meta.',
   'debt-form':'Calcula um plano de quitação com o pagamento mensal e a estratégia escolhidos. Não inclui encargos que você não informou e não registra pagamentos reais.',
   'sim-form':'Projeta os cenários de patrimônio e renda com suas premissas de aporte, prazo e taxas. Simular não registra os aportes no extrato.',
   'research-form36':'Pesquisa preços online usando a descrição digitada. Confira embalagem, loja, preço final e condições; a busca não confirma estoque em uma loja próxima.',
   'research-page36':'Tenta consultar o preço público da página informada. Alguns sites não permitem a leitura. Se não houver um preço verificável, o app não o inventa.',
   'research-near36':'Consulta estabelecimentos ao redor das coordenadas, no raio escolhido. Envia coordenadas aproximadas ao serviço de mapas; os resultados não garantem preço nem estoque.',
   'spend-form':'Testa o valor da compra contra o planejamento cadastrado. Não registra o gasto; confira também avisos de dados incompletos antes de decidir.'
  };
  if(texts[id])return texts[id];
  if(el.closest('.power-form'))return 'Calcula esta comparação usando o período e os valores preenchidos. Desconta a inflação quando ela está disponível. O resultado não altera seu saldo, salário ou investimentos.';
  if(id==='editor'){
   if(/conta para envio/.test(ctx))return 'Salva a configuração e a credencial de e-mail somente neste aparelho. Não envia o relatório agora. Depois use Enviar teste para conferir a conexão e o destinatário.';
   if(/registrar gasto|registrar recebimento|confirmar compra|confirmar pagamento|confirmar recebimento|pagar /.test(ctx))return 'Confirma os valores e a situação preenchidos neste formulário. Movimentos pagos/recebidos atualizam o saldo; compras no cartão ficam a pagar. Confira data, valor e os avisos antes de salvar.';
   if(/conferir saldo/.test(ctx))return 'Ajusta o saldo do Horizonte para o valor do banco informado e registra sua justificativa. Isso não cria uma receita nem uma despesa para explicar a diferença.';
   if(/preparo/.test(ctx))return guideActions['prepare-meal'];
   return 'Salva os dados deste cadastro conforme os campos e o aviso acima. Fechar ou Cancelar sai sem enviar o que foi digitado. Confira valores, unidades e datas antes de confirmar.';
  }
  return 'Usa os campos deste formulário para “'+label.toLowerCase()+'”. Confira valores, datas e avisos antes de confirmar; o tutorial apenas explica e não envia o formulário.';
 }
 if(el.dataset.view||el.dataset.target){const dest=el.dataset.view||el.dataset.target;return 'Abre “'+(uxNames[dest]||label)+'”. '+(guideCopy[dest]||'Você pode consultar os dados deste assunto. Navegar não registra pagamentos.');}
 if(el.id==='theme')return 'Alterna entre o tema claro e o escuro para facilitar a leitura. A preferência visual não muda seus dados ou cálculos.';
 if(/imprimir|pdf/.test(label.toLowerCase()))return guideActions['op-print'];
 if(/voltar|cancelar|fechar|×|✕/.test(label.toLowerCase()))return 'Sai desta etapa ou fecha o painel. Se houver um formulário com alterações ainda não salvas, elas não são confirmadas por este botão.';
 return 'Seleciona a opção “'+label+'” nesta tela. Confira a seção e os avisos que aparecem antes de confirmar qualquer alteração. O tutorial não executa esta ação.';
}
let guideDecorating=false,guideDecorationQueued=false,guideHintCounter=0;
function guideDecorate(){
 if(guideDecorating)return;guideDecorating=true;
 try{
  for(const root of [$('#content'),$('#modal')].filter(Boolean)){
   for(const el of root.querySelectorAll('input:not([type=hidden]):not([type=submit]),select,textarea')){
    if(el.closest('.guide-field-copy')||el.type==='file'||el.disabled)continue;
    const label=el.closest('label');if(!label)continue;
    const text=guideFieldText(el);let hint=[...label.children].find(x=>x.classList.contains('guide-field-copy'));
    if(!hint){hint=document.createElement('small');hint.className='guide-field-copy';hint.id='guide-field-'+(++guideHintCounter);label.appendChild(hint);}
    if(hint.textContent!==text)hint.textContent=text;
    const ids=new Set((el.getAttribute('aria-describedby')||'').split(/\s+/).filter(Boolean));ids.add(hint.id);const desc=[...ids].join(' ');if(el.getAttribute('aria-describedby')!==desc)el.setAttribute('aria-describedby',desc);
   }
  }
 }finally{guideDecorating=false;}
}
function guideQueueDecorate(){if(guideDecorationQueued)return;guideDecorationQueued=true;requestAnimationFrame(()=>{guideDecorationQueued=false;guideDecorate();});}
function guideStartScreen(editor=false){
 const root=editor?$('#modal'):$('#content');if(!root)return;guideDecorate();
 const unique=new Set();const elements=[...root.querySelectorAll('input:not([type=hidden]),select,textarea,button,summary,a[href]'),...(!editor?[...document.querySelectorAll('.toolbar input,.toolbar select,.toolbar button:not(#life-help)')]:[])].filter(el=>guideVisible(el)&&!el.disabled&&!['guide-tour','guide-editor-help','guide-skip-screen','life-help','life-help-skip'].includes(el.dataset.action)).filter(el=>{
  // Repeated row actions with the same purpose are explained once; distinct controls are retained.
  const key=el.matches('input,select,textarea')?'field:'+el.name+':'+guideLabel(el)+':'+(el.closest('.ingredient-row')?[...root.querySelectorAll('.ingredient-row')].indexOf(el.closest('.ingredient-row')):''):el.tagName+':'+(el.dataset.action||'')+':'+guideLabel(el)+':'+(el.dataset.table||'');
  if(unique.has(key))return false;unique.add(key);return true;
 });
 const title=editor?$('#modal-title').textContent:uxNames[view]||$('#page-title').textContent;
 guideStart([{target:()=>editor?$('#modal-title'):$('#page-title'),title,text:editor?'Vamos explicar o que preencher e o que acontece ao confirmar. Nada será digitado nem salvo pelo tutorial. Campos dentro de seções fechadas podem ser vistos depois de abri-las e rever a ajuda.':(guideCopy[view]||'Vamos explicar os controles desta tela, sem alterar seus dados.')+' Você pode pular e rever quando precisar.'},...elements.map(el=>({target:()=>el,title:guideLabel(el),text:guideControlText(el)}))],editor?'editor':view);
}
function guideWatch(){const observer=new MutationObserver(records=>{if(records.some(r=>!r.target.closest?.('#guide-tour-dialog,.guide-field-copy')&&[...r.addedNodes,...r.removedNodes].some(n=>n.nodeType===1&&!n.classList?.contains('guide-field-copy'))))guideQueueDecorate();});for(const el of [$('#content'),$('#modal')].filter(Boolean))observer.observe(el,{subtree:true,childList:true});guideDecorate();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',guideWatch,{once:true});else guideWatch();
document.addEventListener('change',e=>{if(e.target.closest('#content,#modal'))guideQueueDecorate();});
