"""Household stock, recipe costing and meal planning. Quantities use g, ml or unit."""
import copy,math,uuid
from datetime import date,timedelta

def empty():return dict(products=[],lots=[],recipes=[],plans=[],uses=[],settings=dict(days=7,desktop=False))
def uid():return str(uuid.uuid4())
def num(x,lo=0,hi=1e9):
 if type(x) not in (int,float) or not math.isfinite(x) or not lo<=x<=hi:raise ValueError('Quantidade ou valor inválido')
 return round(float(x),6)
def text(x,limit=500):
 if not isinstance(x,str) or len(x)>limit:raise ValueError('Texto inválido')
 return x.strip()
def dt(x):date.fromisoformat(x);return x
def find(rows,key):
 r=next((r for r in rows if r['id']==key),None)
 if r is None:raise ValueError('Registro não encontrado; atualize a tela')
 return r
def cents(x,nullable=False):
 if x is None and nullable:return None
 if type(x) is not int or not 0<=x<=10**12:raise ValueError('Custo inválido')
 return x

def validate(s):
 h=s.get('household',empty());settings=h.get('settings',{})
 if type(settings.get('days')) is not int or not 0<=settings['days']<=90 or type(settings.get('desktop')) is not bool:raise ValueError('Configuração de avisos inválida')
 for key in ('products','lots','recipes','plans','uses'):
  if not isinstance(h.get(key),list) or len(h[key])>30000:raise ValueError('Lista doméstica inválida')
  ids=set()
  for r in h[key]:
   ident=text(r.get('id'),100)
   if not ident or ident in ids:raise ValueError('ID doméstico duplicado')
   ids.add(ident)
 products={p['id']:p for p in h['products']};lots={l['id']:l for l in h['lots']};recipes={r['id']:r for r in h['recipes']};transactions={t['id']:t for t in s['transactions']}
 for p in h['products']:
  if not text(p.get('name'),160):raise ValueError('Informe o nome do produto')
  if p.get('unit') not in ('g','ml','un') or p.get('category') not in ('Alimentação','Limpeza','Higiene','Outros'):raise ValueError('Unidade ou categoria inválida')
  num(p.get('minimum'));text(p.get('notes',''))
 for l in h['lots']:
  if l.get('productId') not in products:raise ValueError('Produto do lote não existe')
  num(l.get('quantity'),.000001);num(l.get('remaining'),0,l['quantity']);cents(l.get('cost'),True);cents(l.get('remainingCost'),True)
  if (l['cost'] is None)!=(l['remainingCost'] is None):raise ValueError('Custo parcial inconsistente')
  if l['cost'] is not None and l['remainingCost']>l['cost']:raise ValueError('Custo restante inconsistente')
  dt(l.get('date'));dt(l['expiry']) if l.get('expiry') else None
  text(l.get('location'));text(l.get('store'));text(l.get('notes',''))
  if l.get('txId'):
   t=transactions.get(l['txId'])
   if not t or t.get('stockLotId')!=l['id'] or t['type']!='expense' or t['amount']!=l['cost'] or t['date']!=l.get('txDate',l['date']) or t['category']!=products[l['productId']]['category']:
    raise ValueError('Compra vinculada ao estoque: corrija ou exclua o lote em Casa e alimentação, sem alterar sua despesa separadamente')
 for t in s['transactions']:
  if t.get('stockLotId') and (t['stockLotId'] not in lots or lots[t['stockLotId']].get('txId')!=t['id']):raise ValueError('Compra aponta para lote inexistente')
 for r in h['recipes']:
  if not text(r.get('name'),160):raise ValueError('Nome da receita obrigatório')
  num(r.get('servings'),.01,10000);text(r.get('notes',''),5000)
  if not isinstance(r.get('ingredients'),list) or not 1<=len(r['ingredients'])<=100:raise ValueError('Inclua ao menos um ingrediente')
  seen=set()
  for i in r['ingredients']:
   p=products.get(i.get('productId'))
   if not p or p['category']!='Alimentação' or p['id'] in seen:raise ValueError('Ingrediente inválido, repetido ou não alimentar')
   num(i.get('quantity'),.000001);seen.add(p['id'])
 for p in h['plans']:
  dt(p.get('date'));text(p.get('meal'),80);num(p.get('servings'),.01,10000)
  if p.get('recipeId') not in recipes or p.get('status') not in ('planned','done'):raise ValueError('Refeição inválida')
 for u in h['uses']:
  dt(u.get('date'));text(u.get('name'),160);text(u.get('kind'),20)
  if u['kind'] not in ('consumption','discard','meal'):raise ValueError('Baixa inválida')
  if not isinstance(u.get('items'),list) or not u['items']:raise ValueError('Baixa sem itens')
  for i in u['items']:
   if i.get('lotId') not in lots:raise ValueError('Histórico aponta para lote inexistente')
   num(i.get('quantity'),.000001);cents(i.get('cost'),True)
 for l in h['lots']:
  used=[i for u in h['uses'] for i in u['items'] if i['lotId']==l['id']]
  if abs(l['remaining']+sum(i['quantity'] for i in used)-l['quantity'])>0.00001:raise ValueError('Quantidade do lote não confere com o histórico de baixas')
  if l['cost'] is not None and (any(i['cost'] is None for i in used) or l['remainingCost']+sum(i['cost'] for i in used)!=l['cost']):raise ValueError('Custo do lote não confere com o histórico')
 return s

