"""Focused personal finance: separate accounts, reviewed imports and monthly routines.
Amounts use integer cents. Transfers are outside income/expense and never change net cash.
"""
import calendar,copy,csv,hashlib,io,re,uuid
from collections import defaultdict
from datetime import date,timedelta
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
from cashflow import local_day,due,months,timeline
from experience import suggest,normalized

def ident():return uuid.uuid4().hex

def money(v,signed=False):
    if type(v) is not int or not (-10**15 if signed else 0)<=v<=10**15:raise ValueError('Valor inválido: use centavos inteiros.')
    return v

def month(v):
    if not isinstance(v,str) or not re.fullmatch(r'(19|20|21)\d\d-(0[1-9]|1[0-2])',v):raise ValueError('Mês inválido.')
    return v

def text(v,limit=160):
    if not isinstance(v,str) or not 1<=len(v.strip())<=limit:raise ValueError('Preencha o texto solicitado.')
    return v.strip()

def fixed_amount(s,b,m):return b.get('monthlyAmounts',{}).get(m,b['amount']) if b.get('estimate') else b['amount']

def account_id(s,t):return t.get('accountId') or s.get('accountBook',{}).get('defaultId','main')

def account_rows(s):
    return copy.deepcopy(s['accountBook']['accounts']) if s.get('accountBook') else [{'id':'main','name':'Conta principal','balance':s['profile']['cash'],'checkedAt':'','archived':False}]

def total_accounts(rows):return None if any(r['balance'] is None for r in rows) else sum(r['balance'] for r in rows)

def flow_by_account(s):
    rows=defaultdict(int)
    for t in s['transactions']:
        if t['status']=='paid' and not t.get('cashIncluded'):rows[account_id(s,t)]+=(1 if t['type']=='income' else -1)*t['amount']
    for t in s.get('accountBook',{}).get('transfers',[]):
        if t['status']=='paid':rows[t['fromId']]-=t['amount'];rows[t['toId']]+=t['amount']
    return rows

def settle_accounts(old,new):
    if not new.get('accountBook'):return new
    book=new['accountBook'];prior=old.get('accountBook')
    if not prior:
        # Enabling preserves the current consolidated cash, it does not import balances.
        if len(book['accounts'])!=1 or book['accounts'][0]['balance']!=old['profile']['cash']:raise ValueError('Ative contas preservando o saldo consolidado atual.')
        return new
    before=flow_by_account(old);after=flow_by_account(new);previous={a['id']:a for a in prior['accounts']}
    for a in book['accounts']:
        old_a=previous.get(a['id']);delta=after[a['id']]-before[a['id']]
        if not old_a:
            if a['balance']!=0 or delta:raise ValueError('Crie a nova conta com saldo zero; depois confira ou transfira o saldo.')
            continue
        if a['balance']!=old_a['balance']:
            if delta:raise ValueError('Confira saldo e registre movimentos em operações separadas.')
        elif delta:
            if a['balance'] is None:raise ValueError('Confira o saldo desta conta antes de movimentá-la.')
            a['balance']+=delta;a['checkedAt']=''
    # Legacy total-balance adjustment is assigned only to the default account.
    aggregate=total_accounts(book['accounts']);expected=new['profile']['cash']
    if aggregate!=expected:
        a=next(a for a in book['accounts'] if a['id']==book['defaultId'])
        if expected is None:raise ValueError('Confira os saldos de todas as contas antes de limpar o total.')
        if aggregate is None:
            unknown=[x for x in book['accounts'] if x['balance'] is None]
            if len(unknown)!=1 or unknown[0]['id']!=a['id']:raise ValueError('Confira o saldo de cada conta separadamente.')
            a['balance']=expected-sum(x['balance'] or 0 for x in book['accounts'])
        else:a['balance']+=expected-aggregate
        a['checkedAt']=''
    new['profile']['cash']=total_accounts(book['accounts']);return new

