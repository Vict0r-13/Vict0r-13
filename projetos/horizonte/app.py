"""Offline desktop app. Python standard library only; optional pywebview."""
import argparse
import hmac
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import threading
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from finance import project, payoff, installments, month_add
from storage import Store, Conflict
from purchasing_power import Inflation, analyze as analyze_power
from onepage import report as onepage_report, command as close_command, suggestions as close_suggestions
from spending import overview as spending_overview, simulate as spending_simulate
from payroll import calculate as salary_calculate, command as salary_command, sync as salary_sync, status as salary_status
from debtbook import report as debtbook_report, command as debtbook_command
from guidance import preview as guidance_preview, apply as guidance_apply
from help_preferences import HelpPreferences
from focus import report as focus_report, command as focus_command, statement_preview, decision as focus_decision
from life import report as life_report, command as life_command, cleanup_models
from experience import suggest
from routines import Reports, report, validate_reports
from investing import analyze, compare_products
from planning import goal_projection, buy
from expense_receipts import document as expense_document, resolve as expense_resolve, import_expense, duplicate as expense_duplicate, similar as expense_similar
from house_notifications import start as start_house_notifications
from market import Market
from email_delivery import Account, Delivery, validate_config
from research import Research
from purchases import command as purchase_command
from receipts import parse as parse_receipt, official_url
from household import command as house_command, summary as house_summary

ASSETS = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'static'


