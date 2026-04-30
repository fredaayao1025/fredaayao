#!/bin/bash
# ============================================
# 每日收盘自动化分析脚本
# 运行时间：工作日 15:35
# 功能：更新日线数据 → 技术分析 → 推送微信
# ============================================

WORKDIR="/vol2/@apphome/trim.openclaw/data/workspace"
DB="$WORKDIR/lgb_chanlun_fundamental.db"
LOG="$WORKDIR/logs/daily_analysis.log"
PYTHON="python3"
DONE_FILE="/tmp/daily_analysis_done_$(date +%Y%m%d)"

# 如果今天已经跑过就跳过（防止重复）
if [ -f "$DONE_FILE" ]; then
    echo "$(date) 今日已分析，跳过" >> $LOG
    exit 0
fi

echo "$(date) 开始每日分析..." >> $LOG

# ============================================
# Part 1: 用东方财富API更新日线数据入库
# ============================================
$PYTHON << PYEOF >> $LOG 2>&1
import duckdb, json, urllib.request, time

db = "/vol2/@apphome/trim.openclaw/data/workspace/lgb_chanlun_fundamental.db"
today = time.strftime("%Y%m%d")

# 拉东方财富日线数据（用curl更稳定）
import subprocess, re

def fetch_kline(secid, name):
    url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58&klt=101&fqt=1&beg={today}&end={today}&ut=fa5fd1943c7b386f172d6893dbfba10b"
    cmd = f'curl -s "{url}" -H "Referer:https://finance.eastmoney.com/" -A "Mozilla/5.0" --max-time 10'
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        klines = d.get('data', {}).get('klines', [])
        if klines:
            k = klines[0].split(',')
            return {
                'date': k[0], 'open': float(k[1]), 'close': float(k[2]),
                'high': float(k[3]), 'low': float(k[4]),
                'vol': float(k[5]), 'amount': float(k[6])
            }
    except: pass
    return None

# 股票列表（重点关注）
stocks = [
    ('300604', '长川科技', '0'),  # 深交所
    ('600183', '生益科技', '1'),  # 上交所
    ('000001', '平安银行', '0'),
    ('600519', '贵州茅台', '1'),
]

conn = duckdb.connect(db)
new_rows = 0
for code, name, market in stocks:
    secid = f"{market}.{code}"
    data = fetch_kline(secid, name)
    if data:
        # 查重
        exists = conn.execute(f"SELECT COUNT(*) FROM stock_daily WHERE stock_code='{code}' AND trade_date='{data['date']}'").fetchone()[0]
        if exists == 0:
            conn.execute(f"INSERT INTO stock_daily VALUES ('{code}','{data['date']}',{data['open']},{data['high']},{data['low']},{data['close']},{data['vol']},{data['amount']})")
            new_rows += 1
            print(f"  {name}({code}): {data['date']} 收{data['close']}")
        else:
            print(f"  {name}({code}): 已有数据")

conn.close()
print(f"入库完成: 新增{new_rows}条")
PYEOF

