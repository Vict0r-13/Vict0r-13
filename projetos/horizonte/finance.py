"""Deterministic educational projections. Rates are user assumptions, not quotes."""
import calendar
import math
from datetime import date


def number(value, name, low, high):
    if isinstance(value, bool):
        raise ValueError(f'{name}: número inválido')
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{name}: informe um número')
    if not math.isfinite(n) or not low <= n <= high:
        raise ValueError(f'{name}: deve estar entre {low} e {high}')
    return n


def month_add(start, count):
    d = date.fromisoformat(start)
    m = d.year * 12 + d.month - 1 + count
    y, mo = divmod(m, 12)
    return date(y, mo + 1, min(d.day, calendar.monthrange(y, mo + 1)[1])).isoformat()


def installments(total_cents, count):
    if type(total_cents) is not int or total_cents <= 0 or type(count) is not int or not 1 <= count <= 600:
        raise ValueError('Valor ou quantidade de parcelas inválido')
    q, r = divmod(total_cents, count)
    if q == 0:
        raise ValueError('Cada parcela precisa ter ao menos um centavo')
    return [q + (i < r) for i in range(count)]


def project(p):
    start = str(p.get('start', date.today().replace(day=1).isoformat()))
    date.fromisoformat(start)
    capital = number(p.get('capital', 0), 'Capital', 0, 1e12)
    contribution = number(p.get('contribution', 0), 'Aporte', 0, 1e9)
    years = int(number(p.get('years', 40), 'Anos', 1, 70))
    annual = number(p.get('annual', 7), 'Retorno nominal líquido anual', -90, 100)
    inflation = number(p.get('inflation', 4), 'Inflação anual', 0, 50)
    growth = number(p.get('growth', 4), 'Reajuste anual dos aportes', -50, 100)
    spending = number(p.get('spending', 4000), 'Renda mensal desejada', 1, 1e8)
    withdrawal = number(p.get('withdrawal', 3.5), 'Retirada anual', .1, 15)
    delay = int(number(p.get('delay', 0), 'Meses até começar os aportes', 0, 840))
    overrides = p.get('overrides', [])
    if not isinstance(overrides, list) or len(overrides) > 840:
        raise ValueError('Lista de aportes inválida')
    extra = {}
    for row in overrides:
        key = str(row.get('month', ''))
        date.fromisoformat(key + '-01')
        if key in extra:
            raise ValueError('Existe mais de uma substituição no mesmo mês')
        extra[key] = number(row.get('amount'), 'Aporte substituto', 0, 1e9)
    target = spending * 12 / (withdrawal / 100)
    paths = []
    for label, a in [('Menor retorno', max(-90, annual - 2)), ('Cenário informado', annual), ('Maior retorno', min(100, annual + 2))]:
        rm = (1 + a / 100) ** (1 / 12) - 1
        nominal, total = capital, capital
        reached = 0 if capital >= target else None
        rows = []
        for m in range(1, years * 12 + 1):
            when = month_add(start, m - 1)
            factor = (1 + inflation / 100) ** (m / 12)
            deposit = 0 if m <= delay else contribution * (1 + growth / 100) ** ((m - 1) // 12)
            deposit = extra.get(when[:7], deposit)
            interest = nominal * rm
            nominal += interest + deposit
            total += deposit
            real = nominal / factor
            if reached is None and real >= target:
                reached = m
            rows.append({'month': when[:7], 'index': m, 'contribution': deposit, 'interest': interest,
                         'invested': total, 'nominal': nominal, 'real': real, 'target': target,
                         'income_real': real * withdrawal / 100 / 12})
        paths.append({'label': label, 'annual': a, 'reached': reached, 'rows': rows})
    required = []
    for path in paths:
        rm=(1+path['annual']/100)**(1/12)-1
        fixed,weight=capital,0.0
        for m in range(1,years*12+1):
            key=month_add(start,m-1)[:7]
            fixed*=1+rm;weight*=1+rm
            if key in extra:fixed+=extra[key]
            elif m>delay:weight+=(1+growth/100)**((m-1)//12)
        needed=target*(1+inflation/100)**years-fixed
        value=0.0 if needed<=0 else needed/weight if weight>0 else None
        required.append({'label':path['label'],'monthly':value,'feasible':value is not None})
    return {'requiredContributions':required,'target': target, 'real_annual': ((1 + annual / 100) / (1 + inflation / 100) - 1) * 100,
            'scenarios': paths, 'assumptions': p}


def payoff(p):
    budget = number(p.get('budget'), 'Pagamento mensal', .01, 1e9)
    extra=number(p.get('extra',0),'Extra mensal',0,1e9)
    lump=number(p.get('lump',0),'Pagamento extraordinário',0,1e9)
    lump_month=int(number(p.get('lumpMonth',1),'Mês do extra',1,600))
    tight_months=int(number(p.get('tightMonths',0),'Meses apertados',0,600))
    tight_budget=number(p.get('tightBudget',budget),'Pagamento durante aperto',0,1e9)
    strategy = p.get('strategy', 'avalanche')
    if strategy not in ('avalanche', 'snowball'):
        raise ValueError('Estratégia inválida')
    items = p.get('debts', [])
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError('Cadastre pelo menos uma dívida')
    debts = []
    for d in items:
        balance = number(d.get('balance'), 'Saldo', 0, 1e10)
        if balance == 0:
            continue
        rate = number(d.get('rate'), 'Taxa mensal (consulte a fatura)', 0, 100) / 100
        minimum = number(d.get('minimum', 0), 'Pagamento mínimo', 0, 1e9)
        debts.append({'name': str(d.get('name', 'Dívida'))[:160], 'balance': balance, 'rate': rate, 'minimum': minimum})
    original = sum(d['balance'] for d in debts)
    rows, total_interest, paid = [], 0, 0
    for month in range(1, 601):
        if all(d['balance'] < .005 for d in debts):
            break
        interest = 0
        for d in debts:
            inc = round(d['balance'] * d['rate'], 2)
            d['balance'] += inc
            interest += inc
        available=(tight_budget if month<=tight_months else budget+extra)+(lump if month==lump_month else 0)
        minimum_sum = sum(min(d['minimum'], d['balance']) for d in debts)
        if minimum_sum > available + .005:
            raise ValueError('Pagamento mensal inferior à soma dos mínimos informados')
        remaining = available
        payments = [0.] * len(debts)
        for i, d in enumerate(debts):
            pay = min(d['minimum'], d['balance'])
            d['balance'] -= pay
            remaining -= pay
            payments[i] += pay
        order = sorted(range(len(debts)), key=lambda i: -debts[i]['rate'] if strategy == 'avalanche' else debts[i]['balance'])
        for i in order:
            pay = min(remaining, debts[i]['balance'])
            debts[i]['balance'] -= pay
            remaining -= pay
            payments[i] += pay
        used = sum(payments)
        paid += used
        total_interest += interest
        balance = sum(d['balance'] for d in debts)
        rows.append({'month': month, 'payment': used, 'interest': interest, 'balance': balance,
                     'payments': [{'name': d['name'], 'amount': payments[i]} for i, d in enumerate(debts)]})
        if balance > 1e13:
            break
    cleared = sum(d['balance'] for d in debts) < .005
    return {'rows': rows, 'cleared': cleared, 'months': len(rows) if cleared else None,
            'interest': total_interest, 'paid': paid, 'initial': original,
            'warning': None if cleared else 'Não quitada no horizonte de até 600 meses. Reveja taxas e pagamento.'}
