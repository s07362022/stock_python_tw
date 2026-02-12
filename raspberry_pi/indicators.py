# -*- coding: utf-8 -*-
"""
技術指標模組 - 股市分析常用指標
========================================
本模組實作金融界廣泛使用的技術分析指標，
參考 TA-Lib、pandas-ta 等主流套件的計算方式。
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple


# =============================================================================
# 一、均線類 (Moving Averages)
# =============================================================================

def sma(series: pd.Series, period: int = 20) -> pd.Series:
    """
    簡單移動平均線 (Simple Moving Average, SMA)
    ----------------------------------------
    用途：判斷趨勢方向，價格在均線上為多頭、下為空頭。
    公式：SMA = (P1 + P2 + ... + Pn) / n
    常用週期：5(短)、20(中)、60(長)
    """
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int = 12) -> pd.Series:
    """
    指數移動平均線 (Exponential Moving Average, EMA)
    -----------------------------------------------
    用途：較 SMA 更重視近期價格，對價格變化反應更靈敏。
    公式：EMA_today = α × Price_today + (1-α) × EMA_yesterday
          α = 2 / (period + 1)
    常用週期：12、26（常與 MACD 搭配）
    """
    return series.ewm(span=period, adjust=False).mean()


def wma(series: pd.Series, period: int = 20) -> pd.Series:
    """
    加權移動平均線 (Weighted Moving Average, WMA)
    -------------------------------------------
    用途：對近期價格賦予更高權重，比 SMA 更敏感。
    公式：WMA = (P1×1 + P2×2 + ... + Pn×n) / (1+2+...+n)
    """
    weights = np.arange(1, period + 1)
    return series.rolling(window=period).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


# =============================================================================
# 二、動能指標 (Momentum Indicators)
# =============================================================================

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    相對強弱指標 (Relative Strength Index, RSI)
    ----------------------------------------
    用途：衡量買賣力道，判斷超買(>70)、超賣(<30)。
    公式：RSI = 100 - 100/(1 + RS)，RS = 平均漲幅 / 平均跌幅
    解讀：>70 超買、<30 超賣、50 附近為多空均衡
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.inf)
    return 100 - (100 / (1 + rs))


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    指數平滑異同移動平均線 (MACD)
    ----------------------------
    用途：趨勢追蹤與轉折訊號，金叉買入、死叉賣出。
    公式：
        DIF = EMA(fast) - EMA(slow)
        DEA = EMA(DIF, signal)
        MACD柱 = (DIF - DEA) × 2
    解讀：DIF 上穿 DEA 為金叉(多)、下穿為死叉(空)
    """
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    dif = ema_fast - ema_slow
    dea = ema(dif, signal)
    macd_hist = (dif - dea) * 2
    return dif, dea, macd_hist


def stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """
    隨機指標 / KD 指標 (Stochastic Oscillator)
    ----------------------------------------
    用途：判斷超買超賣，K 上穿 D 為買入訊號。
    公式：
        %K = (C - L14) / (H14 - L14) × 100
        %D = SMA(%K, 3)
    L14/H14 為 14 日內最低/最高價
    解讀：K>80 超買、K<20 超賣
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = k.rolling(window=d_period).mean()
    return k, d


def roc(series: pd.Series, period: int = 12) -> pd.Series:
    """
    變動率 (Rate of Change, ROC)
    ---------------------------
    用途：衡量價格變動速度，正負值表示趨勢方向。
    公式：ROC = (今日收盤 - N日前收盤) / N日前收盤 × 100
    """
    return series.pct_change(periods=period) * 100


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    威廉指標 (Williams %R)
    --------------------
    用途：與 RSI 類似，判斷超買超賣，但刻度相反。
    公式：%R = (H14 - C) / (H14 - L14) × (-100)
    解讀：> -20 超買、< -80 超賣
    """
    highest = high.rolling(window=period).max()
    lowest = low.rolling(window=period).min()
    return -100 * (highest - close) / (highest - lowest).replace(0, np.nan)


# =============================================================================
# 三、波動率指標 (Volatility Indicators)
# =============================================================================

