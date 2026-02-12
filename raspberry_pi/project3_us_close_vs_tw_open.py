# -*- coding: utf-8 -*-
"""
專案三：昨晚美股收盤 vs 今天台股開盤
====================================
以「昨晚美股收盤」對比「今天台股開盤」的連動關係。
美股收盤時間早於台股開盤，可作為當天台股開盤的領先參考。
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 與台股相關的美股科技股
US_STOCKS = {
    "NVDA": "輝達",
    "AAPL": "蘋果",
    "TSM": "台積電ADR",
    "AMD": "超微",
    "QQQ": "那斯達克100",
}

# 對應台股
TW_STOCKS = {
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
}


def get_us_last_close() -> pd.DataFrame:
    """
    取得昨晚（最近一個交易日）美股收盤價與漲跌
    """
    end = datetime.now()
    start = end - timedelta(days=10)
    result = []
    for ticker, name in US_STOCKS.items():
        try:
            data = yf.download(ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            if not data.empty and len(data) >= 2:
                last = data.iloc[-1]
                prev = data.iloc[-2]
                close = last["Close"]
                chg_pct = (close / prev["Close"] - 1) * 100
                result.append({"ticker": ticker, "name": name, "close": close, "chg_pct": chg_pct})
        except Exception:
            pass
    return pd.DataFrame(result)


def get_tw_today_open() -> pd.DataFrame:
    """
    取得今天（或最近交易日）台股開盤價與漲跌
    """
    end = datetime.now()
    start = end - timedelta(days=10)
    result = []
    for ticker, name in TW_STOCKS.items():
        try:
            data = yf.download(ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            if not data.empty and "Open" in data.columns and len(data) >= 2:
                last = data.iloc[-1]
                prev = data.iloc[-2]
                open_price = last["Open"]
                prev_close = prev["Close"]
                chg_pct = (open_price / prev_close - 1) * 100  # 開盤相對前日收盤
                result.append({"ticker": ticker, "name": name, "open": open_price, "chg_pct": chg_pct})
        except Exception:
            pass
    return pd.DataFrame(result)


def run() -> None:
    print("=" * 55)
    print("專案三：昨晚美股收盤 vs 今天台股開盤")
    print("=" * 55)

    print("\n【昨晚美股收盤】")
    us_df = get_us_last_close()
    if us_df.empty:
        print("  無法取得美股資料")
    else:
        for _, r in us_df.iterrows():
            print(f"  {r['name']:10s} ({r['ticker']:5s})  收盤: {r['close']:,.2f}  漲跌: {r['chg_pct']:+.2f}%")

    print("\n【今天台股開盤】")
    tw_df = get_tw_today_open()
    if tw_df.empty:
        print("  無法取得台股資料")
    else:
        for _, r in tw_df.iterrows():
            print(f"  {r['name']:10s} ({r['ticker']:5s})  開盤: {r['open']:,.2f}  較前收: {r['chg_pct']:+.2f}%")

    if not us_df.empty and not tw_df.empty:
        us_up = (us_df["chg_pct"] > 0).sum() / len(us_df) * 100
        tw_up = (tw_df["chg_pct"] > 0).sum() / len(tw_df) * 100
        print("\n" + "=" * 55)
        print("【對比摘要】")
        print("=" * 55)
        print(f"  美股收紅比例: {us_up:.0f}% ({int(us_up/100*len(us_df))}/{len(us_df)} 檔)")
        print(f"  台股開高比例: {tw_up:.0f}% ({int(tw_up/100*len(tw_df))}/{len(tw_df)} 檔)")
        if us_up >= 60 and tw_up >= 60:
            print("\n  結論：美股昨晚收漲，台股今開同步開高，連動性佳。")
        elif us_up >= 60 and tw_up < 50:
            print("\n  結論：美股昨晚收漲，但台股今開偏弱，可留意後續走勢。")
        elif us_up < 50 and tw_up >= 60:
            print("\n  結論：美股昨晚偏弱，台股今開逆勢開高，屬相對強勢。")
        else:
            print("\n  結論：美股與台股開盤皆偏弱，宜謹慎。")
        print("=" * 55)


if __name__ == "__main__":
    run()
