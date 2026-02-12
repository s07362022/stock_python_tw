# -*- coding: utf-8 -*-
"""
對比回測：動態門檻版
====================
使用動態門檻 (Dynamic Thresholding)：市場平靜時更敏銳，暴風雨時更穩健
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import os
from dynamic_threshold import apply_dynamic_threshold, get_dynamic_threshold

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

US_TICKER = "QQQ"
TW_STOCKS = {
    "2308.TW": "台達電",
    "2337.TW": "旺宏",
    "2303.TW": "聯電",
    "2382.TW": "廣達",
    "2317.TW": "鴻海",
}
START_DATE = "2025-01-01"

# 動態門檻參數：平靜時 0.7%、暴風雨時 1.8%
BASE_LOW, BASE_HIGH = 0.7, 1.8
VOL_LOW, VOL_HIGH = 0.6, 1.4  # 波動率分界（%）


def fetch_us_data():
    end = datetime.now().strftime("%Y-%m-%d")
    us = yf.download(US_TICKER, start=START_DATE, end=end, progress=False, auto_adjust=True)
    if isinstance(us.columns, pd.MultiIndex):
        us.columns = us.columns.get_level_values(0)
    return us


def fetch_tw_data(ticker: str):
    end = datetime.now().strftime("%Y-%m-%d")
    tw = yf.download(ticker, start=START_DATE, end=end, progress=False, auto_adjust=True)
    if isinstance(tw.columns, pd.MultiIndex):
        tw.columns = tw.columns.get_level_values(0)
    return tw


def align_and_label_dynamic(us: pd.DataFrame, tw: pd.DataFrame) -> pd.DataFrame:
    """
    使用動態門檻：每日依 20 日波動率調整大跌/大漲判斷
    """
    us_enriched = apply_dynamic_threshold(us, window=20, base_low=BASE_LOW, base_high=BASE_HIGH)
    us_enriched["us_ret"] = us_enriched["Close"].pct_change()  # 小數

    tw = tw[["Open", "High", "Close"]].copy()
    common = us_enriched.index.intersection(tw.index).sort_values()
    result = []
    for i, d in enumerate(common):
        if i == 0 or i + 2 >= len(common):
            continue
        prev_d = common[i - 1]
        us_prev_ret = us_enriched.loc[prev_d, "us_ret"] if prev_d in us_enriched.index else np.nan
        if np.isnan(us_prev_ret):
            continue

        # 動態門檻：用 prev_d 當下的波動率
        vol = us_enriched.loc[prev_d, "vol_20d"] if prev_d in us_enriched.index else np.nan
        th_crash, th_surge = get_dynamic_threshold(vol, BASE_LOW, BASE_HIGH, VOL_LOW, VOL_HIGH)

        buy_price = tw.loc[d, "Open"]
        d1, d2, d3 = common[i], common[i + 1], common[i + 2]
        high_3d = max(
            tw.loc[d1, "High"] if d1 in tw.index else 0,
            tw.loc[d2, "High"] if d2 in tw.index else 0,
            tw.loc[d3, "High"] if d3 in tw.index else 0,
        )
        win = high_3d > buy_price
        ret_3d = (tw.loc[d3, "Close"] / buy_price - 1) * 100

        us_ret_pct = us_prev_ret * 100
        result.append({
            "date": d,
            "us_prev_ret": us_ret_pct,
            "vol_20d": vol,
            "th_crash": th_crash,
            "th_surge": th_surge,
            "win": win,
            "ret_3d": ret_3d,
            "is_crash": us_ret_pct < th_crash,
            "is_surge": us_ret_pct > th_surge,
        })
    return pd.DataFrame(result)


def run_single(ticker: str, name: str, us: pd.DataFrame) -> dict:
    tw = fetch_tw_data(ticker)
    if tw.empty or "Open" not in tw.columns or "High" not in tw.columns:
        return None
    df = align_and_label_dynamic(us, tw)
    if df.empty:
        return None
    crash_days = df[df["is_crash"]]
    surge_days = df[df["is_surge"]]

    def win_rate(sub):
        if sub.empty:
            return 0, 0, 0
        wins = sub["win"].sum()
        total = len(sub)
        return wins, total, wins / total * 100 if total > 0 else 0

    crash_w, crash_n, crash_wr = win_rate(crash_days)
    surge_w, surge_n, surge_wr = win_rate(surge_days)
    crash_avg = crash_days["ret_3d"].mean() if not crash_days.empty else 0
    surge_avg = surge_days["ret_3d"].mean() if not surge_days.empty else 0

    return {
        "name": name,
        "crash_n": crash_n, "crash_wins": crash_w, "crash_wr": crash_wr, "crash_avg": crash_avg,
        "surge_n": surge_n, "surge_wins": surge_w, "surge_wr": surge_wr, "surge_avg": surge_avg,
    }


def save_chart(results: list) -> None:
    if not results:
        return
    cols = ["標的", "大跌次數", "大跌獲利", "大跌勝率%", "大跌均報酬%", "大漲次數", "大漲獲利", "大漲勝率%", "大漲均報酬%", "較佳"]
    data = []
    for r in results:
        better = "大漲" if r["surge_avg"] > r["crash_avg"] else "大跌"
        data.append([
            r["name"], str(r["crash_n"]), str(r["crash_wins"]), f"{r['crash_wr']:.1f}", f"{r['crash_avg']:+.2f}",
            str(r["surge_n"]), str(r["surge_wins"]), f"{r['surge_wr']:.1f}", f"{r['surge_avg']:+.2f}", better
        ])
    fig, ax = plt.subplots(figsize=(14, len(results) * 0.5 + 3))
    ax.axis("off")
    table = ax.table(
        cellText=data,
        colLabels=cols,
        loc="center",
        cellLoc="center",
        colColours=["#4472C4"] * 10,
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    plt.title(
        f"動態門檻回測（{START_DATE} 至今）\n"
        f"門檻：市場平靜 0.7% / 暴風雨 1.8%，依 20 日波動率自適應",
        fontsize=12
    )
    plt.tight_layout()
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_dynamic_result.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"\n圖表已儲存至: {out_path}")


def print_recommendations(results: list) -> None:
    surge_better = [r["name"] for r in results if r["surge_avg"] > r["crash_avg"]]
    crash_better = [r["name"] for r in results if r["surge_avg"] <= r["crash_avg"]]
    print("\n" + "=" * 60)
    print("【操作建議（動態門檻）】")
    print("=" * 60)
    print("\n一、美股大漲後隔天買入：")
    print(f"   標的：{', '.join(surge_better)}")
    print("\n二、美股大跌後隔天買入：")
    print(f"   標的：{', '.join(crash_better)}")
    print("\n三、動態門檻說明：")
    print("   每日依 QQQ 過去 20 日波動率自動調整門檻")
    print("   - 波動低（<0.6%）：門檻 0.7%（更敏銳）")
    print("   - 波動高（>1.4%）：門檻 1.8%（更穩健）")
    print("=" * 60)


def run() -> None:
    print("=" * 60)
    print("對比回測：動態門檻（市場平靜更敏銳、暴風雨更穩健）")
    print("=" * 60)
    print(f"\n期間：{START_DATE} 至今")
    print("門檻：依 20 日波動率動態調整（0.7% ~ 1.8%）")
    print("策略：隔天開盤買，3 日內有漲即獲利\n")

    us = fetch_us_data()
    if us.empty:
        print("無法取得美股資料")
        return

    results = []
    for ticker, name in TW_STOCKS.items():
        r = run_single(ticker, name, us)
        if r:
            results.append(r)

    print("【彙總表格】")
    print("-" * 95)
    print(f"{'標的':<12} | {'美股大跌後隔天買':<28} | {'美股大漲後隔天買':<28} | 較佳")
    print("-" * 95)
    for r in results:
        crash_s = f"{r['crash_n']:3} {r['crash_wins']:3} {r['crash_wr']:5.1f} {r['crash_avg']:+6.2f}"
        surge_s = f"{r['surge_n']:3} {r['surge_wins']:3} {r['surge_wr']:5.1f} {r['surge_avg']:+6.2f}"
        better = "大漲" if r["surge_avg"] > r["crash_avg"] else "大跌"
        print(f"{r['name']:<12} | {crash_s:<28} | {surge_s:<28} | {better}")
    print("=" * 95)

    save_chart(results)
    print_recommendations(results)


if __name__ == "__main__":
    run()