def validate(s,check_total=True):
    book=s.get('accountBook')
    if book is not None:
        if not isinstance(book,dict) or not isinstance(book.get('accounts'),list) or not 1<=len(book['accounts'])<=30:raise ValueError('Contas inválidas.')
        ids=set()
        for a in book['accounts']:
            if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',str(a.get('id',''))) or a['id'] in ids:raise ValueError('Conta duplicada ou inválida.')
            ids.add(a['id']);text(a.get('name'))
            if a.get('balance') is not None:money(a['balance'],True)
            if type(a.get('archived')) is not bool:raise ValueError('Situação de conta inválida.')
            if a.get('checkedAt'):local_day(a['checkedAt'])
        if book.get('defaultId') not in ids or next(a for a in book['accounts'] if a['id']==book['defaultId'])['archived']:raise ValueError('Conta padrão inválida.')
        ts=book.get('transfers',[])
        if not isinstance(ts,list) or len(ts)>30000:raise ValueError('Transferências inválidas.')
        seen=set()
        for t in ts:
            if t.get('id') in seen or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',str(t.get('id',''))):raise ValueError('Transferência inválida.')
            seen.add(t['id'])
            if t.get('fromId') not in ids or t.get('toId') not in ids or t['fromId']==t['toId']:raise ValueError('Contas de transferência inválidas.')
            if not money(t.get('amount')):raise ValueError('Transferência sem valor.')
            local_day(t.get('date'));text(t.get('name'))
            if t.get('status')!='paid':raise ValueError('Registre transferências somente após realizá-las.')
        if any(account_id(s,t) not in ids for t in s['transactions']):raise ValueError('Lançamento aponta para conta inexistente.')
        if check_total and total_accounts(book['accounts'])!=s['profile']['cash']:raise ValueError('A soma das contas difere do saldo consolidado.')
    keys=set()
    for t in s['transactions']:
        if 'cashIncluded' in t and type(t['cashIncluded']) is not bool:raise ValueError('Tratamento do saldo inválido.')
        k=t.get('statementKey')
        if k:
            if not re.fullmatch('[a-f0-9]{64}',k) or k in keys:raise ValueError('Movimentação de extrato já importada.')
            keys.add(k)
    for b in s['budgets']:
        if 'estimate' in b and type(b['estimate']) is not bool:raise ValueError('Estimativa inválida.')
        values=b.get('monthlyAmounts',{})
        if not isinstance(values,dict) or len(values)>600:raise ValueError('Valores mensais inválidos.')
        for m,v in values.items():month(m);money(v)
    reviews=s.get('monthlyReviews',[])
    if not isinstance(reviews,list) or len(reviews)>1200:raise ValueError('Revisões mensais inválidas.')
    seen=set()
    for r in reviews:
        month(r.get('month'));local_day(r.get('date'));text(r.get('notes') or 'Sem observações',1000)
        if r['month'] in seen:raise ValueError('Revisão mensal duplicada.')
        seen.add(r['month'])
        if not isinstance(r.get('signature'),str) or not re.fullmatch('[a-f0-9]{64}',r['signature']):raise ValueError('Conferência mensal inválida.')

