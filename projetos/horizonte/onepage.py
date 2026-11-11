"""One-page report and confirmed month-end portfolio performance.

Money is stored as integer cents. Performance uses daily-weighted Modified
Dietz estimates; portfolio growth alone is never labelled investment return.
"""
import calendar
import copy
import math
from collections import defaultdict
from datetime import date, datetime, timezone
from purchasing_power import month, shift, inflation_factor
from spending import overview as spending_overview
from debtbook import total as total_debt, distinct as distinct_debts


def _money(v):
    if type(v) is not int or not 0 <= v <= 10**15:
        raise ValueError('Informe um valor em centavos inteiros não negativos')
    return v


def validate_closes(rows):
    if not isinstance(rows, list) or len(rows) > 600:
        raise ValueError('Histórico de fechamentos inválido')
    seen = set()
    for r in rows:
        if not isinstance(r, dict):
            raise ValueError('Fechamento inválido')
        m = month(r.get('month'))
        if m in seen:
            raise ValueError('Já existe um fechamento para este mês')
        seen.add(m)
        if m >= date.today().strftime('%Y-%m'):
            raise ValueError('Feche apenas meses já encerrados')
        _money(r.get('opening'));_money(r.get('closing'))
        if r.get('confirmed') is not True:
            raise ValueError('Confirme os saldos e todos os aportes e resgates do mês')
        if not isinstance(r.get('notes',''), str) or len(r.get('notes','')) > 2000:
            raise ValueError('Observação inválida')
        flows = r.get('flows')
        if not isinstance(flows, list) or len(flows) > 1000:
            raise ValueError('Lista de aportes e resgates inválida')
        sources = set()
        for f in flows:
            if not isinstance(f, dict) or f.get('kind') not in ('in','out'):
                raise ValueError('Tipo de movimentação da carteira inválido')
            if not isinstance(f.get('date'), str) or len(f['date']) != 10:
                raise ValueError('Data de movimentação inválida')
            date.fromisoformat(f['date'])
            if not f['date'].startswith(m+'-'):
                raise ValueError('A data de cada aporte ou resgate deve pertencer ao mês do fechamento')
            if _money(f.get('amount')) == 0:
                raise ValueError('Informe valor positivo para o aporte ou resgate')
            src=f.get('sourceTxId','')
            if not isinstance(src,str) or len(src)>100:
                raise ValueError('Origem do aporte inválida')
            if src and src in sources:
                raise ValueError('O mesmo lançamento não pode entrar duas vezes no fechamento')
            if src:sources.add(src)
    return rows


def dietz(row):
    y,m=map(int,row['month'].split('-'));days=calendar.monthrange(y,m)[1]
    net=0;weighted=0;gross=0
    for f in row['flows']:
        v=f['amount']*(1 if f['kind']=='in' else -1)
        net+=v;gross+=abs(v)
        weighted+=v*(days-int(f['date'][-2:]))/days
    gain=row['closing']-row['opening']-net
    base=row['opening']+weighted
    rate=gain/base if base>0 else None
    warnings=[]
    if rate is None:
        warnings.append('Sem capital ponderado positivo para calcular a taxa.')
    elif rate<=-1:
        warnings.append('Taxa estimada igual ou abaixo de −100%; revise saldos, datas e fluxos antes de acumular.')
    if gross and (not row['opening'] or gross>=row['opening']*.1):
        warnings.append('Movimentação relevante no mês: a aproximação pode divergir de uma taxa calculada a cada fluxo.')
    return {'month':row['month'],'opening':row['opening'],'closing':row['closing'],'netFlows':net,'gain':gain,
            'rate':None if rate is None else rate*100,'chainable':rate is not None and rate>-1,'warnings':warnings}


