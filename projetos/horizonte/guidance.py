"""Reviewed starter budgets. Limits are never expenses or bank movements."""
import copy
import re
import unicodedata
import uuid
from datetime import date

# Product defaults, not a prescribed allocation or an official formula.
CATEGORIES = [
    ('Moradia',25,True,('moradia','aluguel','habitacao')),
    ('Alimentação',15,True,('alimentacao','mercado','supermercado')),
    ('Transporte',10,True,('transporte','combustivel','uber')),
    ('Saúde',5,True,('saude','medicamentos','plano de saude')),
    ('Educação',5,True,('educacao','faculdade','estudos')),
    ('Contas e serviços',7,True,('contas e servicos','agua','luz','energia','internet','telefone')),
    ('Lazer',8,False,('lazer','entretenimento')),
    ('Outros',5,False,('outros','imprevistos')),
]

def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFD',value.lower()) if unicodedata.category(c)!='Mn').strip()

def month(value):
    if not isinstance(value,str) or not re.fullmatch(r'(19|20|21)\d\d-(0[1-9]|1[0-2])',value):raise ValueError('Informe um mês válido.')
    date.fromisoformat(value+'-01');return value

def preview(s,p):
    m=month(p.get('month',date.today().isoformat()[:7]));income=s['profile']['income']
    active=[b for b in s['budgets'] if b['start']<=m and (not b['end'] or b['end']>=m)]
    used=sum(b['amount'] for b in active);room=max(0,income-used)
    candidates=[];covered=[]
    for name,weight,essential,aliases in CATEGORIES:
        matches=[b for b in active if norm(b['name']) in aliases]
        if matches:covered.append(name)
        else:candidates.append((name,weight,essential))
    # Existing fixed AND variable limits take priority; distribute only room left.
    denominator=20+sum(w for _,w,_ in candidates)
    rows=[dict(name=n,amount=room*w//denominator,essential=e,weight=w) for n,w,e in candidates]
    margin=room-sum(r['amount'] for r in rows)
    warnings=[]
    if not income:warnings.append('Informe o salário líquido em Salário e receitas ou a renda líquida no perfil para calcular valores.')
    if used>income:warnings.append('Os limites atuais já ultrapassam a renda de referência. Revise-os antes de acrescentar categorias.')
    if any(d['balance'] for d in s['debts']) or any(t.get('cardId') and t['status']=='planned' for t in s['transactions']):warnings.append('Confira as dívidas e faturas antes de destinar a margem a investimentos. Faturas não são somadas novamente aos limites por categoria.')
    uncovered=sorted({t['category'] for t in s['transactions'] if t['type']=='expense' and t['date'].startswith(m+'-') and not any(b['name']==t['category'] for b in active) and not any(r['name']==t['category'] for r in rows)})
    if uncovered:warnings.append('Há gastos em outras categorias sem limite: '+', '.join(uncovered[:8])+'. Inclua-os na revisão.')
    return dict(month=m,income=income,existing=active,existingTotal=used,rows=rows,margin=margin,covered=covered,warnings=warnings,
                note='Distribuição inicial ilustrativa e ajustável. Valores existentes são mantidos. A margem fica sem destinação: para proteger reserva ou metas no limite diário, programe um aporte ou ajuste o saldo protegido. Não cria despesas, pagamentos nem aportes.')

def apply(s,p):
    m=month(p.get('month'));d=preview(s,{'month':m})
    if type(p.get('income')) is not int or p['income']!=d['income']:raise ValueError('A renda mudou. Recalcule a sugestão antes de aplicar.')
    if not d['income']:raise ValueError('Informe uma renda líquida antes de aplicar.')
    rows=p.get('rows')
    if not isinstance(rows,list) or not 1<=len(rows)<=len(CATEGORIES):raise ValueError('Selecione ao menos uma categoria nova.')
    allowed={r['name']:r for r in d['rows']};seen=set();total=0;result=copy.deepcopy(s)
    for r in rows:
        if not isinstance(r,dict):raise ValueError('Categoria inválida.')
        name=r.get('name');amount=r.get('amount')
        if name not in allowed or name in seen:raise ValueError('Categoria já cadastrada ou inválida. Recalcule a sugestão.')
        if type(amount) is not int or not 0<amount<=10**15:raise ValueError('Informe valores positivos para as categorias selecionadas.')
        seen.add(name);total+=amount
        result['budgets'].append(dict(id=uuid.uuid4().hex,name=name,amount=amount,kind='variable',essential=allowed[name]['essential'],day=None,start=m,end='',payment='Conta / Pix'))
    if total+d['existingTotal']>d['income']:raise ValueError('A soma dos limites ultrapassa a renda líquida. Reduza os valores antes de aplicar.')
    return result