def decimal_cents(raw):
    value=str(raw or '').strip().replace('\u00a0','').replace('R$','').replace(' ','')
    neg=value.startswith('(') and value.endswith(')');value=value.strip('()')
    if ',' in value:value=value.replace('.','').replace(',','.')
    if not re.fullmatch(r'[+-]?\d+(\.\d{1,8})?',value):raise ValueError('Valor monetário ilegível: '+str(raw)[:50])
    try:n=int((Decimal(value)*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    except InvalidOperation:raise ValueError('Valor monetário inválido.')
    if neg:n=-abs(n)
    money(abs(n));return n

def statement_date(raw,fmt='dmy'):
    raw=str(raw or '').strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}(?:$|T)',raw):return local_day(raw[:10]).isoformat()
    if re.match(r'^\d{8}(?:\d{6})?(?:[.\[+\-].*)?$',raw):return date(int(raw[:4]),int(raw[4:6]),int(raw[6:8])).isoformat()
    parts=re.split(r'[/.-]',raw)
    if len(parts)!=3:raise ValueError('Data ilegível: '+raw[:40])
    a,b,c=map(int,parts)
    if c<100:raise ValueError('Use ano com quatro dígitos.')
    return date(c,b,a).isoformat() if fmt=='dmy' else date(c,a,b).isoformat()

def parse_statement(p):
    source=p.get('text','')
    if not isinstance(source,str) or len(source)>5_000_000 or not source.strip():raise ValueError('Selecione um extrato OFX ou CSV de até 5 MB.')
    raw=[];warnings=[];headers=[]
    if p.get('format')=='ofx' or '<OFX' in source.upper():
        if re.search(r'<!DOCTYPE|<!ENTITY',source,re.I):raise ValueError('OFX com declaração externa não é aceito.')
        if re.search(r'<CCSTMT|<INVSTMT',source,re.I):raise ValueError('Use OFX de conta bancária. Faturas e investimentos exigem conferência nos seus cadastros para não duplicar despesas.')
        if len(re.findall(r'<STMTRS[ >]',source,re.I))>1:raise ValueError('Importe o extrato de uma conta por vez.')
        blocks=re.findall(r'<STMTTRN\s*>(.*?)(?:</STMTTRN\s*>|(?=<STMTTRN\s*>)|(?=</BANKTRANLIST))',source,re.I|re.S)
        if not blocks:raise ValueError('Não encontrei movimentações bancárias STMTTRN no OFX. Use extrato de conta, não arquivo de investimentos.')
        for n,b in enumerate(blocks):
            def tag(k):
                m=re.search(r'<'+k+r'\s*>\s*([^<\r\n]*)',b,re.I);return m.group(1).strip() if m else ''
            raw.append({'sourceRow':n+1,'date':tag('DTPOSTED'),'description':tag('NAME') or tag('MEMO'),'amount':tag('TRNAMT'),'bankId':tag('FITID')})
    else:
        delimiter=p.get('delimiter') or (';' if source.splitlines()[0].count(';')>source.splitlines()[0].count(',') else ',')
        if delimiter not in (',',';','\t','|'):raise ValueError('Separador CSV inválido.')
        matrix=list(csv.reader(io.StringIO(source.lstrip('\ufeff')),delimiter=delimiter))
        if not matrix:raise ValueError('CSV vazio.')
        headers=[x.strip() for x in matrix[0]]
        if len(headers)>60:raise ValueError('CSV com colunas demais.')
        mapping=p.get('mapping',{})
        if not mapping:return {'headers':headers,'sample':matrix[1:4],'needsMapping':True,'rows':[],'warnings':[],'delimiter':delimiter}
        for k in ('date','description'):
            if type(mapping.get(k)) is not int or not 0<=mapping[k]<len(headers):raise ValueError('Selecione a coluna de '+k+'.')
        if not any(type(mapping.get(k)) is int and 0<=mapping[k]<len(headers) for k in ('amount','debit','credit')):raise ValueError('Selecione valor assinado ou colunas de débito/crédito.')
        if type(mapping.get('amount')) is int and mapping['amount']>=0 and any(type(mapping.get(k)) is int and mapping[k]>=0 for k in ('debit','credit')):raise ValueError('Use valor com sinal OU débito/crédito separados, não os dois.')
        def cell(r,k):
            i=mapping.get(k);return r[i] if type(i) is int and 0<=i<len(r) else ''
        for n,r in enumerate(matrix[1:]):
            if not any(x.strip() for x in r):continue
            raw.append(dict(sourceRow=n+2,date=cell(r,'date'),description=cell(r,'description'),amount=cell(r,'amount'),debit=cell(r,'debit'),credit=cell(r,'credit'),bankId=cell(r,'bankId')))
    if len(raw)>3000:raise ValueError('Importe no máximo 3000 movimentos por arquivo. Divida o período no banco.')
    rows=[]
    for r in raw:
        try:
            amount=decimal_cents(r['amount']) if str(r.get('amount','')).strip() else abs(decimal_cents(r.get('credit') or '0'))-abs(decimal_cents(r.get('debit') or '0'))
            if not amount:raise ValueError('Linha sem valor ou com débito e crédito iguais.')
            when=statement_date(r['date'],p.get('dateFormat','dmy'));description=text(r['description'] or 'Movimento importado',160)
            if when>p.get('on',date.today().isoformat()):raise ValueError('Movimento futuro: importe somente extrato já realizado.')
            rows.append(dict(index=len(rows),sourceRow=r['sourceRow'],date=when,name=description,amount=abs(amount),type='income' if amount>0 else 'expense',bankId=r['bankId'][:160]))
        except (ValueError,TypeError) as e:warnings.append('Linha '+str(r['sourceRow'])+': '+str(e))
    if not rows and not warnings:raise ValueError('Nenhum movimento encontrado.')
    return dict(rows=rows,warnings=warnings,headers=headers,needsMapping=False)

def statement_preview(s,p):
    aid=p.get('accountId','main');accounts=account_rows(s)
    if not any(a['id']==aid and not a['archived'] for a in accounts):raise ValueError('Escolha uma conta ativa para o extrato.')
    out=parse_statement(p);counts=defaultdict(int);existing={t.get('statementKey') for t in s['transactions'] if t.get('statementKey')}
    for r in out['rows']:
        base=r['bankId'] or '|'.join([r['date'],r['type'],str(r['amount']),normalized(r['name'])]);counts[base]+=1
        key=hashlib.sha256((aid+'|'+base+('' if r['bankId'] else '|'+str(counts[base]))).encode()).hexdigest();r['key']=key;r['duplicate']=key in existing
        r['category']=suggest(s,r['name'],r['type'])['category'] or ('Outras receitas' if r['type']=='income' else 'Outros')
        candidates=[t for t in s['transactions'] if t['amount']==r['amount'] and t['type']==r['type'] and not t.get('cardId') and account_id(s,t)==aid and abs((local_day(t['paidDate'] or t['date'])-local_day(r['date'])).days)<=3]
        r['candidates']=[dict(id=t['id'],name=t['name'],date=t['paidDate'] or t['date'],status=t['status']) for t in candidates[:20]]
        r['caution']='Confira: pode ser transferência entre suas contas ou pagamento de fatura; não registre como despesa/receita nova se já está representado.' if re.search(r'transf|fatura|cart[aã]o|aplica[cç]|resgat',r['name'],re.I) else ''
    return out

def import_statement(s,p):
    preview=statement_preview(s,p);choices=p.get('choices')
    if preview.get('needsMapping'):raise ValueError('Mapeie as colunas antes de importar.')
    if not isinstance(choices,list) or len(choices)>3000:raise ValueError('Confira os movimentos antes de importar.')
    if p.get('confirmed') is not True:raise ValueError('Confirme a conferência e o tratamento do saldo.')
    mode=p.get('balanceMode')
    if mode not in ('history','apply'):raise ValueError('Escolha como tratar o saldo.')
    rows={r['index']:r for r in preview['rows']};seen=set();used=set();n=0;aid=p.get('accountId','main')
    for c in choices:
        index=c.get('index')
        if type(index) is not int or index not in rows or index in seen:raise ValueError('Seleção de linha inválida ou repetida.')
        seen.add(index);r=rows[index];action=c.get('action','skip')
        if action=='skip':continue
        if r['duplicate']:raise ValueError('Um movimento selecionado já foi importado. Atualize a conferência.')
        category=text(c.get('category') or r['category'])
        if action=='link':
            t=next((t for t in s['transactions'] if t['id']==c.get('transactionId')),None)
            if not t or t['id'] in used or not any(x['id']==t['id'] for x in r['candidates']) or t.get('statementKey'):raise ValueError('Vínculo de movimento inválido; confira a linha novamente.')
            used.add(t['id'])
            if t['status']=='planned':t.update(status='paid',paidDate=r['date'],cashIncluded=mode=='history')
            t['statementKey']=r['key'];t['accountId']=aid
        elif action=='new':
            if (r['candidates'] or r['caution']) and c.get('confirmedDifferent') is not True:raise ValueError('Confirme explicitamente a linha parecida ou possível transferência/fatura antes de criar outro movimento.')
            s['transactions'].append(dict(id=ident(),name=r['name'],category=category,amount=r['amount'],date=r['date'],paidDate=r['date'],type=r['type'],status='paid',cardId='',accountId=aid,cashIncluded=mode=='history',statementKey=r['key'],notes='Extrato importado. '+('Saldo já incluía este movimento; correções históricas não alteram o caixa.' if mode=='history' else 'Movimento aplicado ao saldo.')))
        else:raise ValueError('Escolha Ignorar, Novo ou Vincular para cada linha.')
        n+=1
    if not n:raise ValueError('Selecione ao menos um movimento novo ou vínculo.')
    return s

def monthly_report(s,m,on):
    month(m);day=local_day(on);start=m+'-01';end=due(m,31).isoformat();previous=(local_day(start)-timedelta(days=1)).isoformat()[:7]
    tx=[t for t in s['transactions'] if t['status']=='paid' and t['paidDate'].startswith(m+'-')]
    prev=[t for t in s['transactions'] if t['status']=='paid' and t['paidDate'].startswith(previous+'-')]
    values=lambda rows:dict(income=sum(t['amount'] for t in rows if t['type']=='income'),expense=sum(t['amount'] for t in rows if t['type']=='expense'),invested=sum(t['amount'] for t in rows if t['type']=='investment'))
    totals=values(tx);prior=values(prev);active=[b for b in s['budgets'] if b['start']<=m and (not b['end'] or b['end']>=m)]
    names=sorted({b['name'] for b in active}|{t['category'] for t in tx if t['type']=='expense'});categories=[]
    for name in names:
        budget=sum(fixed_amount(s,b,m) if b.get('kind')=='fixed' else b['amount'] for b in active if b['name']==name)
        paid=sum(t['amount'] for t in tx if t['type']=='expense' and t['category']==name);past=sum(t['amount'] for t in prev if t['type']=='expense' and t['category']==name)
        categories.append(dict(name=name,budget=budget,actual=paid,over=paid-budget,change=paid-past))
    pending=[dict(id=t['id'],name=t['name'],date=t['date'],amount=t['amount']) for t in s['transactions'] if t['status']=='planned' and t['date']<=end]
    from routines import fixed_arrears
    y,mo=map(int,m.split('-'));next_m=f'{y+1:04}-01' if mo==12 else f'{y:04}-{mo+1:02}'
    pending += [dict(id='virtual-'+r['id']+'-'+r['date'][:7],name=r['name']+' · previsão recorrente sem lançamento',date=r['date'],amount=r['unregistered']) for r in fixed_arrears(s,next_m)]
    # Signature excludes timestamps/audit and includes values that can invalidate a review.
    import json
    evidence={'tx':sorted(tx,key=lambda t:t['id']),'pending':pending,'budgets':active,'transfers':[t for t in s.get('accountBook',{}).get('transfers',[]) if t['date'].startswith(m+'-')]}
    signature=hashlib.sha256(json.dumps(evidence,sort_keys=True,ensure_ascii=False).encode()).hexdigest();saved=next((r for r in s.get('monthlyReviews',[]) if r['month']==m),None)
    return dict(month=m,closed=end<on,totals=totals,previous=prior,result=totals['income']-totals['expense'],afterInvestments=totals['income']-totals['expense']-totals['invested'],categories=sorted(categories,key=lambda r:-r['actual']),pending=pending,signature=signature,review=saved,changed=bool(saved and saved['signature']!=signature),note='Compara renda de referência e limites com movimentos pela data de pagamento. A diferença do mês não é rendimento de investimentos nem garante saldo bancário. Dados ausentes no extrato tornam a análise parcial.')

def pay_cycles(s,on):
    from spending import overview
    report=overview(s,on);flow=timeline(s,on,90,report['pastFixed']);dates=sorted({t['date'] for t in s['transactions'] if t['type']=='income' and t['status']=='planned' and on<=t['date']<=flow['end']});bounds=[on]+[d for d in dates if d!=on];periods=[]
    for i,start in enumerate(bounds):
        end=(local_day(bounds[i+1])-timedelta(days=1)).isoformat() if i+1<len(bounds) else flow['end'];rows=[r for r in flow['rows'] if start<=r['date']<=end]
        events=[e for r in rows for e in r['events'] if e['source']!='budget']
        periods.append(dict(start=start,end=end,opening=rows[0]['opening'],income=sum(r['income'] for r in rows),commitments=sum(r['committed'] for r in rows),variable=sum(r['variable'] for r in rows),closing=rows[-1]['cash'],lowest=min((r['cash'] for r in rows if r['cash'] is not None),default=None),events=events))
    return dict(periods=periods,firstGap=flow['firstGap'],intradayRisk=flow['intradayRisk'],note='Agrupamento por data prevista de recebimento, até 90 dias. Não garante depósito. Mostra o consumo dos limites variáveis e as contas; transferências próprias não criam renda. O saldo consolidado não garante dinheiro suficiente na conta específica de um pagamento.')

def decision(s,p):
    amount=money(p.get('amount'));on=p.get('on');local_day(on)
    if not amount:raise ValueError('Informe o valor total da decisão.')
    kind=p.get('kind');trial=copy.deepcopy(s);first=p.get('first',on);local_day(first)
    if first<on:raise ValueError('Use hoje ou data futura.')
    from finance import installments
    if kind=='cash':values=[amount];first=on
    elif kind=='installments':
        count=p.get('count')
        if type(count) is not int or not 1<=count<=12:raise ValueError('Use de 1 a 12 parcelas para esta simulação.')
        values=installments(amount,count)
    elif kind=='subscription':values=[amount]*12
    elif kind=='debt':
        debt=next((d for d in s['debts'] if d['id']==p.get('debtId')),None)
        if not debt:raise ValueError('Escolha um contrato cadastrado.')
        if debt.get('coveredByCard'):raise ValueError('Para antecipar fatura de cartão, use o cenário de Dívidas.')
        if p.get('confirmedSettlement') is not True:raise ValueError('Confirme que o valor representa a quitação total combinada com o credor.')
        if any(t.get('debtId')==debt['id'] and t['status']=='planned' for t in s['transactions']):trial['transactions']=[t for t in trial['transactions'] if not(t.get('debtId')==debt['id'] and t['status']=='planned')]
        else:raise ValueError('Vincule primeiro as parcelas deste contrato aos lançamentos para comparar a quitação sem duplicidade.')
        values=[amount];first=on
    else:raise ValueError('Decisão inválida.')
    for i,value in enumerate(values):
        y,m=map(int,first[:7].split('-'));n=y*12+m-1+i;dt=due(f'{n//12:04}-{n%12+1:02}',int(first[-2:])).isoformat()
        trial['transactions'].append(dict(id='decision-'+str(i),name='Decisão simulada',category='Decisão adicional',amount=value,date=dt,paidDate='',status='planned',type='expense',cardId=''))
    end=due(on[:7],31);horizon=366
    from spending import overview
    past=overview(s,on)['pastFixed'];base=timeline(s,on,horizon,past);after=timeline(trial,on,horizon,past)
    bymonth={}
    for a,b in zip(base['rows'],after['rows']):bymonth[a['date'][:7]]=dict(month=a['date'][:7],before=a['cash'],after=b['cash'])
    omitted=sum(t['amount'] for t in trial['transactions'] if t['id'].startswith('decision-') and t['date']>after['end'])
    buffer=s.get('spendingPlan',{}).get('buffer',0)
    return dict(kind=kind,total=sum(values),months=list(bymonth.values()),beforeLowest=base['lowest'],afterLowest=after['lowest'],firstGap=after['firstGap'],belowProtected=after['lowest'] is not None and after['lowest']<buffer,omitted=omitted,until=after['end'],note='Hipótese adicional aos lançamentos atuais, não cria compras ou pagamentos. Inclui receitas previstas e limites cadastrados; não inclui obrigações ausentes, juros desconhecidos ou renovação de salário além do calendário existente. Para compra parcelada, informe o total já com os juros. Antecipação de contrato considera somente parcelas explicitamente vinculadas; confirme o acordo com o credor.')

def report(s,p):
    on=p.get('on',date.today().isoformat());local_day(on);m=p.get('month',on[:7]);month(m)
    life=s.get('lifePlan',{});checks=life.get('checks',{});pending=[]
    if s['profile']['cash'] is None:pending.append('Saldo ainda não informado.')
    for k,label in [('balance','Saldo com o banco'),('income','Renda e datas'),('bills','Contas recorrentes'),('cards','Faturas dos cartões')]:
        if not checks.get(k):pending.append(label+' ainda sem conferência.')
    if s['profile'].get('pendingInstallments'):pending.append('Há parcelas sem vencimento no calendário.')
    if any(a['balance'] is not None and not a.get('checkedAt') for a in account_rows(s)) and s.get('accountBook'):pending.append('Confira o saldo de cada conta; houve movimentação ou ajuste desde a última conferência.')
    for b in s['budgets']:
        if b.get('estimate') and b['start']<=on[:7] and (not b['end'] or b['end']>=on[:7]) and on[:7] not in b.get('monthlyAmounts',{}):pending.append(b['name']+': valor deste mês ainda estimado.')
    from routines import fixed_rows
    groups=defaultdict(list)
    for t in s['transactions']:
        if t['type']=='expense' and t.get('cardId') and t['status']=='planned':groups[(t['cardId'],t['date'][:7])].append(t)
    invoices=[dict(name=next((c['name'] for c in s['cards'] if c['id']==key[0]),'Cartão'),date=min(t['date'] for t in ts),total=sum(t['amount'] for t in ts),count=len(ts)) for key,ts in groups.items()]
    invoices.sort(key=lambda r:r['date'])
    return dict(invoices=invoices,on=on,accounts=account_rows(s),defaultAccount=s.get('accountBook',{}).get('defaultId','main'),transfers=s.get('accountBook',{}).get('transfers',[])[-100:][::-1],monthly=monthly_report(s,m,on),cycles=pay_cycles(s,on),pending=pending,completeness='Parcial — revise os itens abaixo' if pending else 'Conferido conforme seus registros; não é verificação bancária',fixed=fixed_rows(s,on[:7]))

def command(s,p):
    s=copy.deepcopy(s);on=p.get('on',date.today().isoformat());local_day(on);a=p.get('action')
    if a=='accounts-enable':
        if s.get('accountBook'):raise ValueError('As contas já estão ativadas.')
        s['accountBook']={'accounts':account_rows(s),'defaultId':'main','transfers':[]}
    elif a in ('account-new','account-edit','account-reconcile','transfer'):
        if not s.get('accountBook'):raise ValueError('Ative as contas primeiro.')
        book=s['accountBook'];rows=book['accounts'];account=next((r for r in rows if r['id']==p.get('id')),None)
        if a=='account-new':
            name=text(p.get('name'))
            if any(r['name'].casefold()==name.casefold() for r in rows):raise ValueError('Já existe uma conta com esse nome.')
            rows.append(dict(id=ident(),name=name,balance=0,checkedAt='',archived=False))
        if a=='account-edit':
            if not account:raise ValueError('Conta não encontrada.')
            account['name']=text(p.get('name'));account['archived']=p.get('archived') is True
            if account['archived'] and account['balance']!=0:raise ValueError('Transfira o saldo antes de arquivar a conta.')
            if account['archived'] and book['defaultId']==account['id']:raise ValueError('Escolha outra conta padrão primeiro.')
            if p.get('default') is True:
                for t in s['transactions']:t.setdefault('accountId',book['defaultId'])
                book['defaultId']=account['id']
        if a=='account-reconcile':
            if not account:raise ValueError('Conta não encontrada.')
            balance=money(p.get('balance'),True);reason=text(p.get('reason'),300);account['balance']=balance;account['checkedAt']=on
            s['profile']['cash']=total_accounts(rows);s['profile']['snapshotDate']=on
            s['lifePlan']['checks']['balance']=all(r.get('checkedAt')==on for r in rows if not r['archived'])
            s.setdefault('accountReconciliations',[]).append(dict(date=on,accountId=account['id'],reason=reason,balance=balance));s['accountReconciliations']=s['accountReconciliations'][-1000:]
        if a=='transfer':
            value=money(p.get('amount'));when=p.get('date');local_day(when)
            if not value or when>on:raise ValueError('Registre apenas transferências realizadas com valor positivo.')
            f=next((r for r in rows if r['id']==p.get('fromId') and not r['archived']),None);t=next((r for r in rows if r['id']==p.get('toId') and not r['archived']),None)
            if not f or not t or f['id']==t['id']:raise ValueError('Escolha duas contas diferentes e ativas.')
            if f['balance'] is None or t['balance'] is None:raise ValueError('Confira os saldos antes de transferir.')
            book['transfers'].append(dict(id=ident(),name=text(p.get('name') or 'Transferência entre contas'),fromId=f['id'],toId=t['id'],amount=value,date=when,status='paid'))
    elif a=='import':s=import_statement(s,p)
    elif a=='recurring':
        old=next((b for b in s['budgets'] if b['id']==p.get('id')),None);name=text(p.get('name'));amount=money(p.get('amount'));start=month(p.get('start'));end=p.get('end','')
        if not amount:raise ValueError('Informe um valor mensal positivo para planejar.')
        if end:month(end)
        if end and end<start:raise ValueError('Último mês anterior ao primeiro.')
        if type(p.get('day')) is not int or not 1<=p['day']<=31:raise ValueError('Vencimento inválido.')
        if any(b['id']!=(old or {}).get('id') and b['name'].casefold()==name.casefold() for b in s['budgets']):raise ValueError('Use uma categoria exclusiva para a conta recorrente.')
        if old and old['name']!=name and any(t['category']==old['name'] for t in s['transactions']):raise ValueError('Mantenha o nome desta conta para preservar os vínculos.')
        row=dict(old or {},id=old['id'] if old else ident(),name=name,amount=amount,day=p['day'],start=start,end=end,essential=p.get('essential') is True,payment='Conta / Pix',kind='fixed',estimate=p.get('estimate') is True)
        if old:s['budgets']=[row if b['id']==old['id'] else b for b in s['budgets']]
        else:s['budgets'].append(row)
    elif a=='bill-actual':
        b=next((b for b in s['budgets'] if b['id']==p.get('id') and b.get('kind')=='fixed'),None);m=month(p.get('month'));amount=money(p.get('amount'))
        if not b or not b.get('estimate'):raise ValueError('Escolha uma recorrência de valor variável.')
        if b['start']>m or b['end'] and b['end']<m:raise ValueError('Mês fora da vigência da conta.')
        rows=[t for t in s['transactions'] if t['type']=='expense' and t['category']==b['name'] and t['date'].startswith(m+'-')];paid=sum(t['amount'] for t in rows if t['status']=='paid');planned=[t for t in rows if t['status']=='planned']
        if amount<paid or len(planned)>1:raise ValueError('Confira primeiro os pagamentos e previsões desta conta no extrato.')
        b.setdefault('monthlyAmounts',{})[m]=amount
        missing=amount-paid
        if planned:
            if planned[0].get('cardId'):raise ValueError('Confira a cobrança de cartão no extrato antes de ajustar esta conta.')
            if missing:planned[0]['amount']=missing
            else:s['transactions']=[t for t in s['transactions'] if t['id']!=planned[0]['id']]
        elif missing:s['transactions'].append(dict(id=ident(),name=b['name'],category=b['name'],amount=missing,date=due(m,b['day']).isoformat(),paidDate='',status='planned',type='expense',cardId='',accountId=p.get('accountId') or s.get('accountBook',{}).get('defaultId','main'),notes='Valor real da cobrança; confirmar pagamento depois.'))
    elif a=='monthly-review':
        m=month(p.get('month'));r=monthly_report(s,m,on)
        if not r['closed']:raise ValueError('Conclua o fechamento depois que o mês terminar.')
        if not all(p.get(k) is True for k in ('balances','transactions','pending')):raise ValueError('Conclua as três conferências do mês.')
        if p.get('signature')!=r['signature']:raise ValueError('Os dados mudaram; reveja o fechamento antes de concluir.')
        row=dict(month=m,date=on,signature=r['signature'],notes=str(p.get('notes',''))[:1000],pendingCount=len(r['pending']))
        s['monthlyReviews']=[x for x in s.get('monthlyReviews',[]) if x['month']!=m]+[row]
    else:raise ValueError('Ação financeira inválida.')
    return s
