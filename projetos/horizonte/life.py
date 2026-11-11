"""Guided finance routines. All mutations go through the revisioned Store."""
import copy,uuid,calendar
from datetime import date,datetime,timedelta
from collections import defaultdict
from cashflow import local_day,timeline,cycle

def empty():return {'goal':'organize','step':0,'complete':False,'startedAt':'','completedAt':'','checks':{'income':False,'bills':False,'cards':False,'balance':False},'modules':{'house':False,'investments':False},'reviews':[],'cashJournal':[],'reconciliations':[],'activity':[]}

def preferences(s):
    d=copy.deepcopy(empty());d.update(s.get('lifePlan',{}));return d

def validate(p):
    if not isinstance(p,dict):raise ValueError('Rotina financeira inválida.')
    if not p:return
    if p.get('goal') not in ('organize','debt','reserve'):raise ValueError('Objetivo inválido.')
    if type(p.get('step')) is not int or not 0<=p['step']<=4 or type(p.get('complete')) is not bool:raise ValueError('Etapa inválida.')
    for k,keys in [('checks',('income','bills','cards','balance')),('modules',('house','investments'))]:
        if not isinstance(p.get(k),dict) or any(type(p[k].get(x)) is not bool for x in keys):raise ValueError('Preferência inválida.')
    if not isinstance(p.get('startedAt'),str) or len(p['startedAt'])>40:raise ValueError('Data de início inválida.')
    for k in ('reviews','cashJournal','reconciliations','activity'):
        if not isinstance(p.get(k),list) or len(p[k])>1000:raise ValueError('Histórico da rotina inválido.')
    for r in p['reviews']:
        local_day(r['date'])
        if type(r.get('cash')) is not int or abs(r['cash'])>10**15:raise ValueError('Saldo da revisão inválido.')
    for r in p['cashJournal']:
        local_day(r['date'])
        for key in ('before','after','delta'):
            if r.get(key) is not None and (type(r[key]) is not int or abs(r[key])>2*10**15):raise ValueError('Histórico de saldo inválido.')
        if not isinstance(r.get('reason'),str) or len(r['reason'])>800:raise ValueError('Explicação do saldo inválida.')
    for r in p['activity']:
        local_day(r['date'])
        if r.get('type') not in ('setup','reconcile','review','movement','budget','undo','restore'):raise ValueError('Atividade inválida.')

def money(v,signed=False):
    if type(v) is not int or not (-10**15 if signed else 0)<=v<=10**15:raise ValueError('Informe um valor em centavos inteiros.')
    return v

def mark(s,on,kind):
    p=preferences(s);p['activity']=(p['activity']+[{'date':on,'type':kind}])[-1000:];s['lifePlan']=p

def cleanup_models(root):
    from pathlib import Path
    directory=Path(root)/'models';released=0
    for name in ('qwen-0.5b-q4.gguf','qwen-0.5b-q4.part','qwen3-0.6b-q4.gguf','qwen3-0.6b-q4.part'):
        p=directory/name
        if p.is_file() and not p.is_symlink():released+=p.stat().st_size;p.unlink()
    return {'released':released}

def budget_suggestions(s,on):
    day=local_day(on);m=on[:7];past=[];y,mo=day.year,day.month
    for i in range(3):
        y,mo=(y-1,12) if mo==1 else (y,mo-1);past.append(f'{y:04}-{mo:02}')
    fixed={b['name'] for b in s['budgets'] if b.get('kind')=='fixed' and b['start']<=m and (not b['end'] or b['end']>=m)}
    rows=[]
    for b in s['budgets']:
        if b.get('kind')=='fixed' or b['name'] in fixed or b['start']>m or b['end'] and b['end']<m:continue
        totals=defaultdict(int)
        for t in s['transactions']:
            if t['type']=='expense' and t['status']=='paid' and t['category']==b['name'] and t['paidDate'][:7] in past:totals[t['paidDate'][:7]]+=t['amount']
        if len(totals)<2:continue
        avg=round(sum(totals.values())/len(totals))
        if avg<=b['amount']*1.1:continue
        rows.append(dict(id=b['id'],name=b['name'],current=b['amount'],suggested=avg,months=len(totals),difference=avg-b['amount']))
    return rows