def expire(h,on=None):
 today=date.fromisoformat(on) if on else date.today();rows=[]
 for l in h['lots']:
  if l['remaining']<=0 or not l['expiry']:continue
  days=(date.fromisoformat(l['expiry'])-today).days
  if days<=h['settings']['days']:rows.append(dict(lotId=l['id'],name=find(h['products'],l['productId'])['name'],days=days,expiry=l['expiry'],quantity=l['remaining'],unit=find(h['products'],l['productId'])['unit']))
 return sorted(rows,key=lambda r:r['days'])

def allocate(h,product,quantity,on):
 remaining=quantity;items=[]
 for l in sorted([l for l in h['lots'] if l['productId']==product and l['remaining']>0 and l['date']<=on and (not l['expiry'] or l['expiry']>=on)],key=lambda l:(l['expiry'] or '9999-12-31',l['date'],l['id'])):
  take=min(remaining,l['remaining'])
  if take<=0:continue
  cost=None if l['remainingCost'] is None else l['remainingCost'] if abs(take-l['remaining'])<.000001 else round(l['remainingCost']*take/l['remaining'])
  l['remaining']=round(l['remaining']-take,6)
  if cost is not None:l['remainingCost']-=cost
  items.append(dict(lotId=l['id'],quantity=take,cost=cost));remaining=round(remaining-take,6)
  if remaining<=0:break
 return items,max(0,remaining)

def estimate(h,recipe,servings,on=None):
 on=on or date.today().isoformat();work=copy.deepcopy(h);items=[];shortages=[];details=[]
 for i in recipe['ingredients']:
  need=round(i['quantity']*servings/recipe['servings'],6);taken,short=allocate(work,i['productId'],need,on);items+=taken
  details.append(dict(productId=i['productId'],quantity=need,cost=sum(t['cost'] or 0 for t in taken),complete=short==0 and all(t['cost'] is not None for t in taken)))
  if short>0:shortages.append(dict(productId=i['productId'],quantity=short))
 return dict(details=details,items=items,shortages=shortages,cost=sum(i['cost'] or 0 for i in items),complete=not shortages and all(i['cost'] is not None for i in items))

def shopping(h,start,end):
 dt(start);dt(end)
 if end<start:raise ValueError('Período inválido')
 work=copy.deepcopy(h);missing={}
 for p in sorted([p for p in h['plans'] if p['status']=='planned' and start<=p['date']<=end],key=lambda p:p['date']):
  recipe=find(h['recipes'],p['recipeId'])
  for i in recipe['ingredients']:
   _,short=allocate(work,i['productId'],round(i['quantity']*p['servings']/recipe['servings'],6),p['date'])
   missing[i['productId']]=missing.get(i['productId'],0)+short
 result=[]
 for ident,qty in missing.items():
  if qty<=.000001:continue
  p=find(h['products'],ident);history=sorted([l for l in h['lots'] if l['productId']==ident and l['cost'] is not None][::-1],key=lambda l:l['date'],reverse=True)
  price=history[0]['cost']/history[0]['quantity'] if history else None
  result.append(dict(productId=ident,name=p['name'],unit=p['unit'],quantity=round(qty,6),estimatedCost=None if price is None else round(price*qty)))
 return result

