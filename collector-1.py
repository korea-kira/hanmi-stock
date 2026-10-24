import json, math, os, datetime, statistics, time
from pathlib import Path
import requests, feedparser, yfinance as yf

ROOT=Path(__file__).parent/'docs'; ROOT.mkdir(exist_ok=True)
SYMBOLS={'005930.KS':'삼성전자','000660.KS':'SK하이닉스','035420.KS':'NAVER','^KS11':'코스피','^KQ11':'코스닥','AAPL':'애플','MSFT':'마이크로소프트','NVDA':'엔비디아','SPY':'S&P500 ETF','QQQ':'나스닥100 ETF','^GSPC':'S&P500','^IXIC':'나스닥','KRW=X':'원/달러','^TNX':'미국 10년물 금리 지수'}
RSS=[('연준','https://www.federalreserve.gov/feeds/press_all.xml'),('미국 노동통계국','https://www.bls.gov/feed/bls_latest.rss'),('미국 경제분석국','https://www.bea.gov/news/rss.xml'),('한국은행','https://www.bok.or.kr/portal/bbs/B0000217/news.rss')]
HEADERS={'User-Agent':'PersonalMarketBrief/1.0 (public research dashboard)'}
def forecast(prices,i):
    if i<65:return None
    p=prices[:i+1]; last=p[-1]; ma20=sum(p[-20:])/20; ma60=sum(p[-60:])/60
    r20=last/p[-21]-1; r5=last/p[-6]-1
    score=(1 if last>ma20 else -1)+(1 if ma20>ma60 else -1)+(1 if r20>0 else -1)+(1 if r5>0 else -1)
    return {'signal':'상승 관심' if score>=2 else '하락 위험' if score<=-2 else '관망','score':score,'pred':1 if score>=2 else -1 if score<=-2 else 0}
def backtest(prices,horizon=10):
    trials=[]
    for i in range(65,len(prices)-horizon,horizon):
        f=forecast(prices,i)
        if f and f['pred']!=0:
            ret=prices[i+horizon]/prices[i]-1
            trials.append({'prediction':f['pred'],'actual_return':ret,'correct':(ret>0 if f['pred']==1 else ret<0),'error':abs(ret-(0.01 if f['pred']==1 else -0.01))})
    if len(trials)<12:return {'status':'검증 표본 부족','samples':len(trials)}
    return {'status':'검증 가능','samples':len(trials),'hit_rate':round(sum(t['correct'] for t in trials)/len(trials)*100,1),'mean_absolute_error_pct':round(statistics.mean(t['error'] for t in trials)*100,2),'horizon_trading_days':horizon,'method':'60일 이동평균 및 5/20일 추세; 10거래일 비중첩 과거검증','caution':'생존편향·거래비용·슬리피지 미반영. 과거 성과는 미래를 보장하지 않음'}
def get_prices(symbol):
    df=yf.Ticker(symbol).history(period='3y',interval='1d',auto_adjust=True)
    return [float(x) for x in df['Close'].dropna().tolist() if math.isfinite(float(x)) and float(x)>0], (str(df.index[-1].date()) if not df.empty else None)
def news():
    result=[]
    for source,url in RSS:
        try:
            response=requests.get(url,headers=HEADERS,timeout=12);response.raise_for_status()
            feed=feedparser.parse(response.content)
            for entry in feed.entries[:5]:
                result.append({'source':source,'title':entry.get('title','')[:240],'url':entry.get('link',''),'published':entry.get('published',''),'kind':'공식 발표'})
        except Exception as e: print('feed unavailable',source,str(e)[:100])
    return result[:25]
def main():
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    result={'collected_at_utc':now,'market_data_provider':'Yahoo Finance via yfinance (unofficial, may be delayed)','stocks':[],'news':news(),'errors':[],'note':'시장 전체의 모든 자료가 아니라 지정된 종목과 공개 RSS만 수집. 수집 간격 30분. 실시간 체결가가 아님.'}
    for symbol,name in SYMBOLS.items():
        try:
            prices,asof=get_prices(symbol)
            if len(prices)<75:raise ValueError('가격 이력 부족')
            f=forecast(prices,len(prices)-1)
            result['stocks'].append({'symbol':symbol,'name':name,'last_price':round(prices[-1],4),'price_date':asof,'signal':f['signal'],'score':f['score'],'validation':backtest(prices),'horizon_trading_days':10,'data_points':len(prices),'price_source':'Yahoo Finance (비공식·지연 가능)'})
        except Exception as e:result['errors'].append({'symbol':symbol,'error':str(e)[:160]})
    output=ROOT/'data.json'
    if not result['stocks']:
        raise RuntimeError('전체 시세 수집 실패: 기존 정상 데이터를 유지합니다')
    result['health']={'status':'ok' if not result['errors'] else 'partial', 'success_count':len(result['stocks']), 'failure_count':len(result['errors'])}
    tmp=ROOT/'data.json.tmp'
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    json.loads(tmp.read_text(encoding='utf-8'))
    tmp.replace(output)
    print('saved',len(result['stocks']),'stocks',len(result['news']),'news')
if __name__=='__main__':main()
