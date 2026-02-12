# -*- coding: utf-8 -*-
"""
策略歷史統計 - 大跌買/大漲買/平盤買
====================================
依歷史回測產出各標的的策略建議表，
含 0050、0052 在平盤時的建議（買 ETF 或觀望）
"""

import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dynamic_threshold import apply_dynamic_threshold, get_dynamic_threshold

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

US_TICKER = "QQQ"
# 回測區間：往後 3 個月（依執行日動態計算）
BASE_LOW, BASE_HIGH = 0.7, 1.8
VOL_LOW, VOL_HIGH = 0.6, 1.4

# 含 0050、0052、個股
ALL_STOCKS = {
    "0050.TW": "元大台灣50",
    "0052.TW": "富邦科技",
    "2308.TW": "台達電",
    "2337.TW": "旺宏",
    "2303.TW": "聯電",
    "2382.TW": "廣達",
    "2317.TW": "鴻海",
}


def fetch_and_backtest() -> dict:
    """取得歷史回測（最近 3 個月）：大跌買、大漲買、平盤買的勝率與均報酬"""
    return _fetch_and_backtest_by_days(95)


def get_flat_etf_recommendation(stats: dict) -> tuple[str, str]:
    """
    依 0050、0052 平盤歷史表現給建議
    :return: (建議文字, 簡短結論)
    """
    etf_stats = {k: v for k, v in stats.items() if k in ["元大台灣50", "富邦科技"]}
    if not etf_stats:
        return "無 0050/0052 平盤歷史資料。", "觀望"

    avg_flat_ret = np.mean([v["flat_ret"] for v in etf_stats.values()])
    avg_flat_wr = np.mean([v["flat_wr"] for v in etf_stats.values()])
    flat_n = list(etf_stats.values())[0]["flat_n"]

    if flat_n < 5:
        return "平盤樣本數不足，無法給出可靠建議。", "觀望"

    if avg_flat_ret > 0.1 and avg_flat_wr >= 50:
        detail = f"歷史平盤日 {flat_n} 次，0050/0052 平均勝率 {avg_flat_wr:.0f}%，均報酬 +{avg_flat_ret:.2f}%"
        return f"可考慮買入 0050 或 0052。（{detail}）", "可買ETF"
    else:
        detail = f"歷史平盤日 {flat_n} 次，0050/0052 平均勝率 {avg_flat_wr:.0f}%，均報酬 {avg_flat_ret:+.2f}%"
        return f"建議觀望，不宜買入。（{detail}）", "不買"


# 大跌/大漲均報酬差異門檻：若差不到此值，兩者皆推薦
RET_DIFF_THRESHOLD = 0.5


def get_combined_recommendation(stats_3m: dict, stats_6m: dict) -> tuple[list[str], list[str], list[str], list[str]]:
    """
    3 個月建議優先，另提供 3 個月與半年交集建議
    若大跌買與大漲買均報酬差不到 0.5%，則兩者皆推薦
    :param stats_3m: 3 個月回測結果
    :param stats_6m: 半年回測結果
    :return: (crash_3m, surge_3m, crash_intersection, surge_intersection)
    """
    def suggest_crash(s: dict) -> bool:
        return s["crash_ret"] > s["surge_ret"]

    def diff_small(s: dict) -> bool:
        return abs(s["crash_ret"] - s["surge_ret"]) < RET_DIFF_THRESHOLD

    crash_3m, surge_3m = [], []
    for name, s in stats_3m.items():
        if diff_small(s):
            crash_3m.append(name)
            surge_3m.append(name)
        elif suggest_crash(s):
            crash_3m.append(name)
        else:
            surge_3m.append(name)

    crash_intersection, surge_intersection = [], []
    common_names = set(stats_3m.keys()) & set(stats_6m.keys())
    for name in common_names:
        s3, s6 = stats_3m[name], stats_6m[name]
        both_close_3 = diff_small(s3)
        both_close_6 = diff_small(s6)
        if both_close_3 or both_close_6:
            # 任一期間差不到 0.5%，兩者皆推薦
            crash_intersection.append(name)
            surge_intersection.append(name)
        elif suggest_crash(s3) and suggest_crash(s6):
            crash_intersection.append(name)
        elif not suggest_crash(s3) and not suggest_crash(s6):
            surge_intersection.append(name)

    return crash_3m, surge_3m, crash_intersection, surge_intersection


def get_strategy_table(stats: dict) -> str:
    """產出策略表文字"""
    lines = []
    lines.append(f"{'標的':<12} | {'大跌買':<18} | {'大漲買':<18} | {'平盤買':<18} | 建議")
    lines.append("-" * 85)
    for name, s in stats.items():
        crash_s = f"{s['crash_n']:2}次 {s['crash_wr']:4.0f}% {s['crash_ret']:+.2f}%"
        surge_s = f"{s['surge_n']:2}次 {s['surge_wr']:4.0f}% {s['surge_ret']:+.2f}%"
        flat_s = f"{s['flat_n']:2}次 {s['flat_wr']:4.0f}% {s['flat_ret']:+.2f}%"
        better = "大跌" if s["crash_ret"] > s["surge_ret"] else "大漲"
        lines.append(f"{name:<12} | {crash_s:<18} | {surge_s:<18} | {flat_s:<18} | {better}買")
    return "\n".join(lines)


