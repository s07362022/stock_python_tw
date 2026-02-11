# -*- coding: utf-8 -*-
"""
專案二：美股連動分析 - 台股漲幅機率
====================================
依據美股科技股表現，推估台股有機會上漲的機率。
美股與台股科技供應鏈高度相關，美股漲可作為台股跟漲的參考。
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import US_TECH_STOCKS, TECH_STOCKS


def fetch_us_tech_returns(lookback_days: int = 5) -> pd.DataFrame:
    """
    取得美股科技股近期報酬率
    """
    end = datetime.now()
    start = end - timedelta(days=lookback_days + 10)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    result = {}
    for ticker, name in US_TECH_STOCKS.items():
        try:
            data = yf.download(ticker, start=start_str, end=end_str, progress=False, auto_adjust=True)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            if not data.empty and "Close" in data.columns:
                ret_1d = data["Close"].pct_change().dropna().tail(lookback_days)
                ret_5d = (data["Close"].iloc[-1] / data["Close"].iloc[-lookback_days - 1] - 1) if len(data) > lookback_days else np.nan
                result[ticker] = {
                    "name": name,
                    "ret_1d_pct": ret_1d.iloc[-1] * 100 if len(ret_1d) > 0 else np.nan,
                    "ret_5d_pct": ret_5d * 100 if not np.isnan(ret_5d) else np.nan,
                    "up_days": (ret_1d > 0).sum() if len(ret_1d) > 0 else 0,
                    "total_days": len(ret_1d),
                }
        except Exception as e:
            result[ticker] = {"name": name, "ret_1d_pct": np.nan, "ret_5d_pct": np.nan, "up_days": 0, "total_days": 0, "error": str(e)}

    return pd.DataFrame(result).T


def calc_taiwan_rise_probability(us_df: pd.DataFrame) -> float:
    """
    依據美股表現計算「台股有機會漲」的機率
    ---------------------------------------
    邏輯：美股科技漲 → 台股科技供應鏈有較高機率跟漲
    參考歷史相關性與領先性，給予加權機率。
    """
    valid = us_df.dropna(subset=["ret_1d_pct"])
    if valid.empty:
        return 0.5  # 無資料時給 50%

    # 加權：TSM、NVDA、QQQ 與台股相關性最高
    weights = {
        "TSM": 0.25,   # 台積電 ADR 直接連動
        "NVDA": 0.20,  # 輝達與台積電供應鏈
        "QQQ": 0.18,   # 納斯達克大盤
        "AAPL": 0.15,
        "AMD": 0.12,
        "MSFT": 0.06,
        "SMH": 0.04,
    }
    total_weight = 0
    score = 0
    for ticker, row in valid.iterrows():
        w = weights.get(ticker, 0.05)
        # 1 日漲則 +1，跌則 -1；5 日漲則額外加分
        s = 1 if row["ret_1d_pct"] > 0 else (-1 if row["ret_1d_pct"] < 0 else 0)
        if "ret_5d_pct" in row and not np.isnan(row.get("ret_5d_pct", np.nan)) and row["ret_5d_pct"] > 0:
            s += 0.5
        score += s * w
        total_weight += w

    if total_weight == 0:
        return 0.5

    # score 範圍約 -1.5 ~ 1.5，轉成 0~100% 機率
    # 使用 sigmoid 形式：0.5 + 0.4 * tanh(score) → 約 10%~90%
    prob = 0.5 + 0.4 * np.tanh(score)
    return float(np.clip(prob, 0.1, 0.9))


def run_us_tw_signal() -> None:
    """
    主流程：取得美股表現 → 計算台股漲幅機率 → 列印建議
    """
    print("=" * 60)
    print("專案二：美股連動分析 - 台股上漲機率")
    print("=" * 60)

    print("\n取得美股科技股近期表現...")
    us_df = fetch_us_tech_returns(lookback_days=5)

    print("\n【美股科技股表現】")
    print("-" * 50)
    for ticker, row in us_df.iterrows():
        ret1 = row.get("ret_1d_pct", np.nan)
        ret5 = row.get("ret_5d_pct", np.nan)
        r1 = f"{ret1:+.2f}%" if not np.isnan(ret1) else "N/A"
        r5 = f"{ret5:+.2f}%" if not np.isnan(ret5) else "N/A"
        print(f"  {row['name']:8s} ({ticker:5s})  近1日: {r1:>8s}  近5日: {r5:>8s}")

    prob = calc_taiwan_rise_probability(us_df)
    print("\n" + "=" * 60)
    print("【台股上漲機率建議】")
    print("=" * 60)
    print(f"\n  根據美股科技股近期表現，台股科技股有機會上漲的機率為：")
    print(f"\n  >>> {prob*100:.1f}% <<<\n")

    if prob >= 0.6:
        print("  建議：美股科技普遍上漲，台股科技供應鏈有較高機率跟漲，可關注。")
    elif prob <= 0.4:
        print("  建議：美股科技偏弱，台股短期跟漲機率較低，宜謹慎。")
    else:
        print("  建議：美股訊號中性，台股走勢需結合其他因素判斷。")

    print("\n  相關台股標的：", ", ".join(TECH_STOCKS.values()))
    print("=" * 60)


if __name__ == "__main__":
    run_us_tw_signal()
