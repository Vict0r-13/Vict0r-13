"""Goal projections and local investment purchases. No broker execution."""
import copy, math, uuid
from datetime import date
from finance import number, month_add


def goal_capital(state, goal):
    links=goal.get('investmentLinks',[])
    if not links:return goal['saved']/100
    assets={a['id']:a for a in state['holdings']}
    return sum(assets[l['holdingId']]['quantity']*assets[l['holdingId']]['price']*l['percent']/100 for l in links)


def goal_projection(state, p):
    goal=next((g for g in state['goals'] if g['id']==p.get('id')),None)
    if goal is None:raise ValueError('Meta não encontrada')
    capital=goal_capital(state,goal);target=goal['target']/100
    monthly=goal.get('monthly',0)/100
    annual=number(goal.get('annual',0),'Retorno líquido anual',-90,100)
    inflation=number(goal.get('inflation',0),'Inflação da compra',0,50)
    horizon=int(number(goal.get('months',120),'Prazo',1,840))
    if goal.get('due'):
        deadline=date.fromisoformat(goal['due']);now=date.today()
        horizon=max(0,(deadline.year-now.year)*12+deadline.month-now.month)
        if horizon>840:raise ValueError('Escolha um prazo de até 70 anos.')
    rm=(1+annual/100)**(1/12)-1;im=(1+inflation/100)**(1/12)-1
    value=capital;reached=0 if value>=target else None;rows=[]
    for m in range(1,841):
        value=value*(1+rm)+monthly
        current_target=target*(1+im)**m
        if reached is None and value>=current_target:reached=m
        if m<=horizon:rows.append(dict(month=m,balance=value,target=current_target,invested=capital+monthly*m))
    factor=(1+rm)**horizon
    weight=sum((1+rm)**i for i in range(horizon))
    deficit=target*(1+im)**horizon-capital*factor
    needed=0.0 if deficit<=0 else max(0,deficit/weight) if weight else None
    return dict(capital=capital,target=target,reached=reached,date=month_add(date.today().replace(day=1).isoformat(),reached)[:7] if reached is not None else None,
                requiredMonthly=needed,monthly=monthly,horizon=horizon,rows=rows,linked=bool(goal.get('investmentLinks')))


def buy(state,p):
    s=copy.deepcopy(state)
    ticker=str(p.get('ticker','')).strip().upper()
    if not __import__('re').fullmatch(r'[A-Z0-9^.]{2,30}',ticker):raise ValueError('Código do ativo inválido')
    quantity=number(p.get('quantity'),'Quantidade',.00000001,1e9)
    price=number(p.get('price'),'Preço por cota',.00000001,1e9)
    fees=p.get('fees',0)
    if type(fees) is not int or not 0<=fees<=10**12:raise ValueError('Custos devem ser centavos inteiros')
    when=p.get('date');date.fromisoformat(when)
    category=p.get('category','Ações')
    if category not in ('Ações','FIIs','ETFs','Outros'):raise ValueError('Classe inválida')
    amount=math.floor(quantity*price*100+0.5)+fees
    if amount<=0 or amount>10**15:raise ValueError('Total de compra inválido')
    ident=p.get('holdingId','')
    if ident:
        asset=next((a for a in s['holdings'] if a['id']==ident),None)
        if not asset or asset.get('mode')=='balance' or asset['ticker'].upper()!=ticker:raise ValueError('Escolha uma posição do mesmo código')
    else:
        if any(a['ticker'].upper()==ticker and a.get('mode')!='balance' for a in s['holdings']):raise ValueError('Já existe uma posição deste código; selecione-a')
        asset=dict(id=uuid.uuid4().hex,name=str(p.get('name',ticker))[:160],ticker=ticker,category=category,quantity=0,cost=0,price=price,target=0,date=when,source='Preço informado na compra',notes='')
        s['holdings'].append(asset)
    s['transactions'].append(dict(id=uuid.uuid4().hex,name='Compra · '+ticker,type='investment',category='Investimentos',amount=amount,date=when,paidDate=when,status='paid',cardId='',notes='Compra registrada no app; não executa ordem em corretora.',destination=asset['id'],stockBuy=dict(quantity=quantity,price=price,fees=fees)))
    return s
