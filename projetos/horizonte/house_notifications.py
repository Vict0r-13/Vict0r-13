"""Opt-in Windows notifications while the local application service is running."""
import base64,json,subprocess,sys,threading
from datetime import date
from household import expire

def notification_script(expired,soon):
 # Only integer counts enter the script; no user-provided strings or credentials.
 expired=int(expired);soon=int(soon)
 return '''Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.BalloonTipTitle = 'Horizonte - validade dos produtos'
$n.BalloonTipText = '%d lote(s) vencido(s) e %d perto do vencimento. Confira Casa e alimentacao.'
$n.ShowBalloonTip(10000)
$until = [DateTime]::Now.AddSeconds(12)
while ([DateTime]::Now -lt $until) { [System.Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 100 }
$n.Dispose()
'''%(expired,soon)

def start(store):
 stop=threading.Event()
 if sys.platform!='win32':return stop
 marker=store.root/'house_notice.json'
 def run():
  while not stop.is_set():
   try:
    h=store.get()['state']['household'];today=date.today().isoformat()
    try:last=json.loads(marker.read_text(encoding='utf-8')).get('date')
    except (OSError,ValueError):last=None
    alerts=expire(h)
    if h['settings']['desktop'] and alerts and last!=today:
     script=notification_script(sum(a['days']<0 for a in alerts),sum(a['days']>=0 for a in alerts))
     result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode('ascii')],creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
     if result.returncode==0:marker.write_text(json.dumps({'date':today}),encoding='utf-8')
   except Exception:
    # Local in-app alerts remain available even when the OS suppresses notifications.
    pass
   stop.wait(60)
 threading.Thread(target=run,name='house-validity-notices',daemon=True).start()
 return stop
