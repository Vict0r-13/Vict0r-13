"""Local salary estimates and idempotent, planned-only monthly receipts.
2026 tables verified against INSS and Receita Federal on 2026-10-22.
This is not a payroll engine: standard monthly single-employer salary only.
"""
import calendar,copy,re,unicodedata,uuid
from datetime import date
from decimal import Decimal as D,ROUND_HALF_UP
from finance import month_add

SOURCES=[{'name':'INSS · empregado, 2026','url':'https://www.gov.br/inss/pt-br/direitos-e-deveres/inscricao-e-contribuicao/tabela-de-contribuicao-mensal'},
         {'name':'Receita Federal · incidência mensal, 2026','url':'https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/tabelas/2026'}]
SOURCES.append({'name':'Lei 9.430/1996 · art. 67, dispensa de retenção','url':'https://www.planalto.gov.br/ccivil_03/leis/l9430compilada.htm'})
CHECKED='2026-10-22'

def month(value):
    if not isinstance(value,str) or not re.fullmatch(r'(19|20|21)\d\d-(0[1-9]|1[0-2])',value):raise ValueError('Mês inválido')
    return value

def local_day(on=None):
    if on is None:
        from routines import device_now
        return device_now().date().isoformat()
    if not isinstance(on,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',on):raise ValueError('Data local inválida')
    date.fromisoformat(on);month(on[:7]);return on

def money(v):
    if type(v) is not int or not 0<=v<=100_000_000:raise ValueError('Valor salarial deve ser centavos inteiros, até R$ 1 milhão')
    return v

def rounded(v):return int(v.quantize(D('1'),rounding=ROUND_HALF_UP))

def validate(plan):
    if not isinstance(plan,dict):raise ValueError('Programação salarial inválida')
    if not plan:return
    if not isinstance(plan.get('id'),str) or not re.fullmatch('[a-f0-9]{32}',plan['id']):raise ValueError('ID salarial inválido')
    if type(plan.get('enabled')) is not bool:raise ValueError('Ativação salarial inválida')
    if plan.get('mode') not in ('clt','net'):raise ValueError('Selecione CLT ou líquido informado')
    if not isinstance(plan.get('name'),str) or not 1<=len(plan['name'])<=100:raise ValueError('Informe um nome para o salário')
    for key in ['gross','net','pension','other','advance']:money(plan.get(key))
    if type(plan.get('dependents')) is not int or not 0<=plan['dependents']<=50:raise ValueError('Dependentes inválidos')
    if type(plan.get('twice')) is not bool:raise ValueError('Selecione uma ou duas datas')
    if type(plan.get('firstDay')) is not int or not 1<=plan['firstDay']<=28:raise ValueError('O primeiro dia deve ser de 1 a 28')
    if plan.get('split') not in ('netPercent','grossAdvance','fixedAdvance'):raise ValueError('Divisão inválida')
    percent=plan.get('percent')
    if type(percent) not in (int,float) or not 0<=percent<=100:raise ValueError('Percentual inválido')
    if plan['mode']=='net' and plan['split']=='grossAdvance':raise ValueError('Para percentual do bruto, use o cálculo CLT')
    month(plan.get('start'))
    if plan.get('end'):month(plan['end'])
    if not isinstance(plan.get('end'),str) or plan['end'] and plan['end']<plan['start']:raise ValueError('Fim anterior ao início')
    issued=plan.get('issued',{})
    if not isinstance(issued,dict) or len(issued)>12000:raise ValueError('Histórico salarial inválido')
    for key,value in issued.items():
        if not re.fullmatch(r'(19|20|21)\d\d-(0[1-9]|1[0-2])-[12]',key):raise ValueError('Ocorrência salarial inválida')
        if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',value):raise ValueError('Vínculo salarial inválido')
    if plan['mode']=='clt' and not plan['gross']:raise ValueError('Informe o salário bruto')
    if plan['mode']=='net' and not plan['net']:raise ValueError('Informe o salário líquido')
    if plan['twice'] and plan['split']=='fixedAdvance' and not plan['advance']:raise ValueError('Informe quanto recebe na primeira data')

def calculate(plan,m):
    validate(plan);month(m)
    if not plan:raise ValueError('Cadastre seu salário')
    gross=plan['gross'];pension=plan['pension'];other=plan['other'];inss=ir=base=reduction=before=deduction=legal=waived=0;method='Líquido informado';brackets=[]
    if plan['mode']=='clt':
        if not m.startswith('2026-'):raise ValueError('Tabela CLT disponível apenas para 2026. Para outro ano, atualize as regras ou use o líquido do contracheque no modo manual.')
        last=0;total=D(0)
        for cap,rate in [(162100,'0.075'),(290284,'0.09'),(435427,'0.12'),(847555,'0.14')]:
            taxed=max(0,min(gross,cap)-last);part=D(taxed)*D(rate);total+=part
            brackets.append({'cap':cap,'rate':float(D(rate)*100),'base':taxed,'contribution':rounded(part)});last=cap
        inss=rounded(total);legal=inss+plan['dependents']*18959+pension
        deduction=max(60720,legal);method='Deduções legais' if legal>=60720 else 'Desconto simplificado mensal'
        base=max(0,gross-deduction)
        for limit,rate,deduct in [(242880,'0',0),(282665,'.075',18216),(375105,'.15',39416),(466468,'.225',67549),(10**15,'.275',90873)]:
            if base<=limit:before=max(0,rounded(D(base)*D(rate)-D(deduct)));break
        if gross<=500000:reduction=before
        elif gross<=735000:reduction=min(before,max(0,rounded(D(97862)-D('.133145')*D(gross))))
        raw_ir=max(0,before-reduction);waived=raw_ir if raw_ir<=1000 else 0
        ir=raw_ir-waived;net=gross-inss-ir-pension-other
        if net<=0:raise ValueError('Os descontos consomem todo o salário. Confira os valores')
    else:net=plan['net']
    if not plan['twice']:first=0
    elif plan['split']=='fixedAdvance':first=plan['advance']
    else:first=rounded(D(gross if plan['split']=='grossAdvance' else net)*D(str(plan['percent']))/100)
    if plan['twice'] and not 0<first<net:raise ValueError('A primeira parcela precisa ser maior que zero e menor que o líquido mensal')
    y,mo=map(int,m.split('-'));last_day=calendar.monthrange(y,mo)[1]
    payments=([{'slot':1,'date':f'{m}-{plan["firstDay"]:02d}','amount':first,'label':'Adiantamento'}] if plan['twice'] else [])+[{'slot':2,'date':f'{m}-{last_day:02d}','amount':net-first,'label':'Saldo do salário' if plan['twice'] else 'Salário'}]
    return {'month':m,'mode':plan['mode'],'gross':gross if plan['mode']=='clt' else None,'inss':inss,'irrf':ir,'taxBase':base,'taxBeforeReduction':before,'reduction':reduction,'withholdingWaived':waived,
            'legalDeductions':legal,'deduction':deduction,'deductionMethod':method,'pension':pension if plan['mode']=='clt' else 0,'other':other if plan['mode']=='clt' else 0,'net':net,'payments':payments,'inssBrackets':brackets,
            'ruleYear':2026 if plan['mode']=='clt' else None,'verifiedAt':CHECKED if plan['mode']=='clt' else None,'sources':SOURCES if plan['mode']=='clt' else [],
            'note':'Estimativa mensal de um vínculo. Confira no contracheque: benefícios, faltas, horas extras, férias, 13º, PLR, múltiplas fontes e ajustes da empresa podem alterar o depósito. FGTS não é descontado do salário líquido. Datas são de calendário, sem antecipação por feriados.'}

def salary_like(t):
    text=unicodedata.normalize('NFKD',t.get('category','')+' '+t.get('name','')).encode('ascii','ignore').decode().lower()
    return t['type']=='income' and bool(re.search(r'\b(salario|salario-base|adiantamento salarial)\b',text))

def materialize(state,on=None,update=False,strict=False,update_month=None):
    on=local_day(on);s=copy.deepcopy(state);plan=s.get('payroll',{});validate(plan)
    if not plan or not plan['enabled']:return s,[]
    current=on[:7];start=max(current,plan['start']);last=month_add(current+'-01',11)[:7]
    if plan['end']:last=min(last,plan['end'])
    warnings=[];ts=s['transactions'];indexed={t['id']:t for t in ts};m=start
    while m<=last:
        try:estimate=calculate(plan,m)
        except ValueError as e:
            warnings.append(str(e));break
        issued=plan['issued'];linked={value for key,value in issued.items() if key.startswith(m+'-')}
        candidates=[t for t in ts if t['date'].startswith(m+'-') and salary_like(t) and t['id'] not in linked]
        if candidates:
            message='Já há receita de salário sem vínculo em '+m+'. Vincule os lançamentos existentes ou comece a programação em outro mês para evitar duplicidade.'
            if strict:raise ValueError(message)
            warnings.append(message);m=month_add(m+'-01',1)[:7];continue
        paid_rows=[indexed[ident] for key,ident in issued.items() if key.startswith(m+'-') and ident in indexed and indexed[ident]['status']=='paid']
        paid_total=sum(t['amount'] for t in paid_rows)
        if paid_total>estimate['net']:
            message='Recebimentos confirmados excedem o líquido estimado em '+m+'. Preserve o histórico e escolha um mês inicial posterior para o novo salário.'
            if strict:raise ValueError(message)
            warnings.append(message)
            for ident in list(linked):
                row=indexed.get(ident)
                if row and row['status']=='planned':ts.remove(row);indexed.pop(ident,None)
            m=month_add(m+'-01',1)[:7];continue
        for raw in estimate['payments']:
            part=dict(raw)
            key=f'{m}-{part["slot"]}'
            old_row=indexed.get(issued.get(key))
            if paid_rows and not (old_row and old_row['status']=='paid'):
                part['amount']=max(0,estimate['net']-paid_total)
            if part['amount']==0:
                if old_row and old_row['status']=='planned':ts.remove(old_row);indexed.pop(old_row['id'],None)
                continue
            key=f'{m}-{part["slot"]}';existing=indexed.get(issued.get(key))
            # Tombstones intentionally keep deleted receipts from reappearing.
            if key in issued:
                if update and (update_month is None or m==update_month) and existing and existing['status']=='planned':
                    existing.update(amount=part['amount'],date=part['date'],name=plan['name']+' · '+part['label'],notes='Salário previsto. Líquido '+('estimado CLT 2026.' if plan['mode']=='clt' else 'informado pelo usuário.'))
                continue
            ident=uuid.uuid4().hex;issued[key]=ident
            row=dict(id=ident,name=plan['name']+' · '+part['label'],type='income',category='Salário',amount=part['amount'],date=part['date'],paidDate='',status='planned',cardId='',notes='Salário previsto. Líquido '+('estimado CLT 2026.' if plan['mode']=='clt' else 'informado pelo usuário.'),payrollId=plan['id'],payrollKey=key)
            ts.append(row);indexed[ident]=row
        m=month_add(m+'-01',1)[:7]
    return s,list(dict.fromkeys(warnings))

def command(state,p,on=None):
    on=local_day(on);s=copy.deepcopy(state);old=s.get('payroll',{});action=p.get('action')
    if action=='receive':
        if not old:raise ValueError('Não há salário programado')
        row=next((t for t in s['transactions'] if t['id']==p.get('id') and t.get('payrollId')==old['id']),None)
        if not row or row['status']!='planned':raise ValueError('Essa receita não está mais pendente')
        amount=money(p.get('amount'));when=local_day(p.get('date'))
        if not amount or when>on:raise ValueError('Informe o valor recebido e uma data que já ocorreu')
        row.update(amount=amount,status='paid',paidDate=when)
        return materialize(s,on,update=True,update_month=row['payrollKey'][:7])[0]
    if action=='save':
        incoming=p.get('plan')
        if not isinstance(incoming,dict):raise ValueError('Configuração salarial inválida')
        fields=['name','mode','gross','net','dependents','pension','other','advance','twice','firstDay','split','percent','start','end']
        plan={key:incoming.get(key) for key in fields};plan.update(id=old.get('id',uuid.uuid4().hex),enabled=True,issued=copy.deepcopy(old.get('issued',{})))
        validate(plan);calculate(plan,max(on[:7],plan['start']))
        # Changed recurrence shape and date range cancel only unpaid future rows.
        validslots={1,2} if plan['twice'] else {2}
        removed=set()
        for t in s['transactions']:
            if t.get('payrollId')!=plan['id'] or t['status']!='planned':continue
            m=t.get('payrollKey','')[:7];slot=int(t.get('payrollKey','0')[-1])
            if m<plan['start'] or plan['end'] and m>plan['end'] or slot not in validslots:removed.add(t['id'])
        s['transactions']=[t for t in s['transactions'] if t['id'] not in removed]
        # A cancelled future slot may be created again after an explicit save.
        plan['issued']={k:v for k,v in plan['issued'].items() if v not in removed}
        s['payroll']=plan
        used=set()
        for slot in (1,2):
            ident=p.get('link'+str(slot),'')
            if not ident:continue
            t=next((t for t in s['transactions'] if t['id']==ident),None)
            key=plan['start']+'-'+str(slot)
            if slot not in validslots or not t or t['type']!='income' or t['date'][:7]!=plan['start'] or ident in used:raise ValueError('Selecione receitas distintas do mês inicial')
            if t.get('payrollId') and (t['payrollId']!=plan['id'] or t.get('payrollKey')!=key):raise ValueError('Receita já vinculada a outra ocorrência salarial')
            if key in plan['issued'] and plan['issued'][key]!=ident:raise ValueError('Essa parcela já tem um lançamento; edite pelo extrato')
            used.add(ident);plan['issued'][key]=ident;t.update(payrollId=plan['id'],payrollKey=key)
        # Explicit saving updates unpaid forecasts, never actual deposits.
        s['profile']['income']=calculate(plan,max(on[:7],plan['start']))['net']
        s['profile']['salaryDay']=None if plan['twice'] else 31
        return materialize(s,on,update=True,strict=True)[0]
    if action in ('pause','remove'):
        if not old:raise ValueError('Não há salário programado')
        s['transactions']=[t for t in s['transactions'] if not (t.get('payrollId')==old['id'] and t['status']=='planned')]
        if action=='remove':s['payroll']={}
        else:
            old=s['payroll'];old['enabled']=False
            existing={t['id'] for t in s['transactions']};old['issued']={k:v for k,v in old['issued'].items() if v in existing}
        return s
    raise ValueError('Operação salarial inválida')

def sync(store,on=None):
    from storage import Conflict
    current=store.get();updated,warnings=materialize(current['state'],on)
    if updated!=current['state']:
        try:return store.put(updated,current['revision'])
        except Conflict:return store.get()
    return current

def status(s,on=None):
    on=local_day(on);plan=s.get('payroll',{});estimate=None;warnings=[]
    if plan:
        try:estimate=calculate(plan,max(on[:7],plan['start']))
        except ValueError as e:warnings.append(str(e))
        _,more=materialize(s,on);warnings+=more
    rows=[t for t in s['transactions'] if plan and t.get('payrollId')==plan['id']]
    return {'plan':plan,'estimate':estimate,'warnings':list(dict.fromkeys(warnings)),'rows':sorted(rows,key=lambda t:t['date']), 'on':on,'ruleYear':2026,'verifiedAt':CHECKED,'sources':SOURCES}
