"""
每日量化策略信号推送
长川科技(300604) + 生益科技(600183)
运行时间: 工作日 16:05 (收盘后)
"""

import duckdb, numpy as np
from datetime import datetime

DB = '/vol2/@apphome/trim.openclaw/data/workspace/lgb_chanlun_fundamental.db'

def d2s(d): return d.strftime('%Y-%m-%d') if hasattr(d,'strftime') else str(d)

def MA(c,n):
    r=[]
    for i in range(len(c)):
        r.append(np.mean(c[i-n+1:i+1]) if i>=n-1 else None)
    return r

def EMA(p,n):
    k=2/(n+1); e=[p[0]]
    for x in p[1:]: e.append(e[-1]*(1-k)+x*k)
    return e

def MACD(p,f=12,s=26,sig=9):
    ef=EMA(p,f); es=EMA(p,s)
    d=[f-s for f,s in zip(ef,es)]
    de=EMA(d,sig)
    return d, [(d-e)*2 for d,e in zip(d,de)]

def RSI(p,n=14):
    d=np.diff(p)
    g=np.where(d>0,d,0.0); l=np.where(d<0,-d,0.0)
    ag=[np.mean(g[:n])]; al=[np.mean(l[:n])]
    for i in range(n,len(d)):
        ag.append((ag[-1]*(n-1)+g[i])/n); al.append((al[-1]*(n-1)+l[i])/n)
    return [None]*n+[100 if l2==0 else 100-100/(1+g2/l2) for g2,l2 in zip(ag,al)]

def BOLL(p,n=20,k=2):
    ma=MA(p,n)
    std=[]
    for i in range(len(p)):
        if i<n-1: std.append(0.0)
        else: std.append(np.std(p[i-n+1:i+1],ddof=0))
    u=[m+k*s if m is not None else None for m,s in zip(ma,std)]
    l=[m-k*s if m is not None else None for m,s in zip(ma,std)]
    return u, ma, l

def ATR(h,l,co,p=14):
    tr=[0.0]
    for i in range(1,len(h)):
        tr.append(max(h[i]-l[i],abs(h[i]-co[i-1]),abs(l[i]-co[i-1])))
    return MA(tr,p)

def check_signal(code, name):
    conn = duckdb.connect(DB)
    rows = conn.execute(f"""
        SELECT trade_date, open, high, low, close, volume, amount
        FROM stock_daily WHERE stock_code='{code}'
        ORDER BY trade_date DESC LIMIT 60
    """).fetchall()
    conn.close()
    rows = list(reversed(rows))
    if len(rows) < 30:
        return None

    dates=[d2s(r[0]) for r in rows]
    closes=[float(r[4]) for r in rows]
    highs=[float(r[2]) for r in rows]
    lows=[float(r[3]) for r in rows]
    vols=[float(r[5]) for r in rows]
    n=len(rows)

    ma5=MA(closes,5); ma10=MA(closes,10); ma20=MA(closes,20); ma60=MA(closes,60)
    dif,macd=MACD(closes)
    rsi=RSI(closes,14)
    bb_u,bb_m,bb_l=BOLL(closes)
    atr=ATR(highs,lows,closes)

    i=n-1
    close=closes[i]; date=dates[i]
    vol=vols[i]; vol_ma5=np.mean(vols[-5:]) if len(vols)>=5 else vols[0]

    # 趋势判断
    trend = ma5[i] and ma20[i] and ma60[i] and ma5[i]>ma20[i]>ma60[i] and close>ma20[i]
    momentum = macd[i]>0 and rsi[i]>40 and rsi[i]<75
    vol_ok = vol > vol_ma5 * 1.2
    pullback = close < ma5[i]*1.03  # 不过度追高

    # 买入信号
    buy_signal = trend and momentum and pullback and vol_ok
    # 卖出信号
    sell_signal = (ma5[i] and ma20[i] and ma5[i] < ma20[i]) or rsi[i]>80 or (macd[i]<0 and macd[i-1]>0)

    # 强度评分
    score = 0
    if trend: score += 2
    if momentum: score += 2
    if vol_ok: score += 1
    if pullback: score += 1
    if rsi[i] > 70: score -= 1
    if rsi[i] > 80: score -= 2

    strength = "🟢强势" if score>=5 else "🟡偏强" if score>=3 else "🔴偏弱" if score>=1 else "⚫弱势"

    # 价格位置
    bb_pos = (close-bb_l[i])/(bb_u[i]-bb_l[i])*100 if bb_u[i]!=bb_l[i] else 50
    bb_zone = "上轨附近" if bb_pos>70 else "下轨附近" if bb_pos<30 else "中轨附近"

    return {
        'name': name, 'code': code, 'date': date,
        'close': close, 'chg': (closes[i]-closes[i-2])/closes[i-2]*100 if i>=2 else 0,
        'ma5': ma5[i], 'ma10': ma10[i], 'ma20': ma20[i], 'ma60': ma60[i],
        'rsi': rsi[i], 'macd': macd[i], 'atr': atr[i],
        'bb_l': bb_l[i], 'bb_m': bb_m[i], 'bb_u': bb_u[i],
        'trend': trend, 'momentum': momentum, 'vol_ok': vol_ok,
        'buy_signal': buy_signal, 'sell_signal': sell_signal,
        'score': score, 'strength': strength, 'bb_pos': bb_pos, 'bb_zone': bb_zone
    }

def generate_message():
    stocks = [('300604','长川科技'), ('600183','生益科技')]
    results = []
    for code, name in stocks:
        r = check_signal(code, name)
        if r: results.append(r)

    lines = []
    lines.append("📊 每日量化策略信号")
    lines.append(f"推送时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    for r in results:
        chg_emoji = "🔴" if r['chg']>0 else "🟢"
        trend_emoji = "✅多头" if r['trend'] else "❌空头"
        buy = "🟢买入信号" if r['buy_signal'] else ""
        sell = "🔴卖出信号" if r['sell_signal'] else ""

        lines.append(f"【{r['name']} {r['code']}】{r['date']}")
        lines.append(f"  价格: {r['close']:.2f}元 {chg_emoji}{r['chg']:+.2f}%")
        lines.append(f"  强度: {r['strength']} (评分{r['score']}/6)")
        lines.append(f"  趋势: {trend_emoji} | 动量: {'✅' if r['momentum'] else '❌'}")
        lines.append(f"  均线: MA5={r['ma5']:.1f} MA10={r['ma10']:.1f} MA20={r['ma20']:.1f} MA60={r['ma60']:.1f}")
        lines.append(f"  RSI={r['rsi']:.1f} MACD={r['macd']:+.3f} ATR={r['atr']:.2f}")
        lines.append(f"  布林: {r['bb_l']:.1f}~{r['bb_m']:.1f}~{r['bb_u']:.1f} ({r['bb_zone']})")
        signal_text = ""
        if buy: signal_text += buy + " "
        if sell: signal_text += sell + " "
        if not buy and not sell: signal_text += "持有观察"
        lines.append(f"  信号: {signal_text.strip()}")
        lines.append("")

    lines.append("---")
    lines.append("📌 策略说明")
    lines.append("买入: 多头排列+MACD>0+RSI 40-75+量能放大")
    lines.append("止损: 跌破MA20 或 亏4%")
    lines.append("止盈: 涨20% 或 涨>10%后跌破MA10")
    lines.append("")
    lines.append("⚠️ 仅供参考，不构成投资建议")

    return "\n".join(lines)

if __name__ == '__main__':
    msg = generate_message()
    print(msg)