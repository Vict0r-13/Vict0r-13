"""Local, dependency-free report scheduler. MIT; no hosted service required."""
import calendar
import hashlib
import json
import re
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from household import shopping, expire

TOPICS = {'spending','shopping','expiry','bills'}

def device_now():
    try:
        from java import jclass
        return datetime.fromisoformat(str(jclass('java.time.LocalDateTime').now()))
    except ImportError:
        return datetime.now()

def fixed_arrears(s,m):
    result=[]
    starts=[b['start'] for b in s['budgets'] if b.get('kind')=='fixed' and b['start']<m]
    if not starts:return result
    y,mo=map(int,min(starts).split('-'))
    while f'{y:04d}-{mo:02d}'<m:
        grouped={}
        for r in fixed_rows(s,f'{y:04d}-{mo:02d}'):
            if r['name'] not in grouped:grouped[r['name']]=dict(r)
            else:grouped[r['name']]['amount']+=r['amount']
        for r in grouped.values():
            r['unregistered']=max(0,r['amount']-r['paid']-r['pending'])
            if r['unregistered']:result.append(r)
        mo+=1
        if mo==13:y+=1;mo=1
    return result


def validate_reports(rows):
    if not isinstance(rows,list) or len(rows)>100:raise ValueError('Agendamentos inválidos')
    ids=set()
    for r in rows:
        if not isinstance(r,dict):raise ValueError('Agendamento inválido')
        ident=r.get('id','')
        if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',ident) or ident in ids:raise ValueError('ID de relatório inválido')
        ids.add(ident)
        if not isinstance(r.get('name'),str) or not 1<=len(r['name'])<=160:raise ValueError('Nome de relatório inválido')
        if r.get('frequency') not in ('daily','weekly','monthly'):raise ValueError('Periodicidade inválida')
        if not re.fullmatch(r'([01][0-9]|2[0-3]):[0-5][0-9]',str(r.get('time',''))):raise ValueError('Horário inválido')
        for key,lo,hi in [('weekday',0,6),('day',1,31),('days',1,90)]:
            if type(r.get(key)) is not int or not lo<=r[key]<=hi:raise ValueError('Período de relatório inválido')
        if type(r.get('enabled')) is not bool:raise ValueError('Ativação inválida')
        if r.get('channel') not in ('local','whatsapp','email'):raise ValueError('Canal inválido')
        topics=r.get('topics')
        if not isinstance(topics,list) or not topics or any(x not in TOPICS for x in topics) or len(set(topics))!=len(topics):raise ValueError('Selecione os conteúdos do relatório')
        datetime.fromisoformat(r['createdAt'])

def active_budgets(s,m):
    return [b for b in s['budgets'] if b['start']<=m and (not b['end'] or b['end']>=m)]

def fixed_rows(s,m):
    result=[]
    for b in active_budgets(s,m):
        if b.get('kind')!='fixed':continue
        from focus import fixed_amount
        target=fixed_amount(s,b,m)
        rows=[t for t in s['transactions'] if t['type']=='expense' and t['category']==b['name'] and t['date'].startswith(m)]
        paid=sum(t['amount'] for t in rows if t['status']=='paid')
        pending=sum(t['amount'] for t in rows if t['status']=='planned')
        day=min(b['day'],calendar.monthrange(*map(int,m.split('-')))[1])
        result.append(dict(b,amount=target,estimated=bool(b.get('estimate') and m not in b.get('monthlyAmounts',{})),paid=paid,pending=pending,remaining=max(0,target-paid,pending),date=f'{m}-{day:02d}'))
    return result

def brl(cents):
    return 'R$ '+f'{cents/100:,.2f}'.replace(',','X').replace('.',',').replace('X','.')

def report(s,r,on=None):
    on=on or device_now().date();days=r['days'];start=on-timedelta(days=days-1);end=on+timedelta(days=days-1)
    lines=['HORIZONTE · '+r['name'], 'Referência em '+on.strftime('%d/%m/%Y')]
    if 'spending' in r['topics']:
        tx=[t for t in s['transactions'] if t['type']=='expense' and t['status']=='paid' and start.isoformat()<=t['paidDate']<=on.isoformat()]
        cats={}
        for t in tx:cats[t['category']]=cats.get(t['category'],0)+t['amount']
        lines+=['',f'GASTOS · {start:%d/%m} a {on:%d/%m}', 'Total pago: '+brl(sum(cats.values()))]
        lines += [f'• {k}: {brl(v)}' for k,v in sorted(cats.items(),key=lambda kv:-kv[1])[:8]]
        if not tx:lines+=['Nenhum gasto pago registrado no período.']
    if 'shopping' in r['topics']:
        items=shopping(s['household'],on.isoformat(),end.isoformat())
        lines+=['',f'COMPRAS · {on:%d/%m} a {end:%d/%m}']
        lines += [f"• {x['name']}: {x['quantity']:g} {x['unit']} · "+('preço desconhecido' if x['estimatedCost'] is None else brl(x['estimatedCost'])+' estimados') for x in items]
        if not items:lines+=['Nenhuma falta nas refeições planejadas.']
        lines+=['Estimativa pelas refeições cadastradas e estoque disponível; confira também seu estoque mínimo.']
    if 'expiry' in r['topics']:
        import copy
        h=copy.deepcopy(s['household']);h['settings']['days']=min(days,90)
        items=expire(h,on.isoformat())
        lines+=['',f'VALIDADES · próximos {days} dias']
        lines += [f"• {x['name']}: {x['quantity']:g} {x['unit']} · {x['expiry']}"+(' · vencido' if x['days']<0 else '') for x in items]
        if not items:lines+=['Nenhum lote com vencimento próximo registrado.']
    if 'bills' in r['topics']:
        lines+=['',f'A PAGAR · até {end:%d/%m/%Y} (inclui atrasos)']
        tx=[t for t in s['transactions'] if t['status']=='planned' and t['type']!='income' and t['date']<=end.isoformat()]
        items=[(t['date'],t['name'],t['amount']) for t in tx]
        # Add only the portion of each recurring obligation not already represented by transactions.
        items += [(f['date'],f['name'],f['unregistered']) for f in fixed_arrears(s,on.strftime('%Y-%m'))]
        months={on.strftime('%Y-%m'),end.strftime('%Y-%m')}
        cursor=on.replace(day=1)
        while cursor<=end:
            months.add(cursor.strftime('%Y-%m'));cursor=(cursor.replace(day=28)+timedelta(days=4)).replace(day=1)
        for m in sorted(months):
            for f in fixed_rows(s,m):
                missing=max(0,f['amount']-f['paid']-f['pending'])
                if missing and f['date']<=end.isoformat():items.append((f['date'],f['name'],missing))
        lines += [f'• {name} · {dt}: {brl(value)}' for dt,name,value in sorted(items)]
        if not items:lines+=['Nenhum compromisso registrado neste horizonte.']
        lines+=['Total previsto: '+brl(sum(x[2] for x in items))]
    lines+=['','Somente registros deste aparelho. Não inclui movimentações não cadastradas.']
    return '\n'.join(lines)

