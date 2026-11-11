"""Official monthly IPCA, resilient local cache and purchasing-power calculations.

No financial records are sent to providers. Historic comparisons use month-end
index ratios; future inflation is always an explicit scenario assumption.
"""
import copy
import gzip
import io
import json
import math
import re
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

IBGE_URL = 'https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/-480/variaveis/63%7C2266%7C2265?localidades=N1[all]'
BCB_URL = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/480?formato=json'
SOURCE_URL = 'https://sidra.ibge.gov.br/tabela/1737'
ALLOWED = {'servicodados.ibge.gov.br', 'api.bcb.gov.br'}
TTL = 6 * 3600
RETRY = 15 * 60
MAX_BYTES = 2_000_000


class OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        u = urlsplit(newurl)
        if u.scheme != 'https' or u.hostname not in ALLOWED or u.port not in (None, 443):
            raise ValueError('Redirecionamento fora da fonte oficial')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_json(url):
    req = Request(url, headers={'Accept': 'application/json', 'Accept-Encoding': 'identity', 'User-Agent': 'HorizonteFinanceiro/3.11'})
    with build_opener(OfficialRedirect()).open(req, timeout=12) as response:
        u = urlsplit(response.geturl())
        if u.scheme != 'https' or u.hostname not in ALLOWED:
            raise ValueError('Fonte não autorizada')
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Resposta excedeu o limite')
    if raw[:2] == b'\x1f\x8b':
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as zipped:
            raw = zipped.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Resposta descomprimida excedeu o limite')
    return json.loads(raw.decode('utf-8-sig'))


def month(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}', value):
        raise ValueError('Informe um mês válido')
    d = date.fromisoformat(value + '-01')
    if not 1994 <= d.year <= 2199:
        raise ValueError('Mês deve estar entre 1994 e 2199')
    return value


def shift(value, delta):
    y, m = map(int, value.split('-'))
    n = y * 12 + m - 1 + delta
    return f'{n // 12:04d}-{n % 12 + 1:02d}'


def number(v, label, lo=-1e12, hi=1e12):
    if type(v) not in (int, float) or not math.isfinite(v) or not lo <= v <= hi:
        raise ValueError(label + ' inválido')
    return float(v)


def parse_ibge(payload):
    if not isinstance(payload, list):
        raise ValueError('Formato IBGE inválido')
    maps = {}
    for row in payload:
        if row.get('id') not in ('63', '2266', '2265'):
            continue
        results = row.get('resultados', [])
        if len(results) != 1:
            raise ValueError('Recorte IBGE inválido')
        series = results[0].get('series', [])
        if len(series) != 1 or series[0].get('localidade', {}).get('id') != '1':
            raise ValueError('Esperada série nacional do IPCA')
        maps[row['id']] = series[0]['serie']
    if set(maps) != {'63', '2266', '2265'} or any(set(maps['63']) != set(maps[k]) for k in ('2266','2265')):
        raise ValueError('Séries oficiais incompletas')
    rows = []
    for key in sorted(maps['63']):
        if not re.fullmatch(r'\d{6}', key):
            raise ValueError('Competência inválida')
        period = key[:4] + '-' + key[4:]
        if period < '1994-01':
            continue
        rows.append({'month': period, 'monthly': float(maps['63'][key]), 'index': float(maps['2266'][key]), 'annual': float(maps['2265'][key])})
    return validate_rows(rows)


def parse_bcb(payload):
    if not isinstance(payload, list):
        raise ValueError('Formato SGS inválido')
    rows, index = [], 100.0
    ordered = sorted(payload, key=lambda r: datetime.strptime(r['data'], '%d/%m/%Y'))
    for row in ordered:
        d = datetime.strptime(row['data'], '%d/%m/%Y')
        period = d.strftime('%Y-%m')
        if period < '1994-01':
            continue
        rate = float(row['valor'])
        number(rate, 'Taxa mensal', -99, 100)
        index *= 1 + rate / 100
        rows.append({'month': period, 'monthly': rate, 'index': index})
    return validate_rows(rows)