def report(s,p):
    on=p.get('on',date.today().isoformat());day=local_day(on);life=preferences(s)
    from spending import overview
    from debtbook import total
    spending=overview(s,on);flow=timeline(s,on,p.get('horizon',60),spending['pastFixed']);period=cycle(s,on,spending['pastFixed'])
    since=(day-timedelta(days=6)).isoformat();paid=[t for t in s['transactions'] if t['status']=='paid' and since<=t['paidDate']<=on]
    categories=defaultdict(int)
    for t in paid:
        if t['type']=='expense':categories[t['category']]+=t['amount']
    tasks=[]
    if s['profile']['cash'] is None:tasks.append(dict(kind='balance',title='Informe o saldo em conta',text='Sem o saldo, não podemos calcular quanto está disponível.'))
    elif not life['checks']['balance']:tasks.append(dict(kind='balance',title='Confira o saldo com o banco',text='Compare o valor registrado e explique qualquer diferença.'))
    if not life['checks']['income']:tasks.append(dict(kind='income',title='Confira quando vai receber',text='Informe datas e valores líquidos; recebimentos previstos não são dinheiro disponível agora.'))
    if not life['checks']['bills']:tasks.append(dict(kind='bills',title='Revise suas contas fixas',text='Inclua o que precisa pagar, mesmo quando ainda não recebeu a cobrança.'))
    if not life['checks']['cards']:tasks.append(dict(kind='cards',title='Confira cartões e próximas faturas',text='Você pode confirmar que não utiliza cartão. Se utiliza, confira os vencimentos.'))
    from debtbook import distinct
    if any(d['balance']>0 and not any(t.get('debtId')==d['id'] for t in s['transactions']) for d in distinct(s)):tasks.append(dict(kind='debts',title='Confira pagamentos dos contratos',text='Saldos de dívidas não geram parcelas automaticamente. Associe ou registre os pagamentos para completar o calendário.'))
    if flow['firstGap']:tasks.append(dict(kind='cashflow',title='Há falta de caixa projetada em '+flow['firstGap'].split('-')[2]+'/'+flow['firstGap'][5:7],text='Veja a data e o valor. O cenário inclui receitas previstas e consumo planejado.'))
    if not s['budgets']:tasks.append(dict(kind='budget',title='Crie seu primeiro orçamento',text='Comece por uma sugestão editável, baseada na renda líquida.'))
    last=life['reviews'][-1]['date'] if life['reviews'] else None;review_due=last is None or (day-local_day(last)).days>=7
    if review_due:tasks.append(dict(kind='review',title='Faça sua revisão da semana',text='Confira pagamentos, recebimentos e os próximos dias.'))
    if not period['nextIncome']:tasks.append(dict(kind='income',title='Programe o próximo recebimento',text='A renda mensal de referência não é convertida automaticamente em um depósito.'))
    invoices=[];groups=defaultdict(list)
    for t in s['transactions']:
        if t['type']=='expense' and t.get('cardId') and t['status']=='planned':groups[(t['cardId'],t['date'][:7])].append(t)
    for (card,m),rows in sorted(groups.items(),key=lambda x:min(r['date'] for r in x[1])):
        invoices.append(dict(cardId=card,month=m,name=next((c['name'] for c in s['cards'] if c['id']==card),'Cartão'),total=sum(t['amount'] for t in rows),date=min(t['date'] for t in rows),count=len(rows),ids=[t['id'] for t in rows]))
    warnings=list(spending['warnings'])
    if not all(life['checks'].values()):warnings.append('O cadastro ainda tem informações sem conferência. A análise é parcial.')
    if s['profile'].get('pendingInstallments'):warnings.append('Existem parcelas sem calendário; os vencimentos ainda não estão completos.')
    if any(t.get('cardId') and t['category'].startswith('Fatura ·') and t['status']=='planned' for t in s['transactions']):warnings.append('Faturas consolidadas não têm categorias detalhadas. Elas são protegidas separadamente dos limites variáveis; revise antes de substituir o total por compras detalhadas.')
    if flow['intradayRisk']:warnings.append('Há contas e recebimentos no mesmo dia; confira a ordem no banco em '+flow['intradayRisk']+'.')
    active_days=sorted({r['date'] for r in life['activity']});first=active_days[0] if active_days else None
    elapsed=None
    try:
        if life.get('startedAt') and life.get('completedAt'):elapsed=max(0,round((datetime.fromisoformat(life['completedAt'])-datetime.fromisoformat(life['startedAt'])).total_seconds()/60,1))
    except (ValueError,TypeError):pass
    metrics={'setupElapsedMinutes':elapsed,'activeDays':len(active_days),'firstDay':first,'lastDay':active_days[-1] if active_days else None,'reviewCount':len(life['reviews']),'reconcileCount':len(life['reconciliations']),'movements':sum(r['type']=='movement' for r in life['activity']),'d7':None if not first or (day-local_day(first)).days<13 else any(7<=(local_day(d)-local_day(first)).days<=13 for d in active_days),'d30':None if not first or (day-local_day(first)).days<36 else any(30<=(local_day(d)-local_day(first)).days<=36 for d in active_days)}
    return dict(on=on,life=life,spending=spending,cycle=period,timeline=flow,tasks=tasks,invoices=invoices[:120],weekly={'start':since,'end':on,'income':sum(t['amount'] for t in paid if t['type']=='income'),'expense':sum(t['amount'] for t in paid if t['type']=='expense'),'offenders':[dict(name=k,amount=v) for k,v in sorted(categories.items(),key=lambda i:-i[1])[:5]],'lastReview':last,'due':review_due},suggestions=budget_suggestions(s,on),warnings=list(dict.fromkeys(warnings)),ready=spending['ready'] and all(life['checks'].values()),debt=total(s),metrics=metrics)

