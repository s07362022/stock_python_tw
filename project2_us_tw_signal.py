# -*- coding: utf-8 -*-
"""
專案二：美股連動分析 - 台股上漲機率
====================================
1. 連接美股，取得與台股相關性高的科技股表現
2. 判斷美股是否有漲
3. 輸出建議：台股有機會漲的機率
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 與台股科技高度相關的美股（供應鏈、半導體、科技龍頭）
# 美股收盤早於台股，可作為領先指標
US_TECH_STOCKS = {
    "NVDA": "輝達",      # 與台積電高度相關
    "AAPL": "蘋果",      # 台積電大客戶
    "MSFT": "微軟",
    "AMD": "超微",       # 半導體，台積電客戶
    "TSM": "台積電ADR",  # 台積電美股，直接連動
    "QQQ": "那斯達克100",
    "SMH": "半導體ETF",
}

# 對應的台股科技股
TW_TECH_NAMES = "台積電、鴻海、聯發科、聯電、台達電、廣達、日月光、大立光、緯穎、瑞昱"


def fetch_us_tech_returns(lookback_days: int = 5) -> pd.DataFrame:
    """取得美股科技股近期報酬率"""
    end = datetime.now()
    start = end - timedelta(days=lookback_days + 15)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    result = {}
    for ticker, name in US_TECH_STOCKS.items():
        try:
            data = yf.download(ticker, start=start_str, end=end_str, progress=False, auto_adjust=True)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            if not data.empty and "Close" in data.columns and len(data) >= 2:
                ret_1d = data["Close"].pct_change().iloc[-1] * 100
                ret_5d = (data["Close"].iloc[-1] / data["Close"].iloc[-min(lookback_days + 1, len(data))] - 1) * 100 if len(data) > lookback_days else np.nan
                result[ticker] = {"name": name, "ret_1d_pct": ret_1d, "ret_5d_pct": ret_5d}
            else:
                result[ticker] = {"name": name, "ret_1d_pct": np.nan, "ret_5d_pct": np.nan}
        except Exception:
            result[ticker] = {"name": name, "ret_1d_pct": np.nan, "ret_5d_pct": np.nan}

    return pd.DataFrame(result).T


def calc_taiwan_rise_probability(us_df: pd.DataFrame) -> float:
    """
    依據美股表現計算「台股有機會漲」的機率
    美股科技漲 → 台股科技供應鏈有較高機率跟漲
    """
    valid = us_df.dropna(subset=["ret_1d_pct"])
    if valid.empty:
        return 0.5

    weights = {"TSM": 0.25, "NVDA": 0.20, "QQQ": 0.18, "AAPL": 0.15, "AMD": 0.12, "MSFT": 0.06, "SMH": 0.04}
    score = 0
    total_weight = 0
    for ticker, row in valid.iterrows():
        w = weights.get(ticker, 0.05)
        s = 1 if row["ret_1d_pct"] > 0 else (-1 if row["ret_1d_pct"] < 0 else 0)
        if not np.isnan(row.get("ret_5d_pct", np.nan)) and row["ret_5d_pct"] > 0:
            s += 0.5
        score += s * w
        total_weight += w

    if total_weight == 0:
        return 0.5
    prob = 0.5 + 0.4 * np.tanh(score)
    return float(np.clip(prob, 0.1, 0.9))


def run() -> None:
    """主流程：取得美股 → 判斷漲跌 → 輸出台股上漲機率"""
    print("=" * 55)
    print("專案二：美股連動分析 - 台股上漲機率")
    print("=" * 55)

    print("\n正在取得美股科技股近期表現...")
    us_df = fetch_us_tech_returns(lookback_days=5)

    print("\n【美股科技股表現】")
    print("-" * 50)
    for ticker, row in us_df.iterrows():
        r1 = row.get("ret_1d_pct", np.nan)
        r5 = row.get("ret_5d_pct", np.nan)
        s1 = f"{r1:+.2f}%" if not np.isnan(r1) else "N/A"
        s5 = f"{r5:+.2f}%" if not np.isnan(r5) else "N/A"
        print(f"  {row['name']:10s} ({ticker:5s})  近1日: {s1:>8s}  近5日: {s5:>8s}")

    prob = calc_taiwan_rise_probability(us_df)
    print("\n" + "=" * 55)
    print("【台股上漲機率建議】")
    print("=" * 55)
    print(f"\n  根據美股科技股近期表現，台股科技股有機會上漲的機率為：\n")
    print(f"  >>> {prob*100:.1f}% <<<\n")

    if prob >= 0.6:
        print("  建議：美股科技普遍上漲，台股科技供應鏈有較高機率跟漲，可關注。")
    elif prob <= 0.4:
        print("  建議：美股科技偏弱，台股短期跟漲機率較低，宜謹慎。")
    else:
        print("  建議：美股訊號中性，台股走勢需結合其他因素判斷。")

    print(f"\n  相關台股標的：{TW_TECH_NAMES}")
    print("=" * 55)


if __name__ == "__main__":
    run()
