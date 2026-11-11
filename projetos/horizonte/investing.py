"""Transparent educational valuation and comparison, not a recommendation engine."""
import math
from finance import number


def optional(p,k,low=-1e15,high=1e15):
    v=p.get(k)
    return None if v is None or v=='' else number(v,k,low,high)


def analyze(p):
    price=number(p.get('price'),'Preço',.000001,1e12)
    eps=optional(p,'eps');avg=optional(p,'eps3');book=optional(p,'book');dy=optional(p,'dividend',0)
    margin=number(p.get('margin',30),'Margem adicional',0,95)/100
    kind=p.get('kind','Ação');sector=p.get('sector','Não financeiro')
    if kind not in ['Ação','FII','ETF','BDR']:raise ValueError('Categoria inválida')
    stock=kind in ['Ação','BDR']
    pe=price/eps if stock and eps is not None and eps>0 else None
    pe3=price/avg if stock and avg is not None and avg>0 else None
    pb=price/book if book is not None and book>0 else None
    graham=math.sqrt(22.5*avg*book) if stock and avg is not None and book is not None and avg>0 and book>0 else None
    criteria=[]
    def add(name,value,evidence):criteria.append({'name':name,'status':'Não informado' if value is None else ('Atende' if value else 'Não atende'),'evidence':evidence})
    if stock:
        ratio=optional(p,'currentRatio',0);lt=optional(p,'longDebt',0);wc=optional(p,'workingCapital')
        profits=optional(p,'profitYears',0,100);divyears=optional(p,'dividendYears',0,150);growth=optional(p,'growth10',-100,1e6)
        sales=optional(p,'sales',0);floor=optional(p,'salesFloor',0)
        add('Porte • referência pessoal',None if sales is None or floor is None or floor==0 else sales>=floor,'Receita anual versus piso definido por você; não é conversão dos valores históricos do livro.')
        financial=sector=='Não financeiro'
        add('Solidez financeira industrial',None if not financial or ratio is None or lt is None or wc is None else ratio>=2 and lt<=wc,'Liquidez ≥ 2 e dívida de longo prazo ≤ capital de giro. Bancos e seguradoras exigem outra análise.')
        add('Histórico de lucros',None if profits is None else profits>=10,'Anos consecutivos positivos, conferidos nas demonstrações.')
        add('Histórico de dividendos',None if divyears is None else divyears>=20,'Anos consecutivos de pagamentos; não é projeção de distribuição futura.')
        add('Crescimento histórico de LPA',None if growth is None else growth>=100/3,'Crescimento em dez anos comparando médias trienais, informado pelo usuário.')
        add('Preço / lucro médio',None if pe3 is None else pe3<=15,'Preço dividido pelo LPA médio dos últimos três anos.')
        add('Preço / patrimônio combinado',None if pb is None or pe3 is None else pb<=1.5 or pb*pe3<=22.5,'Referência combinada dos múltiplos; não substitui qualidade e contexto setorial.')
    scenarios=[]
    years=number(p.get('years',5),'Horizonte',1,40)
    if stock and eps is not None and eps>0:
        for label,growth,multiple in [('Adverso',p.get('lowGrowth',-5),p.get('lowPE',8)),('Central',p.get('baseGrowth',0),p.get('basePE',12)),('Favorável',p.get('highGrowth',5),p.get('highPE',15))]:
            g=number(growth,'Crescimento do LPA',-90,100)/100
            mult=number(multiple,'Múltiplo final',.01,200)
            terminal=eps*(1+g)**years*mult
            distributions=(dy or 0)*years
            gross=(terminal+distributions)/price
            scenarios.append({'label':label,'growth':g*100,'pe':mult,'terminal':terminal,'distributions':distributions,'totalReturn':(gross-1)*100,'annualized':(gross**(1/years)-1)*100})
    return {'pe':pe,'pe3':pe3,'pb':pb,'yield':None if dy is None else dy/price*100,
            'graham':graham,'marginObserved':None if graham is None else (1-price/graham)*100,
            'entryReference':None if graham is None else graham*(1-margin),'criteria':criteria,'scenarios':scenarios,
            'coverage':sum(c['status']!='Não informado' for c in criteria),'passed':sum(c['status']=='Atende' for c in criteria)}


def compare_products(p):
    capital=number(p.get('capital'),'Capital',0,1e12);contribution=number(p.get('contribution',0),'Aporte mensal',0,1e9);months=int(number(p.get('months'),'Meses',1,600));inflation=number(p.get('inflation',4),'Inflação',0,100)/100
    products=p.get('products',[])
    if not isinstance(products,list) or not 1<=len(products)<=12:raise ValueError('Informe de 1 a 12 alternativas')
    out=[]
    for a in products:
        name=str(a.get('name','Alternativa'))[:120]
        rate=number(a.get('rate'),'Taxa anual bruta',-90,100)/100
        fee=number(a.get('fee',0),'Custo anual',0,50)/100
        tax=number(a.get('tax',0),'Imposto sobre ganho',0,100)/100
        delay=int(number(a.get('liquidity',0),'Prazo de resgate em dias',0,20000))
        rows=[];gross=capital;invested=capital
        rm=((1+rate)*(1-fee))**(1/12)-1
        for m in range(1,months+1):
            gross=gross*(1+rm)+contribution
            invested+=contribution
            net=gross-max(0,gross-invested)*tax
            rows.append({'month':m,'invested':invested,'gross':gross,'net':net,'real':net/(1+inflation)**(m/12)})
        out.append({'name':name,'rate':rate*100,'tax':tax*100,'fee':fee*100,'liquidity':delay,'risk':str(a.get('risk','Não informado'))[:200],'rows':rows,'net':rows[-1]['net'],'real':rows[-1]['real']})
    out.sort(key=lambda x:x['real'],reverse=True)
    return {'products':out,'months':months,'capital':capital,'contribution':contribution,'invested':capital+contribution*months}
