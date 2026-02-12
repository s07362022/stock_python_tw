# -*- coding: utf-8 -*-
"""
策略：自動量化交易機制 - 第一步
================================
收集「今日美股漲跌」→ 輸出「建議買入明日台股的機率」
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 美股科技指標股（與台股連動高）
US_STOCKS = {
    "NVDA": "輝達",
    "AAPL": "蘋果",
    "TSM": "台積電ADR",
    "AMD": "超微",
    "QQQ": "那斯達克100",
}


def get_us_today_performance() -> dict:
    """
    取得今日（最近交易日）美股漲跌
    :return: {"up_count": N, "down_count": M, "avg_chg_pct": float, "details": [...]}
    """
    end = datetime.now()
    start = end - timedelta(days=15)
    details = []
    for ticker, name in US_STOCKS.items():
        try:
            data = yf.download(ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            if not data.empty and len(data) >= 2:
                last = data.iloc[-1]["Close"]
                prev = data.iloc[-2]["Close"]
                chg_pct = (last / prev - 1) * 100
                details.append({"ticker": ticker, "name": name, "chg_pct": chg_pct})
        except Exception:
            pass

    df = pd.DataFrame(details)
    if df.empty:
        return {"up_count": 0, "down_count": 0, "avg_chg_pct": 0, "details": []}

    up = (df["chg_pct"] > 0).sum()
    down = (df["chg_pct"] < 0).sum()
    avg = df["chg_pct"].mean()
    return {"up_count": int(up), "down_count": int(down), "avg_chg_pct": avg, "details": df}


def calc_buy_tomorrow_probability(us_perf: dict) -> float:
    """
    依據今日美股漲跌，計算「建議買入明日台股」的機率
    參考歷史：美股漲時，次日台股上漲機率約 55-65%；美股跌時約 35-45%
    """
    up = us_perf["up_count"]
    down = us_perf["down_count"]
    avg_chg = us_perf["avg_chg_pct"]
    total = up + down
    if total == 0:
        return 0.5

    # 美股上漲比例
    up_ratio = up / total
    # 美股平均漲跌幅（正=漲、負=跌）
    # 綜合：上漲比例 + 平均漲跌 轉成 0.4~0.7 的基礎機率
    base = 0.5 + 0.15 * up_ratio - 0.15 * (1 - up_ratio)  # 全漲→0.65, 全跌→0.35
    adj = np.clip(avg_chg / 3, -0.1, 0.1)  # 漲跌幅微調
    prob = base + adj
    return float(np.clip(prob, 0.1, 0.9))


def run() -> None:
    print("=" * 55)
    print("策略：今日美股 → 明日台股買入機率")
    print("=" * 55)

    us = get_us_today_performance()
    if us["details"].empty:
        print("\n無法取得美股資料，請稍後再試。")
        return

    print("\n【今日美股漲跌】")
    print("-" * 50)
    for _, r in us["details"].iterrows():
        s = "漲" if r["chg_pct"] > 0 else "跌"
        print(f"  {r['name']:10s} ({r['ticker']:5s})  {s}  {r['chg_pct']:+.2f}%")
    print(f"\n  合計：{us['up_count']} 檔漲、{us['down_count']} 檔跌，均漲跌 {us['avg_chg_pct']:+.2f}%")

    prob = calc_buy_tomorrow_probability(us)
    print("\n" + "=" * 55)
    print("【建議買入明日台股的機率】")
    print("=" * 55)
    print(f"\n  >>> {prob*100:.1f}% <<<\n")

    if prob >= 0.6:
        print("  建議：可考慮明日逢低布局台股。")
    elif prob <= 0.4:
        print("  建議：明日宜觀望或謹慎，台股跟跌機率較高。")
    else:
        print("  建議：訊號中性，建議分批或觀望。")

    print("\n  （此機率依今日美股收盤表現推算，僅供參考，不構成投資建議）")
    print("=" * 55)


if __name__ == "__main__":
    run()