def performance(rows, inflation, end, window=12):
    end=month(end)
    if type(window) is not int or window not in (3,6,12,24,60):
        raise ValueError('Janela deve ser 3, 6, 12, 24 ou 60 meses')
    start=shift(end,1-window)
    selected=sorted([r for r in rows if start<=r['month']<=end],key=lambda r:r['month'])
    result={'points':[],'monthly':[],'warnings':[],'start':None,'end':None,'nominal':None,'inflation':None,'real':None,'gain':None,'missingMonths':[],
            'method':'Estimativa Dietz modificada com fluxos no fim do dia; encadeamento geométrico mensal.','waitingIpca':[], 'windowStart':start,'windowEnd':end,'truncated':False}
    if not selected:
        result['warnings'].append('Registre um fechamento mensal confirmado para iniciar o gráfico; saldos antigos não foram convertidos em rendimentos fictícios.')
        return result
    latest=inflation.get('latestMonth') if inflation.get('available') else None
    result['waitingIpca']=[r['month'] for r in selected if not latest or r['month']>latest]
    history=inflation.get('rows',[]) if latest else []
    segments=[];current=[];previous=None
    for r in selected:
        d=dietz(r);result['monthly'].append(d)
        try:factor=inflation_factor(history,shift(r['month'],-1),r['month'])
        except ValueError:factor=None
        valid=d['chainable'] and factor is not None
        linked=previous is not None and r['month']==shift(previous['month'],1) and r['opening']==previous['closing']
        if not valid or (current and not linked):
            if current:segments.append(current);current=[]
        if valid:current.append((r,d,factor))
        previous=r if valid else None
    if current:segments.append(current)
    if not segments:
        result['warnings'].append('Aguardando IPCA do mesmo período ou revisão dos fechamentos. Não há comparação válida para desenhar.')
        return result
    # Do not bridge missing months or incompatible opening balances.
    segment=segments[-1]
    result['truncated']=len(segment)!=len(selected) or segment[0][0]['month']>start
    result['start']=segment[0][0]['month'];result['end']=segment[-1][0]['month']
    if len(segments)>1:
        result['warnings'].append('Há lacuna ou divergência entre saldos mensais. O gráfico usa somente o último trecho contínuo e comparável.')
    if result['truncated']:
        result['warnings'].append('Cobertura parcial da janela solicitada; veja as datas efetivamente comparadas.')
    if result['waitingIpca']:
        result['warnings'].append('Fechamentos posteriores à última divulgação aguardam o IPCA; não foram preenchidos com inflação zero.')
    all_months={r['month'] for r in selected}
    result['missingMonths']=[shift(start,i) for i in range(window) if shift(start,i) not in all_months and (not latest or shift(start,i)<=latest)]
    result['points'].append({'month':shift(result['start'],-1),'investment':0.0,'ipca':0.0,'real':0.0})
    nominal=1.0;ipca=1.0;gain=0
    for r,d,factor in segment:
        nominal*=1+d['rate']/100;ipca*=factor;gain+=d['gain']
        if not all(math.isfinite(v) for v in (nominal,ipca,nominal/ipca)):
            raise ValueError('Fechamentos geraram valores excessivos; revise os dados')
        result['points'].append({'month':r['month'],'investment':(nominal-1)*100,'ipca':(ipca-1)*100,'real':(nominal/ipca-1)*100})
        result['warnings'].extend(d['warnings'])
    result.update(nominal=(nominal-1)*100,inflation=(ipca-1)*100,real=(nominal/ipca-1)*100,gain=gain)
    result['warnings']=list(dict.fromkeys(result['warnings']))
    return result


def command(state,p):
    out=copy.deepcopy(state);rows=out.setdefault('investmentCloses',[])
    action=p.get('action')
    if action=='delete':
        m=month(p.get('month'))
        if not any(r['month']==m for r in rows):raise ValueError('Fechamento não encontrado')
        out['investmentCloses']=[r for r in rows if r['month']!=m]
    elif action=='save':
        row=copy.deepcopy(p.get('row'));validate_closes([row])
        original=p.get('originalMonth','')
        if original and not any(r['month']==original for r in rows):raise ValueError('Fechamento original não encontrado')
        if row['month']!=original and any(r['month']==row['month'] for r in rows):raise ValueError('Esse mês já tem fechamento. Use Editar.')
        row['updatedAt']=datetime.now(timezone.utc).isoformat()
        out['investmentCloses']=[r for r in rows if r['month']!=original]+[row]
        out['investmentCloses'].sort(key=lambda r:r['month'])
    else:raise ValueError('Operação de fechamento inválida')
    validate_closes(out['investmentCloses'])
    return out


