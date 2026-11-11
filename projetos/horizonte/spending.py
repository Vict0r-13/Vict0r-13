"""Explainable cash-funded daily allowance and non-mutating purchase simulation.
All monetary values are integer cents. Future income never funds the allowance.
"""
import calendar
from debtbook import distinct as distinct_debts
from collections import defaultdict
from datetime import date


def preferences(p):
    if not isinstance(p,dict):raise ValueError('Planejamento diário inválido')
    if type(p.get('buffer',0)) is not int or not 0<=p.get('buffer',0)<=10**15:raise ValueError('Valor protegido inválido')
    m=p.get('reviewedMonth','')
    if m:
        if not isinstance(m,str) or len(m)!=7:raise ValueError('Mês da conferência inválido')
        date.fromisoformat(m+'-01')
    elif m!='':raise ValueError('Mês da conferência inválido')


def overview(s,on=None):
    on=on or date.today().isoformat()
    if not isinstance(on,str) or len(on)!=10:raise ValueError('Data local inválida')
    day=date.fromisoformat(on);m=on[:7];end=day.replace(day=calendar.monthrange(day.year,day.month)[1]).isoformat()
    days=(date.fromisoformat(end)-day).days+1
    tx=s['transactions'];active=[b for b in s['budgets'] if b['start']<=m and (not b['end'] or b['end']>=m)]
    fixed=defaultdict(int);variable=defaultdict(int)
    from focus import fixed_amount
    for b in active:(fixed if b.get('kind')=='fixed' else variable)[b['name']]+=fixed_amount(s,b,m) if b.get('kind')=='fixed' else b['amount']
    paid=defaultdict(int);planned=defaultdict(int);fixed_paid=defaultdict(int)
    late=0;invest=0;missing_fixed=0
    history=defaultdict(lambda:defaultdict(int))
    for t in tx:
        if t['type']=='expense':
            history[t['category']][t['date'][:7]]+=t['amount']
            if t['status']=='paid':
                if t['paidDate'].startswith(m+'-'):paid[t['category']]+=t['amount']
                if t['date'].startswith(m+'-'):fixed_paid[t['category']]+=t['amount']
        if t['status']!='planned' or t['type']=='income' or t['date']>end:continue
        if t['date']<m+'-01':late+=t['amount']
        elif t['type']=='investment':invest+=t['amount']
        else:planned[t['category']]+=t['amount']
    # Unrecorded fixed occurrences from past months remain protected. Existing
    # planned occurrences are already in late; paid ones already changed cash.
    from routines import fixed_arrears
    missing_fixed=sum(r['unregistered'] for r in fixed_arrears(s,m))
    fixed_open=sum(max(0,amount-fixed_paid[name],planned[name]) for name,amount in fixed.items())
    variable_pending=sum(amount for name,amount in planned.items() if name not in fixed)
    categories=[{'name':name,'limit':limit,'paid':paid[name],'planned':planned[name],
                 'remaining':max(0,limit-paid[name]-planned[name])} for name,limit in sorted(variable.items()) if name not in fixed]
    variable_remaining=sum(c['remaining'] for c in categories)
    pref=s.get('spendingPlan',{});preferences(pref);buffer=pref.get('buffer',0)
    commitments=fixed_open+missing_fixed+late+variable_pending+invest+buffer
    cash=s['profile']['cash'];cash_room=None if cash is None else cash-commitments
    available=None if cash is None or not categories else min(variable_remaining,max(0,cash_room))
    from cashflow import cycle
    pay_cycle=cycle(s,on,missing_fixed)
    cycle_room=None if cash is None else cash-pay_cycle['commitments']-pay_cycle['futureVariable']-buffer
    if cycle_room is not None:
        cash_room=min(cash_room,cycle_room)
        available=None if not categories else min(variable_remaining,max(0,cash_room))
    surplus=None if cash_room is None else max(0,cash_room-variable_remaining)
    warnings=[];block=False
    if cash is None:warnings.append('Informe e confira o saldo atual em conta.');block=True
    if not categories:warnings.append('Cadastre limites mensais para os gastos variáveis.');block=True
    reviewed=pref.get('reviewedMonth')==m
    if not reviewed:warnings.append('Confira as contas, faturas, dívidas e aportes até o fim deste mês.');block=True
    if s['profile'].get('pendingInstallments',0):warnings.append('Existem parcelas sem calendário; distribua os vencimentos antes de decidir.');block=True
    debt=sum(d['balance'] for d in distinct_debts(s))
    overdue_debt=sum(d['balance'] for d in distinct_debts(s) if d['overdue'])
    if overdue_debt:warnings.append('Há dívida marcada em atraso. Regularize ou atualize o cadastro antes de tratar a compra como confortável.');block=True
    if debt:warnings.append('Saldos de dívidas não viram pagamentos automaticamente. Os pagamentos deste mês devem estar no extrato; confira possíveis duplicidades com faturas.')
    if set(fixed)&set(variable):warnings.append('Há categoria usada como fixa e variável ao mesmo tempo; revise o orçamento.');block=True
    if any(c['paid']+c['planned']>c['limit'] for c in categories):warnings.append('Há categoria variável acima do limite, considerando pagos e previstos.');block=True
    if cash_room is not None and cash_room<0:warnings.append('O saldo atual não cobre os compromissos protegidos até o fim do mês.');block=True
    if any(t['status']=='paid' and t['paidDate']>on for t in tx):warnings.append('Há pagamentos ou recebimentos marcados como realizados em data futura; confira o saldo.');block=True
    if any(t['type']=='expense' and t['status']=='paid' and t['paidDate'].startswith(m+'-') and t['category'] not in fixed and t['category'] not in variable for t in tx):warnings.append('Há gastos pagos sem limite de categoria neste mês; confira se o orçamento está completo.')
    future_cards=sum(t['amount'] for t in tx if t['status']=='planned' and t.get('cardId') and t['date']>end)
    return {'on':on,'month':m,'end':end,'days':days,'cash':cash,'daily':None if available is None else available//days,
            'monthly':available,'variableRemaining':variable_remaining,'extra':surplus,'cashRoom':cash_room,
            'commitments':commitments,'fixed':fixed_open,'pastFixed':missing_fixed,'past':late,'plannedExpenses':variable_pending,
            'investments':invest,'buffer':buffer,'categories':categories,'reviewed':reviewed,'ready':not block,
            'cycle':pay_cycle,'cycleRoom':cycle_room,'warnings':warnings,'futureCards':future_cards,'unfundedBudget':None if cash_room is None else max(0,variable_remaining-max(0,cash_room))}