def latest_slot(r,now):
    hour,minute=map(int,r['time'].split(':'));slot=now.replace(hour=hour,minute=minute,second=0,microsecond=0)
    if r['frequency']=='daily':
        if slot>now:slot-=timedelta(days=1)
    elif r['frequency']=='weekly':
        slot-=timedelta(days=(slot.weekday()-r['weekday'])%7)
        if slot>now:slot-=timedelta(days=7)
    else:
        slot=slot.replace(day=min(r['day'],calendar.monthrange(slot.year,slot.month)[1]))
        if slot>now:
            prev=slot.replace(day=1)-timedelta(days=1)
            slot=prev.replace(day=min(r['day'],prev.day))
    return slot

class Reports:
    def __init__(self,store):
        self.store=store
        with store.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS reports_inbox (id TEXT PRIMARY KEY, rule_id TEXT, slot TEXT, title TEXT, body TEXT, channel TEXT)')
    def tick(self,now=None):
        # Device local time. One latest due occurrence per rule, not a burst after downtime.
        now=now or device_now();snapshot=self.store.get();s=snapshot['state'];made=[]
        for r in s.get('reports',[]):
            if not r['enabled']:continue
            slot=latest_slot(r,now)
            if slot<datetime.fromisoformat(r['createdAt']):continue
            key=hashlib.sha256((r['id']+'|'+slot.isoformat()).encode()).hexdigest()
            body=report(s,r,slot.date())
            with self.store.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                if c.execute('SELECT revision FROM state WHERE id=1').fetchone()[0]!=snapshot['revision']:return made
                n=c.execute('INSERT OR IGNORE INTO reports_inbox VALUES (?,?,?,?,?,?)',(key,r['id'],slot.isoformat(),r['name'],body,r['channel'])).rowcount
            if n:made.append(key)
        # Outbox reconstructed from durable inbox after a crash; no secrets in exported state.
        out=self.store.root/'reports-outbox';out.mkdir(exist_ok=True)
        rules={r['id']:r for r in s.get('reports',[])}
        with self.store.connect() as c:
            rows=c.execute("SELECT id,title,body,rule_id,slot FROM reports_inbox WHERE channel='whatsapp' ORDER BY slot DESC").fetchall()
        seen=set()
        for ident,title,body,rule_id,slot in rows:
            rule=rules.get(rule_id,{})
            if rule_id in seen or not rule.get('enabled') or rule.get('channel')!='whatsapp':
                (out/(ident+'.cancelled')).touch();continue
            seen.add(rule_id)
            file=out/(ident+'.json')
            if not file.exists():
                temp=out/(ident+'.tmp');temp.write_text(json.dumps(dict(id=ident,title=title,body=body),ensure_ascii=False),encoding='utf-8');temp.replace(file)
        from email_delivery import Delivery
        Delivery(self.store).pump()
        return made
    def inbox(self):
        with self.store.connect() as c:
            rows=[dict(zip(['id','ruleId','slot','title','body','channel'],row)) for row in c.execute('SELECT * FROM reports_inbox ORDER BY slot DESC LIMIT 100')]
        for r in rows:
            base=self.store.root/'reports-outbox'/r['id']
            r['delivery']='local' if r['channel']=='local' else 'pending'
            if Path(str(base)+'.error').exists():r['delivery']='error'
            if Path(str(base)+'.cancelled').exists():r['delivery']='cancelled'
            if Path(str(base)+'.sending').exists():r['delivery']='uncertain'
            if Path(str(base)+'.sent').exists():r['delivery']='submitted'
        from email_delivery import Delivery
        statuses=Delivery(self.store).statuses()
        for r in rows:
            if r['channel']=='email':
                status=statuses.get(r['id'],{})
                r['delivery']='email-'+status.get('status','pending');r['emailDetail']=status.get('detail','Aguardando conta habilitada e execução do envio.');r['attempts']=status.get('attempts',0)
        return rows
    def start(self):
        stop=threading.Event()
        def run():
            while not stop.is_set():
                try:self.tick()
                except Exception:pass # Database remains intact; retry next tick, never claim success.
                stop.wait(30)
        threading.Thread(target=run,daemon=True).start();return stop