def suggestions(s,m):
    m=month(m);holdings={a['id'] for a in s['holdings']}
    tx=[t for t in s['transactions'] if t['type']=='investment' and t['status']=='paid' and t['paidDate'].startswith(m+'-')]
    flows=[{'kind':'in','date':t['paidDate'],'amount':t['amount'],'sourceTxId':t['id']} for t in tx if t.get('destination') in holdings]
    def snap(when):
        r=next((h for h in s.get('history',[]) if h['date']==when),None)
        return r['portfolio'] if r and type(r.get('portfolio')) is int else None
    y,mo=map(int,m.split('-'));last=f'{m}-{calendar.monthrange(y,mo)[1]:02d}'
    prev=shift(m,-1);y,mo=map(int,prev.split('-'));prior=f'{prev}-{calendar.monthrange(y,mo)[1]:02d}'
    previous=next((r for r in s.get('investmentCloses',[]) if r['month']==prev),None)
    return {'flows':flows,'unclassified':sum(1 for t in tx if not t.get('destination')),
            'opening':previous['closing'] if previous else snap(prior),'closing':snap(last),
            'note':'Sugestões do extrato só incluem aportes pagos vinculados a posições da carteira; não incluem a reserva. Confira resgates, transferências, custos e todos os saldos.'}


