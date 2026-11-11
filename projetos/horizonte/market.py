"""Opt-in market requests. No personal finance data is sent to the provider."""
import json
import math
import os
import re
import threading
from datetime import datetime,timezone
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.parse import urlsplit
from urllib.error import HTTPError,URLError
from fundamentals import fetch_fundamentus

BASE='https://brapi.dev/api/v2/stocks/'

class ProviderRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        dest=urlsplit(newurl)
        if dest.scheme!='https' or dest.hostname!='brapi.dev' or dest.port not in (None,443):
            raise ValueError('Destino de dados não autorizado')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

urlopen=build_opener(ProviderRedirect()).open

def finite(v):
    return float(v) if type(v) in (int,float) and math.isfinite(v) else None


def unwrap(payload,ticker):
    rows=payload.get('results',[])
    for row in rows:
        if row.get('requestedSymbol',row.get('symbol'))==ticker or row.get('symbol')==ticker:
            d=row.get('data',row)
            if not isinstance(d,dict):raise ValueError('Formato de dados não reconhecido')
            return d,row.get('symbol',ticker)
    raise ValueError('Ticker sem dados disponíveis')


class Market:
    def __init__(self,root):
        self.root=root;self.key=os.environ.get('BRAPI_API_KEY','');self.lock=threading.Lock()
        self.path=root/'market_cache.json'
        try:self.cache=json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError,ValueError):self.cache={}
    def status(self):return {'configured':bool(self.key),'provider':'Fundamentus público + brapi opcional','storage':'Chave mantida somente nesta sessão (ou variável BRAPI_API_KEY)'}
    def set_key(self,key):
        if not isinstance(key,str) or len(key)>512 or any(c in key for c in '\r\n'):raise ValueError('Chave inválida')
        self.key=key.strip();return self.status()
    def request(self,endpoint,ticker):
        headers={'Accept':'application/json','User-Agent':'HorizonteFinanceiro/2.0'}
        if self.key:headers['Authorization']='Bearer '+self.key
        req=Request(BASE+endpoint+'?symbols='+ticker,headers=headers)
        try:
            with urlopen(req,timeout=12) as r:
                if r.geturl().split('/')[2]!='brapi.dev':raise ValueError('Destino de dados não autorizado')
                data=r.read(2_000_001)
                if len(data)>2_000_000:raise ValueError('Resposta de mercado excedeu o limite')
                return unwrap(json.loads(data),ticker)
        except HTTPError as e:
            msg={401:'Informe uma chave válida da brapi.',403:'Dados indisponíveis no seu plano da brapi.',404:'Ticker não encontrado.',429:'Limite do provedor atingido. Aguarde e tente novamente.'}.get(e.code,'Provedor indisponível. Tente mais tarde.')
            raise ValueError(msg) from None
        except (URLError,TimeoutError,OSError):raise ValueError('Sem conexão com o provedor. Confira a internet.') from None
    def quote(self,ticker):
        ticker=str(ticker).strip().upper().removesuffix('.SA')
        if not re.fullmatch(r'[A-Z0-9^]{2,16}',ticker):raise ValueError('Ticker inválido')
        if not self.lock.acquire(blocking=False):raise ValueError('Consulta em andamento. Aguarde.')
        try:
            # Anonymous brapi requests are restricted to four demo tickers; use a public factual source for the general case.
            if not self.key:
                try:
                    result=fetch_fundamentus(ticker);self.cache[ticker]=result;self.persist();return result
                except ValueError as e:
                    if ticker in self.cache:return {**self.cache[ticker],'cached':True,'warning':str(e)+' Última consulta salva, sem atualização.'}
                    if ticker not in ('PETR4','VALE3','MGLU3','ITUB4'):raise
            try:q,symbol=self.request('quote',ticker)
            except ValueError as e:
                if ticker in self.cache:return {**self.cache[ticker],'cached':True,'warning':str(e)+' Exibindo a última consulta salva; não é cotação atual.'}
                try:
                    result=fetch_fundamentus(ticker);result['warning']='A fonte brapi não respondeu. '+result['warning'];self.cache[ticker]=result;self.persist();return result
                except ValueError:raise e
            st={};warning=''
            try:st,_=self.request('statistics',ticker)
            except ValueError as e:warning='Cotação recebida; fundamentos não disponíveis: '+str(e)
            try:
                financial,_=self.request('financial-data',ticker);st={**st,**financial}
            except ValueError:pass
            price=finite(q.get('regularMarketPrice'))
            if price is None or price<=0:raise ValueError('O provedor não retornou preço válido')
            currency=q.get('currency')
            if currency!='BRL':raise ValueError('Esta versão aceita cotações em BRL. Converta outros ativos manualmente.')
            result={'symbol':symbol,'requestedSymbol':ticker,'name':str(q.get('longName') or q.get('shortName') or symbol),
                    'price':price,'currency':currency,'change':finite(q.get('regularMarketChangePercent')),
                    'eps':finite(st.get('trailingEps',st.get('earningsPerShare'))),'book':finite(st.get('bookValue')),
                    'peProvider':finite(st.get('trailingPE')),'pbProvider':finite(st.get('priceToBook')),
                    'sourceTime':q.get('regularMarketTime'),'fundamentalPeriod':st.get('mostRecentQuarter'),
                    'fetchedAt':datetime.now(timezone.utc).isoformat(),'provider':'brapi.dev','cached':False,'warning':warning,'sourceUrl':'https://brapi.dev','metrics':self.brapi_metrics(q,st)}
            self.cache[ticker]=result
            self.persist()
            return result
        finally:self.lock.release()

    def persist(self):
        temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(self.cache,allow_nan=False),encoding='utf-8');temp.replace(self.path)
    def brapi_metrics(self,q,st):
        specs=[('marketCap','Valor de mercado','BRL','company'),('regularMarketVolume','Volume negociado','number','company'),('fiftyTwoWeekLow','Mínima · 52 semanas','BRL','company'),('fiftyTwoWeekHigh','Máxima · 52 semanas','BRL','company'),('trailingPE','Preço / lucro','ratio','valuation'),('priceToBook','Preço / patrimônio','ratio','valuation'),('trailingEps','Lucro por ação','BRL','valuation'),('bookValue','Patrimônio por ação','BRL','valuation'),('enterpriseToEbitda','Valor da firma / EBITDA','ratio','valuation'),('returnOnEquity','Retorno sobre patrimônio','fraction','profit'),('returnOnAssets','Retorno sobre ativos','fraction','profit'),('profitMargins','Margem líquida','fraction','profit'),('grossMargins','Margem bruta','fraction','profit'),('currentRatio','Liquidez corrente','ratio','health'),('totalDebt','Dívida total','BRL','health'),('totalCash','Caixa total','BRL','health'),('totalRevenue','Receita · 12 meses','BRL','results'),('ebitda','EBITDA · 12 meses','BRL','results')]
        values={**q,**st}
        return [dict(key=k,label=l,value=finite(values.get(k)),unit=u,group=g,description='Dado informado pela brapi; confira o período e a definição na fonte.',source='brapi.dev',period=st.get('mostRecentQuarter')) for k,l,u,g in specs]