def summary(s,start,end):
 h=s['household'];today=date.today().isoformat();alerts=expire(h);rows=[]
 for p in h['products']:
  ls=[l for l in h['lots'] if l['productId']==p['id']];valid=[l for l in ls if l['date']<=today and (not l['expiry'] or l['expiry']>=today)];qty=sum(l['remaining'] for l in valid)
  prices=[dict(date=l['date'],store=l['store'],unitCost=l['cost']/l['quantity']) for l in ls if l['cost'] is not None]
  rows.append(dict(**p,quantity=round(qty,6),totalQuantity=round(sum(l['remaining'] for l in ls),6),low=qty<p['minimum'],value=sum(l['remainingCost'] or 0 for l in ls),unknown=sum(1 for l in ls if l['remaining']>0 and l['remainingCost'] is None),prices=prices))
 uses=[u for u in h['uses'] if start<=u['date']<=end];purchases=[t for t in s['transactions'] if (t.get('stockLotId') or t.get('purchaseId')) and t['status']=='paid' and start<=t['paidDate']<=end]
 return dict(products=rows,alerts=alerts,purchases=sum(t['amount'] for t in purchases),consumed=sum(i['cost'] or 0 for u in uses if u['kind']!='discard' for i in u['items']),waste=sum(i['cost'] or 0 for u in uses if u['kind']=='discard' for i in u['items']),unknownUses=sum(1 for u in uses for i in u['items'] if i['cost'] is None),value=sum(l['remainingCost'] or 0 for l in h['lots']),recipes=[dict(id=r['id'],**estimate(h,r,r['servings'])) for r in h['recipes']],shopping=shopping(h,start,end))

