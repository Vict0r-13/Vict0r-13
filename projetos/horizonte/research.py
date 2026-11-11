"""MIT. Small opt-in public-catalog search, JSON-LD extraction and nearby OSM shops.
No LLM, login, CAPTCHA bypass, private checkout APIs or unverified stock claims.
"""
import concurrent.futures,hashlib,ipaddress,json,math,re,socket,threading,time,unicodedata
from datetime import datetime,timezone,date,timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.parse import urlencode,urlsplit,urlunsplit,urljoin
from urllib.error import HTTPError,URLError
from household import shopping

UA='HorizonteFinanceiro/3.6 (personal shopping research)'
PROVIDERS=[dict(id='atacadao',name='Atacadão',host='www.atacadao.com.br'),dict(id='prezunic',name='Prezunic',host='www.prezunic.com.br')]
_ROBOTS={};_HOST_LOCKS={};_GUARD=threading.Lock()
def stamp():return datetime.now(timezone.utc).isoformat()
def safe_url(url):
    u=urlsplit(str(url))
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443) or len(url)>2000:raise ValueError('Use um endereço público HTTPS, sem credenciais ou porta alternativa')
    # Fixed public providers are explicitly allowlisted; arbitrary URLs additionally require public DNS addresses.
    if u.hostname in {'www.atacadao.com.br','www.prezunic.com.br','overpass-api.de'}:
        return urlunsplit((u.scheme,u.netloc,u.path or '/',u.query,''))
    try:
        addresses=socket.getaddrinfo(u.hostname,443,type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):raise ValueError('Endereços locais ou privados não são aceitos')
    except socket.gaierror:raise ValueError('Site não encontrado') from None
    return urlunsplit((u.scheme,u.netloc,u.path or '/',u.query,''))
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def raw_get(url,limit=2_000_000,respect_robots=False):
    for _ in range(5):
        url=safe_url(url)
        if respect_robots and not robots_allowed(url):raise ValueError('A fonte restringe esta consulta automática')
        try:
            with build_opener(NoRedirect()).open(Request(url,headers={'User-Agent':UA,'Accept':'application/json,text/html,text/plain'}),timeout=14) as r:
                b=r.read(limit+1)
                if len(b)>limit:raise ValueError('Resposta maior que o limite local')
                return b,r.headers.get_content_charset() or 'utf-8'
        except HTTPError as e:
            if e.code in (301,302,303,307,308) and e.headers.get('Location'):
                url=urljoin(url,e.headers['Location']);e.close();continue
            raise
    raise ValueError('A fonte redirecionou muitas vezes')

def robot_rules(text,path):
    # Supports wildcard paths and Allow precedence. Our app identifies itself, never masquerades as another crawler.
    groups=[];agents=[];rules=[]
    for line in text.splitlines():
        line=line.split('#',1)[0].strip()
        if ':' not in line:continue
        k,v=[x.strip() for x in line.split(':',1)];k=k.lower()
        if k=='user-agent':
            if rules:groups.append((agents,rules));agents=[];rules=[]
            agents.append(v.lower())
        elif k in ('allow','disallow') and agents and v:rules.append((k,v))
    groups.append((agents,rules))
    specific=[r for a,r in groups if any(x!='*' and x in UA.lower() for x in a)]
    chosen=specific or [r for a,r in groups if '*' in a]
    matches=[]
    for group in chosen:
        for k,p in group:
            pattern='^'+re.escape(p).replace(r'\*','.*')
            if p.endswith('$'):pattern=pattern[:-2]+'$'
            if re.search(pattern,path):matches.append((len(p.replace('*','')),k=='allow'))
    return max(matches,default=(0,True))[1]

def robots_allowed(url):
    u=urlsplit(url);host=u.hostname;now=time.time();saved=_ROBOTS.get(host)
    if not saved or now-saved[0]>86400:
        try:body,_=raw_get('https://'+host+'/robots.txt',200000);text=body.decode('utf-8','replace')
        except HTTPError as e:
            if e.code in (404,410):text=''
            else:raise ValueError('Não foi possível verificar as regras de acesso do site') from None
        except Exception:raise ValueError('Não foi possível verificar as regras de acesso do site') from None
        _ROBOTS[host]=(now,text)
    return robot_rules(_ROBOTS[host][1],u.path+('?' +u.query if u.query else ''))