def serve(store, port=0):
    token = secrets.token_urlsafe(32)
    market = Market(store.root)
    inflation = Inflation(store.root)
    reports = Reports(store)
    email_account=Account(store.root)
    email_delivery=Delivery(store,email_account)
    research=Research(store.root)
    assistant=HelpPreferences(store.root)
    reports.start()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def send(self, body, status=200, mime='application/json; charset=utf-8', headers=None):
            if not isinstance(body,bytes): body = json.dumps(body,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            for k,v in (headers or {}).items():self.send_header(k,v)
            self.end_headers();self.wfile.write(body)
        def allowed(self):
            host = self.headers.get('Host','')
            return host == f'127.0.0.1:{self.server.server_port}'
        def authorized(self):
            try:
                c=SimpleCookie();c.load(self.headers.get('Cookie',''))
                return hmac.compare_digest(c['horizonte'].value, token)
            except (KeyError,ValueError): return False
        def do_GET(self):
            if not self.allowed(): return self.send({'error':'Host inválido'},403)
            u=urlparse(self.path)
            key=parse_qs(u.query).get('token',[''])[0]
            if u.path=='/' and key and hmac.compare_digest(key,token):
                return self.send(b'',303,headers={'Location':'/','Set-Cookie':f'horizonte={token}; HttpOnly; SameSite=Strict; Path=/'})
            if not self.authorized():return self.send({'error':'Abra pelo iniciador desktop.'},403)
            if u.path=='/api/guidance/status':return self.send(assistant.status())
            if u.path=='/api/email/status':return self.send(email_account.status())
            if u.path=='/api/research/needs':return self.send(research.needs(store.get()['state']))
            if u.path=='/api/state':return self.send(salary_sync(store))
            if u.path=='/api/reports/inbox':return self.send(reports.inbox())
            if u.path=='/api/events':return self.send(store.events())
            if u.path=='/api/market/status':return self.send(market.status())
            if u.path=='/api/inflation/status':return self.send(inflation.status(auto=True))
            paths={'/expense-receipts.js':'expense-receipts.js','/expense-receipts.css':'expense-receipts.css','/planning.js':'planning.js','/planning.css':'planning.css','/shopping.js':'shopping.js','/shopping.css':'shopping.css','/':'index.html','/app.js':'app.js','/style.css':'style.css','/guide.html':'guide.html','/v2.js':'v2.js','/v2.css':'v2.css','/v3.js':'v3.js','/v3.css':'v3.css','/clean.js':'clean.js','/clean.css':'clean.css','/house.js':'house.js','/house.css':'house.css','/ux.js':'ux.js','/ux.css':'ux.css','/routines.js':'routines.js','/routines.css':'routines.css','/upgrade.js':'upgrade.js','/upgrade.css':'upgrade.css','/icon.png':'icon.png'}
            paths.update({'/mobile.js':'mobile.js','/mobile.css':'mobile.css','/mobile-compat.js':'mobile-compat.js','/guidance.css':'guidance.css','/debtbook.js':'debtbook.js','/debtbook.css':'debtbook.css','/payroll.js':'payroll.js','/payroll.css':'payroll.css','/spending.js':'spending.js','/spending.css':'spending.css','/onepage.js':'onepage.js','/onepage.css':'onepage.css','/power.js':'power.js','/power.css':'power.css'})
            paths.update({'/focus.js':'focus.js','/focus.css':'focus.css','/life.js':'life.js','/life.css':'life.css','/tour.js':'tour.js'})
            if u.path not in paths:return self.send({'error':'Não encontrado'},404)
            p=ASSETS/paths[u.path]
            mime=mimetypes.guess_type(p.name)[0] or 'text/plain'
            return self.send(p.read_bytes(),mime=mime if p.suffix=='.wasm' else mime+'; charset=utf-8')
        def do_POST(self):
            if not self.allowed() or not self.authorized() or self.headers.get('X-Horizonte')!='1':
                return self.send({'error':'Acesso negado'},403)
            origin=self.headers.get('Origin')
            if origin and origin!=f'http://127.0.0.1:{self.server.server_port}':return self.send({'error':'Origem inválida'},403)
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=12_000_000:raise ValueError('Requisição vazia ou maior que 12 MB')
                p=json.loads(self.rfile.read(n))
                if not isinstance(p,dict):raise ValueError('Objeto JSON esperado')
                def write(state,revision,mode='normal'):
                    if mode=='normal' and p.get('accountId') and state.get('accountBook'):
                        aid=p['accountId']
                        if not any(a['id']==aid and not a['archived'] for a in state['accountBook']['accounts']):raise ValueError('Escolha uma conta ativa.')
                        before={t['id']:t for t in store.get()['state']['transactions']}
                        for t in state['transactions']:
                            old=before.get(t['id'])
                            if old is None or old['status']!='paid' and t['status']=='paid':t['accountId']=aid
                    return store.put(state,revision,mode,on=p.get('on'))
                if self.path in ('/api/focus/report','/api/focus/preview','/api/focus/decision'):
                    current=store.get()
                    fn={'/api/focus/report':focus_report,'/api/focus/preview':statement_preview,'/api/focus/decision':focus_decision}[self.path]
                    return self.send(dict(fn(current['state'],p),revision=current['revision']))
                if self.path=='/api/focus/command':
                    current=store.get()
                    if current['revision']!=p.get('revision'):raise Conflict('Os dados mudaram. Refaça a conferência antes de confirmar.')
                    return self.send(write(focus_command(current['state'],p),p['revision']))
                if self.path=='/api/life/cleanup-models':return self.send(cleanup_models(store.root))
                if self.path=='/api/life/report':
                    current=store.get()
                    return self.send(dict(life_report(current['state'],p),revision=current['revision'],undo=store.undo_status()))
                if self.path=='/api/life/command':
                    current=store.get()
                    if current['revision']!=p.get('revision'):raise Conflict('Os dados mudaram. Atualize a tela antes de confirmar.')
                    return self.send(write(life_command(current['state'],p),p['revision']))
                if self.path=='/api/life/undo':return self.send(store.undo(p.get('revision'),p.get('on')))
                if self.path=='/api/guidance/preview':
                    current=store.get()
                    return self.send(dict(guidance_preview(current['state'],p),revision=current['revision']))
                if self.path=='/api/guidance/apply':
                    current=store.get()
                    if current['revision']!=p.get('revision'):raise Conflict('Os dados mudaram. Recalcule a sugestão.')
                    return self.send(write(guidance_apply(current['state'],p),p['revision']))
                if self.path=='/api/guidance/settings':return self.send(assistant.command(p))
                if self.path=='/api/debtbook/report':
                    current=store.get()
                    return self.send(dict(debtbook_report(current['state'],p),revision=current['revision']))
                if self.path=='/api/debtbook/command':
                    current=store.get()
                    if current['revision']!=p.get('revision'):raise Conflict('Dados mudaram. Recarregue antes de vincular o pagamento.')
                    return self.send(write(debtbook_command(current['state'],p),p['revision']))
                if self.path=='/api/payroll/preview':return self.send(salary_calculate(p['plan'],p['month']))
                if self.path=='/api/payroll/status':return self.send(salary_status(store.get()['state'],p.get('on')))
                if self.path=='/api/payroll/sync':return self.send(salary_sync(store,p.get('on')))
                if self.path=='/api/payroll/command':
                    current=store.get()
                    if current['revision']!=p.get('revision'):raise Conflict('Dados mudaram. Recarregue antes de salvar o salário.')
                    return self.send(write(salary_command(current['state'],p,p.get('on')),p['revision']))
                if self.path in ('/api/spending/overview','/api/spending/simulate'):
                    current=store.get()
                    result=spending_simulate(current['state'],p) if self.path.endswith('/simulate') else spending_overview(current['state'],p.get('on'))
                    return self.send(dict(result,revision=current['revision']))
                if self.path=='/api/onepage/report':return self.send(onepage_report(store.get()['state'],inflation.status(auto=True),p['month'],p.get('window',12)))
                if self.path=='/api/onepage/suggestions':return self.send(close_suggestions(store.get()['state'],p['month']))
                if self.path=='/api/onepage/close':
                    current=store.get()
                    if current['revision']!=p.get('revision'):raise Conflict('Dados mudaram. Recarregue antes de salvar o fechamento.')
                    return self.send(write(close_command(current['state'],p),p['revision']))
                if self.path=='/api/inflation/refresh':
                    inflation.refresh(force=True)
                    return self.send(inflation.status())
                if self.path=='/api/power/analyze':return self.send(analyze_power(inflation.status(),p))
                if self.path in ('/api/receipts/read','/api/receipts/resolve'):
                    result=expense_resolve(p.get('url','')) if self.path.endswith('/resolve') else expense_document(p.get('text',''),p.get('kind','text'),p.get('blocks'))
                    state=store.get()['state'];result['duplicate']=expense_duplicate(state,result.get('fingerprint',''))
                    result['similar']=expense_similar(state,result['total'],result['date']) if result.get('total') and result.get('date') else []
                    return self.send(result)
                if self.path=='/api/receipts/import':
                    current=store.get()
                    if current['revision']!=p.get('revision'):raise Conflict('Dados mudaram. Recarregue antes de salvar a nota.')
                    return self.send(write(import_expense(current['state'],p),p['revision']))
                if self.path=='/api/shopping/parse':return self.send(parse_receipt(p.get('text',''),p.get('kind','text'),p.get('blocks')))
                if self.path=='/api/shopping/qr':return self.send({'url':official_url(p.get('value',''))})
                if self.path=='/api/shopping/command':
                    current=store.get()
                    if current['revision']!=p['revision']:raise Conflict('Dados mudaram. Recarregue antes de continuar.')
                    return self.send(write(purchase_command(current['state'],p),p['revision']))
                if self.path=='/api/email/config':return self.send(email_account.save(p))
                if self.path=='/api/email/clear':return self.send(email_account.clear())
                if self.path=='/api/email/retry':
                    email_delivery.retry(str(p.get('id','')));email_delivery.pump();return self.send(reports.inbox())
                if self.path=='/api/email/test':
                    from email_delivery import transmit
                    account=email_account.read()
                    if not account:raise ValueError('Configure o e-mail primeiro')
                    status,detail=transmit(account,'Teste de configuração','Este é um teste solicitado por você. Nenhum dado financeiro foi incluído.',secrets.token_hex(32))
                    return self.send(dict(status=status,detail=detail))
                if self.path=='/api/research/prices':return self.send(research.prices(p))
                if self.path=='/api/research/page':return self.send(research.page(p))
                if self.path=='/api/research/nearby':return self.send(research.nearby(p))
                if self.path=='/api/reports/preview':
                    validate_reports([p['rule']]);return self.send({'text':report(store.get()['state'],p['rule'])})
                if self.path=='/api/reports/check':
                    reports.tick();return self.send(reports.inbox())
                if self.path=='/api/category/suggest':return self.send(suggest(store.get()['state'],p.get('description',''),p.get('type','expense')))
                if self.path=='/api/house/summary':return self.send(house_summary(store.get()['state'],p['start'],p['end']))
                if self.path=='/api/house/command':
                    current=store.get()
                    if current['revision']!=p['revision']:raise Conflict('Dados mudaram. Recarregue antes de continuar.')
                    return self.send(write(house_command(current['state'],p),p['revision']))
                if self.path=='/api/state':return self.send(write(p['state'],p['revision'],p.get('mode','normal')))
                if self.path=='/api/market/key':return self.send(market.set_key(p.get('key','')))
                if self.path=='/api/market/quote':return self.send(market.quote(p.get('ticker','')))
                if self.path=='/api/goals/project':return self.send(goal_projection(store.get()['state'],p))
                if self.path=='/api/investments/buy':
                    current=store.get()
                    if current['revision']!=p.get('revision'):raise Conflict('Dados mudaram. Recarregue antes de comprar.')
                    return self.send(write(buy(current['state'],p),p['revision']))
                if self.path=='/api/house/recipe-preview':
                    from household import estimate
                    current=store.get()['state']
                    from household import command as hc
                    preview=hc(current,dict(action='recipe',name='Prévia',servings=p.get('servings'),ingredients=p.get('ingredients'),notes=''))
                    from household import validate as vh
                    vh(preview)
                    return self.send(estimate(preview['household'],preview['household']['recipes'][-1],p.get('servings')))
                if self.path=='/api/analyze':return self.send(analyze(p))
                if self.path=='/api/compare':return self.send(compare_products(p))
                if self.path=='/api/project':return self.send(project(p))
                if self.path=='/api/payoff':return self.send(payoff(p))
                if self.path=='/api/installments':
                    amounts=installments(p['total'],p['count'])
                    return self.send([{'date':month_add(p['first'],i),'amount':a} for i,a in enumerate(amounts)])
                if self.path=='/api/quit':
                    self.send({'ok':True});threading.Thread(target=self.server.shutdown,daemon=True).start();return
                self.send({'error':'Não encontrado'},404)
            except Conflict as e:self.send({'error':str(e)},409)
            except (ValueError,KeyError,TypeError,OverflowError) as e:self.send({'error':str(e)},400)
            except Exception:
                self.send({'error':'Não foi possível concluir. Os dados anteriores foram preservados.'},500)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    return server, f'http://127.0.0.1:{server.server_port}/?token={token}'


def open_desktop(url, root):
    if sys.platform=='win32':
        candidates=[Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe',
                    Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Microsoft/Edge/Application/msedge.exe',
                    Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Google/Chrome/Application/chrome.exe']
        for path in candidates:
            if path.exists():
                subprocess.Popen([str(path),'--app='+url,'--window-size=1380,900','--user-data-dir='+str(root/'window-profile')])
                return
    webbrowser.open(url)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-dir',default=os.environ.get('HORIZONTE_DATA_DIR',str(Path.home()/'.horizonte_financeiro')))
    parser.add_argument('--port',type=int,default=0);parser.add_argument('--no-open',action='store_true')
    args=parser.parse_args()
    root=Path(args.data_dir).resolve()
    # Single desktop instance per data directory, released automatically by the OS.
    root.mkdir(parents=True,exist_ok=True)
    lock=open(root/'instance.lock','a+b')
    try:
        if sys.platform=='win32':
            import msvcrt
            lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        if not args.no_open:
            try:
                session=json.loads((root/'session.json').read_text(encoding='utf-8'))
                open_desktop(session['url'], root)
            except (OSError,ValueError,KeyError):
                print('Horizonte já está aberto. Use a janela existente.')
        return
    store=Store(root);server,url=serve(store,args.port)
    notice_stop=start_house_notifications(store)
    session_path=root/'session.json'
    session_path.write_text(json.dumps({'url':url}),encoding='utf-8')
    try:session_path.chmod(0o600)
    except OSError:pass
    print('Horizonte Financeiro iniciado. Dados em:', root)
    if args.no_open:print(url,flush=True)
    else:open_desktop(url,root)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        notice_stop.set();server.server_close();lock.close();session_path.unlink(missing_ok=True)

if __name__=='__main__':
    try:
        main()
    except Exception:
        import traceback
        error=traceback.format_exc()
        log=Path.home()/'.horizonte_financeiro'/'erro_inicializacao.log'
        log.parent.mkdir(parents=True,exist_ok=True);log.write_text(error,encoding='utf-8')
        if sys.platform=='win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, 'Não foi possível iniciar. Consulte '+str(log), 'Horizonte Financeiro', 16)
        else:
            print(error,file=sys.stderr)
        sys.exit(1)

