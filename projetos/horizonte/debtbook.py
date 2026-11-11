"""Consolidated debt calendar and read-only card anticipation scenarios.
Integer cents; no bank operations, invented card interest or inferred deduplication.
"""
import copy,math,re
from collections import defaultdict
from datetime import date
from decimal import Decimal,ROUND_HALF_UP
from finance import month_add


def distinct(s):
    cards={c['id'] for c in s['cards']}
    return [d for d in s['debts'] if not d.get('coveredByCard') or d['coveredByCard'] not in cards]


def total(s):
    return sum(d['balance'] for d in distinct(s))+s['profile'].get('pendingInstallments',0)+sum(t['amount'] for t in s['transactions'] if t['type']=='expense' and t.get('cardId') and t['status']=='planned')


def validate_links(s):
    if any(not isinstance(s.get(k),list) for k in ('cards','debts','transactions')):raise ValueError('Cadastros financeiros inválidos')
    if any(not isinstance(c,dict) or not isinstance(c.get('id'),str) for c in s['cards']):raise ValueError('Cartão inválido')
    if any(not isinstance(d,dict) for d in s['debts']) or any(not isinstance(t,dict) for t in s['transactions']):raise ValueError('Registro financeiro inválido')
    cards={c['id'] for c in s['cards']}
    for d in s['debts']:
        covered=d.get('coveredByCard','')
        if not isinstance(covered,str) or covered and covered not in cards:raise ValueError('Revise o vínculo do saldo manual ao cartão antes de excluir o cartão')
        if covered and any(t.get('debtId')==d.get('id') and t.get('status')=='planned' for t in s['transactions']):raise ValueError('Desvincule os pagamentos previstos dessa dívida antes de usar somente o calendário do cartão')
        category=d.get('paymentCategory','Dívidas / encargos')
        if not isinstance(category,str) or not 1<=len(category)<=160:raise ValueError('Categoria de pagamento da dívida inválida')
    for t in s['transactions']:
        if t.get('debtId'):
            if t['type']!='expense' or t.get('cardId') or not isinstance(t['debtId'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',t['debtId']):raise ValueError('Vínculo do pagamento à dívida inválido')


def command(s,p):
    result=copy.deepcopy(s)
    if p.get('action')=='linkCategory':
        ident=p.get('debtId');category=p.get('category')
        if not isinstance(category,str) or not 1<=len(category)<=160:raise ValueError('Selecione uma categoria de pagamentos')
        d=next((d for d in result['debts'] if d['id']==ident and not d.get('coveredByCard')),None)
        if not d:raise ValueError('Selecione uma dívida avulsa')
        matched=0
        for row in result['transactions']:
            if row['type']=='expense' and not row.get('cardId') and row['status']=='planned' and row['category']==category:
                if row.get('debtId') and row['debtId']!=ident:raise ValueError('A categoria contém pagamentos vinculados a outra dívida')
                row['debtId']=ident;matched+=1
        if not matched:raise ValueError('Não há pagamentos previstos de conta/Pix nessa categoria')
        return result
    if p.get('action')!='link':raise ValueError('Operação inválida')
    t=next((t for t in result['transactions'] if t['id']==p.get('transactionId')),None)
    if not t or t['type']!='expense' or t.get('cardId'):raise ValueError('Selecione uma despesa de conta/Pix para vincular')
    ident=p.get('debtId','')
    d=next((d for d in result['debts'] if d['id']==ident),None)
    if ident and (not d or d.get('coveredByCard')):raise ValueError('Selecione uma dívida avulsa, sem referência duplicada de cartão')
    if ident:t['debtId']=ident
    else:t.pop('debtId',None)
    return result


def options(p):
    horizon=p.get('horizon',12)
    if type(horizon) is not int or horizon not in (6,12,24,36,60):raise ValueError('Escolha 6, 12, 24, 36 ou 60 meses')
    on=p.get('on')
    if on is None:
        from routines import device_now
        on=device_now().date().isoformat()
    if not isinstance(on,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',on):raise ValueError('Data local inválida')
    date.fromisoformat(on)
    for key in ['monthlyExtra','lump']:
        value=p.get(key,0)
        if type(value) is not int or not 0<=value<=10**12:raise ValueError('Antecipação deve ser um valor em centavos não negativos')
    idx=p.get('lumpMonth',1)
    if type(idx) is not int or not 1<=idx<=horizon:raise ValueError('Mês da antecipação pontual fora da janela')
    order=p.get('order','earliest')
    if order not in ('earliest','latest'):raise ValueError('Ordem de antecipação inválida')
    discount=p.get('discount',0)
    if type(discount) not in (float,int) or not math.isfinite(discount) or not 0<=discount<=90:raise ValueError('Desconto ofertado deve ser de 0 a 90%')
    respect=p.get('respectCash',True)
    if type(respect) is not bool:raise ValueError('Proteção de caixa inválida')
    return dict(on=on,horizon=horizon,monthlyExtra=p.get('monthlyExtra',0),lump=p.get('lump',0),lumpMonth=idx,order=order,discount=discount,
                discountBps=int((Decimal(str(discount))*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP)),respectCash=respect,cardId=p.get('cardId',''))


def trajectory(s,p):
    from spending import overview as spending_overview
    on=p['on'];current=on[:7];horizon=p['horizon'];warnings=[]
    cardnames={c['id']:c['name'] for c in s['cards']}
    if p['cardId'] and p['cardId'] not in cardnames:raise ValueError('Cartão não encontrado')
    cards=[dict(t,remaining=t['amount']) for t in s['transactions'] if t['type']=='expense' and t.get('cardId') and t['status']=='planned']
    loans=distinct(s);loanids={d['id'] for d in loans};balances={d['id']:d['balance'] for d in loans}
    cash=s['profile']['cash'];buffer=s.get('spendingPlan',{}).get('buffer',0);uncal=s['profile'].get('pendingInstallments',0)
    if uncal:warnings.append('Há parcelas sem calendário. Entram no saldo total, mas não nos vencimentos nem na quitação estimada.')
    if cash is None:warnings.append('Informe o saldo em conta para projetar caixa e limitar antecipações por dinheiro disponível.')
    if any(t['date']<on for t in cards):warnings.append('Faturas vencidas são concentradas no mês atual pelo valor cadastrado, sem novos encargos. Confira o saldo com o emissor.')
    ts=s['transactions'];planned=defaultdict(list);paid=defaultdict(list);linked=defaultdict(lambda:defaultdict(list));ambiguous=set()
    for t in ts:
        if t['status']=='paid':paid[t['paidDate'][:7]].append(t)
        elif not t.get('cardId'):planned[max(t['date'][:7],current)].append(t)
        if t['type']=='expense' and not t.get('cardId') and t.get('debtId') in loanids:
            key=max(t['date'][:7],current) if t['status']=='planned' else t['paidDate'][:7]
            linked[t['debtId']][key].append(t)
    if any(d['balance']>0 and d['minimum']>0 for d in loans) and any(t['type']=='expense' and not t.get('cardId') and not t.get('debtId') and t['status']=='planned' for t in ts):warnings.append('Há despesas de conta/Pix sem vínculo. Se incluírem parcelas dos contratos, associe-as para não somar uma previsão adicional.')
    for d in loans:
        cat=d.get('paymentCategory','Dívidas / encargos')
        if any(t['type']=='expense' and not t.get('cardId') and not t.get('debtId') and t['category']==cat and (t['status']=='planned' and t['date']>=current+'-01' or t['status']=='paid' and t['paidDate'].startswith(current+'-')) for t in ts):
            ambiguous.add(d['id']);warnings.append('Associe os pagamentos da categoria '+cat+' à dívida '+d['name']+'. A amortização dessa dívida fica suspensa para evitar duplicidade.')
    modeled={d['id']:d['rate'] is not None and d['id'] not in ambiguous and (d['minimum']>0 or any(t['status']=='planned' for rows in linked[d['id']].values() for t in rows)) for d in loans}
    for d in loans:
        if d['balance'] and not modeled[d['id']]:warnings.append(d['name']+': saldo sem amortização confiável; confira juros, pagamento mensal e vínculos no extrato.')
    if any(t['status']=='paid' and t['paidDate']>on for t in ts):warnings.append('Há movimentações marcadas como realizadas em data futura; confira o saldo de partida.')
    missing_fixed=spending_overview(s,on)['pastFixed']
    initial=total(s);rows=[];anticipations=[];prepaid=defaultdict(lambda:defaultdict(int));card_clear=None;clear=None;total_advance=0;total_released=0;total_interest=0;requested_total=0
    for i in range(horizon):
        m=month_add(current+'-01',i)[:7];scheduled=defaultdict(int);past_cost=0;card_due=0;manual_cash=0;manual_interest=0;invest=0
        # Due installments are settled in full in this illustrative baseline.
        for t in cards:
            if t['remaining'] and max(t['date'][:7],current)==m:
                value=t['remaining'];card_due+=value;t['remaining']=0
                if t['date'][:7]<current:past_cost+=value
                else:scheduled[t['category']]+=value
        for t in planned[m]:
            if t['type']=='investment':invest+=t['amount']
            elif t['type']=='expense' and t.get('debtId') not in loanids:
                if t['date'][:7]<current:past_cost+=t['amount']
                else:scheduled[t['category']]+=t['amount']
        for d in loans:
            ident=d['id'];linked_rows=[t for t in linked[ident][m] if t['status']=='planned'];known=sum(t['amount'] for t in linked_rows)
            paid_month=sum(t['amount'] for t in linked[ident][m] if t['status']=='paid') if i==0 else 0
            payment=0;interest=0;monthly=max(0,d['minimum']-paid_month)
            past_linked=sum(t['amount'] for t in linked_rows if t['date'][:7]<current)
            current_linked=[t for t in linked_rows if t['date'][:7]>=current]
            intended=past_linked+(sum(t['amount'] for t in current_linked) if current_linked else monthly)
            if current_linked and sum(t['amount'] for t in current_linked)<monthly:warnings.append(d['name']+': os pagamentos previstos são menores que a referência mensal. O calendário usa o valor lançado, sem presumir encargos por pagamento parcial.')
            if ident not in ambiguous:
                if modeled[ident] and balances[ident]>0:
                    interest=int((Decimal(balances[ident])*Decimal(str(d['rate']))/100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
                    owing=balances[ident]+interest
                    payment=min(owing,intended);balances[ident]=owing-payment
                    if balances[ident]>10**18:
                        balances[ident]=10**18;modeled[ident]=False;warnings.append(d['name']+': projeção excedeu o limite numérico; saldo parcial e sem data de quitação.')
                    if intended and intended<interest:warnings.append(d['name']+': pagamento simulado inferior aos juros; o saldo cresce.')
                    if known>owing:warnings.append(d['name']+': pagamento cadastrado maior que o saldo estimado. O caixa preserva o lançamento; confira o contrato.')
                elif not modeled[ident] and balances[ident]>0:
                    payment=intended
            # Explicit ledger rows are never silently removed from cash projections.
            actual_cash=max(known,payment);manual_cash+=actual_cash;manual_interest+=interest
            for t in linked_rows:
                if t['date'][:7]<current:past_cost+=t['amount']
                else:scheduled[t['category']]+=t['amount']
            if actual_cash>known:scheduled[d.get('paymentCategory','Dívidas / encargos')]+=actual_cash-known
        # Remaining budgets supplement, rather than duplicate, scheduled expenses.
        active=[b for b in s['budgets'] if b['start']<=m and (not b['end'] or b['end']>=m)]
        targets=defaultdict(int);fixed_names=set()
        for b in active:
            from focus import fixed_amount
            targets[b['name']]+=fixed_amount(s,b,m) if b.get('kind')=='fixed' else b['amount']
            if b.get('kind')=='fixed':fixed_names.add(b['name'])
        spent=defaultdict(int)
        if i==0:
            for t in paid[m]:
                if t['type']=='expense' and t['category'] not in fixed_names:spent[t['category']]+=t['amount']
            for t in ts:
                if t['type']=='expense' and t['status']=='paid' and t['category'] in fixed_names and t['date'].startswith(m+'-'):spent[t['category']]+=t['amount']
        expenses=sum(max(scheduled[name],max(0,targets[name]-spent[name]-prepaid[m][name])) for name in set(targets)|set(scheduled))+past_cost+(missing_fixed if i==0 else 0)
        inc_rows=[t for t in planned[m] if t['type']=='income']
        # Future months without any income record use a visible reference hypothesis.
        any_income=any(t['type']=='income' and t['date'].startswith(m+'-') for t in ts)
        income=sum(t['amount'] for t in inc_rows)
        income_basis='calendar'
        if i>0 and not any_income:income=s['profile']['income'];income_basis='reference'
        ratio_income=income+sum(t['amount'] for t in paid[m] if t['type']=='income') if i==0 else income
        if not ratio_income:ratio_income=s['profile']['income'];ratio_basis='reference'
        else:ratio_basis=income_basis
        if cash is not None:cash+=income-expenses-invest
        requested=p['monthlyExtra']+(p['lump'] if i+1==p['lumpMonth'] else 0);requested_total+=requested
        budget=requested
        if p['respectCash']:budget=0 if cash is None else min(budget,max(0,cash-buffer))
        advance=0;released=0
        eligible=sorted((t for t in cards if t['remaining']>0 and t['date'][:7]>m and (not p['cardId'] or t['cardId']==p['cardId'])),key=lambda t:(t['date'],t['id']),reverse=p['order']=='latest')
        factor=10000-p['discountBps']
        for t in eligible:
            if budget<=0:break
            nominal=min(t['remaining'],budget*10000//factor)
            if nominal<=0:continue
            cost=(nominal*factor+9999)//10000
            t['remaining']-=nominal;budget-=cost;advance+=cost;released+=nominal
            prepaid[t['date'][:7]][t['category']]+=nominal
            anticipations.append({'month':m,'transactionId':t['id'],'cardId':t['cardId'],'originalMonth':t['date'][:7],'nominal':nominal,'cost':cost,'discount':nominal-cost})
        if cash is not None:cash-=advance
        total_advance+=advance;total_released+=released;total_interest+=manual_interest
        card_balance=sum(t['remaining'] for t in cards);manual_balance=sum(balances.values());remaining=card_balance+manual_balance+uncal
        debt_payment=card_due+manual_cash+advance
        if card_clear is None and card_balance==0:card_clear=m
        if clear is None and remaining==0:clear=m
        rows.append(dict(month=m,income=income,incomeBasis=income_basis,incomeForRatio=ratio_income,ratioBasis=ratio_basis,cardPayment=card_due,manualPayment=manual_cash,advance=advance,
                         debtPayment=debt_payment,interest=manual_interest,expenses=expenses,otherExpenses=max(0,expenses-card_due-manual_cash),investments=invest,
                         cash=cash,buffer=buffer,shortfall=None if cash is None else max(0,buffer-cash),ratio=debt_payment/ratio_income*100 if ratio_income else None,
                         cardRemaining=card_balance,manualRemaining=manual_balance,remaining=remaining))
    unmodeled=sum(balances[d['id']] for d in loans if not modeled[d['id']])
    bycard=[{'id':c['id'],'name':c['name'],'total':sum(t['amount'] for t in cards if t['cardId']==c['id']),
             'overdue':sum(t['amount'] for t in cards if t['cardId']==c['id'] and t['date']<on),'remaining':sum(t['remaining'] for t in cards if t['cardId']==c['id']),
             'lastDue':max((t['date'] for t in cards if t['cardId']==c['id']),default=None)} for c in s['cards']]
    if any(r['cash'] is not None and r['cash']<0 for r in rows):warnings.append('O calendário pressupõe pagamento integral mesmo quando falta caixa. Nesses meses, a quitação indicada não está financiada pelo saldo projetado.')
    if any(r['incomeBasis']=='reference' for r in rows):warnings.append('Meses sem receita cadastrada usam a renda de referência como hipótese, sem garantir recebimento.')
    return {'initial':initial,'rows':rows,'cards':bycard,'clearMonth':clear,'cardClearMonth':card_clear,'unmodeled':unmodeled,'uncalendared':uncal,
            'warnings':list(dict.fromkeys(warnings)),'anticipations':anticipations,'advanceCost':total_advance,'released':total_released,'discountSaving':total_released-total_advance,
            'requestedExtra':requested_total,'unusedExtra':requested_total-total_advance,'interest':total_interest,
            'tightMonths':[r['month'] for r in rows if r['shortfall'] is not None and r['shortfall']>0],
            'maxBurden':max(rows,key=lambda r:r['debtPayment']) if rows else None,'coveredDebts':[d['id'] for d in s['debts'] if d not in loans]}


def report(s,p):
    o=options(p);base=trajectory(s,dict(o,monthlyExtra=0,lump=0,discount=0,discountBps=0));scenario=None
    if o['monthlyExtra'] or o['lump']:scenario=trajectory(s,o)
    return {'on':o['on'],'horizon':o['horizon'],'base':base,'scenario':scenario,'options':o,
            'notes':['Faturas são pagas integralmente no vencimento pelo valor cadastrado; não calcula juros de atraso, rotativo, multas ou compras novas.',
                     'Contratos avulsos com taxa e pagamento cadastrados usam juros mensais constantes. O saldo atual é manual: após pagar, confira e atualize com o credor. O vínculo de um pagamento não baixa esse saldo automaticamente.',
                     'Antecipação é apenas uma simulação de alocação, inclusive parcial. Não altera lançamentos nem executa pagamento. Confirme no banco a possibilidade de antecipar e o valor ofertado.',
                     'O valor nominal antecipado continua cumprindo o orçamento da categoria no mês original, evitando reservar novamente a mesma parcela. O cenário não cria novo limite para gastar o valor antecipado.',
                     'Desconto é hipótese informada pelo usuário e vale somente para a parte antecipada. Sem oferta informada, a economia é zero.',
                     'Extra mensal e pontual são pagamentos adicionais com dinheiro do caixa, não receitas novas. Para simular PLR, cadastre a receita prevista no extrato.',
                     'O mês atual considera os pagamentos ainda pendentes; os próximos meses são integrais. Contratos usam um período mensal cheio de juros a cada fechamento, inclusive no mês inicial.',
                     'Caixa é avaliado no fechamento mensal: pode haver falta de dinheiro entre os dias de recebimento e vencimento.']}