def fetch(url,check_robots=True,limit=2_000_000):
    url=safe_url(url);host=urlsplit(url).hostname
    if check_robots and not robots_allowed(url):raise ValueError('A fonte restringe esta consulta automática; abra o site para pesquisar')
    with _GUARD:lock=_HOST_LOCKS.setdefault(host,threading.Lock())
    if not lock.acquire(blocking=False):raise ValueError('Consulta a esta fonte em andamento; aguarde')
    try:
        # One request at a time per host; result caching prevents repeated scans.
        return raw_get(url,limit,respect_robots=check_robots)
    except HTTPError as e:raise ValueError('A fonte recusou ou limitou o acesso ('+str(e.code)+'). Nenhum bloqueio foi contornado.') from None
    except (URLError,TimeoutError,OSError):raise ValueError('Fonte sem resposta. Tente mais tarde.') from None
    finally:lock.release()

def tokens(text):return re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',text.lower()).encode('ascii','ignore').decode())
def package_size(name):
    text=name.lower()
    if re.search(r'\b(kit|pack|fardo|leve)\b|\b\d+\s*x\s*\d|\bcom\s+\d+\s*(un|pac|fras)',text):return None,None
    matches=re.findall(r'(?<![\d.])(\d+(?:[.,]\d+)?)\s*(kg|mg|g|ml|litros?|l)\b',text)
    if len(matches)!=1:return None,None
    number,unit=matches[0];q=float(number.replace(',','.'))
    if q<=0:return None,None
    if unit in ('kg','g','mg'):return q*{'kg':1,'g':.001,'mg':.000001}[unit],'kg'
    return q*(.001 if unit=='ml' else 1),'L'

def catalog_rows(payload,provider,query):
    if not isinstance(payload,list):raise ValueError('Catálogo retornou um formato inesperado')
    result=[];words=set(tokens(query));fetched=stamp()
    for p in payload[:12]:
        if not isinstance(p,dict):continue
        for item in p.get('items',[])[:3]:
            for seller in item.get('sellers',[])[:2]:
                o=seller.get('commertialOffer',{});price=o.get('Price')
                if type(price) not in (int,float) or not math.isfinite(price) or price<=0:continue
                name=str(item.get('name') or p.get('productName',''))[:300]
                if not words.intersection(tokens(name)):continue
                q,unit=package_size(name);link=str(p.get('link',''))
                if urlsplit(link).scheme!='https':link='https://'+provider['host']
                result.append(dict(name=name,ean=str(item.get('ean','')),price=round(price*100),store=provider['name'],seller=str(seller.get('sellerName') or provider['name'])[:200],url=link,source=provider['host'],checkedAt=fetched,availability='Informada no catálogo online' if o.get('IsAvailable') is True else 'Indisponível no catálogo' if o.get('IsAvailable') is False else 'Disponibilidade não confirmada',localStockConfirmed=False,packageQuantity=q,unit=unit,unitPrice=round(price/q*100) if q else None,location=None,match='Confira marca, variedade e embalagem',score=len(words.intersection(tokens(name)))/max(1,len(words))))
    return sorted(result,key=lambda r:(-r['score'],r['price']))[:12]

class JsonLd(HTMLParser):
    def __init__(self):super().__init__();self.active=False;self.text='';self.data=[]
    def handle_starttag(self,t,a):
        if t=='script' and dict(a).get('type','').lower()=='application/ld+json':self.active=True;self.text=''
    def handle_data(self,d):
        if self.active:self.text+=d
    def handle_endtag(self,t):
        if t=='script' and self.active:
            self.active=False
            try:self.data.append(json.loads(self.text))
            except (ValueError,TypeError):pass