def command(s,p):
    s=copy.deepcopy(s);on=p.get('on',date.today().isoformat());day=local_day(on);life=preferences(s);s['lifePlan']=life;action=p.get('action')
    if action=='setup':
        step=p.get('step')
        if type(step) is not int or not 0<=step<=4:raise ValueError('Etapa inválida.')
        life['startedAt']=life['startedAt'] or datetime.now().astimezone().isoformat()
        if step==0:
            if p.get('goal') not in ('organize','debt','reserve'):raise ValueError('Escolha uma prioridade.')
            life['goal']=p['goal']
        if step==1:
            if not p.get('unknown',False):s['profile']['cash']=money(p.get('cash'),True);s['profile']['snapshotDate']=on;life['checks']['balance']=True
            else:life['checks']['balance']=False
        if step==2:
            life['checks']['income']=bool(p.get('checked',False))
            if p.get('income') is not None:s['profile']['income']=money(p['income'])
            if p.get('nextDate'):
                local_day(p['nextDate']);amount=money(p.get('nextAmount'))
                if p['nextDate']<on or not amount:raise ValueError('Informe uma data futura ou de hoje e um recebimento positivo.')
                matches=[t for t in s['transactions'] if t['type']=='income' and t['date']==p['nextDate'] and t['amount']==amount]
                if not matches:s['transactions'].append(dict(id=uuid.uuid4().hex,name='Próximo recebimento',category='Salário',amount=amount,date=p['nextDate'],paidDate='',status='planned',type='income',cardId='',notes='Previsto no cadastro guiado. Confirmar somente após o depósito.'))
        if step==3:life['checks']['bills']=bool(p.get('checked',False))
        if step==4:
            life['checks']['cards']=bool(p.get('checked',False));life['complete']=True;life['completedAt']=life.get('completedAt') or datetime.now().astimezone().isoformat()
            if all(life['checks'].values()):s.setdefault('spendingPlan',{})['reviewedMonth']=on[:7]
            mark(s,on,'setup')
        life['step']=min(4,step+1)
    elif action=='check':
        key=p.get('key')
        if key not in life['checks'] or type(p.get('value')) is not bool:raise ValueError('Conferência inválida.')
        if key=='balance' and s['profile']['cash'] is None:raise ValueError('Informe o saldo primeiro.')
        life['checks'][key]=p['value']
    elif action=='modules':
        for key in ('house','investments'):
            if type(p.get(key)) is not bool:raise ValueError('Preferência de módulos inválida.')
            life['modules'][key]=p[key]
    elif action=='reconcile':
        value=money(p.get('cash'),True);reason=p.get('reason','')
        if not isinstance(reason,str):raise ValueError('Explique a conferência em texto.')
        reason=reason.strip()
        if not isinstance(reason,str) or not 3<=len(reason)<=300:raise ValueError('Explique a conferência ou diferença em até 300 caracteres.')
        before=s['profile']['cash'];s['profile']['cash']=value;s['profile']['snapshotDate']=on;life['checks']['balance']=True
        life['reconciliations']=(life['reconciliations']+[dict(date=on,before=before,after=value,reason=reason)])[-1000:];mark(s,on,'reconcile')
    elif action=='review':
        if s['profile']['cash'] is None:raise ValueError('Informe e confira o saldo antes de concluir a revisão.')
        if not all(p.get(k) is True for k in ('balance','transactions','upcoming')):raise ValueError('Conclua as três conferências antes de finalizar.')
        life['reviews']=(life['reviews']+[{'date':on,'cash':s['profile']['cash']}])[-1000:];life['checks']['balance']=True;s.setdefault('spendingPlan',{})['reviewedMonth']=on[:7];mark(s,on,'review')
    elif action=='invoice':
        ids=p.get('ids');paid=p.get('date');local_day(paid)
        if paid>on:raise ValueError('Confirme somente pagamentos já realizados.')
        if not isinstance(ids,list) or not ids or len(ids)!=len(set(ids)) or len(ids)>30000:raise ValueError('Seleção de fatura inválida.')
        rows=[t for t in s['transactions'] if t['id'] in ids]
        if len(rows)!=len(ids) or any(t['type']!='expense' or not t.get('cardId') or t['status']!='planned' for t in rows):raise ValueError('Esta fatura mudou ou já foi paga. Atualize a tela.')
        if len({(t['cardId'],t['date'][:7]) for t in rows})!=1:raise ValueError('Pague um cartão e mês por vez.')
        if p.get('total')!=sum(t['amount'] for t in rows):raise ValueError('O total mudou. Confira os itens antes de confirmar.')
        for t in rows:t.update(status='paid',paidDate=paid)
    elif action=='quick':
        kind=p.get('type');payment=p.get('payment');amount=money(p.get('amount'));name=p.get('name','').strip();category=p.get('category','').strip();when=p.get('date',on);local_day(when)
        if kind not in ('income','expense') or payment not in ('paid','planned','card') or not amount or not name or not category or len(name)>160 or len(category)>160:raise ValueError('Confira descrição, valor, categoria e pagamento.')
        if kind=='income' and payment=='card':raise ValueError('Receita não usa cartão.')
        card=p.get('cardId','') if payment=='card' else ''
        if card and not any(c['id']==card for c in s['cards']):raise ValueError('Cartão inexistente.')
        if payment=='card' and not card:raise ValueError('Selecione um cartão.')
        if payment=='paid' and when>on:raise ValueError('Recebimentos e pagamentos futuros devem ficar previstos.')
        matches=[t for t in s['transactions'] if t['type']==kind and t['amount']==amount and t['date']==when and t['name'].strip().casefold()==name.casefold()]
        if matches and p.get('confirmDuplicate') is not True:raise ValueError('Já existe um lançamento com descrição, data e valor iguais. Confira o extrato e confirme a opção de compra diferente somente se for outro movimento.')
        if kind=='expense' and not card and 'fatura' in name.casefold():
            names={c['id']:c['name'].casefold() for c in s['cards']}
            for ident,card_name in names.items():
                rows=[t for t in s['transactions'] if t.get('cardId')==ident and t['status']=='planned' and t['date'][:7]==when[:7]]
                if rows and card_name in name.casefold() and sum(t['amount'] for t in rows)==amount:raise ValueError('Essa fatura já está representada pelas compras do cartão. Abra Cartões e confirme o pagamento, sem criar outra despesa.')
        s['transactions'].append(dict(id=uuid.uuid4().hex,name=name,category=category,amount=amount,date=when,paidDate=when if payment=='paid' else '',status='paid' if payment=='paid' else 'planned',type=kind,cardId=card,notes='Registro rápido.'))
    elif action=='invoice-add':
        card=next((c for c in s['cards'] if c['id']==p.get('cardId')),None);due=p.get('date');local_day(due);amount=money(p.get('amount'))
        if not card or not amount:raise ValueError('Selecione o cartão e um valor positivo.')
        if any(t.get('cardId')==card['id'] and t['date'][:7]==due[:7] for t in s['transactions']):raise ValueError('Já existem compras/fatura neste cartão e mês. Confira o total existente em vez de acrescentar a fatura inteira.')
        s['transactions'].append(dict(id=uuid.uuid4().hex,name='Fatura consolidada · '+card['name'],category='Fatura · '+card['name'],invoiceConsolidated=True,amount=amount,date=due,paidDate='',status='planned',type='expense',cardId=card['id'],notes='Total consolidado, sem categorias detalhadas. Não registre as mesmas compras novamente.'))
    elif action=='adapt-budget':
        proposal=next((r for r in budget_suggestions(s,on) if r['id']==p.get('id')),None)
        if not proposal:raise ValueError('A sugestão mudou. Atualize a revisão.')
        b=next(b for b in s['budgets'] if b['id']==proposal['id']);m=on[:7]
        total=sum(b['amount'] for b in s['budgets'] if b['start']<=m and (not b['end'] or b['end']>=m))
        if total+proposal['difference']>s['profile']['income']:raise ValueError('A mudança ultrapassa a renda de referência. Primeiro realoque limites de outras categorias no orçamento.')
        if b['start']<m:
            old_end=b['end'];last=day.replace(day=1)-timedelta(days=1);b['end']=last.isoformat()[:7]
            s['budgets'].append({**b,'id':uuid.uuid4().hex,'start':m,'end':old_end,'amount':proposal['suggested']})
        else:b['amount']=proposal['suggested']
        mark(s,on,'budget')
    else:raise ValueError('Ação da rotina inválida.')
    return s

