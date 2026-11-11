"""Atomic checkout: one reviewed purchase, category expenses and ordered stock lots."""
import copy, re
from datetime import date
from household import uid, text, num, cents, dt, find
from receipts import norm
CATEGORIES=('Alimentação','Limpeza','Higiene','Outros')
def empty():return dict(cart=None,purchases=[])
def validate_item(i,incomplete=False):
 if not text(i.get('name'),160):raise ValueError('Informe o produto')
 if i.get('needsReview'):
  if incomplete:
   text(i.get('code',''),80)
   if i.get('category') not in CATEGORIES or i.get('stockUnit') not in ('g','ml','un'):raise ValueError('Confira a unidade e categoria do rascunho')
   if i.get('quantity') is not None:num(i['quantity'],.000001)
   if i.get('stockQuantity') is not None:num(i['stockQuantity'],.000001)
   cents(i.get('cost'),True)
   return
  raise ValueError('Há produtos com campos não reconhecidos. Abra Conferir para preencher quantidade, unidade e valor.')
 num(i.get('quantity'),.000001);cents(i.get('cost'))
 if i.get('stockUnit') not in ('g','ml','un') or i.get('category') not in CATEGORIES:raise ValueError('Confira a unidade e categoria de cada item')
 num(i.get('stockQuantity'),.000001);text(i.get('code',''),80)
 if i.get('expiry'):dt(i['expiry'])
def validate(s):
 sh=s.get('shopping',empty())
 if not isinstance(sh,dict) or not isinstance(sh.get('purchases'),list) or len(sh['purchases'])>10000:raise ValueError('Histórico de compras inválido')
 cart=sh.get('cart')
 if cart:
  text(cart.get('id'),100);text(cart.get('store',''),160);cents(cart.get('budget',0))
  if not isinstance(cart.get('items'),list) or len(cart['items'])>500:raise ValueError('Carrinho suporta até 500 itens')
  for i in cart['items']:validate_item(i,True)
  count=cart.get('expectedItems')
  if count is not None and (type(count) is not int or not 1<=count<=500):raise ValueError('Quantidade de itens da nota inválida')
 seen=set();prints=set();lots={l['id']:l for l in s['household']['lots']};products={p['id']:p for p in s['household']['products']}
 for p in sh['purchases']:
  if not p.get('id') or p['id'] in seen:raise ValueError('Compra duplicada')
  seen.add(p['id']);dt(p['date']);text(p['store'],160);cents(p['total']);text(p.get('fingerprint',''),64)
  fp=p.get('fingerprint')
  if fp and p['payment']!='existing' and any(t.get('receiptFingerprint')==fp for t in s['transactions']):raise ValueError('Nota já registrada no extrato: use somente estoque, sem nova despesa.')
  if fp and fp in prints:raise ValueError('Esta nota já foi importada')
  if fp:prints.add(fp)
  if p.get('payment') not in ('existing','cash','card'):raise ValueError('Pagamento inválido')
  if not isinstance(p.get('items'),list) or not 1<=len(p['items'])<=500:raise ValueError('Compra sem itens')
  groups={};used=set()
  for i in p['items']:
   validate_item(i);l=lots.get(i.get('lotId'));product=products.get(i.get('productId'))
   if not l or not product or l['id'] in used or l.get('purchaseId')!=p['id'] or l['productId']!=product['id'] or l['cost']!=i['cost'] or abs(l['quantity']-i['stockQuantity'])>.000001 or l['date']!=p['date'] or product['unit']!=i['stockUnit'] or product['category']!=i['category']:raise ValueError('Compra e estoque vinculados: corrija a compra inteira em Comprar')
   used.add(l['id']);groups[i['category']]=groups.get(i['category'],0)+i['cost']
  if {l['id'] for l in lots.values() if l.get('purchaseId')==p['id']}!=used:raise ValueError('Lote não corresponde aos itens da compra')
  if sum(groups.values())!=p['total']:raise ValueError('O total deve ser igual à soma dos itens. Confira descontos e acréscimos.')
  tx=[t for t in s['transactions'] if t.get('purchaseId')==p['id']]
  if p['payment']=='existing':
   if tx:raise ValueError('Compra já lançada não pode gerar despesa adicional')
  else:
   if len(tx)!=len(groups) or {t['category']:t['amount'] for t in tx}!=groups or any(t['type']!='expense' or t['date']!=p['due'] or t.get('cardId','')!=p['cardId'] for t in tx):raise ValueError('Despesa vinculada à compra: altere a compra inteira em Comprar; use Baixar para pagar')
 for t in s['transactions']:
  if t.get('purchaseId') and t['purchaseId'] not in seen:raise ValueError('Despesa aponta para compra inexistente')
 for l in lots.values():
  if l.get('purchaseId') and l['purchaseId'] not in seen:raise ValueError('Lote aponta para compra inexistente')
 return s