def structured_offers(html,url):
    parser=JsonLd();parser.feed(html);rows=[]
    def walk(node):
        if isinstance(node,list):
            for x in node:walk(x)
        elif isinstance(node,dict):
            typ=node.get('@type');types=typ if isinstance(typ,list) else [typ]
            if 'Product' in types:
                offers=node.get('offers',[]);offers=offers if isinstance(offers,list) else [offers]
                for o in offers:
                    if not isinstance(o,dict):continue
                    raw=o.get('price');currency=o.get('priceCurrency')
                    try:price=float(raw)
                    except (ValueError,TypeError):continue
                    if currency!='BRL' or not math.isfinite(price) or price<=0:continue
                    name=str(node.get('name','Produto'))[:300];q,unit=package_size(name);seller=o.get('seller',{});seller=seller if isinstance(seller,dict) else {};geo=seller.get('geo',{})
                    location=None
                    try:
                        lat,lon=float(geo['latitude']),float(geo['longitude'])
                        if -90<=lat<=90 and -180<=lon<=180:location=dict(lat=lat,lon=lon)
                    except (TypeError,KeyError,ValueError):pass
                    rows.append(dict(name=name,ean=str(node.get('gtin13') or node.get('gtin') or ''),price=round(price*100),store=str(seller.get('name') or urlsplit(url).hostname)[:200],seller=str(seller.get('name',''))[:200],url=url,source=urlsplit(url).hostname,checkedAt=stamp(),availability='Conferir na página: '+str(o.get('availability','não informada')).split('/')[-1],localStockConfirmed=False,packageQuantity=q,unit=unit,unitPrice=round(price/q*100) if q else None,location=location,match='Preço extraído de dados estruturados da página',score=1))
            if '@graph' in node:walk(node['@graph'])
    for x in parser.data:walk(x)
    if not rows:raise ValueError('A página não publicou uma oferta estruturada em reais. Preço não foi estimado nem inventado.')
    return rows[:20]

def distance(lat,lon,lat2,lon2):
    a,b,c,d=map(math.radians,(lat,lon,lat2,lon2));h=math.sin((c-a)/2)**2+math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
    return 6371*2*math.asin(min(1,math.sqrt(h)))

def coordinates(p):
    try:lat=float(p['lat']);lon=float(p['lon'])
    except (ValueError,TypeError,KeyError):raise ValueError('Informe uma localização válida') from None
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError('Coordenadas inválidas')
    return round(lat,3),round(lon,3) # Approximate position only, not exact home address.

