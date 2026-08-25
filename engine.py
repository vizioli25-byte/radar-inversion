import json, urllib.request
from datetime import datetime, timezone
from pathlib import Path
BASE="https://data912.apidocs.ar"
ASSETS=["NVDA","MELI","META","MSFT","AMZN","GOOGL","AAPL","TSLA","NFLX","AMD","AVGO","SPY","QQQ","VIST","GGAL","YPF","PAMP","BMA","BBAR","TGS","TRAN","CEPU","COME"]
OUT=Path("data/weekly_top5.json")
def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"RadarInversion/1.0"})
    with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
def sma(a,n):return sum(a[-n:])/n if len(a)>=n else None
def ema(a,n):
    if len(a)<n:return None
    e=sum(a[:n])/n;k=2/(n+1)
    for x in a[n:]:e=x*k+e*(1-k)
    return e
def rsi(a,n=14):
    if len(a)<n+1:return 50
    g=l=0
    for i in range(len(a)-n,len(a)):
        d=a[i]-a[i-1];g+=max(d,0);l+=max(-d,0)
    return 100 if l==0 else 100-100/(1+g/l)
def analyze(t):
    rows=get_json(f"{BASE}/historical/cedears/{t}")
    c=[float(x["c"]) for x in rows if x.get("c") is not None];v=[float(x.get("v",0) or 0) for x in rows]
    if len(c)<60:return None
    last=c[-1];m20=sma(c,20);m50=sma(c,50);m200=sma(c,200);rr=rsi(c);e12,e26=ema(c,12),ema(c,26)
    macd=(e12-e26) if e12 is not None and e26 is not None else 0
    ret20=(last/c[-21]-1)*100;ret60=(last/c[-61]-1)*100 if len(c)>61 else ret20
    av=sma(v,20) or 0;vr=v[-1]/av if av else 1
    trend=(25 if last>m20 else 10)+(25 if last>m50 else 10)+(20 if m20>m50 else 8)+(15 if not m200 else (15 if last>m200 else 5))
    momentum=max(0,min(100,50+ret20*3+ret60*1.5));volume=max(0,min(100,50+(vr-1)*30))
    rsis=100 if 50<=rr<=70 else (70 if rr>70 else (55 if rr>=40 else 30))
    score=round(max(0,min(100,trend*.30+momentum*.25+volume*.15+rsis*.15+(80 if macd>0 else 35)*.15)))
    daily=[c[i]/c[i-1]-1 for i in range(max(1,len(c)-21),len(c))]
    vol=(sum((x-sum(daily)/len(daily))**2 for x in daily)/len(daily))**.5 if daily else .03
    rp=max(.035,min(.09,vol*2.2));stop=last*(1-rp);t1=last*(1+rp*1.5);t2=last*(1+rp*2.5)
    conf=round(max(0,min(100,score*.65+min(100,len(c)/252*100)*.20+max(0,100-vol*1000)*.15)))
    sig="COMPRA FUERTE" if score>=85 else "COMPRA" if score>=75 else "ESPERAR" if score>=60 else "EVITAR"
    return {"ticker":t,"price":round(last,4),"score":score,"signal":sig,"confidence":conf,"entry_low":round(last*(1-min(.012,rp/3)),4),"entry_high":round(last*(1+min(.012,rp/3)),4),"target1":round(t1,4),"target2":round(t2,4),"stop_loss":round(stop,4),"risk_reward":round((t1-last)/(last-stop),2),"rsi":round(rr,1),"ret20":round(ret20,2),"ret60":round(ret60,2),"volume_ratio":round(vr,2),"volatility_20d":round(vol*100,2),"sma20":round(m20,4),"sma50":round(m50,4),"sma200":round(m200,4) if m200 else None,"macd":round(macd,4)}
def main():
    out=[]
    for t in ASSETS:
        try:
            x=analyze(t)
            if x:out.append(x)
        except Exception as e:print("ERROR",t,e)
    out.sort(key=lambda x:(x["score"],x["confidence"]),reverse=True)
    OUT.write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),"horizon":"1-12 semanas","assets_analyzed":len(out),"top5":out[:5],"all_ranked":out},ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":main()