def bollinger_bands(
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    布林通道 (Bollinger Bands)
    ------------------------
    用途：衡量波動率，價格觸及上軌可能回檔、下軌可能反彈。
    公式：
        中軌 = SMA(close, 20)
        上軌 = 中軌 + k × 標準差
        下軌 = 中軌 - k × 標準差
    常用：k=2，period=20
    """
    middle = sma(series, period)
    std = series.rolling(window=period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return upper, middle, lower


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    平均真實波幅 (Average True Range, ATR)
    ------------------------------------
    用途：衡量波動程度，用於設定停損、評估風險。
    公式：TR = max(H-L, |H-PC|, |L-PC|)，ATR = EMA(TR)
    PC = 前一日收盤
    """
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# =============================================================================
# 四、成交量指標 (Volume Indicators)
# =============================================================================

def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    能量潮 (On Balance Volume, OBV)
    ------------------------------
    用途：量價關係，OBV 上升表示買盤積極。
    公式：收盤漲則 OBV += 成交量，跌則 OBV -= 成交量
    """
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    return (direction * volume).cumsum()


def mfi(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    資金流量指標 (Money Flow Index, MFI)
    ----------------------------------
    用途：結合價格與成交量，稱為「加權 RSI」。
    公式：典型價 = (H+L+C)/3，資金流 = 典型價 × 成交量
         MFI = 100 - 100/(1 + 正資金流總和/負資金流總和)
    解讀：>80 超買、<20 超賣
    """
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    delta = typical_price.diff()
    pos_flow = money_flow.where(delta > 0, 0).rolling(window=period).sum()
    neg_flow = money_flow.where(delta < 0, 0).rolling(window=period).sum()
    mfi_ratio = pos_flow / neg_flow.replace(0, np.nan)
    return 100 - (100 / (1 + mfi_ratio))


# =============================================================================
# 五、趨勢指標 (Trend Indicators)
# =============================================================================

def cci(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 20
) -> pd.Series:
    """
    順勢指標 (Commodity Channel Index, CCI)
    -------------------------------------
    用途：偏離均值的程度，判斷超買超賣。
    公式：CCI = (典型價 - SMA典型價) / (0.015 × MD)
         MD = 平均絕對偏差
    解讀：>100 超買、<-100 超賣
    """
    typical = (high + low + close) / 3
    sma_tp = typical.rolling(window=period).mean()
    mad = typical.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (typical - sma_tp) / (0.015 * mad.replace(0, np.nan))


def adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    平均趨向指標 (Average Directional Index, ADX)
    -------------------------------------------
    用途：衡量趨勢強度，不判斷方向。ADX>25 表示趨勢明顯。
    公式：+DM、-DM、TR → +DI、-DI → DX → ADX = EMA(DX)
    解讀：ADX 上升 = 趨勢增強；+DI>-DI 多頭、反之空頭
    """
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

    tr = atr(high, low, close, 1)  # period=1 即 TR 本身

    atr_smooth = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr_smooth)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr_smooth)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_val = dx.ewm(span=period, adjust=False).mean()

    return plus_di, minus_di, adx_val


# =============================================================================
# 六、整合函式：一次計算所有技術指標
# =============================================================================

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    將所有技術指標加入 DataFrame
    --------------------------
    輸入：含 Open, High, Low, Close, Volume 的 OHLCV DataFrame
    輸出：加上各技術指標欄位的 DataFrame
    """
    result = df.copy()
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    v = df["Volume"] if "Volume" in df.columns else pd.Series(0, index=df.index)

    # 均線
    result["SMA_5"] = sma(c, 5)
    result["SMA_20"] = sma(c, 20)
    result["SMA_60"] = sma(c, 60)
    result["EMA_12"] = ema(c, 12)
    result["EMA_26"] = ema(c, 26)

    # 動能
    result["RSI_14"] = rsi(c, 14)
    dif, dea, macd_hist = macd(c, 12, 26, 9)
    result["MACD_DIF"] = dif
    result["MACD_DEA"] = dea
    result["MACD_Hist"] = macd_hist
    result["Stoch_K"], result["Stoch_D"] = stochastic(h, l, c, 14, 3)
    result["ROC_12"] = roc(c, 12)
    result["Williams_R"] = williams_r(h, l, c, 14)

    # 波動率
    result["BB_Upper"], result["BB_Middle"], result["BB_Lower"] = bollinger_bands(c, 20, 2)
    result["ATR_14"] = atr(h, l, c, 14)

    # 成交量
    result["OBV"] = obv(c, v)
    result["MFI_14"] = mfi(h, l, c, v, 14)

    # 趨勢
    result["CCI_20"] = cci(h, l, c, 20)
    result["ADX_Plus"], result["ADX_Minus"], result["ADX_14"] = adx(h, l, c, 14)

    return result