def simulate(s,p):
    amount=p.get('amount')
    if type(amount) is not int or not 0<amount<=10**15:raise ValueError('Informe um preço positivo em centavos inteiros')
    category=p.get('category','__extra__');r=overview(s,p.get('on'))
    if category=='__extra__':room=r['extra'];category_room=None
    else:
        c=next((c for c in r['categories'] if c['name']==category),None)
        if c is None:raise ValueError('Escolha uma categoria variável ativa ou Compra extra')
        category_room=c['remaining']
        room=None if r['cashRoom'] is None else min(category_room,max(0,r['cashRoom']-(r['variableRemaining']-category_room)))
    fits=room is not None and amount<=room
    after_variable=max(0,r['variableRemaining']-(amount if category!='__extra__' else 0))
    after_monthly=None if r['cashRoom'] is None or r['monthly'] is None else min(after_variable,max(0,r['cashRoom']-amount))
    if room is None:status='unknown';message='Falta saldo para calcular. Complete os dados antes de decidir.'
    elif not fits:status='red';message='A compra compromete o planejamento registrado. Reduza o preço, espere ou ajuste o orçamento conscientemente.'
    elif not r['ready']:status='unknown';message='Cabe na estimativa, mas falta conferir o planejamento antes de decidir.'
    elif r['daily'] is not None and amount>r['daily']:status='amber';message='Cabe no mês, mas supera o ritmo diário. O limite dos próximos dias fica menor.' if category!='__extra__' else 'Cabe na sobra extra registrada. O preço supera o ritmo diário dos gastos variáveis.'
    else:status='green';message='Cabe no planejamento registrado e no ritmo diário de hoje.'
    return {'overview':r,'amount':amount,'category':category,'categoryRemaining':category_room,'capacity':room,'fits':fits,'status':status,'message':message,
            'missing':None if room is None else max(0,amount-room),'cashAfter':None if r['cash'] is None else r['cash']-amount,
            'monthlyAfter':after_monthly,'dailyAfter':None if after_monthly is None else after_monthly//r['days'],
            'extraAfter':None if r['cashRoom'] is None else max(0,r['cashRoom']-amount-after_variable)}
