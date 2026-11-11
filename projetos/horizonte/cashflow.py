"""Cash dates, virtual fixed occurrences and budget consumption, integer cents."""
import calendar
from collections import defaultdict
from datetime import date,timedelta

def local_day(value):
    if not isinstance(value,str) or len(value)!=10:raise ValueError('Informe uma data válida.')
    return date.fromisoformat(value)

def months(first,last):
    y,m=first.year,first.month
    while (y,m)<=(last.year,last.month):
        yield f'{y:04}-{m:02}'
        y,m=(y+1,1) if m==12 else (y,m+1)

def due(m,day):
    y,mo=map(int,m.split('-'));return date(y,mo,min(day,calendar.monthrange(y,mo)[1]))

def scheduled(s,on,end):
    """No forecast income invented from reference salary. Never emits paid rows."""
    first=local_day(on);last=local_day(end);rows=[];occurrences=defaultdict(int)
    for t in s['transactions']:
        if t['type']=='expense':occurrences[(t['category'],t['date'][:7])]+=t['amount']
        if t['status']!='planned' or t['date']>end:continue
        if t['type']=='income' and t['date']<on:continue
        rows.append(dict(id=t['id'],name=t['name'],category=t['category'],date=max(t['date'],on),originalDate=t['date'],amount=t['amount'],type=t['type'],source='ledger',cardId=t.get('cardId',''),overdue=t['date']<on))
    # Fixed definitions with the same category supplement existing occurrences.
    targets=defaultdict(int);definitions={}
    for m in months(first,last):
        for b in s['budgets']:
            if b.get('kind')!='fixed' or b['start']>m or b['end'] and b['end']<m:continue
            key=(b['name'],m);from focus import fixed_amount
            targets[key]+=fixed_amount(s,b,m);definitions.setdefault(key,[]).append(b)
    for key,amount in targets.items():
        missing=max(0,amount-occurrences[key])
        if not missing:continue
        name,m=key;d=min(due(m,b['day']) for b in definitions[key]);d=max(first,d)
        if d>last:continue
        rows.append(dict(id='fixed-'+m+'-'+definitions[key][0]['id'],name=name,category=name,date=d.isoformat(),originalDate=due(m,definitions[key][0]['day']).isoformat(),amount=missing,type='expense',source='fixed',cardId='',overdue=due(m,definitions[key][0]['day'])<first))
    return sorted(rows,key=lambda r:(r['date'],r['type']=='income',r['name']))

def cycle(s,on,past_fixed=0):
    first=local_day(on);last=first+timedelta(days=120)
    incomes=[t for t in s['transactions'] if t['status']=='planned' and t['type']=='income' and on<=t['date']<=last.isoformat()]
    next_day=min((t['date'] for t in incomes),default=None)
    # Exclude the payday itself: do not assume the deposit precedes the bills.
    stop=local_day(next_day)-timedelta(days=1) if next_day else due(on[:7],31)
    stop=max(first,stop)
    rows=scheduled(s,on,stop.isoformat());out=sum(t['amount'] for t in rows if t['type']!='income')+past_fixed
    future_variable=0
    for m in months(first,stop):
        if m==on[:7]:continue
        end_month=due(m,31);protected=(min(stop,end_month)-date.fromisoformat(m+'-01')).days+1
        fixed_names={b['name'] for b in s['budgets'] if b.get('kind')=='fixed' and b['start']<=m and (not b['end'] or b['end']>=m)}
        targets=defaultdict(int)
        for b in s['budgets']:
            if b.get('kind')!='fixed' and b['name'] not in fixed_names and b['start']<=m and (not b['end'] or b['end']>=m):targets[b['name']]+=b['amount']
        for name,limit in targets.items():
            used=sum(t['amount'] for t in s['transactions'] if t['type']=='expense' and t['category']==name and (t['paidDate'] if t['status']=='paid' else t['date']).startswith(m+'-'))
            q,r=divmod(max(0,limit-used),end_month.day)
            future_variable+=q*protected+min(r,protected)
    return dict(futureVariable=future_variable,nextIncome=next_day,nextIncomeAmount=sum(t['amount'] for t in incomes if t['date']==next_day),end=stop.isoformat(),days=(stop-first).days+1,commitments=out,rows=rows,basis='recebimento previsto' if next_day else 'fim do mês · sem recebimento programado')

