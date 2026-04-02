"""BTC+ETH 4년 파라미터 스윕"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, pandas_ta as ta, numpy as np

coins = ['BTC', 'ETH']
prepped = {}

for coin in coins:
    df = pd.read_csv(f'okx_data/{coin}_1h.csv', index_col='timestamp', parse_dates=True)
    for l in [9,21,55,200]:
        df[f"EMA_{l}"] = df.ta.ema(length=l)
    df["RSI"] = df.ta.rsi(length=14)
    m = df.ta.macd(fast=12, slow=26, signal=9)
    if m is not None:
        df["MACD_hist"] = m.iloc[:, 2]
    bb = df.ta.bbands(length=20, std=2.0)
    if bb is not None:
        br = bb.iloc[:, 0] - bb.iloc[:, 2]
        df["BB_pctB"] = np.where(br > 0, (df["close"] - bb.iloc[:, 2]) / br, 0.5)
    df["ATR"] = df.ta.atr(length=14)
    adx = df.ta.adx(length=14)
    if adx is not None:
        df["ADX"] = adx.iloc[:, 0]
        df["DMP"] = adx.iloc[:, 1]
        df["DMN"] = adx.iloc[:, 2]
    st = df.ta.stochrsi(length=14, rsi_length=14, k=3, d=3)
    if st is not None:
        df["STOCH_K"] = st.iloc[:, 0]
        df["STOCH_D"] = st.iloc[:, 1]
    df["VOL_MA"] = df.ta.sma(close=df["volume"], length=20)
    hi = df["high"].rolling(50).max()
    lo = df["low"].rolling(50).min()
    di = hi - lo
    for lv in [0.382, 0.5, 0.618]:
        df[f"FIB_{lv}_support"] = hi - di * lv
        df[f"FIB_{lv}_resist"] = lo + di * lv
    df["bullish"] = df["close"] > df["open"]
    df["bearish"] = df["close"] < df["open"]
    df["bull_3"] = df["bullish"].rolling(3).sum() >= 2
    df["bear_3"] = df["bearish"].rolling(3).sum() >= 2
    df["atr_pct"] = df["ATR"] / df["close"]

    # 스코어 계산
    n = len(df)
    ls_arr = np.zeros(n, dtype=int)
    ss_arr = np.zeros(n, dtype=int)
    for i in range(200, n):
        r = df.iloc[i]
        p = df.iloc[i - 1]
        cl = r["close"]
        l_, s_ = 0, 0
        e9, e21, e55 = r.get("EMA_9", np.nan), r.get("EMA_21", np.nan), r.get("EMA_55", np.nan)
        if not any(np.isnan(v) for v in [e9, e21, e55]):
            if e9 > e21 > e55: l_ += 1
            if e9 < e21 < e55: s_ += 1
        e200 = r.get("EMA_200", np.nan)
        if not np.isnan(e200):
            if cl > e200: l_ += 1
            if cl < e200: s_ += 1
        rsi = r.get("RSI", np.nan)
        if not np.isnan(rsi):
            if 30 < rsi < 60: l_ += 1
            if 40 < rsi < 70: s_ += 1
        mh = r.get("MACD_hist", np.nan)
        pmh = p.get("MACD_hist", np.nan)
        if not any(np.isnan(v) for v in [mh, pmh]):
            if (pmh <= 0 < mh) or (mh > 0 and mh > pmh): l_ += 1
            if (pmh >= 0 > mh) or (mh < 0 and mh < pmh): s_ += 1
        sk = r.get("STOCH_K", np.nan)
        sd = r.get("STOCH_D", np.nan)
        pk = p.get("STOCH_K", np.nan)
        pd_ = p.get("STOCH_D", np.nan)
        if not any(np.isnan(v) for v in [sk, sd, pk, pd_]):
            if pk <= pd_ and sk > sd and sk < 80: l_ += 1
            if pk >= pd_ and sk < sd and sk > 20: s_ += 1
        bb_ = r.get("BB_pctB", np.nan)
        if not np.isnan(bb_):
            if bb_ < 0.25: l_ += 1
            if bb_ > 0.75: s_ += 1
        ax = r.get("ADX", np.nan)
        dm = r.get("DMP", np.nan)
        dn = r.get("DMN", np.nan)
        if not any(np.isnan(v) for v in [ax, dm, dn]):
            if dm > dn and ax > 18: l_ += 1
            if dn > dm and ax > 18: s_ += 1
        for lv in [0.618, 0.5, 0.382]:
            fs = r.get(f"FIB_{lv}_support", np.nan)
            if not np.isnan(fs) and abs(cl - fs) / cl < 0.008:
                l_ += 1
                break
        for lv in [0.618, 0.5, 0.382]:
            fr = r.get(f"FIB_{lv}_resist", np.nan)
            if not np.isnan(fr) and abs(cl - fr) / cl < 0.008:
                s_ += 1
                break
        vol = r.get("volume", 0)
        vma = r.get("VOL_MA", np.nan)
        if not np.isnan(vma) and vma > 0 and vol > vma * 0.8:
            l_ += 1
            s_ += 1
        ls_arr[i] = l_
        ss_arr[i] = s_
    df["LS"] = ls_arr
    df["SS"] = ss_arr
    prepped[coin] = df
    print(f"{coin}: {n} bars ready")

# 고속 백테스트
def fast_bt(prepped, thr, risk, sl_m, tp_m, max_pos=2, lev=3):
    cap = 1000.0
    trades = []
    positions = {}
    cooldowns = {c: 0 for c in coins}

    all_times = set()
    for c in coins:
        all_times.update(prepped[c].index[200:-1].tolist())
    timeline = sorted(all_times)

    for t in timeline:
        for coin in coins:
            df = prepped[coin]
            if t not in df.index:
                continue
            i = df.index.get_loc(t)
            if i < 200 or i >= len(df) - 1:
                continue
            r = df.iloc[i]

            if cooldowns[coin] > 0:
                cooldowns[coin] -= 1

            if coin in positions:
                p = positions[coin]
                ep = 0.0
                if p["s"] == 1:
                    if r["low"] <= p["sl"]: ep = p["sl"]
                    elif r["high"] >= p["tp"]: ep = p["tp"]
                else:
                    if r["high"] >= p["sl"]: ep = p["sl"]
                    elif r["low"] <= p["tp"]: ep = p["tp"]
                if ep > 0:
                    pnl = (ep - p["e"]) / p["e"] if p["s"] == 1 else (p["e"] - ep) / p["e"]
                    net = p["m"] * pnl * lev - p["m"] * lev * 0.0006 * 2
                    cap += net
                    trades.append(net)
                    if pnl < 0:
                        cooldowns[coin] = 3
                    del positions[coin]

            if coin not in positions and len(positions) < max_pos and cooldowns[coin] <= 0:
                ls = int(r["LS"])
                ss = int(r["SS"])
                ap = r["atr_pct"]
                th = thr + (1 if not np.isnan(ap) and ap > 0.012 else 0)
                e200 = r["EMA_200"]
                cl = r["close"]

                sig = 0
                if ls >= th and ls > ss and r["bullish"] and r["bull_3"]:
                    lt = th + (1 if not np.isnan(e200) and cl < e200 else 0)
                    if ls >= lt: sig = 1
                elif ss >= th and ss > ls and r["bearish"] and r["bear_3"]:
                    st = th + (1 if not np.isnan(e200) and cl > e200 else 0)
                    if ss >= st: sig = -1

                if sig != 0 and cap > 10:
                    atr = r["ATR"]
                    if np.isnan(atr) or atr <= 0:
                        atr = cl * 0.01
                    sl_d = min(atr * sl_m, cl * 0.025)
                    tp_d = min(atr * tp_m, cl * 0.12)
                    tp_d = max(tp_d, cl * 0.015)
                    if sig == 1:
                        sl, tp = cl - sl_d, cl + tp_d
                    else:
                        sl, tp = cl + sl_d, cl - tp_d
                    sl_dist = abs(cl - sl)
                    if sl_dist <= 0:
                        continue
                    alloc = cap / (max_pos - len(positions))
                    ps = alloc * risk / sl_dist
                    m = (ps * cl) / lev
                    if m > alloc * 0.9:
                        m = alloc * 0.9
                    positions[coin] = {"s": sig, "e": cl, "sl": sl, "tp": tp, "m": m}

    n = len(trades)
    if n < 5:
        return None
    wins = sum(1 for t in trades if t > 0)
    gp = sum(t for t in trades if t > 0)
    gl = abs(sum(t for t in trades if t <= 0)) or 1
    weeks = 1463 / 7
    ret = (cap - 1000) / 10
    return {"ret": ret, "wk": ret / weeks, "wr": wins / n * 100, "pf": gp / gl, "n": n, "cap": cap}


print("\nBTC+ETH sweep...")
results = []
for thr in [7, 8, 9]:
    for risk in [0.02, 0.03, 0.04, 0.05]:
        for sl in [1.5, 2.0, 2.5, 3.0]:
            for tp in [3.0, 4.0, 5.0, 6.0, 8.0]:
                r = fast_bt(prepped, thr, risk, sl, tp)
                if r:
                    r.update({"thr": thr, "risk": risk, "sl": sl, "tp": tp})
                    results.append(r)

results.sort(key=lambda x: x["wk"], reverse=True)
print(f"\nBTC+ETH 4yr Top 20 / {len(results)}:")
print(f'{"Thr":>3} {"Risk":>5} {"SL":>4} {"TP":>4} | {"N":>4} {"WR%":>5} {"Wk%":>6} {"Tot%":>7} {"PF":>5} {"Cap":>8}')
print("-" * 65)
for r in results[:20]:
    print(
        f'{r["thr"]:>3} {r["risk"]:>5.2f} {r["sl"]:>4.1f} {r["tp"]:>4.1f} | '
        f'{r["n"]:>4} {r["wr"]:>5.1f} {r["wk"]:>6.3f} {r["ret"]:>7.1f} {r["pf"]:>5.2f} {r["cap"]:>8.1f}'
    )
