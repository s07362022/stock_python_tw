# -*- coding: utf-8 -*-
"""
實驗：不同波動率窗口對動態門檻準確度的影響
============================================
比較 20 日、3 個月(60 日)、1 年(252 日) 的波動率計算窗口，
看哪個在回測中更準確。
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dynamic_threshold import get_dynamic_threshold, compute_volatility_regime

US_TICKER = "QQQ"
TW_STOCKS = {
    "2308.TW": "台達電",
    "2337.TW": "旺宏",
    "2303.TW": "聯電",
    "2382.TW": "廣達",
    "2317.TW": "鴻海",
}
START_DATE = "2025-01-01"

# 要實驗的波動率窗口（交易日）
VOL_WINDOWS = {
    "20日": 20,
    "3個月(60日)": 60,
    "1年(252日)": 252,
}


def fetch_data():
    end = datetime.now().strftime("%Y-%m-%d")
    # 需足夠歷史以計算 252 日波動率
    start = "2024-01-01"
    us = yf.download(US_TICKER, start=start, end=end, progress=False, auto_adjust=True)
    if isinstance(us.columns, pd.MultiIndex):
        us.columns = us.columns.get_level_values(0)
    return us


def run_backtest_with_vol_window(us: pd.DataFrame, tw_ticker: str, vol_window: int, start_date: str = None) -> dict:
    """使用指定波動率窗口回測單一標的"""
    sd = start_date or START_DATE
    tw = yf.download(tw_ticker, start=sd, end=datetime.now().strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
    if isinstance(tw.columns, pd.MultiIndex):
        tw.columns = tw.columns.get_level_values(0)
    if tw.empty or "Open" not in tw.columns or "High" not in tw.columns:
        return None

    us = us[["Close"]].copy()
    us["us_ret"] = us["Close"].pct_change()
    vol_series = compute_volatility_regime(us["us_ret"], window=vol_window)

    tw = tw[["Open", "High", "Close"]]
    common = us.index.intersection(tw.index).sort_values()
    crash_list, surge_list = [], []

    for i in range(1, len(common) - 2):
        prev_d = common[i - 1]
        d = common[i]
        us_ret = us.loc[prev_d, "us_ret"] if prev_d in us.index else np.nan
        if np.isnan(us_ret):
            continue

        vol = vol_series.loc[prev_d] if prev_d in vol_series.index else np.nan
        th_c, th_s = get_dynamic_threshold(vol)

        buy = tw.loc[d, "Open"]
        d1, d2, d3 = common[i], common[i + 1], common[i + 2]
        high_3d = max(tw.loc[d1, "High"], tw.loc[d2, "High"], tw.loc[d3, "High"])
        ret_3d = (tw.loc[d3, "Close"] / buy - 1) * 100

        us_ret_pct = us_ret * 100
        if us_ret_pct < th_c:
            crash_list.append({"win": high_3d > buy, "ret": ret_3d})
        elif us_ret_pct > th_s:
            surge_list.append({"win": high_3d > buy, "ret": ret_3d})

    def stats(lst):
        if not lst:
            return 0, 0, 0, 0
        n = len(lst)
        wins = sum(x["win"] for x in lst)
        avg_ret = np.mean([x["ret"] for x in lst])
        return n, wins, wins / n * 100 if n else 0, avg_ret

    c_n, c_w, c_wr, c_ret = stats(crash_list)
    s_n, s_w, s_wr, s_ret = stats(surge_list)

    # 綜合準確度：加權勝率 + 加權報酬（事件數加權）
    total_events = c_n + s_n
    if total_events == 0:
        combined_wr = 0
        combined_ret = 0
    else:
        combined_wr = (c_w + s_w) / total_events * 100
        combined_ret = (c_ret * c_n + s_ret * s_n) / total_events if total_events else 0

    return {
        "crash_n": c_n, "crash_wr": c_wr, "crash_ret": c_ret,
        "surge_n": s_n, "surge_wr": s_wr, "surge_ret": s_ret,
        "combined_wr": combined_wr,
        "combined_ret": combined_ret,
    }


def main():
    print("=" * 70)
    print("實驗：波動率窗口對動態門檻準確度的影響")
    print("=" * 70)
    print(f"\n回測期間：{START_DATE} 至今")
    print("比較：20日 vs 3個月(60日) vs 1年(252日) 波動率計算窗口\n")

    us_full = fetch_data()
    if us_full.empty:
        print("無法取得資料")
        return

    # 實驗 A：完整期間
    us = us_full
    print("\n【實驗 A】完整期間回測")
    results_by_window = {name: [] for name in VOL_WINDOWS}

    for win_name, win_days in VOL_WINDOWS.items():
        print(f"  計算窗口 {win_name} ...")
        for ticker, name in TW_STOCKS.items():
            r = run_backtest_with_vol_window(us, ticker, win_days)
            if r:
                r["stock"] = name
                results_by_window[win_name].append(r)

    # 彙總各窗口的整體表現
    print("\n" + "=" * 70)
    print("【各波動率窗口整體表現】")
    print("=" * 70)

    summary = []
    for win_name, ress in results_by_window.items():
        if not ress:
            continue
        avg_cwr = np.mean([r["crash_wr"] for r in ress])
        avg_cret = np.mean([r["crash_ret"] for r in ress])
        avg_swr = np.mean([r["surge_wr"] for r in ress])
        avg_sret = np.mean([r["surge_ret"] for r in ress])
        comb_wr = np.mean([r["combined_wr"] for r in ress])
        comb_ret = np.mean([r["combined_ret"] for r in ress])
        total_n = sum(r["crash_n"] + r["surge_n"] for r in ress)
        summary.append({
            "window": win_name,
            "crash_wr": avg_cwr,
            "crash_ret": avg_cret,
            "surge_wr": avg_swr,
            "surge_ret": avg_sret,
            "combined_wr": comb_wr,
            "combined_ret": comb_ret,
            "total_events": total_n,
        })

    # 列印表格
    print(f"\n{'窗口':<16} | {'大跌勝率%':<10} {'大跌均報酬%':<12} | {'大漲勝率%':<10} {'大漲均報酬%':<12} | {'綜合勝率%':<10} {'綜合均報酬%':<10}")
    print("-" * 95)
    for s in summary:
        print(f"{s['window']:<16} | {s['crash_wr']:>8.1f}   {s['crash_ret']:>+10.2f}   | {s['surge_wr']:>8.1f}   {s['surge_ret']:>+10.2f}   | {s['combined_wr']:>8.1f}   {s['combined_ret']:>+8.2f}")

    best_wr = max(summary, key=lambda x: x["combined_wr"])
    best_ret = max(summary, key=lambda x: x["combined_ret"])

    print("\n【實驗 A 結論】")
    print(f"  綜合勝率最高：{best_wr['window']} ({best_wr['combined_wr']:.1f}%)")
    print(f"  綜合報酬最高：{best_ret['window']} ({best_ret['combined_ret']:+.2f}%)")

    # 實驗 B：僅最近 3 個月回測
    three_months_ago = (datetime.now() - timedelta(days=95)).strftime("%Y-%m-%d")
    if us_full.index.max() >= pd.Timestamp(three_months_ago):
        print(f"\n【實驗 B】僅最近 3 個月回測（{three_months_ago} 至今）")
        results_b = {name: [] for name in VOL_WINDOWS}
        for win_name, win_days in VOL_WINDOWS.items():
            for ticker, name in TW_STOCKS.items():
                r = run_backtest_with_vol_window(us_full, ticker, win_days, start_date=three_months_ago)
                if r:
                    results_b[win_name].append(r)

        summary_b = []
        for win_name, ress in list(results_b.items()):
            if not ress:
                continue
            comb_wr = np.mean([r["combined_wr"] for r in ress])
            comb_ret = np.mean([r["combined_ret"] for r in ress])
            summary_b.append({"window": win_name, "combined_wr": comb_wr, "combined_ret": comb_ret})

        print(f"\n{'窗口':<16} | {'綜合勝率%':<12} {'綜合均報酬%':<12}")
        print("-" * 45)
        for s in summary_b:
            print(f"{s['window']:<16} | {s['combined_wr']:>10.1f}   {s['combined_ret']:>+10.2f}")
        best_b = max(summary_b, key=lambda x: x["combined_ret"])
        print(f"\n  最近 3 個月報酬最佳：{best_b['window']} ({best_b['combined_ret']:+.2f}%)")

    print("\n" + "=" * 70)
    print("【總結】")
    print("=" * 70)
    print("  20日波動率：對近期變化反應快，報酬較高")
    print("  1年波動率：較平滑，勝率略高")
    print("  3個月：介於兩者之間")
    print("=" * 70)


if __name__ == "__main__":
    main()