def command(s,p):
 sh=s.setdefault('shopping',empty());action=p.get('action')
 if action=='cart':
  sh['cart']=copy.deepcopy(p.get('cart'));validate(s);return s
 if action=='expiry':
  rows=p.get('items')
  if not isinstance(rows,list) or len(rows)>500:raise ValueError('Lista de validades inválida')
  for r in rows:
   l=find(s['household']['lots'],r.get('lotId'));l['expiry']=dt(r['date']) if r.get('date') else ''
  return s
 if action=='reverse':
  purchase=find(sh['purchases'],p.get('id'));ids={i['lotId'] for i in purchase['items']}
  if any(i['lotId'] in ids for u in s['household']['uses'] for i in u['items']):raise ValueError('Há produtos com baixas. Estorne os usos antes de desfazer a compra.')
  s['household']['lots']=[l for l in s['household']['lots'] if l['id'] not in ids];s['transactions']=[t for t in s['transactions'] if t.get('purchaseId')!=purchase['id']];sh['purchases'].remove(purchase);return s
 if action!='checkout':raise ValueError('Operação de compras desconhecida')
 cart=copy.deepcopy(p.get('cart',{}));ident=text(cart.get('id'),100)
 if cart.get('fingerprint') and any(t.get('receiptFingerprint')==cart['fingerprint'] for t in s['transactions']) and p.get('payment')!='existing':raise ValueError('Esta nota já foi lançada no extrato. Escolha Despesa já lançada · somente estoque para não duplicar o gasto.')
 if any(a['id']==ident or (cart.get('fingerprint') and a.get('fingerprint')==cart['fingerprint']) for a in sh['purchases']):raise ValueError('Esta compra já foi registrada. Consulte o histórico em Comprar.')
 items=cart.get('items',[])
 if not 1<=len(items)<=500:raise ValueError('Inclua de 1 a 500 itens')
 when=dt(p.get('date'));today=date.today().isoformat()
 if when>today:raise ValueError('Registre a compra após receber os produtos')
 total=cents(p.get('total'));payment=p.get('payment');store=text(cart.get('store',''),160)
 if payment not in ('cash','card','existing'):raise ValueError('Escolha a forma de pagamento')
 if cart.get('fromPhoto') and (cart.get('fiscalTotal') is None or cart.get('expectedItems') is None):raise ValueError('Confira o total e a quantidade de itens da nota antes de registrar a foto.')
 if cart.get('fiscalTotal') is not None and cart.get('fromPhoto') and total!=cart['fiscalTotal']:raise ValueError('O total confirmado difere do valor conferido da nota.')
 if cart.get('expectedItems') is not None and cart['expectedItems']!=len(items):raise ValueError('A quantidade de produtos difere da nota. Adicione os itens ausentes ou corrija a contagem conferindo o documento.')
 for i in items:validate_item(i)
 if sum(cents(i.get('cost')) for i in items)!=total:raise ValueError('A soma dos itens não confere com o total. Corrija os itens ou distribua o desconto antes de confirmar.')
 card=find(s['cards'],p.get('cardId')) if payment=='card' else None
 due=dt(p.get('due')) if card else when;h=s['household'];groups={}
 for i in items:
  validate_item(i);prod=next((a for a in h['products'] if a['id']==i.get('productId')),None)
  if not prod:prod=next((a for a in h['products'] if norm(a['name'])==norm(i['name']) and a['unit']==i['stockUnit'] and a['category']==i['category']),None)
  if prod and (prod['unit']!=i['stockUnit'] or prod['category']!=i['category']):raise ValueError('Unidade ou categoria difere do produto existente. Confira a conversão do estoque.')
  if not prod:
   prod=dict(id=uid(),name=i['name'],unit=i['stockUnit'],category=i['category'],minimum=0,notes='');h['products'].append(prod)
  lot=dict(id=uid(),productId=prod['id'],purchaseId=ident,quantity=i['stockQuantity'],remaining=i['stockQuantity'],cost=i['cost'],remainingCost=i['cost'],date=when,expiry=i.get('expiry',''),location='',store=store,notes='',txId='')
  h['lots'].append(lot);i['lotId']=lot['id'];i['productId']=prod['id'];groups[i['category']]=groups.get(i['category'],0)+i['cost']
 purchase=dict(id=ident,store=store,date=when,due=due,cardId=card['id'] if card else '',payment=payment,total=total,items=items,fingerprint=cart.get('fingerprint',''))
 sh['purchases'].append(purchase)
 if payment!='existing':
  for cat,cost in groups.items():s['transactions'].append(dict(id=uid(),name='Compra · '+(store or 'Mercado')+' · '+cat,amount=cost,date=due,paidDate='' if card else when,status='planned' if card else 'paid',type='expense',category=cat,cardId=card['id'] if card else '',notes='Itens e validades em Comprar. Não lançar novamente.',purchaseId=ident))
 sh['cart']=None;return s
