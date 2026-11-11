import json
import math
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

from household import empty as empty_house, validate as validate_house
from purchases import empty as empty_shopping, validate as validate_shopping

SCHEMA = 3


def seed():
    return {'shopping':empty_shopping(),'reports':[],'household':empty_house(),'schema':3,'profile':{'name':'Seu nome','birth':'','income':0,
        'cash':None,'reserve':0,'portfolio':0,'reserveMonths':6,'salaryDay':None,
        'pendingInstallments':0,'distrato':'','snapshotDate':date.today().isoformat(),'notes':''},
        **{k:[] for k in ['budgets','transactions','cards','debts','goals','checklist','scenarios','notes','holdings','analyses','history']}}


def migrate(s):
    if not isinstance(s,dict):return s
    s=json.loads(json.dumps(s))
    if s.get('schema')==1:
        s['schema']=2;s['holdings']=[];s['analyses']=[]
    if s.get('schema')==2:
        s['schema']=3
        s['profile']['pendingInstallments']=0
        s['debts']=[d for d in s['debts'] if not (d['id']=='d0' and d['name']=='Duas faturas atrasadas — consolidado' and d['balance']==140000)]
        s['cards']=[c for c in s['cards'] if not (c['id']=='card0' and c['name']=='Cartões — consolidado a detalhar' and not any(t.get('cardId')=='card0' for t in s['transactions']))]
        for t in s['transactions']:t['allocated']=False
    s.setdefault('household',empty_house())
    s.setdefault('history',[])
    s.setdefault('reports',[])
    s.setdefault('shopping',empty_shopping())
    s.setdefault('purchasingPower',{})
    s.setdefault('investmentCloses',[])
    s.setdefault('spendingPlan',{})
    s.setdefault('payroll',{})
    from life import empty as empty_life
    s.setdefault('lifePlan',empty_life())
    return s


def cash_flow(s):
    return sum((1 if t['type']=='income' else -1)*t['amount'] for t in s['transactions'] if t['status']=='paid' and not t.get('cashIncluded'))


def allocated_flow(s,destination):
    return sum(t['amount'] for t in s['transactions'] if t['status']=='paid' and t['type']=='investment' and t.get('destination')==destination)


def settle(old,new):
    delta=cash_flow(new)-cash_flow(old)
    if new['profile']['cash']==old['profile']['cash']:
        if delta and old['profile']['cash'] is None:
            raise ValueError('Informe primeiro o saldo atual em Perfil. Depois registre os novos pagamentos e recebimentos.')
        if delta:new['profile']['cash']+=delta
    new['profile']['reserve']+=allocated_flow(new,'reserve')-allocated_flow(old,'reserve')
    for asset in new['holdings']:
        delta=allocated_flow(new,asset['id'])-allocated_flow(old,asset['id'])
        qty_delta=sum(t.get('stockBuy',{}).get('quantity',0) for t in new['transactions'] if t.get('destination')==asset['id'] and t['status']=='paid')-sum(t.get('stockBuy',{}).get('quantity',0) for t in old['transactions'] if t.get('destination')==asset['id'] and t['status']=='paid')
        if delta or qty_delta:
            if asset.get('mode')=='balance':
                asset['cost']=round(asset['cost']+delta/100,2)
                asset['price']=round(asset['price']+delta/100,2)
            else:
                def buys(st):return [t for t in st['transactions'] if t.get('destination')==asset['id'] and t['status']=='paid']
                before,after=buys(old),buys(new)
                if any(not t.get('stockBuy') for t in before+after):raise ValueError('Use Registrar compra para ativos por quantidade.')
                qty=sum(t['stockBuy']['quantity'] for t in after)-sum(t['stockBuy']['quantity'] for t in before)
                value=asset['quantity']*asset['cost']+delta/100
                asset['quantity']=round(asset['quantity']+qty,8)
                if asset['quantity']<0 or value<-.00001:raise ValueError('A compra não pode ser estornada após alterações incompatíveis na posição.')
                asset['cost']=max(0,value)/asset['quantity'] if asset['quantity'] else 0

    old_assets={a['id'] for a in old['holdings']}
    new_assets={a['id'] for a in new['holdings']}
    if any(t.get('destination') in old_assets-new_assets for t in new['transactions']):
        raise ValueError('Remova os aportes vinculados antes de excluir esta aplicação.')
    if new['holdings'] or old['holdings']:new['profile']['portfolio']=round(sum(a['quantity']*a['price'] for a in new['holdings'])*100)
    from focus import settle_accounts
    return settle_accounts(old,new)