def fetch_and_backtest_6m() -> dict:
    """取得過去半年歷史回測：大跌買、大漲買、平盤買"""
    return _fetch_and_backtest_by_days(185)  # 約 6 個月


def fetch_and_backtest_10d() -> dict:
    """
    取得 10 日持有回測：大跌買、大漲買、平盤買
    勝率＝10 日內最高價曾超過買入價；均報酬＝持有至第 10 日收盤的報酬
    """
    return _fetch_and_backtest_hold_days(95, hold_days=10)


def get_strategy_table_10d(stats: dict) -> str:
    """產出 10 日持有策略表文字"""
    lines = []
    lines.append(f"{'標的':<12} | {'大跌買(10日)':<20} | {'大漲買(10日)':<20} | {'平盤買(10日)':<20} | 建議")
    lines.append("-" * 95)
    for name, s in stats.items():
        crash_s = f"{s['crash_n']:2}次 {s['crash_wr']:4.0f}% {s['crash_ret']:+.2f}%"
        surge_s = f"{s['surge_n']:2}次 {s['surge_wr']:4.0f}% {s['surge_ret']:+.2f}%"
        flat_s = f"{s['flat_n']:2}次 {s['flat_wr']:4.0f}% {s['flat_ret']:+.2f}%"
        better = "大跌" if s["crash_ret"] > s["surge_ret"] else "大漲"
        lines.append(f"{name:<12} | {crash_s:<20} | {surge_s:<20} | {flat_s:<20} | {better}買")
    return "\n".join(lines)


