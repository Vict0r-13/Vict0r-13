"""Reviewed receipt-to-ledger imports; opt-in CE public consultation, no TLS bypass."""
import copy,hashlib,re,ssl,socket,ipaddress,threading
from datetime import date
from urllib.parse import urlsplit,urlunsplit,parse_qs,urljoin,quote
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import URLError,HTTPError
from receipts import parse,layout_text,key_hash,norm,money,TextHTML
from household import uid,text,cents,dt,find

HOSTS={'nfceh.sefaz.ce.gov.br','nfce.sefaz.ce.gov.br','cfe.sefaz.ce.gov.br'}
_LOCK=threading.Lock()

def fiscal_url(raw):
    if not isinstance(raw,str) or len(raw)>4096 or re.search(r'[\x00-\x20\x7f]',raw):raise ValueError('Endereço fiscal inválido')
    u=urlsplit(raw.strip())
    if u.scheme not in ('http','https') or u.hostname not in HOSTS or u.username or u.password or u.port not in (None,80 if u.scheme=='http' else 443):raise ValueError('A consulta automática aceita somente portais oficiais do Ceará, sem porta alternativa.')
    return urlunsplit((u.scheme,u.netloc,u.path or '/',quote(u.query,safe='=&%+'),''))

def access_key(value):
    # Whitespace inside the printed key is accepted only after its explicit label.
    direct=re.search(r'(?<!\d)(\d{44})(?!\d)',str(value))
    if direct:return direct[1]
    m=re.search(r'CHAVE\s+(?:DE\s+)?ACESSO\s*:?\s*((?:\d[ \t\r\n]*){44})(?!\d)',norm(value))
    return re.sub(r'\D','',m[1]) if m else ''

def fingerprint(value):
    key=access_key(value)
    return hashlib.sha256(key.encode()).hexdigest() if key else ''

def qr_metadata(raw):
    url=fiscal_url(raw);u=urlsplit(url);params=parse_qs(u.query)
    value=params.get('p',[''])[0];parts=value.split('|');key=parts[0] if parts and re.fullmatch(r'\d{44}',parts[0]) else access_key(raw)
    out=dict(items=[],total=None,date='',store='',fingerprint=fingerprint(key),source='QR fiscal · dados locais',sourceKind='qr',online=False,warnings=[],url=url)
    # Version 2 offline layout: key | version | environment | day | total | digest | idCSC | hash.
    if len(parts)==8 and parts[1]=='2' and parts[2] in ('1','2') and key and key[20:22]=='65' and key[34]=='9':
        if re.fullmatch(r'\d{1,2}',parts[3]) and re.fullmatch(r'\d{1,12}\.\d{2}',parts[4]):
            try:out['date']=date(2000+int(key[2:4]),int(key[4:6]),int(parts[3])).isoformat();out['total']=money(parts[4])
            except ValueError:pass
    if len(parts)>2 and parts[2]=='2':out['warnings'].append('QR de ambiente de testes / homologação. Não representa uma despesa real por si só.')
    out['warnings'].append('Dados lidos do QR, sem validação da autorização fiscal. Confira o documento antes de salvar.')
    return out