# ============================================
# Part 2: 技术分析
# ============================================
RESULT=$($PYTHON << 'PYEOF'
import duckdb, warnings, json
warnings.filterwarnings('ignore')
db = "/vol2/@apphome/trim.openclaw/data/workspace/lgb_chanlun_fundamental.db"
c = duckdb.connect(db)

def get_data(code, days=60):
    rows = c.execute(f"""
        SELECT trade_date, open, high, low, close, volume
        FROM stock_daily WHERE stock_code='{code}'
        ORDER BY trade_date DESC LIMIT {days}
    """).fetchall()
    return list(reversed(rows))

def calc_ma(prices, n):
    res = []
    for i in range(len(prices)):
        if i < n-1: res.append(None)
        else: res.append(sum(prices[i-n+1:i+1])/n)
    return res

def calc_macd(prices, fast=12, slow=26, signal=9):
    import numpy as np
    p = np.array(prices, dtype=float)
    ema_f = [p[0]]
    for x in p[1:]: ema_f.append(ema_f[-1]*2/(fast+1) + x*(fast-1)/(fast+1))
    ema_s = [p[0]]
    for x in p[1:]: ema_s.append(ema_s[-1]*2/(slow+1) + x*(slow-1)/(slow+1))
    dif = [f-s for f,s in zip(ema_f, ema_s)]
    dea = [dif[0]]
    for x in dif[1:]: dea.append(dea[-1]*2/(signal+1) + x*(signal-1)/(signal+1))
    macd = [(d-e)*2 for d,e in zip(dif, dea)]
    return dif, dea, macd

def calc_rsi(prices, n=14):
    import numpy as np
    p = np.array(prices, dtype=float)
    deltas = np.diff(p)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_g = [sum(gains[:n])/n]
    avg_l = [sum(losses[:n])/n]
    for i in range(n, len(deltas)):
        avg_g.append((avg_g[-1]*(n-1) + gains[i])/n)
        avg_l.append((avg_l[-1]*(n-1) + losses[i])/n)
    rsi = []
    for ag, al in zip(avg_g, avg_l):
        rsi.append(100 - 100/(1 + ag/al) if al > 0 else 100)
    return [None]*n + rsi

def analyze(code, name):
    rows = get_data(code)
    if not rows: return None
    dates = [r[0] for r in rows]
    closes = [float(r[4]) for r in rows]
    highs = [float(r[2]) for r in rows]
    lows = [float(r[3]) for r in rows]
    vols = [float(r[5])/1e4 for r in rows]
    c0, c1 = closes[-1], closes[-2]
    chg = (c0-c1)/c1*100
    ma5 = calc_ma(closes, 5); ma10 = calc_ma(closes, 10)
    ma20 = calc_ma(closes, 20); ma60 = calc_ma(closes, 60)
    dif, dea, macd = calc_macd(closes)
    rsi14 = calc_rsi(closes, 14)
    macd_hist = macd[-1]
    vol_ma5 = sum(vols[-5:])/5
    vol_ratio = vols[-1]/vol_ma5 if vol_ma5 else 0
    # KDJ简化
    import numpy as np
    low9 = np.min(lows[-9:]); high9 = np.max(highs[-9:])
    rsv = (closes[-1]-low9)/(high9-low9)*100 if high9!=low9 else 50
    k = rsv*1/3 + 50*2/3
    d = k*1/3 + 50*2/3
    j = 3*k - 2*d
    # 布林带
    ma20_arr = np.array(ma20[-20:])
    std = np.std(ma20_arr, ddof=0)
    boll_m = ma20[-1]; boll_u = boll_m+2*std; boll_l = boll_m-2*std
    # ATR
    trs = [max(h-l, abs(h-c2), abs(l-c2)) for h,l,c2 in zip(highs[1:],lows[1:],closes[:-1])]
    atr = sum(trs[-14:])/14 if len(trs)>=14 else 0
    # 评分
    score = sum([c0>ma20[-1] if ma20[-1] else 0, c0>ma60[-1] if ma60[-1] else 0,
        macd_hist>0, macd_hist>macd[-2], j<80, 30<rsi14[-1]<70, vol_ratio>1.0])
    state = "强势" if score>=5 else "中性偏强" if score>=4 else "中性偏弱"
    return {
        'name': name, 'code': code, 'date': dates[-1],
        'close': c0, 'chg': chg, 'high': highs[-1], 'low': lows[-1],
        'ma5': ma5[-1], 'ma10': ma10[-1], 'ma20': ma20[-1], 'ma60': ma60[-1],
        'dif': dif[-1], 'dea': dea[-1], 'macd': macd_hist,
        'rsi14': rsi14[-1], 'k': k, 'j': j,
        'boll_l': boll_l, 'boll_m': boll_m, 'boll_u': boll_u,
        'atr': atr, 'vol': vols[-1], 'vol_ma5': vol_ma5, 'vol_ratio': vol_ratio,
        'score': score, 'state': state,
        'above_ma20': c0>ma20[-1] if ma20[-1] else False,
        'above_ma60': c0>ma60[-1] if ma60[-1] else False,
        'macd_bull': macd_hist>0,
        'golden_cross': dif[-1]>dea[-1] and dif[-2]<=dea[-2],
    }

reports = []
for code, name in [('300604','长川科技'), ('600183','生益科技')]:
    a = analyze(code, name)
    if a: reports.append(a)

c.close()

for r in reports:
    print(f"=== {r['name']} {r['code']} ===")
    print(f"日期:{r['date']} 收盘:{r['close']:.2f} 涨跌:{r['chg']:+.2f}%")
    print(f"MA5:{r['ma5']:.1f} MA10:{r['ma10']:.1f} MA20:{r['ma20']:.1f} MA60:{r['ma60']:.1f}")
    print(f"MACD:DIF={r['dif']:.3f} DEA={r['dea']:.3f} 柱={r['macd']:.3f}")
    print(f"RSI14:{r['rsi14']:.1f} K:{r['k']:.1f} J:{r['j']:.1f}")
    print(f"布林:{r['boll_l']:.1f}~{r['boll_m']:.1f}~{r['boll_u']:.1f}")
    print(f"量:{r['vol']:.0f}万 均量:{r['vol_ma5']:.0f}万 {'放量' if r['vol_ratio']>1 else '缩量'}({r['vol_ratio']:.1f}x)")
    print(f"综合:{r['score']}/6 → {r['state']}")
    print(f"信号:{'✅' if r['above_ma20'] else '❌'}价>{'MA20' if r['above_ma20'] else '<MA20'} {'✅' if r['above_ma60'] else '❌'}价>{'MA60' if r['above_ma60'] else '<MA60'} {'✅金叉' if r['golden_cross'] else ''} {'🔴多头' if r['macd_bull'] else '🟢空头'}")
    print(f"支撑:MA5={r['ma5']:.1f} 压力:布林上轨={r['boll_u']:.1f}")
    print()

# 输出JSON供后续使用
print("JSON_START")
print(json.dumps(reports))
print("JSON_END")
PYEOF
)

