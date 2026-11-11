"""Public factual fundamentals parser; standard library, no login or bypass."""
import math,re
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.parse import urlsplit
from urllib.error import HTTPError,URLError

class Cells(HTMLParser):
    def __init__(self):super().__init__();self.active=False;self.cell='';self.cells=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('td','th'):self.active=True;self.cell=''
    def handle_data(self,data):
        if self.active:self.cell+=data
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.active:self.cells.append(re.sub(r'\s+',' ',self.cell).strip().lstrip('?').strip());self.active=False

def decimal_br(value):
    s=str(value).strip().replace('\xa0','').replace('%','').replace('R$','').strip()
    if s in ('','-','--','N/A','n/a'):return None
    try:
        n=float(s.replace('.','').replace(',','.'))
        return n if math.isfinite(n) else None
    except ValueError:return None

# Numeric values retain the unit reported by the source. Percentages are percentage points.
FIELDS=[
 ('P/L','pe','Preço / lucro','valuation','ratio','Anos de lucro por ação equivalentes ao preço, usando os dados da fonte.'),
 ('P/VP','pb','Preço / valor patrimonial','valuation','ratio','Preço em relação ao patrimônio por ação.'),
 ('P/Cap. Giro','pWorkingCapital','Preço / capital de giro','valuation','ratio','Valor de mercado em relação ao capital de giro, conforme a fonte.'),
 ('P/Ativ Circ Liq','pNetCurrentAssets','Preço / ativos circulantes líquidos','valuation','ratio','Múltiplo dos ativos circulantes líquidos conforme definição da fonte.'),
 ('Giro Ativos','assetTurnover','Giro dos ativos','profit','ratio','Receita em relação aos ativos.'),
 ('EBIT / Ativo','ebitAssets','Lucro operacional / ativos','profit','percent','Lucro operacional em relação aos ativos.'),
 ('Ativo','assets','Ativos totais','health','BRL','Total de ativos no balanço processado.'),
 ('P/EBIT','pEbit','Preço / lucro operacional','valuation','ratio','Preço em relação ao resultado antes de juros e impostos.'),
 ('PSR','psr','Preço / receita','valuation','ratio','Valor de mercado dividido pela receita.'),
 ('P/Ativos','pAssets','Preço / ativos','valuation','ratio','Valor de mercado em relação aos ativos.'),
 ('EV / EBITDA','evEbitda','Valor da firma / EBITDA','valuation','ratio','Valor da firma em relação ao resultado operacional antes de depreciação.'),
 ('EV / EBIT','evEbit','Valor da firma / EBIT','valuation','ratio','Valor da firma dividido pelo lucro operacional.'),
 ('Div. Yield','dy','Rendimento de dividendos','valuation','percent','Rendimento histórico informado pela fonte; não é rendimento garantido.'),
 ('LPA','eps','Lucro por ação','valuation','BRL','Lucro por ação dos últimos 12 meses, conforme a fonte. Não é a média trienal.'),
 ('VPA','book','Patrimônio por ação','valuation','BRL','Parcela do patrimônio contábil por ação.'),
 ('Marg. Bruta','grossMargin','Margem bruta','profit','percent','Lucro bruto em relação à receita.'),
 ('Marg. EBIT','ebitMargin','Margem operacional','profit','percent','Lucro operacional em relação à receita.'),
 ('Marg. Líquida','netMargin','Margem líquida','profit','percent','Lucro líquido em relação à receita.'),
 ('ROIC','roic','Retorno sobre capital investido','profit','percent','Retorno operacional sobre o capital investido, conforme metodologia da fonte.'),
 ('ROE','roe','Retorno sobre patrimônio','profit','percent','Lucro em relação ao patrimônio contábil.'),
 ('Cres. Rec (5a)','revenueGrowth5','Crescimento da receita · 5 anos','profit','percent','Taxa de crescimento histórico informada pela fonte.'),
 ('Liquidez Corr','currentRatio','Liquidez corrente','health','ratio','Ativos circulantes divididos por passivos circulantes.'),
 ('Dív Líq / Patrim','netDebtEquity','Dívida líquida / patrimônio','health','ratio','Dívida bruta menos disponibilidades, em relação ao patrimônio. Pode ser negativa.'),
 ('Dív. Bruta','grossDebt','Dívida bruta','health','BRL','Saldo de dívida bruta no balanço processado.'),
 ('Dív. Líquida','netDebt','Dívida líquida','health','BRL','Dívida bruta menos disponibilidades; valor negativo indica caixa líquido segundo esta definição.'),
 ('Disponibilidades','cash','Disponibilidades','health','BRL','Caixa e equivalentes informados pela fonte.'),
 ('Ativo Circulante','currentAssets','Ativo circulante','health','BRL','Ativos classificados no curto prazo.'),
 ('Patrim. Líq','equity','Patrimônio líquido','health','BRL','Patrimônio contábil total.'),
 ('Valor de mercado','marketCap','Valor de mercado','company','BRL','Preço multiplicado pelo número de ações considerado pela fonte.'),
 ('Valor da firma','enterpriseValue','Valor da firma','company','BRL','Valor empresarial conforme metodologia da fonte.'),
 ('Nro. Ações','shares','Número de ações','company','number','Número de ações informado pela fonte.'),
 ('Vol $ méd (2m)','volume2m','Volume financeiro médio · 2 meses','company','BRL','Média financeira diária informada pela fonte.'),
 ('Min 52 sem','low52','Mínima · 52 semanas','company','BRL','Menor cotação na janela histórica.'),
 ('Max 52 sem','high52','Máxima · 52 semanas','company','BRL','Maior cotação na janela histórica.'),
 ('Receita Líquida','revenue','Receita líquida · 12 meses','results','BRL','Receita acumulada em 12 meses conforme a tabela da fonte.'),
 ('EBIT','ebit','Lucro operacional · 12 meses','results','BRL','EBIT acumulado em 12 meses.'),
 ('Lucro Líquido','netIncome','Lucro líquido · 12 meses','results','BRL','Lucro acumulado em 12 meses.')]

