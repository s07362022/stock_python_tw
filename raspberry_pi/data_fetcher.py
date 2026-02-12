# -*- coding: utf-8 -*-
"""
資料取得模組 - 使用 yfinance 下載台股資料
"""

import yfinance as yf
import pandas as pd
from typing import Optional
from config import TECH_STOCKS, START_DATE, END_DATE


def fetch_stock(ticker: str, start: str = START_DATE, end: str = END_DATE) -> pd.DataFrame:
    """
    取得單一股票 OHLCV 資料
    :param ticker: Yahoo Finance 股票代碼，如 2330.TW
    :param start: 開始日期
    :param end: 結束日期
    :return: 含 Open, High, Low, Close, Volume 的 DataFrame
    """
    data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data


def fetch_all_stocks(start: str = START_DATE, end: str = END_DATE) -> dict[str, pd.DataFrame]:
    """
    取得所有前十大科技股資料
    :return: {ticker: DataFrame} 字典
    """
    result = {}
    for ticker, name in TECH_STOCKS.items():
        df = fetch_stock(ticker, start, end)
        if not df.empty:
            result[ticker] = df
    return result