# 提取JSON部分
JSON_DATA=$(echo "$RESULT" | sed -n '/JSON_START/,/JSON_END/p' | sed '1d;$d')

# ============================================
# Part 3: 生成微信消息并发送
# ============================================
$PYTHON << PYEOF
import json

try:
    reports = json.loads("""$JSON_DATA""")
except:
    print("JSON解析失败，跳过发送")
    exit(0)

from datetime import datetime
today_str = datetime.now().strftime("%Y-%m-%d")

msg = f"📊 每日个股分析 {today_str}\n\n"

for r in reports:
    emoji = "🔴" if r['chg'] > 0 else "🟢"
    rsi_state = "超买⚠️" if r['rsi14'] > 70 else "超卖" if r['rsi14'] < 30 else "正常"
    trend = "多头排列" if r['above_ma20'] and r['above_ma60'] else "部分多头" if r['above_ma20'] else "偏弱"

    msg += f"【{r['name']} {r['code']}】{r['date']}\n"
    msg += f"  收盘 {r['close']:.2f}元 {emoji}{r['chg']:+.2f}%\n"
    msg += f"  均线: MA5={r['ma5']:.1f} MA10={r['ma10']:.1f} MA20={r['ma20']:.1f}\n"
    msg += f"  MACD: {'🔴多头' if r['macd_bull'] else '🟢空头'} DIF={r['dif']:.2f} DEA={r['dea']:.2f}\n"
    msg += f"  RSI={r['rsi14']:.0f}({rsi_state}) | KDJ: K={r['k']:.0f} J={r['j']:.0f}\n"
    msg += f"  布林: {r['boll_l']:.0f}~{r['boll_m']:.0f}~{r['boll_u']:.0f}\n"
    msg += f"  量: {r['vol']:.0f}万 {'✅放量' if r['vol_ratio']>1 else '❌缩量'}\n"
    msg += f"  综合: {r['score']}/6 → {r['state']}\n"
    msg += f"  趋势: {trend}\n"
    msg += f"  支撑: {r['ma5']:.1f} / 压力: {r['boll_u']:.1f}\n"
    msg += "\n"

msg += "⚠️ 仅供参考，不构成投资建议 🦞"

print("MSG_START")
print(msg)
print("MSG_END")
PYEOF

# 标记完成
touch "$DONE_FILE"
echo "$(date) 分析完成" >> $LOG