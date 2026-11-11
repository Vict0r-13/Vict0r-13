"""Local fiscal document extraction. Never executes markup or submits access keys."""
import re, hashlib, calendar, unicodedata, math
from statistics import median
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date
from xml.etree import ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urlsplit, parse_qs

def norm(v):return ''.join(c for c in unicodedata.normalize('NFKD',str(v)).upper() if not unicodedata.combining(c))
def money(v):
 s=re.sub(r'[^\d,.-]','',str(v))
 if ',' in s:s=s.replace('.','').replace(',','.')
 try:return int((Decimal(s)*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
 except InvalidOperation:raise ValueError('Preço não reconhecido')
def number(v):return float(str(v).strip().replace(',','.'))
def key_hash(raw):
 m=re.search(r'(?<!\d)(\d{44})(?!\d)',raw)
 return hashlib.sha256(m[1].encode()).hexdigest() if m else ''
def official_url(raw):
 raw=raw.strip();u=urlsplit(raw)
 host=(u.hostname or '').lower()
 if u.scheme not in ('https','http') or u.username or u.password or u.port not in (None,80,443):raise ValueError('Use o endereço de consulta oficial do QR da nota.')
 if not (host.endswith('.sefaz.ce.gov.br') or host.endswith('.fazenda.gov.br') or re.fullmatch(r'(?:[a-z0-9-]+\.)*(?:sefaz|fazenda)\.[a-z]{2}\.gov\.br',host)):
  raise ValueError('O QR deve apontar para um portal fiscal oficial brasileiro.')
 return 'https://'+u.netloc+u.path+('?' +u.query if u.query else '')+('#'+u.fragment if u.fragment else '')

def stock_hint(name,qty,unit):
 u=norm(unit).strip();q=qty
 if u in ('KG','KILO'):return dict(stockQuantity=round(q*1000,6),stockUnit='g')
 if u in ('G','GR'):return dict(stockQuantity=q,stockUnit='g')
 if u in ('L','LT','LITRO'):return dict(stockQuantity=round(q*1000,6),stockUnit='ml')
 if u=='ML':return dict(stockQuantity=q,stockUnit='ml')
 # Only a single explicit package size is safe to suggest. Kits stay in units.
 packs=re.findall(r'(?<![\d.,])(\d+(?:[.,]\d+)?)\s*(KG|ML|G|L)\b',norm(name))
 if len(packs)==1 and not re.search(r'\b(KIT|PACK|C/|X\s*\d)',norm(name)):
  n,pu=packs[0];factor=1000 if pu in ('KG','L') else 1
  return dict(stockQuantity=round(q*number(n)*factor,6),stockUnit='ml' if pu in ('ML','L') else 'g')
 return dict(stockQuantity=q,stockUnit='un')
def row(name,quantity,unit,cost,code=''):
 name=re.sub(r'\s+',' ',name).strip()[:160]
 if not name or quantity<=0 or cost<0:raise ValueError('Item da nota inválido')
 return dict(name=name,quantity=quantity,unit=unit[:12],cost=cost,code=code[:80],category='Alimentação',**stock_hint(name,quantity,unit))

def xml_document(text):
 if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():raise ValueError('XML com entidades não é aceito')
 root=ET.fromstring(text)
 for el in root.iter():el.tag=el.tag.split('}')[-1]
 def txt(e,path,default=''):return e.findtext(path,default)
 items=[]
 for d in root.iter('det'):
  p=d.find('prod')
  if p is None:continue
  cost=money(txt(p,'vProd','0'))-money(txt(p,'vDesc','0'))+money(txt(p,'vFrete','0'))+money(txt(p,'vSeg','0'))+money(txt(p,'vOutro','0'))
  items.append(row(txt(p,'xProd'),number(txt(p,'qCom','1')),txt(p,'uCom','UN'),cost,txt(p,'cEAN') if txt(p,'cEAN') not in ('','SEM GTIN') else txt(p,'cProd')))
 total=next((money(el.text) for tag in ('vNF','vCFe') for el in root.iter(tag) if el.text),None)
 store=next((txt(e,'xFant') or txt(e,'xNome') for e in root.iter('emit')),'')
 when=next((el.text[:10] for el in root.iter('dhEmi') if el.text),'')
 if not when:
  when=next((el.text for el in root.iter('dEmi') if el.text),'')
  if len(when)==8:when=when[:4]+'-'+when[4:6]+'-'+when[6:]
 return dict(items=items,total=total,store=store[:160],date=when,source='XML fiscal')
class TextHTML(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.skip=0
 def handle_starttag(self,t,a):
  if t in ('script','style'):self.skip+=1
  if t in ('tr','div','p','br','li'):self.parts.append('\n')
 def handle_endtag(self,t):
  if t in ('script','style'):self.skip=max(0,self.skip-1)
  if t in ('tr','div','p','li'):self.parts.append('\n')
 def handle_data(self,d):
  if not self.skip:self.parts.append(d+' ')
def layout_text(blocks):
 """Join separate OCR columns by physical baseline; never deduplicate repeated products."""
 if not isinstance(blocks,list) or len(blocks)>1500:raise ValueError('Quantidade de trechos reconhecidos inválida')
 words=[];slopes=[]
 for r in blocks:
  if not isinstance(r,dict) or not isinstance(r.get('text'),str) or len(r['text'])>10000:raise ValueError('Trecho reconhecido inválido')
  b=r.get('box')
  if not isinstance(b,list) or len(b)!=4 or any(not isinstance(x,list) or len(x)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e6 for v in x) for x in b):raise ValueError('Posição do texto inválida')
  x=sum(q[0] for q in b)/4;y=sum(q[1] for q in b)/4;h=max(math.hypot(b[3][0]-b[0][0],b[3][1]-b[0][1]),1);w=math.hypot(b[1][0]-b[0][0],b[1][1]-b[0][1]);dx=b[1][0]-b[0][0];slope=(b[1][1]-b[0][1])/dx if abs(dx)>1 else 0
  if abs(slope)<.3 and w>h*3:slopes.append(slope)
  words.append(dict(text=r['text'].strip(),x=x,y=y,h=h,slope=slope if abs(slope)<.3 else 0,w=w))
 if not words:return ''
 tilt=median(slopes) if slopes else 0;rows=[]
 for word in sorted(words,key=lambda a:a['y']-tilt*a['x']):
  nearest=None;distance=float('inf')
  for row_ in rows:
   anchor=max(row_,key=lambda a:a['w']);predicted=anchor['y']+anchor['slope']*(word['x']-anchor['x']);d=abs(word['y']-predicted)
   if d<min(anchor['h'],word['h'])*.53 and d<distance:nearest=row_;distance=d
  if nearest is None:rows.append([word])
  else:nearest.append(word)
 rows.sort(key=lambda a:median(v['y']-tilt*v['x'] for v in a))
 return '\n'.join(' '.join(w['text'] for w in sorted(r,key=lambda a:a['x'])) for r in rows)

AMOUNT=r'\d+(?:[.,]\d{2,3})'
UNITS=r'UNID|UND|UN|KG|GR|G|ML|LT|L|PC|PCT|CX'
def clean_name(name):
 name=re.sub(r'^\s*\d{1,4}\s+','',name);code='';barcode=re.match(r'^(\d{6,14})\s+',name)
 if barcode:code=barcode[1];name=name[barcode.end():]
 return name.strip(),code

def plain_document(text):
 lines=[re.sub(r'\s+',' ',x).strip() for x in text.splitlines() if x.strip()];items=[];total=None;warnings=[];expected=None
 for idx,line in enumerate(lines):
  n=norm(line)
  if re.search(r'(?:QTD[E]?\.?|QUANTIDADE)\s*:?\s*(?:TOTAL\s+)?(?:DE\s+)?ITENS',n):
   tail=re.split(r'ITENS',n,1)[-1];m=re.search(r'^\s*[:=]?\s*(\d{1,3})\s*$',tail)
   if not m:
    m=next((re.match(r'^\s*(\d{1,3})\s*$',v) for v in lines[idx+1:idx+3] if re.match(r'^\s*(\d{1,3})\s*$',v)),None)
   if m and 1<=int(m[1])<=500:expected=int(m[1])
 # Structured public NFC-e rows.
 pattern=r'(.+?)\s*\(\s*C[oó]digo\s*:\s*([^)]*)\)\s*Qtde\.?\s*:\s*([\d.,]+)\s*UN\s*:\s*(\w+)\s*Vl\.?\s*Unit\.?\s*:\s*([\d.,]+)(?:\s*Vl\.?\s*Total\s*[:\s]*)?\s*([\d.,]+)'
 for line in lines:
  m=re.search(pattern,line,re.I)
  if m:items.append(row(m[1],number(m[3]),m[4],money(m[6]),m[2]))
 if not items:
  pending='';in_table=False;pending_code=''
  def incomplete(raw):
   name,code=clean_name(raw)
   # A name-only row is a draft, never a zero-cost product or a confirmed expense.
   if not re.search(r'[A-ZÀ-Ý]{2}',norm(name)) or re.fullmatch(UNITS,norm(name)):return
   name=re.sub(r'\s+\d+[.,]\d{2}(?:\s+\d+[.,]\d{2})?\s*$','',name).strip()
   if name:items.append(dict(name=name[:160],code=code,quantity=None,unit='UN',cost=None,stockQuantity=None,stockUnit='un',category='Alimentação',needsReview=True))
  for line in lines:
   upper=norm(line)
   if upper=='CODIGO' or re.search(r'DESCRIC[A4Ã]?[O0]|(?:QTD[E]?|QTDE).*VL.*UNIT',upper):in_table=True;pending='';continue
   if re.search(r'\b(TOTAL|SUBTOTAL|TROCO|PAGAMENTO|DINHEIRO|CARTAO|PIX|DESCONTO|CNPJ|CPF|CHAVE|TRIBUTOS|QTDE|QTD|QUANTIDADE|ITENS)\b',upper):
    if in_table and pending:incomplete(pending)
    pending='';in_table=False;continue
   m=re.search(r'(?<![\w.,])([\d]+(?:[,.]\d+)?)\s*('+UNITS+r')\s*(?:[xX*]|[aà])?\s*(?:R\$\s*)?('+AMOUNT+r')\s+(?:R\$\s*)?('+AMOUNT+r')\s*$',line,re.I)
   if m:
    prefix=line[:m.start()].strip()
    if prefix and pending and in_table:incomplete(pending)
    name,code=clean_name(prefix or pending)
    if name:
     item=row(name,number(m[1]),m[2],money(m[4]),code);item['unitPrice']=money(m[3])
     if abs(round(item['quantity']*item['unitPrice'])-item['cost'])>2:item['needsReview']=True;item['reviewReason']='Quantidade × preço unitário difere do total. Confira possíveis erros ou descontos.'
     items.append(item)
    pending=''
   else:
    # Keep uncertain product names only within a recognized product table or after a product code.
    if pending and in_table:incomplete(pending)
    if in_table or re.match(r'^\d{6,14}\s+\S',line):pending=line
    elif not re.search(r'FISCAL|CONSUMIDOR|CUPOM|EMISSAO|ENDERECO|FORMA DE|VALOR|QTDE|ITENS|CODIGO|CEP|FONE',upper):pending=line
  if in_table and pending:incomplete(pending)
 total_priority=0
 for idx,line in enumerate(lines):
  if re.search(r'(VALOR\s+A\s+PAGAR|VALOR\s+TOTAL(?:\s+R\$)?|TOTAL\s+DA\s+NOTA|TOTAL\s+R\$)',norm(line)):
   if re.search(r'DESCONTO|QTD|QUANTIDADE|TRIBUT',norm(line)):continue
   amounts=re.findall(r'\d[\d.]*[,.]\d{2}\b',line)
   if not amounts and idx+1<len(lines):amounts=re.findall(r'^\s*(?:R\$\s*)?(\d[\d.]*[,.]\d{2})\s*$',lines[idx+1])
   priority=3 if 'A PAGAR' in norm(line) else 2 if 'DA NOTA' in norm(line) else 1
   if amounts and priority>=total_priority:total=money(amounts[-1]);total_priority=priority
 when='';m=re.search(r'\b(\d{2})/(\d{2})/(20\d{2})\b',text)
 if m:
  try:when=date(int(m[3]),int(m[2]),int(m[1])).isoformat()
  except ValueError:pass
 if not items:warnings.append('Não reconheci produtos com segurança. Refaça a foto com os preços nítidos, ajuste os cantos ou use o QR / XML.')
 missing=sum(bool(i.get('needsReview')) for i in items)
 if missing:warnings.append(f'{missing} produto(s) com campos não reconhecidos. Abra Conferir em cada um antes de registrar. Valores ausentes não foram preenchidos com zero.')
 if expected is not None and expected!=len(items):warnings.append(f'A nota informa {expected} itens, mas a leitura encontrou {len(items)}. Confira os produtos ausentes antes de registrar.')
 return dict(items=items,total=total,store='',date=when,source='Leitura da nota',warnings=warnings,expectedItems=expected)

def parse(text,kind='text',blocks=None):
 if blocks is not None:text=layout_text(blocks)
 if not isinstance(text,str) or len(text)>2_000_000:raise ValueError('Nota vazia ou maior que 2 MB')
 if kind=='xml' or re.search(r'<(?:\w+:)?(?:nfeProc|NFe|CFe)\b',text):
  try:out=xml_document(text)
  except ET.ParseError:raise ValueError('XML fiscal inválido')
 else:
  if kind=='html':
   original=text
   p=TextHTML();p.feed(text);plain=''.join(p.parts)
   rows=[]
   for htmlrow in re.findall(r'<tr\b[^>]*>(.*?)</tr>',text,re.I|re.S):
    r=TextHTML();r.feed(htmlrow);rows.append(re.sub(r'\s+',' ',''.join(r.parts)).strip())
   text='\n'.join(rows)+'\n'+plain if rows else plain
   out=plain_document(text)
   out['fingerprint']=key_hash(original)
  else:out=plain_document(text)
 out.setdefault('fingerprint',key_hash(text));out.setdefault('warnings',[])
 if blocks is not None and out.get('expectedItems') is None:out['warnings'].append('Quantidade total de itens não reconhecida. Confira a contagem da nota: a leitura pode estar incompleta.')
 out['recognizedText']=text[:200000] if kind!='xml' else ''
 out['itemTotal']=sum(i['cost'] or 0 for i in out['items'])
 if out['total'] is None:out['warnings'].append('Total da nota não reconhecido. Confira o valor impresso antes de confirmar.')
 elif out['itemTotal']!=out['total']:out['warnings'].append('A soma dos itens difere do total. Confira itens, descontos e acréscimos antes de registrar.')
 if not out['fingerprint']:out['warnings'].append('Chave fiscal não reconhecida. Confira se esta compra já foi lançada antes de confirmar.')
 if not out['date']:out['warnings'].append('Data não reconhecida. Informe a data da compra.')
 return out

def expiry_candidates(text):
 result=[]
 for line in text.splitlines():
  n=norm(line)
  if ('FAB' in n or 'LOTE' in n) and not re.search(r'VAL|VENC|CONSUM',n):continue
  for m in re.finditer(r'\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2}|20\d{2})\b',n):
   try:
    y=int(m[3]);y=y+2000 if y<100 else y;d=date(y,int(m[2]),int(m[1]));result.append(dict(date=d.isoformat(),precision='day'))
   except ValueError:pass
 return list({r['date']:r for r in result}.values())