def report(s, inflation, m, window=12):
    m=month(m);today=date.today().isoformat();current=today[:7]
    active=lambda period:[b for b in s['budgets'] if b['start']<=period and (not b['end'] or b['end']>=period)]
    from focus import fixed_amount
    bs=active(m);ts=s['transactions'];p=s['profile']
    paid=[t for t in ts if t['status']=='paid' and t['paidDate'].startswith(m+'-')]
    amount=lambda rows:sum(t['amount'] for t in rows)
    income=amount([t for t in paid if t['type']=='income']);expenses=amount([t for t in paid if t['type']=='expense'])
    invested=amount([t for t in paid if t['type']=='investment'])
    fixed_names={b['name'] for b in bs if b.get('kind')=='fixed'}
    fixed=sum(fixed_amount(s,b,m) for b in bs if b.get('kind')=='fixed')
    fixed_paid=0;fixed_open=0
    for b in [b for b in bs if b.get('kind')=='fixed']:
        settled=amount([t for t in ts if t['type']=='expense' and t['category']==b['name'] and t['date'].startswith(m+'-') and t['status']=='paid'])
        fixed_paid+=min(fixed_amount(s,b,m),settled);fixed_open+=max(0,fixed_amount(s,b,m)-settled)
    variable_limit=sum(b['amount'] for b in bs if b.get('kind')!='fixed')
    variable_spent=amount([t for t in paid if t['type']=='expense' and t['category'] not in fixed_names])
    essential=sum(fixed_amount(s,b,m) if b.get('kind')=='fixed' else b['amount'] for b in bs if b['essential'])
    categories=defaultdict(int)
    for t in paid:
        if t['type']=='expense':categories[t['category']]+=t['amount']
    cb=active(current);out=[t for t in ts if t['status']=='planned' and t['type']!='income' and t['date']<=current+'-31']
    late=amount([t for t in out if t['date']<current+'-01'])
    future_invested=amount([t for t in out if t['type']=='investment' and t['date']>=current+'-01'])
    current_paid=[t for t in ts if t['status']=='paid' and t['type']=='expense' and t['paidDate'].startswith(current+'-')]
    current_pending=[t for t in out if t['type']=='expense' and t['date']>=current+'-01']
    names={b['name'] for b in cb}|{t['category'] for t in current_pending}
    remaining=sum(max(0,sum(fixed_amount(s,b,current) if b.get('kind')=='fixed' else b['amount'] for b in cb if b['name']==n)-amount([t for t in current_paid if t['category']==n]),amount([t for t in current_pending if t['category']==n])) for n in names)
    committed=late+future_invested+remaining
    debt=total_debt(s)
    assets={a['id']:a for a in s['holdings']};portfolio=round(sum(a['quantity']*a['price'] for a in s['holdings'])*100) if assets else p['portfolio']
    goals=[]
    for g in s['goals']:
        links=g.get('investmentLinks',[])
        saved=round(sum(assets[l['holdingId']]['quantity']*assets[l['holdingId']]['price']*l['percent'] for l in links if l['holdingId'] in assets)) if links else g['saved']
        goals.append({'name':g['name'],'target':g['target'],'saved':saved,'progress':saved/g['target']*100 if g['target'] else None,'due':g['due']})
    h=s['household'];uses=[u for u in h['uses'] if u['date'].startswith(m+'-')]
    alerts=[l for l in h['lots'] if l['remaining']>0 and l['date']<=today and l.get('expiry')]
    expired=sum(l['expiry']<today for l in alerts)
    nearby=sum(0<=(date.fromisoformat(l['expiry'])-date.today()).days<=7 for l in alerts)
    stocks=[l for l in h['lots'] if l['remaining']>0 and l['date']<=today]
    low=0
    for product in h['products']:
        quantity=sum(l['remaining'] for l in stocks if l['productId']==product['id'] and (not l['expiry'] or l['expiry']>=today))
        if quantity<product['minimum']:low+=1
    scenario=s['scenarios'][-1] if s['scenarios'] else None
    return {'month':m,'asOf':datetime.now().astimezone().isoformat(),'name':p['name'],'currentMonth':current,
            'finance':{'cash':p['cash'],'free':None if p['cash'] is None else p['cash']-committed,'committed':committed,
                       'netWorth':None if p['cash'] is None else p['cash']+p['reserve']+portfolio-debt,'portfolio':portfolio,'reserve':p['reserve'],
                       'income':income,'expenses':expenses,'result':income-expenses,'savingsRate':(income-expenses)/income*100 if income else None,
                       'contributions':invested,'debt':debt,'overdueDebt':sum(d['balance'] for d in distinct_debts(s) if d['overdue']),
                       'essential':essential,'reserveMonths':p['reserve']/essential if essential else None,'fixed':fixed,'fixedPaid':fixed_paid,'fixedOpen':fixed_open,
                       'variableLimit':variable_limit,'variableSpent':variable_spent,'variablePercent':variable_spent/variable_limit*100 if variable_limit else None},
            'dailySpending':spending_overview(s,today),
            'topSpending':[{'category':name,'amount':value,'percent':value/expenses*100 if expenses else 0} for name,value in sorted(categories.items(),key=lambda x:(-x[1],x[0]))[:3]],
            'goals':goals,'scenario':None if not scenario else {'name':scenario['name'],'years':scenario['params'].get('years'),'spending':scenario['params'].get('spending'),'monthly':scenario['params'].get('contribution')},
            'house':{'stockValue':sum(l['remainingCost'] or 0 for l in stocks),'unknownStock':sum(l['remainingCost'] is None for l in stocks),
                     'consumed':sum(i['cost'] or 0 for u in uses if u['kind']!='discard' for i in u['items']),
                     'waste':sum(i['cost'] or 0 for u in uses if u['kind']=='discard' for i in u['items']),
                     'unknownUses':sum(i['cost'] is None for u in uses for i in u['items']),'expired':expired,'nearExpiry':nearby,'lowProducts':low},
            'performance':performance(s.get('investmentCloses',[]),inflation,m,window),
            'inflation':{k:inflation.get(k) for k in ('available','latestMonth','provider','checkedAt','warning','needsCheck','updating')},
            'closes':sorted(s.get('investmentCloses',[]),key=lambda r:r['month'],reverse=True)}