def timeline(s,on,horizon=60,past_fixed=0):
    first=local_day(on)
    if type(horizon) is not int or not 7<=horizon<=730:raise ValueError('Use um horizonte entre 7 e 730 dias.')
    last=first+timedelta(days=horizon-1);events=scheduled(s,on,last.isoformat());by_day=defaultdict(list)
    for row in events:by_day[row['date']].append(row)
    if past_fixed:by_day[on].append(dict(id='past-fixed',name='Fixos anteriores sem lançamento',category='Contas',date=on,originalDate=on,amount=past_fixed,type='expense',source='fixed-history',cardId='',overdue=True))
    budgets=defaultdict(int);fixed=set()
    for m in months(first,last):
        for b in s['budgets']:
            if b['start']<=m and (not b['end'] or b['end']>=m):
                if b.get('kind')=='fixed':fixed.add((b['name'],m))
                else:budgets[(b['name'],m)]+=b['amount']
    spent=defaultdict(int);planned=defaultdict(int)
    for t in s['transactions']:
        if t['type']!='expense':continue
        if t['status']=='paid':spent[(t['category'],t['paidDate'][:7])]+=t['amount']
        else:planned[(t['category'],t['date'][:7])]+=t['amount']
    # Remaining variable limits are hypothetical consumption, not ledger entries.
    for (name,m),limit in budgets.items():
        if (name,m) in fixed:continue
        start=max(first,date.fromisoformat(m+'-01'));end=due(m,31)
        n=(end-start).days+1
        if n<=0:continue
        remain=max(0,limit-spent[(name,m)]-planned[(name,m)]);q,r=divmod(remain,n)
        for i in range(min(n,(last-start).days+1)):
            amount=q+(i<r)
            if amount:by_day[(start+timedelta(days=i)).isoformat()].append(dict(id='budget-'+m+'-'+name,name='Consumo planejado · '+name,category=name,date=(start+timedelta(days=i)).isoformat(),originalDate='',amount=amount,type='expense',source='budget',cardId='',overdue=False))
    cash=s['profile']['cash'];without=cash;buffer=s.get('spendingPlan',{}).get('buffer',0);rows=[];low=None;low_day=None;gap=None;intraday=None
    for i in range(horizon):
        day=(first+timedelta(days=i)).isoformat();items=by_day[day];income=sum(t['amount'] for t in items if t['type']=='income');known=sum(t['amount'] for t in items if t['type']!='income' and t['source']!='budget');variable=sum(t['amount'] for t in items if t['source']=='budget')
        before=cash
        if cash is not None:
            if cash-known-variable<0 and income and intraday is None:intraday=day
            cash+=income-known-variable;without-=known+variable
            if low is None or cash<low:low=cash;low_day=day
            if cash<0 and gap is None:gap=day
        rows.append(dict(date=day,opening=before,income=income,committed=known,variable=variable,cash=cash,withoutIncome=without,events=items))
    return dict(on=on,end=last.isoformat(),rows=rows,lowest=low,lowestDate=low_day,firstGap=gap,intradayRisk=intraday,buffer=buffer,
                notes=['Receitas previstas entram apenas nas datas programadas, sem garantia de depósito. A linha sem receitas futuras mostra o efeito de não recebê-las.','Consumo planejado distribui limites variáveis restantes ao longo de cada mês. Não cria lançamentos. Fixos sem registro aparecem como previsão virtual.','Saldos são de fim de dia. Em dias com recebimento e conta, confira a ordem dos movimentos no banco.','Dívidas sem pagamentos programados, encargos não informados e gastos não cadastrados não podem ser previstos.'])
