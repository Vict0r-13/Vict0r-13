"""Inicia uma demonstração separada, sem abrir a base pessoal do Horizonte."""
import argparse
from datetime import date,timedelta
from pathlib import Path

from storage import Store,seed,migrate


def demo_state(on=None):
    day=date.fromisoformat(on) if on else date.today()
    month=day.strftime('%Y-%m')
    state=migrate(seed())
    state['profile'].update(name='Pessoa de demonstração',cash=120000,income=200000,
                            snapshotDate=day.isoformat(),notes='Cenário fictício para demonstração.')
    state['budgets']=[dict(id='demo-food',name='Alimentação',amount=90000,kind='variable',day=None,
                           start=month,end='',payment='',essential=True)]
    def transaction(ident,name,amount,when,kind,category):
        return dict(id=ident,name=name,amount=amount,date=when.isoformat(),type=kind,
                    category=category,status='planned',paidDate='',cardId='',notes='Fictício',allocated=False)
    state['transactions']=[transaction('demo-income','Próximo recebimento',200000,day+timedelta(days=4),'income','Salário'),
                           transaction('demo-bill','Conta de demonstração',30000,day+timedelta(days=1),'expense','Outras contas')]
    state['spendingPlan']={'buffer':0,'reviewedMonth':month}
    return state


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',default=str(Path(__file__).resolve().parent/'.demo-horizonte'))
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--no-open',action='store_true')
    args=parser.parse_args()
    root=Path(args.data_dir).resolve()
    personal=(Path.home()/'.horizonte_financeiro').resolve()
    if root==personal or personal in root.parents:
        parser.error('Use uma pasta separada da base pessoal para a demonstração.')
    store=Store(root)
    current=store.get()
    if current['revision']==0:
        store.put(demo_state(),0,on=date.today().isoformat())
    print('Demonstração com dados fictícios. Base separada em:',root,flush=True)
    import app
    import sys
    sys.argv=['app.py','--data-dir',str(root),'--port',str(args.port)]+(['--no-open'] if args.no_open else [])
    app.main()


if __name__=='__main__':
    main()
