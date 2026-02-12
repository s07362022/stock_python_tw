# -*- coding: utf-8 -*-
"""
對比回測：美股大跌 vs 美股大漲後，隔天買台股的勝率
========================================================
2025 年至今資料，比較兩種策略：
1. 美股大跌後隔天買
2. 美股大漲後隔天買
標的：台達電、旺宏、聯電、廣達、鴻海
勝率定義：隔天開盤買入後，三天內有漲（最高價曾超過買入價）
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import os

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

US_TICKER = "QQQ"
# 台達電、旺宏、聯電、廣達、鴻海
TW_STOCKS = {
    "2308.TW": "台達電",
    "2337.TW": "旺宏",
    "2303.TW": "聯電",
    "2382.TW": "廣達",
    "2317.TW": "鴻海",
}
START_DATE = "2025-01-01"

THRESHOLD_CRASH = -1.0
THRESHOLD_SURGE = 1.0


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


def align_and_label(us: pd.DataFrame, tw: pd.DataFrame) -> pd.DataFrame:
    """
    隔天開盤買入，三天內有漲（最高價曾超過買入價）即為獲利
    """
    us = us[["Close"]].copy()
    us["us_ret"] = us["Close"].pct_change()

    tw = tw[["Open", "High", "Close"]].copy()
    common = us.index.intersection(tw.index).sort_values()
    result = []
    for i, d in enumerate(common):
        if i == 0 or i + 2 >= len(common):  # 需有往後 3 個交易日
            continue
        prev_d = common[i - 1]
        us_prev_ret = us.loc[prev_d, "us_ret"] if prev_d in us.index else np.nan
        if np.isnan(us_prev_ret):
            continue
        buy_price = tw.loc[d, "Open"]
        # 買入後 3 天內的最高價
        d1, d2, d3 = common[i], common[i + 1], common[i + 2]
        high_3d = max(
            tw.loc[d1, "High"] if d1 in tw.index else 0,
            tw.loc[d2, "High"] if d2 in tw.index else 0,
            tw.loc[d3, "High"] if d3 in tw.index else 0,
        )
        win = high_3d > buy_price
        ret_3d = (tw.loc[d3, "Close"] / buy_price - 1) * 100  # 持有 3 天報酬
        result.append({
            "date": d,
            "us_prev_ret": us_prev_ret * 100,
            "win": win,
            "ret_3d": ret_3d,
            "is_crash": us_prev_ret < THRESHOLD_CRASH / 100,
            "is_surge": us_prev_ret > THRESHOLD_SURGE / 100,
        })
    return pd.DataFrame(result)


def run_single(ticker: str, name: str, us: pd.DataFrame) -> dict:
    tw = fetch_tw_data(ticker)
    if tw.empty or "Open" not in tw.columns or "High" not in tw.columns:
        return None
    df = align_and_label(us, tw)
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
    """將表格繪製成圖並儲存到本地"""
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
    fig, ax = plt.subplots(figsize=(14, len(results) * 0.5 + 2))
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
    plt.title(f"美股大跌 vs 美股大漲後隔天買台股（{START_DATE} 至今）\n策略：隔天開盤買，3日內有漲即獲利", fontsize=12)
    plt.tight_layout()
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_result.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"\n圖表已儲存至: {out_path}")


def print_recommendations(results: list) -> None:
    """依回測結果輸出操作建議"""
    surge_better = [r["name"] for r in results if r["surge_avg"] > r["crash_avg"]]
    crash_better = [r["name"] for r in results if r["surge_avg"] <= r["crash_avg"]]
    print("\n" + "=" * 60)
    print("【操作建議】")
    print("=" * 60)
    print("\n一、美股大漲後隔天買入（跟漲）：")
    print(f"   標的：{', '.join(surge_better)}")
    print("   邏輯：美股強勢時，台股跟漲機率較高")
    print("\n二、美股大跌後隔天買入（抄底）：")
    print(f"   標的：{', '.join(crash_better)}")
    print("   邏輯：跌深反彈，大跌後買入報酬較佳")
    print("\n三、每日流程：")
    print(f"   1. 美股收盤後看 QQQ 漲跌 >±{THRESHOLD_SURGE}%")
    print("   2. 大漲 → 隔日開盤買入「跟漲」標的")
    print("   3. 大跌 → 隔日開盤買入「抄底」標的")
    print("   4. 持有 3 日內若有漲可考慮獲利了結")
    print("=" * 60)


def run() -> None:
    print("=" * 60)
    print("對比回測：美股大跌 vs 美股大漲後隔天買台股")
    print("=" * 60)
    print(f"\n期間：{START_DATE} 至今")
    print(f"美股大跌：跌幅 > {abs(THRESHOLD_CRASH)}%")
    print(f"美股大漲：漲幅 > {THRESHOLD_SURGE}%")
    print("策略：隔天開盤買，持有 3 日內有漲（最高價超過買入價）即為獲利\n")

    us = fetch_us_data()
    if us.empty:
        print("無法取得美股資料")
        return

    results = []
    for ticker, name in TW_STOCKS.items():
        r = run_single(ticker, name, us)
        if r:
            results.append(r)

    # 彙總表格
    print("【彙總表格】")
    print("-" * 95)
    print(f"{'標的':<12} | {'美股大跌後隔天買':<28} | {'美股大漲後隔天買':<28} | 較佳")
    print(f"{'':12} | {'次數 獲利 勝率% 均報酬%':<28} | {'次數 獲利 勝率% 均報酬%':<28} |")
    print("-" * 95)
    for r in results:
        crash_s = f"{r['crash_n']:3} {r['crash_wins']:3} {r['crash_wr']:5.1f} {r['crash_avg']:+6.2f}"
        surge_s = f"{r['surge_n']:3} {r['surge_wins']:3} {r['surge_wr']:5.1f} {r['surge_avg']:+6.2f}"
        # 較佳：以「持有3日均報酬」為準，報酬高者勝
        better = "大漲" if r["surge_avg"] > r["crash_avg"] else "大跌"
        print(f"{r['name']:<12} | {crash_s:<28} | {surge_s:<28} | {better}")
    print("=" * 95)

    # 儲存圖表到本地
    save_chart(results)

    # 輸出操作建議
    print_recommendations(results)


if __name__ == "__main__":
    run()