def validate_rows(rows, now=None):
    today = (now or datetime.now(timezone.utc)).strftime('%Y-%m')
    if not isinstance(rows, list) or not 13 <= len(rows) <= 480:
        raise ValueError('Histórico insuficiente ou excessivo')
    prev = None
    for i, row in enumerate(rows):
        m = month(row['month'])
        if m >= today or (prev and m != shift(prev, 1)):
            raise ValueError('Histórico com lacuna, ordem incorreta ou mês ainda não encerrado')
        number(row['monthly'], 'Variação mensal', -99, 100)
        number(row['index'], 'Número-índice', 1e-12, 1e15)
        if 'annual' in row:
            number(row['annual'], 'Acumulado anual', -99, 1e15)
            if i >= 12 and abs((row['index'] / rows[i-12]['index'] - 1) * 100 - row['annual']) > .02:
                raise ValueError('Acumulado anual e número-índice não conferem')
        if prev:
            implied = (row['index'] / last_index - 1) * 100
            if abs(implied - row['monthly']) > .02:
                raise ValueError('Taxa e número-índice não conferem')
        prev, last_index = m, row['index']
    return rows


class Inflation:
    def __init__(self, root, fetcher=None):
        self.path = Path(root) / 'inflation_cache_v1.json'
        self.fetcher = fetcher or fetch_json
        self.lock = threading.RLock()
        self.running = False
        self.last_attempt = None
        self.error = ''
        self.data = None
        try:
            if self.path.stat().st_size > MAX_BYTES:
                raise ValueError('Cache excessivo')
            saved = json.loads(self.path.read_text(encoding='utf-8'))
            validate_rows(saved['rows'])
            if saved['provider'] not in ('IBGE / SIDRA', 'IBGE via Banco Central / SGS 433'):
                raise ValueError('Fonte inválida')
            datetime.fromisoformat(saved['checkedAt'])
            self.data = saved
        except (OSError, ValueError, KeyError, TypeError, OverflowError):
            self.error = 'Ainda não há uma consulta oficial salva. Conecte à internet para atualizar.'

    def _age(self, stamp):
        try:
            d = datetime.fromisoformat(stamp)
            if d.tzinfo is None:
                return float('inf')
            age = (datetime.now(timezone.utc) - d).total_seconds()
            return age if age >= 0 else float('inf')
        except (ValueError, TypeError):
            return float('inf')

    def refresh(self, force=False):
        with self.lock:
            if self.running:
                return False
            if force:
                if self._age(self.last_attempt) < 30:
                    return False
            elif self._age(self.last_attempt) < (RETRY if self.error else TTL):
                return False
            elif self.data and not self.error and self._age(self.data['checkedAt']) < TTL:
                return False
            self.running = True
            self.last_attempt = datetime.now(timezone.utc).isoformat()
        threading.Thread(target=self.update, daemon=True, name='horizonte-ipca').start()
        return True

    def update(self):
        errors = []
        try:
            result = None
            for provider, url, parser in [('IBGE / SIDRA', IBGE_URL, parse_ibge), ('IBGE via Banco Central / SGS 433', BCB_URL, parse_bcb)]:
                try:
                    rows = parser(self.fetcher(url))
                    with self.lock:
                        if self.data and rows[-1]['month'] < self.data['rows'][-1]['month']:
                            raise ValueError('Fonte retornou competência anterior à já salva')
                    candidate = {'provider': provider, 'rows': rows, 'checkedAt': datetime.now(timezone.utc).isoformat(), 'sourceUrl': SOURCE_URL,
                              'method': 'Número-índice publicado pelo IBGE' if provider == 'IBGE / SIDRA' else 'Índice calculado por composição das taxas mensais publicadas; pode diferir por arredondamento do acumulado oficial'}
                    temp = self.path.with_suffix('.tmp')
                    temp.write_text(json.dumps(candidate, ensure_ascii=False, allow_nan=False), encoding='utf-8')
                    temp.replace(self.path)
                    result = candidate
                    break
                except Exception:
                    errors.append(provider)
            with self.lock:
                if result is not None:
                    self.data, self.error = result, ''
                else:
                    self.error = 'Não foi possível atualizar nas fontes oficiais. ' + ('Exibindo a última consulta salva; atualização pendente.' if self.data else 'Nenhum índice foi estimado ou preenchido automaticamente.')
        finally:
            with self.lock:
                self.running = False

    def status(self, auto=False):
        if auto:
            self.refresh()
        with self.lock:
            r = {'updating': self.running, 'lastAttempt': self.last_attempt, 'warning': self.error, 'available': bool(self.data),
                 'checkedAt': None, 'provider': None, 'latestMonth': None, 'monthly': None, 'annual': None, 'rows': [], 'needsCheck': True, 'sourceUrl': SOURCE_URL}
            if self.data:
                r.update(copy.deepcopy(self.data))
                rows = r['rows']
                r.update(latestMonth=rows[-1]['month'], monthly=rows[-1]['monthly'], annual=rows[-1].get('annual',(rows[-1]['index'] / rows[-13]['index'] - 1) * 100), annualPublished='annual' in rows[-1],
                         needsCheck=self._age(r['checkedAt']) >= TTL)
                if rows[-1]['month'] < shift(date.today().strftime('%Y-%m'), -2):
                    r['warning'] = (r['warning'] + ' Histórico termina há mais de dois meses. Verifique a conexão e a divulgação oficial.').strip()
            return r