def parse_fundamentus(html,ticker):
    p=Cells();p.feed(html);c=p.cells
    values={}
    for i,label in enumerate(c[:-1]):
        if label not in values:values[label]=c[i+1]
    if values.get('Papel','').upper()!=ticker:raise ValueError('A fonte pública não retornou este código. Confira se a ação está listada e coberta.')
    price=decimal_br(values.get('Cotação'))
    if price is None or price<=0:raise ValueError('Cotação indisponível para este ativo na fonte pública.')
    period=values.get('Últ balanço processado')
    metrics=[dict(key=k,label=label,value=decimal_br(values.get(raw)),unit=unit,group=group,description=desc,source='Fundamentus',period=period) for raw,k,label,group,unit,desc in FIELDS]
    by={x['key']:x['value'] for x in metrics}
    # Dividend yield is kept as a historical yield, never converted into a fabricated cash dividend.
    return dict(symbol=ticker,requestedSymbol=ticker,name=values.get('Empresa',ticker),price=price,currency='BRL',change=decimal_br(values.get('Dia')),eps=by.get('eps'),book=by.get('book'),peProvider=by.get('pe'),pbProvider=by.get('pb'),sourceTime=values.get('Data últ cot'),fundamentalPeriod=period,fetchedAt=datetime.now(timezone.utc).isoformat(),provider='Fundamentus',sourceUrl='https://www.fundamentus.com.br/detalhes.php?papel='+ticker,cached=False,warning='Cotação da data indicada, com possível atraso. Não há garantia de cobertura de todos os ativos ou de atualização em tempo real.',sector=values.get('Setor',''),subsector=values.get('Subsetor',''),metrics=metrics)

class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        u=urlsplit(newurl)
        if u.scheme!='https' or u.hostname not in ('www.fundamentus.com.br','fundamentus.com.br'):raise ValueError('Redirecionamento da fonte não autorizado')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch_fundamentus(ticker):
    if not re.fullmatch(r'[A-Z][A-Z0-9]{3}[0-9]{1,2}',ticker):raise ValueError('A fonte pública aceita códigos de ações e outros ativos brasileiros cobertos, como B3SA3 ou TAEE11.')
    url='https://www.fundamentus.com.br/detalhes.php?papel='+ticker
    try:
        with build_opener(SafeRedirect()).open(Request(url,headers={'User-Agent':'HorizonteFinanceiro/3.6 (personal finance app)','Accept':'text/html'}),timeout=12) as response:
            raw=response.read(1_000_001)
            if len(raw)>1_000_000:raise ValueError('Resposta da fonte excedeu o limite')
            html=raw.decode(response.headers.get_content_charset() or 'latin1',errors='replace')
            return parse_fundamentus(html,ticker)
    except HTTPError as e:raise ValueError('Fonte pública temporariamente indisponível ou acesso limitado ('+str(e.code)+').') from None
    except (URLError,TimeoutError,OSError):raise ValueError('Não foi possível conectar à fonte pública. Tente mais tarde.') from None
