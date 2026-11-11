import json,re,threading
from pathlib import Path

class HelpPreferences:
    def __init__(self,root):
        self.path=Path(root)/'guidance-settings.json';self.lock=threading.RLock()
    def status(self):
        with self.lock:
            try:d=json.loads(self.path.read_text(encoding='utf-8'))
            except (OSError,ValueError):d={}
            return {'intro':d.get('intro','pending'),'screens':d.get('screens',{}),'auto':d.get('auto',True)}
    def command(self,p):
        with self.lock:
            d=self.status();action=p.get('action')
            if action=='tour':
                key=p.get('screen');status=p.get('status')
                if not isinstance(key,str) or not re.fullmatch('[a-z]{1,24}',key) or status not in ('done','skipped'):raise ValueError('Preferência do tutorial inválida.')
                if key=='intro':d['intro']=status
                else:d['screens'][key]=status
            elif action=='auto':
                if type(p.get('value')) is not bool:raise ValueError('Preferência inválida.')
                d['auto']=p['value']
            elif action=='reset':d.update(intro='pending',screens={},auto=True)
            else:raise ValueError('Comando inválido.')
            tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8');tmp.replace(self.path)
            return d
