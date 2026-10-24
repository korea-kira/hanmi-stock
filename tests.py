import unittest
import ast
from pathlib import Path
source=ast.parse((Path(__file__).parent/'collector.py').read_text())
functions=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ('forecast','backtest')]
namespace={'statistics':__import__('statistics')}
exec(compile(ast.Module(body=functions,type_ignores=[]),'<forecast>', 'exec'),namespace)
forecast=namespace['forecast']; backtest=namespace['backtest']

class ForecastTests(unittest.TestCase):
    def test_short_series(self):
        self.assertIsNone(forecast([100.0]*20,19))
    def test_rising(self):
        p=[100+i for i in range(150)]
        self.assertEqual(forecast(p,len(p)-1)['pred'],1)
    def test_falling(self):
        p=[300-i for i in range(150)]
        self.assertEqual(forecast(p,len(p)-1)['pred'],-1)
    def test_backtest_sample(self):
        self.assertEqual(backtest([100+i for i in range(80)])['status'],'검증 표본 부족')
    def test_backtest_no_future_leakage(self):
        p=[100+i for i in range(220)]
        self.assertEqual(forecast(p[:100],99),forecast(p,99))

if __name__=='__main__':unittest.main()
