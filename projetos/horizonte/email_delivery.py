"""MIT. Local SMTP delivery with durable claims, TLS and device-protected secrets."""
import ctypes,json,os,re,smtplib,socket,ssl,sys,threading,time
from datetime import datetime,timezone
from email.message import EmailMessage
from pathlib import Path

_LOCK=threading.Lock()
_SESSION={}

def validate_config(p,need_secret=True):
    if not isinstance(p,dict):raise ValueError('Configuração de e-mail inválida')
    out={k:str(p.get(k,'')).strip() for k in ('sender','recipient','username','password')}
    for k in ('sender','recipient'):
        if not re.fullmatch(r'[^\s@<>;,\r\n]{1,120}@[^\s@<>;,\r\n]{1,150}\.[A-Za-z]{2,30}',out[k]):raise ValueError('Informe remetente e destinatário válidos, sem listas de endereços')
    # Fixed endpoints avoid leaking credentials to an arbitrary host typed by mistake.
    provider=p.get('provider','gmail')
    if provider not in ('gmail','outlook'):raise ValueError('Provedor suportado: Gmail ou Outlook SMTP')
    out['provider']=provider;out['host']='smtp.gmail.com' if provider=='gmail' else 'smtp-mail.outlook.com';out['port']=465 if provider=='gmail' else 587
    out['username']=out['username'] or out['sender'];out['enabled']=p.get('enabled') is True
    if need_secret and not out['password']:raise ValueError('Informe a senha de aplicativo do provedor')
    if len(out['password'])>512 or '\r' in out['password'] or '\n' in out['password']:raise ValueError('Credencial inválida')
    return out

