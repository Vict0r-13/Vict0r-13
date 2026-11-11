"""Android adapter: same core and schema as desktop; no cloud sync."""
import json
import threading
from pathlib import Path
from datetime import date
from storage import Store
from household import expire

_server=None
_url=None
_lock=threading.Lock()

def start(root, assets):
    global _server,_url
    with _lock:
        if _server is None:
            import app
            app.ASSETS=Path(assets)
            _server,_url=app.serve(Store(root))
            threading.Thread(target=_server.serve_forever,daemon=True).start()
        return _url

def alerts(root):
    s=Store(root).get()['state'];h=s['household'];rows=expire(h)
    return json.dumps({'enabled':bool(h['settings']['desktop']),'count':len(rows),'expired':sum(r['days']<0 for r in rows),'day':date.today().isoformat()})


def reports_status(root):
    from routines import Reports
    store=Store(root);reports=Reports(store);reports.tick()
    rows=reports.inbox()
    return json.dumps({'enabled':any(r['enabled'] for r in store.get()['state'].get('reports',[])), 'latest':rows[0]['id'] if rows else ''})