def validate(s, _unsettled=False):
    if not isinstance(s, dict) or s.get('schema') != SCHEMA:
        raise ValueError('Backup incompatível: schema deve ser 3')
    def money(v, nullable=False):
        if nullable and v is None:
            return
        if type(v) is not int or not 0 <= v <= 10**15:
            raise ValueError('Valores monetários devem ser centavos inteiros não negativos')
    def txt(v, maxlen=10000):
        if not isinstance(v, str) or len(v) > maxlen:
            raise ValueError('Texto inválido ou muito longo')
    def day(v, nullable=False):
        if nullable and v is None: return
        if type(v) is not int or not 1 <= v <= 31: raise ValueError('Dia deve estar entre 1 e 31')
    def dt(v, optional=False, month=False):
        txt(v, 10)
        if optional and v == '': return
        date.fromisoformat(v + '-01' if month else v)
    from focus import validate as validate_focus
    validate_focus(s,check_total=not _unsettled)
    p = s.get('profile', {})
    from life import validate as validate_life
    validate_life(s.get('lifePlan',{}))
    from purchasing_power import validate_preferences
    validate_preferences(s.get('purchasingPower',{}))
    from debtbook import validate_links
    validate_links(s)
    from payroll import validate as validate_payroll
    validate_payroll(s.get('payroll',{}))
    from spending import preferences
    preferences(s.get('spendingPlan',{}))
    from onepage import validate_closes
    validate_closes(s.get('investmentCloses',[]))
    for k in ['income', 'reserve', 'portfolio', 'pendingInstallments']: money(p.get(k))
    if p.get('cash') is not None and (type(p['cash']) is not int or abs(p['cash'])>10**15):raise ValueError('Saldo em conta inválido')
    day(p.get('salaryDay'), True)
    if type(p.get('reserveMonths')) is not int or not 1 <= p['reserveMonths'] <= 36: raise ValueError('Meses de reserva inválidos')
    for k in ['name', 'distrato', 'notes']: txt(p.get(k))
    dt(p.get('birth'),True); dt(p.get('snapshotDate'))
    salary_keys=set()
    for table in ['budgets','transactions','cards','debts','goals','scenarios','notes','holdings','analyses']:
        rows = s.get(table)
        if not isinstance(rows, list) or len(rows) > 30000: raise ValueError('Lista inválida: ' + table)
        ids = set()
        for r in rows:
            if not isinstance(r,dict): raise ValueError('Registro inválido')
            txt(r.get('id'),100)
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', r['id']) or r['id'] in ids: raise ValueError('ID duplicado ou vazio')
            ids.add(r['id'])
            if table == 'budgets':
                if r.get('kind','variable') not in ('variable','fixed'):raise ValueError('Tipo de orçamento inválido')
                if r.get('kind')=='fixed' and not '1900-01'<=r.get('start','')<='2199-12':raise ValueError('Primeiro mês do custo fixo deve estar entre 1900 e 2199')
                if r.get('kind')=='fixed' and r.get('day') is None:raise ValueError('Informe o vencimento do custo fixo')
                txt(r.get('name'),160); money(r.get('amount')); day(r.get('day'),True)
                dt(r.get('start'),month=True);dt(r.get('end'),True,True);txt(r.get('payment'),100)
                if r['end'] and r['end'] < r['start']: raise ValueError('Fim anterior ao início')
                if type(r.get('essential')) is not bool: raise ValueError('Essencial inválido')
            elif table == 'transactions':
                txt(r.get('tags',''),500)
                txt(r.get('name'),160); txt(r.get('category'),160); txt(r.get('cardId'),100);txt(r.get('notes'))
                money(r.get('amount')); dt(r.get('date')); dt(r.get('paidDate'),True)
                if 'allocated' in r and type(r['allocated']) is not bool: raise ValueError('Origem da parcela inválida')
                if any(k in r for k in ('receiptImportId','receiptFingerprint','receiptSource','receiptDate')):
                    txt(r['receiptImportId'],100);dt(r.get('receiptDate'))
                    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',r['receiptImportId']):raise ValueError('Identificação da nota inválida')
                    if r.get('receiptSource') not in ('text','html','xml','photo','qr','qr-online') or r['type']!='expense':raise ValueError('Origem fiscal inválida')
                    fp=r.get('receiptFingerprint','')
                    if not isinstance(fp,str) or (fp and not re.fullmatch('[a-f0-9]{64}',fp)):raise ValueError('Identificação fiscal inválida')
                if 'payrollId' in r or 'payrollKey' in r:
                    if r.get('type')!='income' or not isinstance(r.get('payrollId'),str) or not re.fullmatch('[a-f0-9]{32}',r['payrollId']) or not isinstance(r.get('payrollKey'),str) or not re.fullmatch(r'(19|20|21)\d\d-(0[1-9]|1[0-2])-[12]',r['payrollKey']):raise ValueError('Vínculo salarial inválido')
                    key=(r['payrollId'],r['payrollKey'])
                    if key in salary_keys:raise ValueError('Receita salarial duplicada para a mesma parcela')
                    salary_keys.add(key)
                if r.get('cardId') and r.get('type') != 'expense': raise ValueError('Cartão só pode ser usado em despesas')
                if r.get('type') not in ['income','expense','investment']:raise ValueError('Tipo inválido')
                if r.get('status') not in ['planned','paid']:raise ValueError('Status inválido')
                if r['status']=='paid' and not r['paidDate']:raise ValueError('Informe a data do pagamento')
            elif table == 'cards':
                txt(r.get('name'),160);day(r.get('dueDay'));day(r.get('closeDay'),True);money(r.get('limit'),True)
            elif table == 'debts':
                txt(r.get('name'),160);money(r.get('balance')); money(r.get('minimum'));txt(r.get('notes'))
                v = r.get('rate')
                if v is not None and (type(v) not in [float,int] or not math.isfinite(v) or not 0<=v<=100):raise ValueError('Taxa mensal inválida')
                if type(r.get('overdue')) is not bool:raise ValueError('Atraso inválido')
            elif table == 'goals':
                txt(r.get('name'),160);money(r.get('target'));money(r.get('saved'));dt(r.get('due'),True);txt(r.get('notes'))
                money(r.get('monthly',0))
                for key,lo,hi in [('annual',-90,100),('inflation',0,50),('months',1,840)]:
                    v=r.get(key,120 if key=='months' else 0)
                    if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi or (key=='months' and type(v) is not int):raise ValueError('Premissa da meta inválida')
                links=r.get('investmentLinks',[])
                if not isinstance(links,list) or len(links)>100:raise ValueError('Vínculos da meta inválidos')
                seen=set()
                for link in links:
                    if not isinstance(link,dict) or link.get('holdingId') in seen:raise ValueError('Vínculo da meta duplicado')
                    txt(link.get('holdingId'),100);seen.add(link['holdingId'])
                    v=link.get('percent')
                    if type(v) not in (int,float) or not math.isfinite(v) or not 0<v<=100:raise ValueError('Percentual da meta inválido')
                if r.get('priority') not in ['Alta','Média','Baixa']: raise ValueError('Prioridade inválida')
            elif table == 'scenarios':
                from finance import project
                txt(r.get('name'),160);project(r.get('params',{}))
            elif table == 'holdings':
                txt(r.get('name'),160);txt(r.get('ticker'),30);txt(r.get('category'),100);txt(r.get('source'),300);dt(r.get('date'));txt(r.get('notes'))
                if r['category'] not in ['Ações','FIIs','ETFs','Renda fixa','Tesouro Direto','CDB / RDB','LCI / LCA','Fundos','Cripto','Outros']:raise ValueError('Classe inválida')
                for k in ['quantity','cost','price','target']:
                    v=r.get(k)
                    if type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1e12:raise ValueError('Posição inválida')
                if r.get('mode')=='balance' and r['quantity']!=1:raise ValueError('Aplicação por saldo deve usar quantidade 1')
                if r['target']>100:raise ValueError('Peso-alvo acima de 100%')
            elif table == 'analyses':
                from investing import analyze
                txt(r.get('name'),160);dt(r.get('date'));txt(r.get('source'),500);analyze(r.get('params',{}))
            else:
                txt(r.get('name'),160);txt(r.get('text'));dt(r.get('date'))
    if not isinstance(s.get('checklist'),list) or len(s['checklist'])>100: raise ValueError('Checklist inválido')
    for x in s['checklist']:txt(x,100)
    fiscal_ids=[t['receiptImportId'] for t in s['transactions'] if t.get('receiptImportId')]
    fiscal_prints=[t['receiptFingerprint'] for t in s['transactions'] if t.get('receiptFingerprint')]
    if len(set(fiscal_ids))!=len(fiscal_ids) or len(set(fiscal_prints))!=len(fiscal_prints):raise ValueError('Esta nota já foi registrada no extrato.')
    cards = {r['id'] for r in s['cards']}
    if any(r['cardId'] and r['cardId'] not in cards for r in s['transactions']): raise ValueError('Lançamento aponta para cartão inexistente')
    consolidated=set()
    for t in s['transactions']:
        if 'invoiceConsolidated' in t and type(t['invoiceConsolidated']) is not bool:raise ValueError('Identificação de fatura inválida.')
        if t.get('invoiceConsolidated'):
            if t['type']!='expense' or not t.get('cardId'):raise ValueError('Uma fatura consolidada deve estar vinculada a um cartão.')
            key=(t['cardId'],t['date'][:7])
            if key in consolidated:raise ValueError('Já existe uma fatura consolidada neste cartão e mês.')
            consolidated.add(key)
    if any(sum(t.get('cardId')==card and t['date'][:7]==m for t in s['transactions'])>1 for card,m in consolidated):raise ValueError('Este cartão e mês têm uma fatura consolidada. Edite esse total ou substitua-o pelos itens; não some as mesmas compras novamente.')
    assets={a['id'] for a in s['holdings']}
    allocations={}
    for g in s['goals']:
        for link in g.get('investmentLinks',[]):
            ident=link['holdingId']
            if ident not in assets:raise ValueError('Desvincule a meta antes de excluir o investimento.')
            allocations[ident]=allocations.get(ident,0)+link['percent']
    if any(v>100.000001 for v in allocations.values()):raise ValueError('As metas não podem reservar mais de 100% do mesmo investimento.')
    for t in s['transactions']:
        dest=t.get('destination','')
        if dest and (t['type']!='investment' or dest not in assets|{'reserve'}):raise ValueError('Destino de aporte inválido')
        if 'stockBuy' in t:
            b=t['stockBuy']
            if not isinstance(b,dict) or not dest or dest=='reserve' or t['type']!='investment':raise ValueError('Compra vinculada inválida')
            for k in ('quantity','price'):
                if type(b.get(k)) not in (float,int) or not math.isfinite(b[k]) or not 0<b[k]<=1e9:raise ValueError('Quantidade/preço de compra inválido')
            money(b.get('fees'))
            if t['amount']!=math.floor(b['quantity']*b['price']*100+.5)+b['fees']:raise ValueError('Total da compra não confere')
            if next(a for a in s['holdings'] if a['id']==dest).get('mode')=='balance':raise ValueError('Compra por quantidade exige posição em cotas')
    if not isinstance(s.get('history',[]),list) or len(s.get('history',[]))>4000:raise ValueError('Histórico inválido')
    for h in s.get('history',[]):
        dt(h.get('date'))
        for k in ('cash','reserve','portfolio','debts'):
            if h.get(k) is not None and (type(h[k]) is not int or abs(h[k])>10**15):raise ValueError('Histórico inválido')
    from routines import validate_reports
    validate_reports(s.get('reports',[]))
    validate_house(s)
    validate_shopping(s)
    return s