def _fetch_and_backtest_by_days(days: int) -> dict:
    """依指定天數取得回測統計"""
    end = datetime.now()
    start = (end - timedelta(days=days)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    us = yf.download(US_TICKER, start="2024-01-01", end=end_str, progress=False, auto_adjust=True)
    if isinstance(us.columns, pd.MultiIndex):
        us.columns = us.columns.get_level_values(0)
    if us.empty or len(us) < 30:
        return {}

    us_e = apply_dynamic_threshold(us, 20, BASE_LOW, BASE_HIGH)
    us_e["us_ret"] = us_e["Close"].pct_change()

    results = {}
    for ticker, name in ALL_STOCKS.items():
        tw = yf.download(ticker, start=start, end=end_str, progress=False, auto_adjust=True)
        if isinstance(tw.columns, pd.MultiIndex):
            tw.columns = tw.columns.get_level_values(0)
        if tw.empty or "Open" not in tw.columns or "High" not in tw.columns:
            continue

        tw = tw[["Open", "High", "Close"]]
        common = us_e.index.intersection(tw.index).sort_values()
        crash_list, surge_list, flat_list = [], [], []

        for i in range(1, len(common) - 2):
            prev_d = common[i - 1]
            d = common[i]
            us_ret = us_e.loc[prev_d, "us_ret"] if prev_d in us_e.index else np.nan
            if np.isnan(us_ret):
                continue

            vol = us_e.loc[prev_d, "vol_20d"] if prev_d in us_e.index and "vol_20d" in us_e.columns else 1.0
            th_c, th_s = get_dynamic_threshold(vol, BASE_LOW, BASE_HIGH, VOL_LOW, VOL_HIGH)

            buy = tw.loc[d, "Open"]
            d1, d2, d3 = common[i], common[i + 1], common[i + 2]
            high_3d = max(tw.loc[d1, "High"], tw.loc[d2, "High"], tw.loc[d3, "High"])
            ret_3d = (tw.loc[d3, "Close"] / buy - 1) * 100
            win = high_3d > buy

            us_pct = us_ret * 100
            if us_pct < th_c:
                crash_list.append({"win": win, "ret": ret_3d})
            elif us_pct > th_s:
                surge_list.append({"win": win, "ret": ret_3d})
            else:
                flat_list.append({"win": win, "ret": ret_3d})

        def stats(lst):
            if not lst:
                return 0, 0, 0
            n = len(lst)
            w = sum(x["win"] for x in lst)
            r = np.mean([x["ret"] for x in lst])
            return n, w / n * 100 if n else 0, r

        c_n, c_wr, c_ret = stats(crash_list)
        s_n, s_wr, s_ret = stats(surge_list)
        f_n, f_wr, f_ret = stats(flat_list)

        results[name] = {
            "crash_n": c_n, "crash_wr": c_wr, "crash_ret": c_ret,
            "surge_n": s_n, "surge_wr": s_wr, "surge_ret": s_ret,
            "flat_n": f_n, "flat_wr": f_wr, "flat_ret": f_ret,
        }

    return results


def _fetch_and_backtest_hold_days(days: int, hold_days: int = 10) -> dict:
    """
    依指定天數與持有天數取得回測統計
    :param days: 回測區間天數
    :param hold_days: 持有天數（開盤買入，持有至第 hold_days 日收盤）
    """
    end = datetime.now()
    start = (end - timedelta(days=days)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    us = yf.download(US_TICKER, start="2024-01-01", end=end_str, progress=False, auto_adjust=True)
    if isinstance(us.columns, pd.MultiIndex):
        us.columns = us.columns.get_level_values(0)
    if us.empty or len(us) < 30:
        return {}

    us_e = apply_dynamic_threshold(us, 20, BASE_LOW, BASE_HIGH)
    us_e["us_ret"] = us_e["Close"].pct_change()

    need_forward = hold_days + 1
    results = {}
    for ticker, name in ALL_STOCKS.items():
        tw = yf.download(ticker, start=start, end=end_str, progress=False, auto_adjust=True)
        if isinstance(tw.columns, pd.MultiIndex):
            tw.columns = tw.columns.get_level_values(0)
        if tw.empty or "Open" not in tw.columns or "High" not in tw.columns:
            continue

        tw = tw[["Open", "High", "Close"]]
        common = us_e.index.intersection(tw.index).sort_values()
        crash_list, surge_list, flat_list = [], [], []

        for i in range(1, len(common) - need_forward):
            prev_d = common[i - 1]
            d = common[i]
            us_ret = us_e.loc[prev_d, "us_ret"] if prev_d in us_e.index else np.nan
            if np.isnan(us_ret):
                continue

            vol = us_e.loc[prev_d, "vol_20d"] if prev_d in us_e.index and "vol_20d" in us_e.columns else 1.0
            th_c, th_s = get_dynamic_threshold(vol, BASE_LOW, BASE_HIGH, VOL_LOW, VOL_HIGH)

            buy = tw.loc[d, "Open"]
            hold_indices = [common[i + j] for j in range(hold_days)]
            high_hold = max(tw.loc[dd, "High"] for dd in hold_indices)
            close_last = tw.loc[hold_indices[-1], "Close"]
            ret_hold = (close_last / buy - 1) * 100
            win = high_hold > buy

            us_pct = us_ret * 100
            if us_pct < th_c:
                crash_list.append({"win": win, "ret": ret_hold})
            elif us_pct > th_s:
                surge_list.append({"win": win, "ret": ret_hold})
            else:
                flat_list.append({"win": win, "ret": ret_hold})

        def stats(lst):
            if not lst:
                return 0, 0, 0
            n = len(lst)
            w = sum(x["win"] for x in lst)
            r = np.mean([x["ret"] for x in lst])
            return n, w / n * 100 if n else 0, r

        c_n, c_wr, c_ret = stats(crash_list)
        s_n, s_wr, s_ret = stats(surge_list)
        f_n, f_wr, f_ret = stats(flat_list)

        results[name] = {
            "crash_n": c_n, "crash_wr": c_wr, "crash_ret": c_ret,
            "surge_n": s_n, "surge_wr": s_wr, "surge_ret": s_ret,
            "flat_n": f_n, "flat_wr": f_wr, "flat_ret": f_ret,
        }

    return results


def generate_backtest_chart_6m(save_path: str) -> str | None:
    """
    產生過去半年歷史回測圖表並儲存
    :param save_path: 圖檔儲存路徑
    :return: 儲存成功則回傳路徑，否則 None
    """
    stats = fetch_and_backtest_6m()
    if not stats:
        return None

    cols = ["標的", "大跌買", "大漲買", "平盤買", "建議"]
    data = []
    for name, s in stats.items():
        crash_s = f"{s['crash_n']}次 {s['crash_wr']:.0f}% {s['crash_ret']:+.2f}%"
        surge_s = f"{s['surge_n']}次 {s['surge_wr']:.0f}% {s['surge_ret']:+.2f}%"
        flat_s = f"{s['flat_n']}次 {s['flat_wr']:.0f}% {s['flat_ret']:+.2f}%"
        better = "大跌買" if s["crash_ret"] > s["surge_ret"] else "大漲買"
        data.append([name, crash_s, surge_s, flat_s, better])

    try:
        fig, ax = plt.subplots(figsize=(14, len(data) * 0.6 + 3))
        ax.axis("off")
        table = ax.table(
            cellText=data,
            colLabels=cols,
            loc="center",
            cellLoc="center",
            colColours=["#4472C4"] * 5,
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        end_d = datetime.now().strftime("%Y-%m-%d")
        start_d = (datetime.now() - timedelta(days=185)).strftime("%Y-%m-%d")
        plt.title(
            f"過去半年歷史回測表（{start_d} ~ {end_d}）\n"
            "依動態門檻，持有 3 日內有漲即獲利",
            fontsize=12
        )
        plt.tight_layout()
        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        plt.savefig(save_path, dpi=150)
        plt.close()
        return save_path
    except Exception:
        return None