def document(text_,kind='text',blocks=None):
    if blocks is not None:text_=layout_text(blocks)
    if not isinstance(text_,str) or not text_.strip() or len(text_)>2_000_000:raise ValueError('Informe o texto/XML/HTML da nota (até 2 MB).')
    if kind not in ('text','html','xml'):raise ValueError('Formato da nota inválido')
    out=parse(text_,kind)
    if kind=='html':
        p=TextHTML();p.feed(text_);plain=''.join(p.parts)
    else:plain=text_
    out['fingerprint']=out.get('fingerprint') or fingerprint(text_ if kind=='xml' else plain)
    # Prioritize emission rather than authorization dates when both are present.
    m=re.search(r'(?:EMISS[AÃ]O|EMITIDA\s+EM)\s*:?\s*(\d{2})/(\d{2})/(20\d{2})',norm(plain))
    if m:
        try:out['date']=date(int(m[3]),int(m[2]),int(m[1])).isoformat()
        except ValueError:pass
    if not out.get('store'):
        # NFC-e public layouts commonly identify the merchant with txtTopo.
        m=re.search(r'<[^>]+class=[\'\"][^\'\"]*\btxtTopo\b[^\'\"]*[\'\"][^>]*>(.*?)</[^>]+>',text_,re.I|re.S) if kind=='html' else None
        if m:
            p=TextHTML();p.feed(m[1]);out['store']=re.sub(r'\s+',' ',''.join(p.parts)).strip()[:160]
        else:
            lines=[x.strip() for x in plain.splitlines() if x.strip()]
            for i,line in enumerate(lines):
                if re.search(r'\bCNPJ\b',norm(line)) and i>0:
                    candidate=lines[i-1]
                    if not re.search(r'FISCAL|CONSUMIDOR|DANFE|AUTORIZ|CONSULT|GOVERNO',norm(candidate)):out['store']=candidate[:160]
                    break
    if re.search(r'\b(?:CANCELADA|CANCELADO|SEM VALOR FISCAL|AMBIENTE DE HOMOLOGACAO)\b',norm(plain)):
        out.setdefault('warnings',[]).append('O documento menciona cancelamento, homologação ou ausência de valor fiscal. Confira a situação antes de registrar qualquer despesa.')
    # Product-row warnings are irrelevant to a single total expense.
    out['warnings']=[w for w in out.get('warnings',[]) if any(k in w for k in ('Total da nota não','Chave fiscal não','Data não','O documento menciona'))]
    if out['total'] is not None and out['total']<=0:out['total']=None
    out.update(sourceKind='photo' if blocks is not None else kind,online=False)
    return out

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def fetch_public(url):
    """Only the exact CE government allowlist; default certificate validation stays enabled."""
    original=fiscal_url(url);candidate=original
    # Never infer unrelated endpoints or a production/homologation hostname.
    if urlsplit(original).scheme=='http':candidate='https:'+original.split(':',1)[1]
    choices=[candidate]+([original] if candidate!=original else [])
    last='Consulta indisponível'
    if not _LOCK.acquire(False):raise ValueError('Já existe uma consulta fiscal em andamento.')
    try:
        for choice in choices:
            current=choice
            try:
                for _ in range(4):
                    current=fiscal_url(current);u=urlsplit(current)
                    if u.scheme=='http' and urlsplit(original).scheme!='http':raise ValueError('Redirecionamento para HTTP não aceito.')
                    addresses=socket.getaddrinfo(u.hostname,u.port or (443 if u.scheme=='https' else 80),type=socket.SOCK_STREAM)
                    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise ValueError('O portal não resolveu para um endereço público.')
                    try:
                        with build_opener(NoRedirect()).open(Request(current,headers={'User-Agent':'HorizonteFinanceiro/3.10 (consulta solicitada pelo consumidor)','Accept':'text/html,application/xml,text/xml'}),timeout=8) as response:
                            body=response.read(2_000_001)
                            if len(body)>2_000_000:raise ValueError('Documento fiscal maior que 2 MB.')
                            charset=response.headers.get_content_charset() or 'utf-8'
                            try:content=body.decode(charset,'replace')
                            except LookupError:content=body.decode('utf-8','replace')
                            return content,current
                    except HTTPError as e:
                        if e.code in (301,302,303,307,308) and e.headers.get('Location'):
                            current=urljoin(current,e.headers['Location']);e.close();continue
                        raise
                last='O portal redirecionou muitas vezes.'
            except (URLError,TimeoutError,OSError,ValueError):last='Não foi possível consultar o portal com uma conexão válida. Use os dados do QR, foto ou XML.'
        raise ValueError(last)
    finally:_LOCK.release()

