"""Record live 10-session forecasts and evaluate them only after the horizon."""
import json
from datetime import datetime, timezone
from pathlib import Path
import yfinance as yf

ROOT = Path(__file__).resolve().parent / 'docs'
DATA = ROOT / 'data.json'
HISTORY = ROOT / 'prediction_history.json'


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default


def main():
    data = read_json(DATA, {})
    if not data.get('stocks'):
        raise RuntimeError('docs/data.json missing stocks')
    records = read_json(HISTORY, [])
    if not isinstance(records, list):
        raise ValueError('Invalid prediction history')
    now = datetime.now(timezone.utc).isoformat()
    for stock in data['stocks']:
        symbol = stock['symbol']
        if symbol.startswith('^') or symbol in ('KRW=X', '^TNX'):
            continue
        date = stock.get('price_date')
        signal = stock.get('signal')
        validation = stock.get('validation') or {}
        if signal not in ('상승 관심', '하락 위험') or validation.get('status') != '검증 가능':
            continue
        key = (symbol, date)
        if date and not any((r.get('symbol'), r.get('date')) == key for r in records):
            records.append({'symbol': symbol, 'name': stock.get('name'), 'date': date,
                            'price': stock['last_price'], 'signal': signal,
                            'horizon_sessions': 10, 'created_at_utc': now,
                            'status': '대기'})
    for record in records:
        if record.get('status') != '대기':
            continue
        try:
            frame = yf.Ticker(record['symbol']).history(start=record['date'], period=None,
                                                        interval='1d', auto_adjust=True)
            if frame.empty:
                continue
            series = [(str(dt.date()), float(value)) for dt, value in frame['Close'].dropna().items()]
            idx = next((i for i, (day, _) in enumerate(series) if day == record['date']), None)
            if idx is None or idx + 10 >= len(series):
                continue
            end_date, end_price = series[idx + 10]
            ret = (end_price / float(record['price']) - 1) * 100
            record.update({'status': '평가완료', 'end_date': end_date,
                           'end_price': round(end_price, 4), 'return_pct': round(ret, 2),
                           'correct': ret > 0 if record['signal'] == '상승 관심' else ret < 0})
        except Exception as exc:
            print('evaluation deferred:', record['symbol'], str(exc)[:120])
    completed = [r for r in records if r.get('status') == '평가완료']
    correct = sum(bool(r['correct']) for r in completed)
    data['forward_validation'] = {
        'completed': len(completed), 'pending': sum(r.get('status') == '대기' for r in records),
        'hit_rate_pct': round(correct / len(completed) * 100, 1) if completed else None,
        'method': '실제 기록 시점부터 이후 10개 거래 세션의 종가 방향 평가',
        'warning': '사후 평가이며 수익 보장 아님. 무료 데이터 제공처의 수정/지연 가능.'
    }
    HISTORY.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('tracking:', data['forward_validation'])


if __name__ == '__main__':
    main()
