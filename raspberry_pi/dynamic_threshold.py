# -*- coding: utf-8 -*-
"""
動態門檻 (Dynamic Thresholding) 模組
====================================
自適應能力：市場平靜時更敏銳（低門檻），市場波動大時更穩健（高門檻）
"""

import numpy as np
import pandas as pd
from typing import Tuple


def compute_volatility_regime(us_returns: pd.Series, window: int = 20) -> pd.Series:
    """
    計算滾動波動率（20 日報酬標準差，%）
    市場平靜時 std 小、暴風雨時 std 大
    us_returns 為小數（0.01 = 1%），輸出為百分比
    """
    return us_returns.rolling(window=window).std() * 100


def get_dynamic_threshold(
    vol_pct: float,
    base_low: float = 0.7,
    base_high: float = 1.8,
    vol_low: float = 0.6,
    vol_high: float = 1.4
) -> Tuple[float, float]:
    """
    依波動率動態計算大跌/大漲門檻
    ---------------------------------
    - 波動率低（市場平靜）：門檻較低，更敏銳
    - 波動率高（市場暴風雨）：門檻較高，更穩健

    :param vol_pct: 當前 20 日波動率（%）
    :return: (crash_threshold, surge_threshold) 皆為負數/正數的百分比
    """
    if np.isnan(vol_pct) or vol_pct <= 0:
        return -1.0, 1.0  # 預設

    # 線性插值：vol_low → base_low, vol_high → base_high
    if vol_pct <= vol_low:
        t = base_low
    elif vol_pct >= vol_high:
        t = base_high
    else:
        t = base_low + (base_high - base_low) * (vol_pct - vol_low) / (vol_high - vol_low)

    return -t, t


def apply_dynamic_threshold(
    us_df: pd.DataFrame,
    window: int = 20,
    base_low: float = 0.7,
    base_high: float = 1.8
) -> pd.DataFrame:
    """
    對美股資料加上每日動態門檻
    :param us_df: 含 Close 的 DataFrame
    :return: 加上 vol_20d, threshold_crash, threshold_surge 的 DataFrame
    """
    us = us_df[["Close"]].copy()
    us["us_ret"] = us["Close"].pct_change()  # 小數

    vol = compute_volatility_regime(us["us_ret"], window)  # %
    us["vol_20d"] = vol

    thresholds = [get_dynamic_threshold(v, base_low, base_high) for v in us["vol_20d"]]
    us["threshold_crash"] = [t[0] for t in thresholds]
    us["threshold_surge"] = [t[1] for t in thresholds]

    return us
