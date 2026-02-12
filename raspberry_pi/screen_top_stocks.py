# -*- coding: utf-8 -*-
"""
熱門台股篩選器 - 回測 3 個月並篩選最佳 20 檔
=============================================
1. 從 50 檔熱門高交易量台股中
2. 依美股大跌/大漲後隔天買入策略回測 3 個月
3. 篩選勝率與報酬率最高的 20 檔
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dynamic_threshold import apply_dynamic_threshold, get_dynamic_threshold

US_TICKER = "QQQ"
BASE_LOW, BASE_HIGH = 0.7, 1.8
VOL_LOW, VOL_HIGH = 0.6, 1.4

# 50 檔熱門高交易量台股（台灣 50 成分股 + 熱門中小型股）
TOP_50_STOCKS = {
    # 台灣 50 成分股（主要）
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
    "2308.TW": "台達電",
    "2881.TW": "富邦金",
    "2882.TW": "國泰金",
    "2303.TW": "聯電",
    "1301.TW": "台塑",
    "1303.TW": "南亞",
    "2002.TW": "中鋼",
    "2912.TW": "統一超",
    "2886.TW": "兆豐金",
    "2891.TW": "中信金",
    "3711.TW": "日月光投控",
    "2382.TW": "廣達",
    "2412.TW": "中華電",
    "1326.TW": "台化",
    "2884.TW": "玉山金",
    "5880.TW": "合庫金",
    "2892.TW": "第一金",
    "2357.TW": "華碩",
    "3008.TW": "大立光",
    "2327.TW": "國巨",
    "6505.TW": "台塑化",
    "2395.TW": "研華",
    # 熱門科技股
    "2379.TW": "瑞昱",
    "3034.TW": "聯詠",
    "2474.TW": "可成",
    "3037.TW": "欣興",
    "2301.TW": "光寶科",
    "2345.TW": "智邦",
    "3231.TW": "緯創",
    "2324.TW": "仁寶",
    "3017.TW": "奇鋐",
    "6669.TW": "緯穎",
    # 熱門傳產與金融
    "1216.TW": "統一",
    "2207.TW": "和泰車",
    "9910.TW": "豐泰",
    "1101.TW": "台泥",
    "2105.TW": "正新",
    "2801.TW": "彰銀",
    "5871.TW": "中租-KY",
    "2883.TW": "開發金",
    # 熱門中小型股
    "2337.TW": "旺宏",
    "2344.TW": "華邦電",
    "2409.TW": "友達",
    "3481.TW": "群創",
    "2603.TW": "長榮",
    "2609.TW": "陽明",
    "2615.TW": "萬海",
}


def fetch_us_data(days: int = 120) -> pd.DataFrame:
    """取得美股 QQQ 資料"""
    end = datetime.now()
    start = end - timedelta(days=days)
    us = yf.download(
        US_TICKER,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=True
    )
    if isinstance(us.columns, pd.MultiIndex):
        us.columns = us.columns.get_level_values(0)
    return us


def fetch_tw_data(ticker: str, days: int = 120) -> pd.DataFrame:
    """取得台股資料"""
    end = datetime.now()
    start = end - timedelta(days=days)
    tw = yf.download(
        ticker,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=True
    )
    if isinstance(tw.columns, pd.MultiIndex):
        tw.columns = tw.columns.get_level_values(0)
    return tw


def backtest_single_stock(ticker: str, name: str, us_e: pd.DataFrame) -> dict | None:
    """
    對單一台股進行回測
    :return: 包含勝率、報酬等統計的 dict，或 None（資料不足）
    """
    tw = fetch_tw_data(ticker, days=120)
    if tw.empty or "Open" not in tw.columns or "High" not in tw.columns:
        return None

    tw = tw[["Open", "High", "Close"]]
    common = us_e.index.intersection(tw.index).sort_values()

    if len(common) < 10:
        return None

    crash_list, surge_list, flat_list = [], [], []

    for i in range(1, len(common) - 2):
        prev_d = common[i - 1]
        d = common[i]
        us_ret = us_e.loc[prev_d, "us_ret"] if prev_d in us_e.index else np.nan
        if np.isnan(us_ret):
            continue

        vol = us_e.loc[prev_d, "vol_20d"] if "vol_20d" in us_e.columns else 1.0
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

    # 綜合評分：取大跌買和大漲買中較佳者
    if c_n >= 3 and s_n >= 3:
        best_strategy = "大跌買" if c_ret > s_ret else "大漲買"
        best_wr = c_wr if c_ret > s_ret else s_wr
        best_ret = max(c_ret, s_ret)
    elif c_n >= 3:
        best_strategy = "大跌買"
        best_wr = c_wr
        best_ret = c_ret
    elif s_n >= 3:
        best_strategy = "大漲買"
        best_wr = s_wr
        best_ret = s_ret
    else:
        return None  # 樣本數不足

    return {
        "ticker": ticker,
        "name": name,
        "crash_n": c_n, "crash_wr": c_wr, "crash_ret": c_ret,
        "surge_n": s_n, "surge_wr": s_wr, "surge_ret": s_ret,
        "flat_n": f_n, "flat_wr": f_wr, "flat_ret": f_ret,
        "best_strategy": best_strategy,
        "best_wr": best_wr,
        "best_ret": best_ret,
        # 綜合分數：勝率 × 0.4 + 報酬率 × 0.6（報酬率權重較高）
        "score": best_wr * 0.4 + best_ret * 10 * 0.6,
    }


# 10 日回測使用半年資料（約 185 交易日）
SCREEN_10D_DAYS = 200  # 約 6 個月，含緩衝


def backtest_single_stock_10d(ticker: str, name: str, us_e: pd.DataFrame, days: int = SCREEN_10D_DAYS) -> dict | None:
    """
    對單一台股進行 10 日持有回測（半年資料）
    :return: 包含勝率、報酬等統計的 dict，或 None（資料不足）
    """
    tw = fetch_tw_data(ticker, days=days)
    if tw.empty or "Open" not in tw.columns or "High" not in tw.columns:
        return None

    tw = tw[["Open", "High", "Close"]]
    common = us_e.index.intersection(tw.index).sort_values()
    hold_days = 10
    need_forward = hold_days + 1

    if len(common) < need_forward:
        return None

    crash_list, surge_list, flat_list = [], [], []

    for i in range(1, len(common) - need_forward):
        prev_d = common[i - 1]
        d = common[i]
        us_ret = us_e.loc[prev_d, "us_ret"] if prev_d in us_e.index else np.nan
        if np.isnan(us_ret):
            continue

        vol = us_e.loc[prev_d, "vol_20d"] if "vol_20d" in us_e.columns else 1.0
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

    if c_n >= 3 and s_n >= 3:
        best_strategy = "大跌買" if c_ret > s_ret else "大漲買"
        best_wr = c_wr if c_ret > s_ret else s_wr
        best_ret = max(c_ret, s_ret)
    elif c_n >= 3:
        best_strategy = "大跌買"
        best_wr = c_wr
        best_ret = c_ret
    elif s_n >= 3:
        best_strategy = "大漲買"
        best_wr = s_wr
        best_ret = s_ret
    else:
        return None

    return {
        "ticker": ticker,
        "name": name,
        "crash_n": c_n, "crash_wr": c_wr, "crash_ret": c_ret,
        "surge_n": s_n, "surge_wr": s_wr, "surge_ret": s_ret,
        "flat_n": f_n, "flat_wr": f_wr, "flat_ret": f_ret,
        "best_strategy": best_strategy,
        "best_wr": best_wr,
        "best_ret": best_ret,
        "score": best_wr * 0.4 + best_ret * 10 * 0.6,
    }


def run_screening_10d() -> list[dict]:
    """
    執行 50 檔股票 10 日持有回測篩選（半年資料）
    :return: 排序後的結果列表
    """
    us = fetch_us_data(days=SCREEN_10D_DAYS)
    if us.empty or len(us) < 30:
        return []

    us_e = apply_dynamic_threshold(us, 20, BASE_LOW, BASE_HIGH)
    us_e["us_ret"] = us_e["Close"].pct_change()

    results = []
    for ticker, name in TOP_50_STOCKS.items():
        r = backtest_single_stock_10d(ticker, name, us_e, days=SCREEN_10D_DAYS)
        if r:
            results.append(r)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# 10 日建議最低均報酬門檻
MIN_RET_10D = 4.0


def get_top20_recommendations_10d(results: list[dict], min_ret: float = MIN_RET_10D) -> tuple[list[str], list[str]]:
    """
    從 10 日回測前 20 名取得建議標的，僅納入均報酬 >= min_ret% 的標的
    :return: (crash_buy_list, surge_buy_list)
    """
    top_20 = results[:20]
    crash_buy, surge_buy = [], []
    for r in top_20:
        crash_ok = r["crash_ret"] >= min_ret
        surge_ok = r["surge_ret"] >= min_ret
        if not crash_ok and not surge_ok:
            continue
        diff = abs(r["crash_ret"] - r["surge_ret"])
        if diff < RET_DIFF_THRESHOLD and crash_ok and surge_ok:
            crash_buy.append(r["name"])
            surge_buy.append(r["name"])
        elif r["best_strategy"] == "大跌買" and crash_ok:
            crash_buy.append(r["name"])
        elif surge_ok:
            surge_buy.append(r["name"])
    return crash_buy, surge_buy


def run_screening() -> list[dict]:
    """
    執行全部 50 檔股票篩選
    :return: 排序後的結果列表
    """
    print("=" * 60)
    print("熱門台股篩選器 - 3 個月回測")
    print("=" * 60)
    print(f"篩選標的：{len(TOP_50_STOCKS)} 檔熱門台股")
    print("策略：美股大跌/大漲後隔天開盤買入，持有 3 日內有漲即獲利")
    print("=" * 60)

    # 取得美股資料
    print("\n[1/3] 取得美股 QQQ 資料...")
    us = fetch_us_data(days=120)
    if us.empty or len(us) < 30:
        print("無法取得美股資料")
        return []

    us_e = apply_dynamic_threshold(us, 20, BASE_LOW, BASE_HIGH)
    us_e["us_ret"] = us_e["Close"].pct_change()

    # 逐一回測
    print(f"\n[2/3] 回測 {len(TOP_50_STOCKS)} 檔股票...")
    results = []
    for idx, (ticker, name) in enumerate(TOP_50_STOCKS.items(), 1):
        print(f"  ({idx:2}/{len(TOP_50_STOCKS)}) {name} ({ticker})...", end=" ")
        r = backtest_single_stock(ticker, name, us_e)
        if r:
            print(f"勝率 {r['best_wr']:.0f}%  報酬 {r['best_ret']:+.2f}%  {r['best_strategy']}")
            results.append(r)
        else:
            print("樣本不足，跳過")

    # 排序：依綜合分數排序
    results.sort(key=lambda x: x["score"], reverse=True)

    return results


def print_top_20(results: list[dict]) -> None:
    """印出前 20 名"""
    top_20 = results[:20]

    print("\n" + "=" * 80)
    print("【篩選結果】前 20 名最佳標的（依勝率 + 報酬綜合評分）")
    print("=" * 80)
    print(f"{'排名':<4} {'股票':<12} {'建議策略':<8} {'勝率':<8} {'均報酬':<10} {'大跌買':<16} {'大漲買':<16}")
    print("-" * 80)

    for i, r in enumerate(top_20, 1):
        crash_s = f"{r['crash_n']:2}次 {r['crash_wr']:.0f}% {r['crash_ret']:+.1f}%"
        surge_s = f"{r['surge_n']:2}次 {r['surge_wr']:.0f}% {r['surge_ret']:+.1f}%"
        print(f"{i:<4} {r['name']:<10} {r['best_strategy']:<8} {r['best_wr']:.0f}%{'':<4} {r['best_ret']:+.2f}%{'':<4} {crash_s:<16} {surge_s:<16}")

    print("=" * 80)


# 大跌/大漲均報酬差異門檻：若差不到此值，兩者皆推薦
RET_DIFF_THRESHOLD = 0.5
# 最低均報酬門檻：至少達此值才列入熱門 50 檔前 20 名建議
MIN_RET_THRESHOLD = 2.0


def get_recommendations(results: list[dict]) -> tuple[list[str], list[str]]:
    """
    從前 20 名中，分出大跌買和大漲買的建議標的
    若大跌買與大漲買均報酬差不到 0.5%，則兩者皆推薦
    僅納入均報酬 >= 2% 的標的
    :return: (crash_buy_list, surge_buy_list)
    """
    top_20 = results[:20]
    crash_buy, surge_buy = [], []
    for r in top_20:
        crash_ok = r["crash_ret"] >= MIN_RET_THRESHOLD
        surge_ok = r["surge_ret"] >= MIN_RET_THRESHOLD
        if not crash_ok and not surge_ok:
            continue
        diff = abs(r["crash_ret"] - r["surge_ret"])
        if diff < RET_DIFF_THRESHOLD and crash_ok and surge_ok:
            crash_buy.append(r["name"])
            surge_buy.append(r["name"])
        elif r["best_strategy"] == "大跌買" and crash_ok:
            crash_buy.append(r["name"])
        elif surge_ok:
            surge_buy.append(r["name"])
    return crash_buy, surge_buy


def save_results(results: list[dict], top_n: int = 20) -> str:
    """儲存結果至檔案"""
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    stock_dir = os.path.join(base_dir, "stock")
    os.makedirs(stock_dir, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    save_path = os.path.join(stock_dir, f"{today}_篩選結果.txt")

    top_results = results[:top_n]
    crash_buy, surge_buy = get_recommendations(results)

    with open(save_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("  熱門台股篩選結果\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"篩選日期：{today}\n")
        f.write(f"篩選標的：{len(TOP_50_STOCKS)} 檔熱門台股\n")
        f.write(f"回測區間：最近 3 個月\n")
        f.write("策略：美股大跌/大漲後隔天開盤買入，持有 3 日內有漲即獲利\n\n")

        f.write("-" * 60 + "\n")
        f.write(f"【前 {top_n} 名最佳標的】\n")
        f.write("-" * 60 + "\n\n")

        for i, r in enumerate(top_results, 1):
            f.write(f"{i:2}. {r['name']}（{r['ticker']}）\n")
            f.write(f"    建議策略：{r['best_strategy']}  勝率：{r['best_wr']:.0f}%  均報酬：{r['best_ret']:+.2f}%\n")
            f.write(f"    大跌買：{r['crash_n']}次 {r['crash_wr']:.0f}% {r['crash_ret']:+.2f}%\n")
            f.write(f"    大漲買：{r['surge_n']}次 {r['surge_wr']:.0f}% {r['surge_ret']:+.2f}%\n\n")

        f.write("-" * 60 + "\n")
        f.write("【操作建議】\n")
        f.write("-" * 60 + "\n\n")
        f.write(f"美股大跌後隔天買：{', '.join(crash_buy)}\n\n")
        f.write(f"美股大漲後隔天買：{', '.join(surge_buy)}\n\n")

        f.write("=" * 60 + "\n")
        f.write("※ 此篩選結果僅供參考，不構成投資建議，請自行評估風險。\n")
        f.write("=" * 60 + "\n")

    return save_path


def run():
    """主程式"""
    results = run_screening()

    if not results:
        print("無法取得足夠資料進行篩選")
        return

    print_top_20(results)

    crash_buy, surge_buy = get_recommendations(results)
    print("\n【操作建議】")
    print(f"  美股大跌後隔天買：{', '.join(crash_buy)}")
    print(f"  美股大漲後隔天買：{', '.join(surge_buy)}")

    save_path = save_results(results)
    print(f"\n篩選結果已儲存至：{save_path}")


def get_top20_table_text(results: list[dict]) -> str:
    """
    產出前 20 名的文字表格（供信件使用）
    :param results: 篩選結果列表
    :return: 表格文字
    """
    if not results:
        return "（無法取得足夠資料進行篩選）"

    top_20 = results[:20]
    lines = []
    lines.append(f"{'排名':<4} {'股票':<10} {'策略':<8} {'勝率':<6} {'均報酬':<8}")
    lines.append("-" * 50)

    for i, r in enumerate(top_20, 1):
        lines.append(f"{i:<4} {r['name']:<8} {r['best_strategy']:<8} {r['best_wr']:.0f}%{'':<3} {r['best_ret']:+.2f}%")

    return "\n".join(lines)


def get_top20_recommendations(results: list[dict]) -> tuple[list[str], list[str]]:
    """
    從前 20 名取得建議標的
    若大跌買與大漲買均報酬差不到 0.5%，則兩者皆推薦
    :return: (crash_buy_list, surge_buy_list)
    """
    return get_recommendations(results)


if __name__ == "__main__":
    run()
