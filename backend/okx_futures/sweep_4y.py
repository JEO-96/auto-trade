"""4년 BTC 파라미터 스윕 (최적화 버전)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pandas_ta as ta
import numpy as np

# BTC 데이터 로드
df = pd.read_csv('okx_data/BTC_1h.csv', index_col='timestamp', parse_dates=True)
print(f'BTC 1h: {len(df)} bars | {df.index[0].date()} ~ {df.index[-1].date()}')

# 지표 계산 (RSI 다이버전스 제외 — 속도 위해)
for length in [9, 21, 55, 200]:
    df[f"EMA_{length}"] = df.ta.ema(length=length)
df["RSI"] = df.ta.rsi(length=14)
macd_df = df.ta.macd(fast=12, slow=26, signal=9)
if macd_df is not None:
    df["MACD_hist"] = macd_df.iloc[:, 2]
bb_df = df.ta.bbands(length=20, std=2.0)
if bb_df is not None:
    bb_range = bb_df.iloc[:, 0] - bb_df.iloc[:, 2]
    df["BB_pctB"] = np.where(bb_range > 0, (df["close"] - bb_df.iloc[:, 2]) / bb_range, 0.5)
df["ATR"] = df.ta.atr(length=14)
adx_df = df.ta.adx(length=14)
if adx_df is not None:
    df["ADX"] = adx_df.iloc[:, 0]
    df["DMP"] = adx_df.iloc[:, 1]
    df["DMN"] = adx_df.iloc[:, 2]
stoch = df.ta.stochrsi(length=14, rsi_length=14, k=3, d=3)
if stoch is not None:
    df["STOCH_K"] = stoch.iloc[:, 0]
    df["STOCH_D"] = stoch.iloc[:, 1]
df["VOL_MA"] = df.ta.sma(close=df["volume"], length=20)

# 피보나치
highs = df["high"].rolling(50).max()
lows = df["low"].rolling(50).min()
diff = highs - lows
for lv in [0.382, 0.5, 0.618]:
    df[f"FIB_{lv}_support"] = highs - diff * lv
    df[f"FIB_{lv}_resist"] = lows + diff * lv

# 캔들/볼륨 사전계산
df["bullish"] = df["close"] > df["open"]
df["bearish"] = df["close"] < df["open"]
df["bull_3"] = df["bullish"].rolling(3).sum() >= 2
df["bear_3"] = df["bearish"].rolling(3).sum() >= 2
df["atr_pct"] = df["ATR"] / df["close"]

# 스코어 사전계산
def calc_scores(df):
    n = len(df)
    ls = np.zeros(n, dtype=int)
    ss = np.zeros(n, dtype=int)

    c = df
    for i in range(200, n):
        r = c.iloc[i]
        p = c.iloc[i-1]
        cl = r["close"]
        l, s = 0, 0

        e9,e21,e55 = r.get("EMA_9",np.nan), r.get("EMA_21",np.nan), r.get("EMA_55",np.nan)
        if not any(np.isnan(v) for v in [e9,e21,e55]):
            if e9>e21>e55: l+=1
            if e9<e21<e55: s+=1

        e200 = r.get("EMA_200",np.nan)
        if not np.isnan(e200):
            if cl>e200: l+=1
            if cl<e200: s+=1

        rsi = r.get("RSI",np.nan)
        if not np.isnan(rsi):
            if 30<rsi<60: l+=1
            if 40<rsi<70: s+=1

        mh = r.get("MACD_hist",np.nan)
        pmh = p.get("MACD_hist",np.nan)
        if not any(np.isnan(v) for v in [mh,pmh]):
            if (pmh<=0<mh) or (mh>0 and mh>pmh): l+=1
            if (pmh>=0>mh) or (mh<0 and mh<pmh): s+=1

        sk,sd = r.get("STOCH_K",np.nan), r.get("STOCH_D",np.nan)
        pk,pd_ = p.get("STOCH_K",np.nan), p.get("STOCH_D",np.nan)
        if not any(np.isnan(v) for v in [sk,sd,pk,pd_]):
            if pk<=pd_ and sk>sd and sk<80: l+=1
            if pk>=pd_ and sk<sd and sk>20: s+=1

        bb = r.get("BB_pctB",np.nan)
        if not np.isnan(bb):
            if bb<0.25: l+=1
            if bb>0.75: s+=1

        adx,dmp,dmn = r.get("ADX",np.nan), r.get("DMP",np.nan), r.get("DMN",np.nan)
        if not any(np.isnan(v) for v in [adx,dmp,dmn]):
            if dmp>dmn and adx>18: l+=1
            if dmn>dmp and adx>18: s+=1

        for lv in [0.618,0.5,0.382]:
            fs = r.get(f"FIB_{lv}_support",np.nan)
            if not np.isnan(fs) and abs(cl-fs)/cl<0.008:
                l+=1; break
        for lv in [0.618,0.5,0.382]:
            fr = r.get(f"FIB_{lv}_resist",np.nan)
            if not np.isnan(fr) and abs(cl-fr)/cl<0.008:
                s+=1; break

        vol,vma = r.get("volume",0), r.get("VOL_MA",np.nan)
        if not np.isnan(vma) and vma>0 and vol>vma*0.8:
            l+=1; s+=1

        ls[i]=l; ss[i]=s

    return ls, ss

print("스코어 계산 중...")
ls_arr, ss_arr = calc_scores(df)
df["LS"] = ls_arr
df["SS"] = ss_arr
print("스코어 계산 완료")

# 초고속 백테스트
vals = df[["close","high","low","open","ATR","EMA_200","atr_pct",
           "LS","SS","bullish","bearish","bull_3","bear_3"]].values
close_i,high_i,low_i,open_i,atr_i,ema200_i,atrp_i = 0,1,2,3,4,5,6
ls_i,ss_i,bull_i,bear_i,bull3_i,bear3_i = 7,8,9,10,11,12

def fast_bt(vals, thr, risk, sl_m, tp_m, lev=3):
    cap = 1000.0
    trades = []
    in_pos = False
    p_side = 0  # 1=long, -1=short
    p_entry = 0.0
    p_sl = 0.0
    p_tp = 0.0
    p_margin = 0.0
    cooldown = 0

    for i in range(200, len(vals)-1):
        v = vals[i]

        if cooldown > 0:
            cooldown -= 1

        if in_pos:
            ep = 0.0
            if p_side == 1:
                if v[low_i] <= p_sl: ep = p_sl
                elif v[high_i] >= p_tp: ep = p_tp
            else:
                if v[high_i] >= p_sl: ep = p_sl
                elif v[low_i] <= p_tp: ep = p_tp
            if ep > 0:
                pnl = ((ep-p_entry)/p_entry if p_side==1 else (p_entry-ep)/p_entry)
                net = p_margin*pnl*lev - p_margin*lev*0.0006*2
                cap += net
                trades.append(net)
                if pnl < 0: cooldown = 3
                in_pos = False

        if not in_pos and cooldown <= 0:
            ls = int(v[ls_i])
            ss = int(v[ss_i])
            ap = v[atrp_i]
            t = thr + (1 if not np.isnan(ap) and ap > 0.012 else 0)

            e200 = v[ema200_i]
            cl = v[close_i]

            sig = 0
            if ls >= t and ls > ss and v[bull_i] and v[bull3_i]:
                lt = t + (1 if not np.isnan(e200) and cl < e200 else 0)
                if ls >= lt: sig = 1
            elif ss >= t and ss > ls and v[bear_i] and v[bear3_i]:
                st = t + (1 if not np.isnan(e200) and cl > e200 else 0)
                if ss >= st: sig = -1

            if sig != 0 and cap > 10:
                atr = v[atr_i]
                if np.isnan(atr) or atr <= 0: atr = cl * 0.01
                sl_d = min(atr*sl_m, cl*0.025)
                tp_d = min(atr*tp_m, cl*0.08)
                tp_d = max(tp_d, cl*0.015)

                if sig == 1:
                    sl, tp = cl-sl_d, cl+tp_d
                else:
                    sl, tp = cl+sl_d, cl-tp_d

                sl_dist = abs(cl-sl)
                if sl_dist <= 0: continue
                ps = cap*risk/sl_dist
                m = (ps*cl)/lev
                if m > cap*0.9: m = cap*0.9

                in_pos = True
                p_side = sig
                p_entry = cl
                p_sl = sl
                p_tp = tp
                p_margin = m

    n = len(trades)
    if n < 10: return None
    wins = sum(1 for t in trades if t > 0)
    gp = sum(t for t in trades if t > 0)
    gl = abs(sum(t for t in trades if t <= 0)) or 1
    return (cap-1000)/10, wins/n*100, gp/gl, n, cap

# 스윕 실행
print("스윕 시작...")
results = []
for thr in [7, 8, 9]:
    for risk in [0.02, 0.03, 0.04, 0.05]:
        for sl in [1.5, 2.0, 2.5, 3.0]:
            for tp in [3.0, 4.0, 5.0, 6.0, 8.0]:
                r = fast_bt(vals, thr, risk, sl, tp)
                if r:
                    ret, wr, pf, n, cap = r
                    weeks = 1463/7
                    results.append({
                        'thr':thr,'risk':risk,'sl':sl,'tp':tp,
                        'ret':ret,'wk':ret/weeks,'wr':wr,'pf':pf,'n':n,'cap':cap
                    })

results.sort(key=lambda x: x['wk'], reverse=True)
print(f'\nBTC 4년 Top 20 / {len(results)}:')
print(f'{"Thr":>3} {"Risk":>5} {"SL":>4} {"TP":>4} | {"N":>4} {"WR%":>5} {"Wk%":>6} {"Tot%":>7} {"PF":>5} {"Cap":>8}')
print('-' * 65)
for r in results[:20]:
    print(f'{r["thr"]:>3} {r["risk"]:>5.2f} {r["sl"]:>4.1f} {r["tp"]:>4.1f} | '
          f'{r["n"]:>4} {r["wr"]:>5.1f} {r["wk"]:>6.3f} {r["ret"]:>7.1f} {r["pf"]:>5.2f} {r["cap"]:>8.1f}')