def command(s,p):
 h=s['household'];action=p.get('action');today=date.today().isoformat()
 if action=='product':
  old=next((a for a in h['products'] if a['id']==p.get('id')),None)
  row=dict(id=old['id'] if old else uid(),name=text(p.get('name'),160),unit=p.get('unit'),category=p.get('category'),minimum=num(p.get('minimum',0)),notes=text(p.get('notes','')))
  if old and any(l['productId']==old['id'] for l in h['lots']) and (old['unit']!=row['unit'] or old['category']!=row['category']):raise ValueError('Unidade e categoria não podem mudar após registrar lotes')
  h['products']=[row if a['id']==row['id'] else a for a in h['products']] if old else h['products']+[row]
 elif action=='lot':
  product=find(h['products'],p.get('productId'));quantity=num(p.get('quantity'),.000001);when=dt(p.get('date'));cost=cents(p.get('cost'),True)
  if when>today:raise ValueError('Registre a entrada quando o produto estiver em casa')
  expiry=p.get('expiry','');dt(expiry) if expiry else None
  l=dict(id=uid(),productId=product['id'],quantity=quantity,remaining=quantity,cost=cost,remainingCost=cost,date=when,expiry=expiry,location=text(p.get('location','')),store=text(p.get('store','')),notes=text(p.get('notes','')),txId='')
  mode=p.get('payment','existing')
  if mode not in ('existing','cash','card'):raise ValueError('Forma de registro inválida')
  if mode!='existing':
   if cost is None:raise ValueError('Informe o valor pago pela compra')
   card=find(s['cards'],p.get('cardId')) if mode=='card' else None
   due=dt(p.get('due')) if card else when
   l['txId']=uid();s['transactions'].append(dict(id=l['txId'],name='Compra · '+product['name'],amount=cost,date=due,paidDate='' if card else when,status='planned' if card else 'paid',type='expense',category=product['category'],cardId=card['id'] if card else '',notes='Gerado pelo estoque. Não lançar novamente.',stockLotId=l['id']))
   l['date']=when
   # Card due date is distinct from physical receipt date.
   l['txDate']=due
  h['lots'].append(l)
 elif action=='lot_details':
  l=find(h['lots'],p.get('id'));l['expiry']=p.get('expiry','');dt(l['expiry']) if l['expiry'] else None;l['location']=text(p.get('location',''));l['notes']=text(p.get('notes',''))
 elif action=='remove_lot':
  l=find(h['lots'],p.get('id'))
  if l.get('purchaseId'):raise ValueError('Use Comprar para desfazer a compra inteira e preservar os totais')
  if l['remaining']!=l['quantity'] or any(any(i['lotId']==l['id'] for i in u['items']) for u in h['uses']):raise ValueError('Lote com baixas: estorne os usos antes de excluir')
  h['lots'].remove(l);s['transactions']=[t for t in s['transactions'] if t['id']!=l['txId']]
 elif action=='recipe':
  old=next((r for r in h['recipes'] if r['id']==p.get('id')),None)
  if old and any(pl['recipeId']==old['id'] and pl['status']=='done' for pl in h['plans']):raise ValueError('Receita já preparada: crie outra versão para preservar o histórico')
  row=dict(id=old['id'] if old else uid(),name=text(p.get('name'),160),servings=num(p.get('servings'),.01),ingredients=p.get('ingredients'),notes=text(p.get('notes',''),5000))
  h['recipes']=[row if r['id']==row['id'] else r for r in h['recipes']] if old else h['recipes']+[row]
 elif action=='plan':
  find(h['recipes'],p.get('recipeId'));h['plans'].append(dict(id=uid(),date=dt(p.get('date')),meal=text(p.get('meal'),80),recipeId=p['recipeId'],servings=num(p.get('servings'),.01),status='planned'))
 elif action=='remove_plan':
  pl=find(h['plans'],p.get('id'))
  if pl['status']=='done':raise ValueError('Estorne o preparo antes de excluir a refeição')
  h['plans'].remove(pl)
 elif action=='prepare':
  pl=find(h['plans'],p.get('id'))
  if pl['status']=='done':raise ValueError('Essa refeição já foi preparada')
  when=dt(p.get('date',today))
  if when>today:raise ValueError('Preparo não pode ser registrado no futuro')
  recipe=find(h['recipes'],pl['recipeId']);preview=estimate(h,recipe,pl['servings'],when)
  if preview['shortages']:raise ValueError('Estoque insuficiente ou vencido. Confira a lista de compras e os lotes.')
  items=[]
  for ingredient in recipe['ingredients']:
   allocated,_=allocate(h,ingredient['productId'],round(ingredient['quantity']*pl['servings']/recipe['servings'],6),when);items+=allocated
  h['uses'].append(dict(id=uid(),date=when,name=recipe['name'],kind='meal',planId=pl['id'],items=items));pl['status']='done'
 elif action=='use':
  l=find(h['lots'],p.get('id'));q=num(p.get('quantity'),.000001,l['remaining']);kind=p.get('kind');when=dt(p.get('date',today))
  if when>today or when<l['date']:raise ValueError('Data da baixa inválida')
  if kind not in ('consumption','discard'):raise ValueError('Tipo de baixa inválido')
  if kind=='consumption' and l['expiry'] and l['expiry']<when:raise ValueError('Lote vencido: registre descarte ou corrija a data conferindo o rótulo')
  cost=None if l['remainingCost'] is None else l['remainingCost'] if q==l['remaining'] else round(l['remainingCost']*q/l['remaining']);l['remaining']=round(l['remaining']-q,6)
  if cost is not None:l['remainingCost']-=cost
  h['uses'].append(dict(id=uid(),name=find(h['products'],l['productId'])['name'],kind=kind,date=when,items=[dict(lotId=l['id'],quantity=q,cost=cost)]))
 elif action=='undo_use':
  u=find(h['uses'],p.get('id'))
  for i in u['items']:
   l=find(h['lots'],i['lotId']);l['remaining']=round(l['remaining']+i['quantity'],6)
   if i['cost'] is not None:l['remainingCost']+=i['cost']
  if u.get('planId'):find(h['plans'],u['planId'])['status']='planned'
  h['uses'].remove(u)
 elif action=='settings':h['settings']=dict(days=p.get('days'),desktop=p.get('desktop'))
 elif action=='delete_product':
  ident=p.get('id')
  if any(l['productId']==ident for l in h['lots']) or any(any(i['productId']==ident for i in r['ingredients']) for r in h['recipes']):raise ValueError('Produto possui lotes ou receitas vinculadas')
  h['products'].remove(find(h['products'],ident))
 elif action=='delete_recipe':
  if any(pl['recipeId']==p.get('id') for pl in h['plans']):raise ValueError('Receita possui refeições planejadas ou preparadas')
  h['recipes'].remove(find(h['recipes'],p.get('id')))
 else:raise ValueError('Operação doméstica desconhecida')
 return s