def dpapi(data,encrypt):
    from ctypes import wintypes
    class Blob(ctypes.Structure):_fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_byte))]
    buf=ctypes.create_string_buffer(data);src=Blob(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_byte)));dst=Blob()
    crypt=ctypes.windll.crypt32;kernel=ctypes.windll.kernel32
    crypt.CryptProtectData.argtypes=[ctypes.POINTER(Blob),wintypes.LPCWSTR,ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    crypt.CryptUnprotectData.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    if encrypt:ok=crypt.CryptProtectData(ctypes.byref(src),'Horizonte email',None,None,None,1,ctypes.byref(dst))
    else:ok=crypt.CryptUnprotectData(ctypes.byref(src),None,None,None,None,1,ctypes.byref(dst))
    if not ok:raise ValueError('Não foi possível acessar a proteção de credenciais do Windows')
    try:return ctypes.string_at(dst.pbData,dst.cbData)
    finally:kernel.LocalFree(dst.pbData)

class Account:
    def __init__(self,root):self.root=Path(root);self.path=self.root/'email-account.dpapi'
    def read(self):
        try:
            from java import jclass
            raw=str(jclass('com.ivanildo.horizonte.EmailVault').read())
            return validate_config(json.loads(raw)) if raw else None
        except ImportError:pass
        if sys.platform=='win32':
            try:return validate_config(json.loads(dpapi(self.path.read_bytes(),False).decode('utf-8')))
            except FileNotFoundError:return None
            except Exception:raise ValueError('Credencial de e-mail inacessível. Configure novamente neste Windows.') from None
        return _SESSION.get(str(self.root))
    def save(self,p):
        p=validate_config(p)
        try:
            from java import jclass
            jclass('com.ivanildo.horizonte.EmailVault').save(json.dumps(p));return self.status()
        except ImportError:pass
        if sys.platform=='win32':
            temp=self.path.with_suffix('.tmp');temp.write_bytes(dpapi(json.dumps(p).encode('utf-8'),True));temp.replace(self.path)
        else:_SESSION[str(self.root)]=p
        return self.status()
    def clear(self):
        try:
            from java import jclass
            jclass('com.ivanildo.horizonte.EmailVault').clear()
        except ImportError:pass
        self.path.unlink(missing_ok=True);_SESSION.pop(str(self.root),None);return self.status()
    def status(self):
        error=''
        try:p=self.read()
        except Exception:p=None;error='Não foi possível ler a credencial protegida. Configure novamente neste aparelho.'
        try:
            from java import jclass
            protection='Android Keystore'
        except ImportError:protection='Windows DPAPI' if sys.platform=='win32' else 'Somente nesta sessão de desenvolvimento'
        return dict(configured=bool(p),enabled=bool(p and p['enabled']),sender=p['sender'] if p else '',recipient=p['recipient'] if p else '',provider=p['provider'] if p else 'gmail',protected=protection,error=error)

def transmit(account,subject,body,ident,transport=None):
    message=EmailMessage();message['From']=account['sender'];message['To']=account['recipient'];message['Subject']='Horizonte · '+' '.join(subject.split())[:160];message['Message-ID']='<'+ident+'@horizonte.local>';message['Auto-Submitted']='auto-generated';message.set_content(body+'\n\nEnviado pelo seu Horizonte. Gerencie os agendamentos no aplicativo.')
    stage='connecting'
    try:
        # No plain-text password fallback. Outlook depends on whether SMTP app authentication is enabled in that account.
        factory=transport or (smtplib.SMTP_SSL if account['port']==465 else smtplib.SMTP)
        kwargs={'timeout':20}
        if account['port']==465:kwargs['context']=ssl.create_default_context()
        with factory(account['host'],account['port'],**kwargs) as smtp:
            smtp.ehlo()
            if account['port']==587:smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
            smtp.login(account['username'],account['password']);stage='submitting'
            refused=smtp.send_message(message)
            if refused:return 'blocked','Destinatário recusado pelo provedor.'
        return 'sent','Aceito pelo servidor de e-mail; recebimento e leitura não confirmados.'
    except smtplib.SMTPAuthenticationError:return 'blocked','Autenticação recusada. Confira a senha de aplicativo e as regras SMTP da conta.'
    except (smtplib.SMTPRecipientsRefused,smtplib.SMTPSenderRefused,smtplib.SMTPDataError):return 'blocked','O provedor recusou o remetente, destinatário ou conteúdo. Confira a configuração.'
    except (TimeoutError,OSError,smtplib.SMTPException):
        if stage=='submitting':return 'uncertain','Resultado incerto após iniciar o envio. Confira sua caixa antes de reenviar; não haverá repetição automática.'
        return 'retry','Sem conexão SMTP. Será feita outra tentativa quando houver conexão e o aplicativo executar.'

class Delivery:
    def __init__(self,store,account=None):
        self.store=store;self.account=account or Account(store.root)
        with store.connect() as c:c.execute('CREATE TABLE IF NOT EXISTS email_deliveries (id TEXT PRIMARY KEY,status TEXT,attempts INTEGER,next_at REAL,updated_at TEXT,detail TEXT)')
    def pump(self,transport=None):
        if not _LOCK.acquire(blocking=False):return
        try:
            try:account=self.account.read()
            except Exception:return
            if not account or not account['enabled']:return
            now=time.time();snapshot=self.store.get();state=snapshot['state'];active={r['id']:r for r in state.get('reports',[]) if r['enabled'] and r['channel']=='email'}
            with self.store.connect() as c:
                # A previous process could have died after SMTP accepted: never silently resend.
                c.execute("UPDATE email_deliveries SET status='uncertain',detail='Execução interrompida durante envio. Confira a caixa de e-mail antes de repetir.' WHERE status='sending'")
                inbox=c.execute("SELECT id,rule_id,slot,title,body FROM reports_inbox WHERE channel='email' ORDER BY slot DESC").fetchall()
            seen=set()
            for ident,rule_id,slot,title,body in inbox:
                if rule_id not in active or rule_id in seen:continue
                seen.add(rule_id)
                with self.store.connect() as c:
                    c.execute('BEGIN IMMEDIATE')
                    if c.execute('SELECT revision FROM state WHERE id=1').fetchone()[0]!=snapshot['revision']:return
                    row=c.execute('SELECT status,attempts,next_at FROM email_deliveries WHERE id=?',(ident,)).fetchone()
                    if row and (row[0] not in ('retry','pending') or row[2]>now or row[1]>=6):continue
                    attempt=(row[1] if row else 0)+1;stamp=datetime.now(timezone.utc).isoformat()
                    c.execute('INSERT OR REPLACE INTO email_deliveries VALUES (?,?,?,?,?,?)',(ident,'sending',attempt,0,stamp,'Conectando ao provedor.'))
                status,detail=transmit(account,title,body,ident,transport)
                if status=='retry' and attempt>=6:status,detail='blocked','Conexão indisponível após seis tentativas. Confira a internet e solicite nova tentativa.'
                with self.store.connect() as c:c.execute('UPDATE email_deliveries SET status=?,next_at=?,updated_at=?,detail=? WHERE id=?',(status,now+min(21600,300*2**(attempt-1)),datetime.now(timezone.utc).isoformat(),detail,ident))
        finally:_LOCK.release()
    def statuses(self):
        with self.store.connect() as c:return {row[0]:dict(status=row[1],attempts=row[2],updatedAt=row[3],detail=row[4]) for row in c.execute('SELECT id,status,attempts,updated_at,detail FROM email_deliveries')}
    def retry(self,ident):
        # Explicit user action only, with a warning in UI for uncertain deliveries.
        with self.store.connect() as c:
            row=c.execute("SELECT rule_id FROM reports_inbox WHERE id=? AND channel='email'",(ident,)).fetchone()
            if not row:raise ValueError('Relatório de e-mail não encontrado')
            latest=c.execute("SELECT id FROM reports_inbox WHERE rule_id=? AND channel='email' ORDER BY slot DESC LIMIT 1",(row[0],)).fetchone()[0]
            if latest!=ident:raise ValueError('O reenvio automático está disponível apenas para o relatório mais recente deste agendamento. Compartilhe os anteriores manualmente.')
            c.execute('INSERT OR REPLACE INTO email_deliveries VALUES (?,?,?,?,?,?)',(ident,'pending',0,0,datetime.now(timezone.utc).isoformat(),'Nova tentativa solicitada por você.'))