def inflation_factor(rows, start, end):
    start, end = month(start), month(end)
    if end < start:
        raise ValueError('O mês final deve ser igual ou posterior ao inicial')
    values = {r['month']: r['index'] for r in rows}
    if start not in values or end not in values:
        raise ValueError('O período escolhido ainda não tem IPCA disponível. Selecione meses divulgados.')
    return values[end] / values[start]


def validate_preferences(p):
    if not isinstance(p, dict) or len(p) > 20:
        raise ValueError('Parâmetros de poder de compra inválidos')
    allowed = {'start','end','initial','final','oldIncome','newIncome','netReturn','target','capital','monthly','years','annual','futureMode','futureInflation'}
    if set(p) - allowed:
        raise ValueError('Parâmetro de poder de compra desconhecido')
    for key in ('start', 'end'):
        if key in p:
            month(p[key])
    for key in ('initial','final','oldIncome','newIncome','target','capital','monthly'):
        if key in p:
            number(p[key], key, 0, 1e12)
    for key in ('netReturn', 'annual'):
        if key in p:
            number(p[key], key, -90, 100)
    if 'years' in p:
        number(p['years'], 'Prazo', 1, 70)
        if int(p['years']) != p['years']:
            raise ValueError('Prazo deve ser um número inteiro de anos')
    if 'futureMode' in p and p['futureMode'] not in ('observed', 'manual'):
        raise ValueError('Premissa de inflação inválida')
    if 'futureInflation' in p:
        number(p['futureInflation'], 'Inflação hipotética', -20, 50)
    return p


def analyze(data, p):
    validate_preferences(p)
    if not data.get('available'):
        raise ValueError('Aguarde a primeira consulta oficial. Sem índice confirmado não calculamos a inflação.')
    factor = inflation_factor(data['rows'], p['start'], p['end'])
    initial = number(p['initial'], 'Valor inicial', 0, 1e12)
    final = number(p['final'], 'Valor final', 0, 1e12)
    old = number(p['oldIncome'], 'Renda inicial', 0, 1e12)
    new = number(p['newIncome'], 'Renda final', 0, 1e12)
    net = number(p['netReturn'], 'Retorno líquido do período', -90, 100)
    target = number(p['target'], 'Meta', 0, 1e12)
    capital = number(p['capital'], 'Capital reservado', 0, 1e12)
    contribution = number(p['monthly'], 'Aporte mensal', 0, 1e12)
    years = int(number(p['years'], 'Prazo', 1, 70))
    annual = number(p['annual'], 'Retorno futuro', -90, 100)
    observed = p.get('futureMode', 'observed') == 'observed'
    future = data['annual'] if observed else number(p['futureInflation'], 'Inflação futura', -20, 50)
    months = years * 12
    growth = (1 + annual / 100) ** years
    monthly = (1 + annual / 100) ** (1 / 12) - 1
    annuity = months if abs(monthly) < 1e-12 else math.expm1(months * math.log1p(monthly)) / monthly
    scenarios = []
    for label, rate in [('Inflação menor', max(-20, future - 2)), ('Referência escolhida', future), ('Inflação maior', future + 2)]:
        inf = (1 + rate / 100) ** years
        future_target = target * inf
        balance = capital * growth + contribution * annuity
        scenarios.append({'label': label, 'inflation': rate, 'futureTarget': future_target, 'nominal': balance, 'real': balance / inf,
                          'requiredMonthly': max(0, (future_target - capital * growth) / annuity)})
    return {'start': p['start'], 'end': p['end'], 'inflation': (factor - 1) * 100, 'factor': factor,
            'money': {'required': initial * factor, 'realFinal': final / factor, 'realChange': (final / factor / initial - 1) * 100 if initial else None, 'realDifference': final / factor - initial},
            'income': {'required': old * factor, 'realCurrent': new / factor, 'realChange': (new / factor / old - 1) * 100 if old else None},
            'investment': {'netReturn': net, 'realReturn': ((1 + net / 100) / factor - 1) * 100},
            'future': {'years': years, 'annual': annual, 'inflation': future, 'observedAssumption': observed, 'scenarios': scenarios},
            'data': {k: data.get(k) for k in ('provider','checkedAt','latestMonth','warning','needsCheck','method')}}