def audit(old,new,mode,on):
    life=preferences(new);before=old['profile']['cash'];after=new['profile']['cash']
    if before!=after:
        if mode=='undo':reason='Desfazer a última alteração financeira.'
        elif mode=='restore':reason='Saldo trazido de backup restaurado.'
        elif after is None:reason='Saldo voltou a ficar desconhecido.'
        elif before is None:reason='Saldo inicial informado; não é uma receita.'
        elif new['profile']['cash']!=old['profile']['cash']:
            from storage import cash_flow
            delta=cash_flow(new)-cash_flow(old)
            if delta==after-before:
                old_tx={t['id']:t for t in old['transactions']};changed=[t['name'] for t in new['transactions'] if t['status']=='paid' and old_tx.get(t['id'])!=t]
                reason='Movimentações confirmadas ou corrigidas: '+(', '.join(changed[:4]) if changed else 'estorno, remoção ou correção no extrato')
            else:reason='Saldo reconciliado ou informado manualmente; a diferença não é receita/despesa.'
        life['cashJournal']=(preferences(old)['cashJournal']+[dict(date=on,before=before,after=after,delta=None if before is None or after is None else after-before,reason=reason[:800])])[-1000:]
    if old.get('transactions')!=new.get('transactions') and mode=='normal':
        life['activity']=(life['activity']+[{'date':on,'type':'movement'}])[-1000:]
        # Any ledger edit makes a previous balance confirmation stale.
        if [t for t in old['transactions'] if t['status']=='paid']!=[t for t in new['transactions'] if t['status']=='paid']:life['checks']['balance']=False
    if mode in ('undo','restore'):life['activity']=(life['activity']+[{'date':on,'type':mode}])[-1000:];life['checks']['balance']=False
    new['lifePlan']=life
    return new