class Conflict(Exception): pass


class Store:
    def __init__(self, root):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'financas.sqlite3'
        self.backups = self.root / 'backups'; self.backups.mkdir(exist_ok=True)
        with self.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, payload TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS undo_state (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, payload TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS events (revision INTEGER PRIMARY KEY, at TEXT NOT NULL, kind TEXT NOT NULL, summary TEXT NOT NULL)')
            c.execute('INSERT OR IGNORE INTO state VALUES (1,0,?)', (json.dumps(seed(),ensure_ascii=False),))
    def connect(self):
        return sqlite3.connect(self.path, timeout=15)
    def get(self):
        with self.connect() as c:
            rev, payload = c.execute('SELECT revision,payload FROM state WHERE id=1').fetchone()
            return {'revision':rev,'state':migrate(json.loads(payload))}
    def events(self):
        with self.connect() as c:
            return [{'revision':r,'at':at,'kind':kind,'summary':json.loads(summary)} for r,at,kind,summary in c.execute('SELECT revision,at,kind,summary FROM events ORDER BY revision DESC LIMIT 100')]
    def put(self, state, revision, mode="normal", _undo=False, on=None):
        state=migrate(state)
        validate(state,_unsettled=True)
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            oldrev, oldpayload = c.execute('SELECT revision,payload FROM state WHERE id=1').fetchone()
            if type(revision) is not int or oldrev != revision: raise Conflict('Dados mudaram em outra janela. Recarregue antes de salvar.')
            if mode not in ('normal','restore') and not (mode=='undo' and _undo):raise ValueError('Operação inválida')
            if mode=='normal':state=settle(migrate(json.loads(oldpayload)),state)
            if mode=='restore':
                for r in state.get('reports',[]):r['enabled']=False
                if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='reports_inbox'").fetchone():c.execute('DELETE FROM reports_inbox')
                if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='email_deliveries'").fetchone():c.execute('DELETE FROM email_deliveries')
            validate(state)
            now=on or date.today().isoformat()
            if not isinstance(now,str) or len(now)!=10:raise ValueError('Data local inválida.')
            date.fromisoformat(now)
            from life import audit
            previous=migrate(json.loads(oldpayload))
            state=audit(previous,state,mode,now)
            validate(state)
            p=state['profile']
            from debtbook import total as total_debt
            snap={'date':now,**{k:p[k] for k in ['cash','reserve','portfolio']},'debts':total_debt(state)}
            state['history']=([h for h in state.get('history',[]) if h['date']!=now]+[snap])[-4000:]
            payload=json.dumps(state,ensure_ascii=False,allow_nan=False)
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            (self.backups / f'backup_{stamp}.json').write_text(oldpayload,encoding='utf-8')
            c.execute('UPDATE state SET revision=?,payload=? WHERE id=1',(oldrev+1,payload))
            changes=[key for key in state if key!='history' and previous.get(key)!=state[key]]
            financial=any(previous.get(k)!=state.get(k) for k in ('profile','transactions','budgets','cards','debts','goals','holdings','payroll','spendingPlan','shopping','household','accountBook','monthlyReviews'))
            if mode=='normal' and financial and previous.get('reports')==state.get('reports'):
                c.execute('INSERT OR REPLACE INTO undo_state VALUES (1,?,?)',(oldrev+1,oldpayload))
            else:c.execute('DELETE FROM undo_state')
            c.execute('INSERT INTO events VALUES (?,?,?,?)',(oldrev+1,datetime.now().astimezone().isoformat(),'state.restored' if mode=='restore' else 'state.undone' if mode=='undo' else 'state.committed',json.dumps({'changed':changes})))
        if mode=='restore':
            out=self.root/'reports-outbox'
            if out.exists():
                for report_file in out.glob('*.json'):
                    if re.fullmatch(r'[a-f0-9]{64}',report_file.stem):
                        (out/(report_file.stem+'.cancelled')).touch()
                        report_file.unlink(missing_ok=True)
        for path in sorted(self.backups.glob('backup_*.json'))[:-30]: path.unlink(missing_ok=True)
        return {'revision':oldrev+1,'state':state}

    def undo_status(self):
        with self.connect() as c:
            row=c.execute('SELECT revision FROM undo_state WHERE id=1').fetchone()
            current=c.execute('SELECT revision FROM state WHERE id=1').fetchone()[0]
            return {'available':bool(row and row[0]==current),'revision':current}
    def undo(self,revision,on=None):
        with self.connect() as c:
            row=c.execute('SELECT revision,payload FROM undo_state WHERE id=1').fetchone()
        if not row or row[0]!=revision:raise Conflict('Não há alteração recente disponível para desfazer. Atualize a tela.')
        return self.put(json.loads(row[1]),revision,'undo',_undo=True,on=on)