class Research:
    def __init__(self,root):
        self.root=Path(root);self.cache_path=self.root/'research-cache.json';self.lock=threading.Lock()
        try:self.cache=json.loads(self.cache_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):self.cache={}
    def cached(self,key,maxage):
        row=self.cache.get(key)
        return row['result'] if row and time.time()-row['at']<maxage else None
    def save(self,key,result):
        with self.lock:
            self.cache[key]={'at':time.time(),'result':result};self.cache=dict(sorted(self.cache.items(),key=lambda kv:kv[1]['at'])[-100:]);temp=self.cache_path.with_suffix('.tmp');temp.write_text(json.dumps(self.cache,ensure_ascii=False,allow_nan=False),encoding='utf-8');temp.replace(self.cache_path)
        return result
    def prices(self,p):
        query=str(p.get('query','')).strip()
        if not 2<=len(query)<=120:raise ValueError('Informe um produto entre 2 e 120 caracteres')
        key='prices:'+query.lower()
        selected=p.get('providers',['atacadao','prezunic'])
        if not isinstance(selected,list) or not selected or any(x not in ('atacadao','prezunic') for x in selected):raise ValueError('Selecione fontes suportadas')
        key+=':'+','.join(sorted(selected));saved=self.cached(key,3600)
        if saved:return {**saved,'cached':True}
        def run(provider):
            try:
                url='https://'+provider['host']+'/api/catalog_system/pub/products/search/?'+urlencode(dict(ft=query,_from=0,_to=5))
                b,_=fetch(url);rows=catalog_rows(json.loads(b),provider,query)
                return dict(provider=provider['name'],status='ok',count=len(rows),rows=rows)
            except Exception as e:return dict(provider=provider['name'],status='unavailable',message=str(e)[:250],rows=[])
        with concurrent.futures.ThreadPoolExecutor(2) as ex:out=list(ex.map(run,[x for x in PROVIDERS if x['id'] in selected]))
        rows=[x for source in out for x in source.pop('rows')]
        result=dict(query=query,checkedAt=stamp(),cached=False,offers=sorted(rows,key=lambda r:(-r['score'],r['price'])),sources=out,notice='Preços online consultados sem CEP de entrega; podem variar por região, clube e frete. Não confirmam preço ou estoque da loja física. Compare apenas embalagens equivalentes.')
        return result if out and all(x['status']=='unavailable' for x in out) else self.save(key,result)
    def page(self,p):
        url=safe_url(p.get('url',''));key='page:'+url;saved=self.cached(key,3600)
        if saved:return {**saved,'cached':True}
        b,encoding=fetch(url);rows=structured_offers(b.decode(encoding,'replace'),url)
        return self.save(key,dict(query=url,checkedAt=stamp(),cached=False,offers=rows,sources=[dict(provider=urlsplit(url).hostname,status='ok',count=len(rows))],notice='Oferta extraída da página pública; condições e disponibilidade devem ser conferidas no site.'))
    def nearby(self,p):
        lat,lon=coordinates(p);radius=p.get('radius',3)
        if type(radius) not in (float,int) or not 1<=radius<=10:raise ValueError('Raio permitido: 1 a 10 km')
        key=f'nearby:{lat}:{lon}:{radius}';saved=self.cached(key,86400)
        if saved:return {**saved,'cached':True}
        query=f'[out:json][timeout:18];nwr[shop~"^(supermarket|convenience|greengrocer|chemist|department_store)$"](around:{round(radius*1000)},{lat},{lon});out center tags 50;'
        url='https://overpass-api.de/api/interpreter?'+urlencode({'data':query})
        b,_=fetch(url,check_robots=False);data=json.loads(b);shops=[]
        for x in data.get('elements',[])[:50]:
            tags=x.get('tags',{});center=x.get('center',x)
            if 'lat' not in center or 'lon' not in center or not tags.get('name'):continue
            slat,slon=center['lat'],center['lon'];address=' '.join(str(tags.get(k,'')) for k in ['addr:street','addr:housenumber','addr:suburb','addr:city']).strip()
            shops.append(dict(id=str(x.get('id')),name=tags['name'],address=address or 'Endereço não cadastrado na base',lat=slat,lon=slon,distanceKm=round(distance(lat,lon,slat,slon),2),url='https://www.openstreetmap.org/'+x['type']+'/'+str(x['id']),directions='https://www.google.com/maps/dir/?api=1&destination='+str(slat)+','+str(slon),source='OpenStreetMap contributors',stockConfirmed=False))
        result=dict(shops=sorted(shops,key=lambda x:x['distanceKm']),checkedAt=stamp(),cached=False,notice='Locais cadastrados no OpenStreetMap, sem confirmação de estoque ou preço. Distância em linha reta a partir de localização aproximada, não percurso. Base pode estar incompleta.',attribution='© OpenStreetMap contributors · ODbL')
        return self.save(key,result)
    def needs(self,s):
        h=s['household'];on=date.today().isoformat();rows={r['productId']:{**r,'reason':'Refeições planejadas'} for r in shopping(h,on,(date.today()+timedelta(days=6)).isoformat())}
        for p in h['products']:
            current=sum(l['remaining'] for l in h['lots'] if l['productId']==p['id'] and (not l['expiry'] or l['expiry']>=on))
            missing=max(0,p['minimum']-current)
            if missing:
                if p['id'] in rows:rows[p['id']]['reason']+=' e estoque mínimo';rows[p['id']]['quantity']=max(rows[p['id']]['quantity'],missing)
                else:rows[p['id']]=dict(productId=p['id'],name=p['name'],quantity=missing,unit=p['unit'],estimatedCost=None,reason='Estoque abaixo do mínimo')
        return list(rows.values())