def resolve(raw):
    local=qr_metadata(raw)
    try:
        content,url=fetch_public(local['url'])
        kind='xml' if re.search(r'<(?:\w+:)?(?:nfeProc|NFe|CFe)\b',content) else 'html'
        remote=document(content,kind)
        if remote.get('fingerprint') and local['fingerprint'] and remote['fingerprint']!=local['fingerprint']:raise ValueError('O portal retornou uma chave diferente da nota lida.')
        if remote['total'] is None:raise ValueError('O portal não retornou um total legível. Pode exigir carregamento ou captcha; nada foi contornado.')
        if local['total'] is not None and remote['total']!=local['total']:raise ValueError('O total da página difere do QR. Confira o documento antes de registrar.')
        remote['fingerprint']=remote['fingerprint'] or local['fingerprint'];remote['online']=True;remote['sourceKind']='qr-online';remote['source']='Consulta pública da SEFAZ-CE';remote['url']=local['url']
        remote['date']=remote['date'] or local['date']
        if urlsplit(url).scheme=='http':remote['warnings'].append('Página pública acessada em HTTP, conforme o endereço original do QR. Confira o documento; não houve conexão criptografada.')
        return remote
    except ValueError as e:
        local['warnings'].insert(0,str(e));return local

def similar(state,total,when):
    return [dict(id=t['id'],name=t['name'],date=t.get('receiptDate') or t['date'],amount=t['amount']) for t in state['transactions'] if t['type']=='expense' and t['amount']==total and (t.get('receiptDate') or t['paidDate'] or t['date'])==when][:10]

def duplicate(state,fp):
    if not fp:return ''
    if any(t.get('receiptFingerprint')==fp for t in state['transactions']):return 'Esta nota já está no extrato. Edite ou exclua o lançamento existente para corrigir.'
    if any(p.get('fingerprint')==fp and p['payment']!='existing' for p in state.get('shopping',{}).get('purchases',[])):return 'Esta nota já gerou despesa em Comprar. Não registre novamente no extrato.'
    return ''

def import_expense(state,p):
    s=copy.deepcopy(state)
    if p.get('checked') is not True:raise ValueError('Confira o total, data e pagamento antes de salvar.')
    ident=text(p.get('importId'),100)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',ident):raise ValueError('Identificação do rascunho inválida')
    if any(t.get('receiptImportId')==ident for t in s['transactions']):raise ValueError('Este rascunho já foi registrado.')
    fp=p.get('fingerprint','')
    if not isinstance(fp,str) or (fp and not re.fullmatch('[a-f0-9]{64}',fp)):raise ValueError('Identificação fiscal inválida')
    error=duplicate(s,fp)
    if error:raise ValueError(error)
    total=cents(p.get('total'));when=dt(p.get('date'))
    if total<=0:raise ValueError('Informe o total final pago na nota.')
    if when>date.today().isoformat():raise ValueError('A emissão da nota não pode ser futura.')
    if similar(s,total,when) and not p.get('confirmSimilar'):raise ValueError('Já existe despesa com o mesmo valor e data. Confira o extrato e marque a confirmação de lançamento distinto.')
    source=p.get('source','text')
    if source not in ('text','html','xml','photo','qr','qr-online'):raise ValueError('Origem da leitura inválida')
    payment=p.get('payment');card=find(s['cards'],p.get('cardId')) if payment=='card' else None
    if payment not in ('cash','card','planned'):raise ValueError('Escolha a forma de pagamento.')
    due=dt(p.get('due')) if card else when
    if card and due<when:raise ValueError('O vencimento da fatura deve ser igual ou posterior à compra.')
    name=text(p.get('name'),160);category=text(p.get('category'),160)
    if not name or not category:raise ValueError('Informe descrição e categoria.')
    s['transactions'].append(dict(id=uid(),name=name,amount=total,date=due,paidDate=when if payment=='cash' else '',status='paid' if payment=='cash' else 'planned',type='expense',category=category,cardId=card['id'] if card else '',notes=text(p.get('notes',''),10000),receiptImportId=ident,receiptFingerprint=fp,receiptDate=when,receiptSource=source))
    return s
