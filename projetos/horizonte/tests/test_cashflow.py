import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cashflow import cycle,timeline
from spending import overview
from storage import validate
from demo import demo_state


class ProjectionTests(unittest.TestCase):
    def test_period_ends_before_payday(self):
        result=cycle(demo_state('2026-11-11'),'2026-11-11')
        self.assertEqual(result['nextIncome'],'2026-11-15')
        self.assertEqual(result['end'],'2026-11-14')
        self.assertEqual(result['commitments'],30000)
        self.assertEqual(result['days'],4)

    def test_forecast_detects_gap_before_income(self):
        state=demo_state('2026-11-11');state['profile']['cash']=20000
        self.assertEqual(timeline(state,'2026-11-11',7)['firstGap'],'2026-11-12')

    def test_no_scheduled_income_uses_month_end(self):
        state=demo_state('2026-11-11')
        state['transactions']=[t for t in state['transactions'] if t['type']!='income']
        result=cycle(state,'2026-11-11')
        self.assertIsNone(result['nextIncome'])
        self.assertEqual(result['end'],'2026-11-30')

    def test_projections_do_not_mutate_input(self):
        state=demo_state('2026-11-11');before=copy.deepcopy(state)
        cycle(state,'2026-11-11');timeline(state,'2026-11-11',7);overview(state,'2026-11-11')
        self.assertEqual(state,before)

    def test_future_income_is_not_available_cash(self):
        state=demo_state('2026-11-11')
        before=overview(state,'2026-11-11')
        state['transactions'][0]['amount']*=10
        after=overview(state,'2026-11-11')
        self.assertEqual(before['daily'],after['daily'])
        self.assertEqual(before['cashRoom'],after['cashRoom'])

    def test_more_bills_reduce_daily_allowance(self):
        state=demo_state('2026-11-11')
        before=overview(state,'2026-11-11')
        state['transactions'][1]['amount']=60000
        after=overview(state,'2026-11-11')
        self.assertLess(after['daily'],before['daily'])

    def test_unknown_balance_does_not_create_allowance(self):
        state=demo_state('2026-11-11');state['profile']['cash']=None
        result=overview(state,'2026-11-11')
        self.assertIsNone(result['daily'])
        self.assertFalse(result['ready'])

    def test_demo_respects_application_schema(self):
        validate(demo_state('2026-11-11'))


if __name__=='__main__':
    unittest.main()
