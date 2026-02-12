# -*- coding: utf-8 -*-
"""
每日美股結果統整與台股建議 - 自動寄信
=======================================
每天先計算 20 日波動率 → 更新閥值 → 產生報告 → 寄送
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dynamic_threshold import get_dynamic_threshold, compute_volatility_regime
from strategy_stats import (
    fetch_and_backtest,
    fetch_and_backtest_6m,
    get_flat_etf_recommendation,
    get_strategy_table,
    get_combined_recommendation,
)
from screen_top_stocks import (
    run_screening,
    run_screening_10d,
    get_top20_table_text,
    get_top20_recommendations,
    get_top20_recommendations_10d,
)

# 樹莓派 24 小時運作：寄件者與收件者信箱（直接寫入）
GMAIL_SENDER = "gish1040403@gmail.com"
GMAIL_APP_PASSWORD = "cffakphyrorydcti"  # Gmail 應用程式密碼
RECIPIENT = "s07362022@gmail.com"  # 收件者信箱
US_TICKER = "QQQ"

# 大跌/大漲建議改由第五項+第六項回測綜合結果動態產生（見 get_combined_recommendation）


def get_us_report() -> dict:
    """
    每日流程：計算 20 日波動率 → 更新閥值 → 取得美股昨日表現
    """
    end = datetime.now()
    start = end - timedelta(days=35)  # 需 20+ 日算波動率
    try:
        data = yf.download(
            US_TICKER,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            progress=False,
            auto_adjust=True
        )
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        if data.empty or len(data) < 2:
            return None

        # Step 1: 計算 20 日波動率
        ret = data["Close"].pct_change()
        vol_series = compute_volatility_regime(ret, window=20)
        vol_20d = vol_series.iloc[-2] if len(vol_series) >= 2 and not pd.isna(vol_series.iloc[-2]) else 1.0

        # Step 2: 依波動率更新閥值
        th_crash, th_surge = get_dynamic_threshold(vol_20d)

        # Step 3: 取得美股最新收盤（yfinance 即時抓取，最後一筆為最近交易日收盤價）
        last = data.iloc[-1]
        prev = data.iloc[-2]
        chg_pct = (last["Close"] / prev["Close"] - 1) * 100

        is_crash = chg_pct < th_crash
        is_surge = chg_pct > th_surge
        status = "大跌" if is_crash else ("大漲" if is_surge else "平盤")

        return {
            "date": str(data.index[-1].date()),
            "close": last["Close"],
            "data_source": "yfinance 即時抓取，為最近一個美股交易日的收盤價",
            "chg_pct": chg_pct,
            "vol_20d": vol_20d,
            "th_crash": th_crash,
            "th_surge": th_surge,
            "is_crash": is_crash,
            "is_surge": is_surge,
            "status": status,
        }
    except Exception:
        return None


def _build_integrated_recommendations(
    strategy_stats: dict,
    crash_3m: list,
    surge_3m: list,
    crash_intersection: list,
    surge_intersection: list,
    crash_top50: list,
    surge_top50: list,
    top50_results: list,
    crash_top50_10d: list,
    surge_top50_10d: list,
    top50_results_10d: list,
) -> str:
    """
    整合第四項與第八項，分別呈現短期（3日）與長期（10日）建議，並附報酬率
    """
    sep2 = "-" * 55

    # 短期：建立 3 日報酬對照（strategy_stats 7 檔 + top50）
    ret_3d = {}
    if strategy_stats:
        for name, s in strategy_stats.items():
            ret_3d[name] = (s["crash_ret"], s["surge_ret"])
    if top50_results:
        for r in top50_results:
            ret_3d[r["name"]] = (r["crash_ret"], r["surge_ret"])

    # 短期大跌：合併 crash_3m + crash_top50，去重並附報酬
    short_crash = []
    seen = set()
    for name in crash_3m + crash_top50:
        if name in seen:
            continue
        seen.add(name)
        if name in ret_3d:
            r_val = ret_3d[name][0]
            short_crash.append(f"{name} {r_val:+.2f}%")
        else:
            short_crash.append(name)

    # 短期大漲：合併 surge_3m + surge_top50
    short_surge = []
    seen = set()
    for name in surge_3m + surge_top50:
        if name in seen:
            continue
        seen.add(name)
        if name in ret_3d:
            r_val = ret_3d[name][1]
            short_surge.append(f"{name} {r_val:+.2f}%")
        else:
            short_surge.append(name)

    # 長期：建立 10 日報酬對照
    ret_10d = {}
    if top50_results_10d:
        for r in top50_results_10d:
            ret_10d[r["name"]] = (r["crash_ret"], r["surge_ret"])

    long_crash = []
    for name in crash_top50_10d:
        if name in ret_10d:
            r_val = ret_10d[name][0]
            long_crash.append(f"{name} {r_val:+.2f}%")
        else:
            long_crash.append(name)

    long_surge = []
    for name in surge_top50_10d:
        if name in ret_10d:
            r_val = ret_10d[name][1]
            long_surge.append(f"{name} {r_val:+.2f}%")
        else:
            long_surge.append(name)

    lines = [
        "",
        f"{sep2}",
        "九、短期與長期建議整合（第四項＋第八項，含報酬率）",
        sep2,
        "  【短期】3 日持有，來自第四項（3 個月建議＋熱門 50 前 20 名）",
        f"  美股大跌後隔天買：{', '.join(short_crash) if short_crash else '無'}",
        f"  美股大漲後隔天買：{', '.join(short_surge) if short_surge else '無'}",
        "",
        "  【長期】10 日持有，來自第八項（熱門 50 選 20，半年回測，均報酬 >= 4%）",
        f"  美股大跌後隔天買：{', '.join(long_crash) if long_crash else '無'}",
        f"  美股大漲後隔天買：{', '.join(long_surge) if long_surge else '無'}",
        "",
    ]
    return "\n".join(lines)


def build_email_content(
    report: dict,
    strategy_stats: dict = None,
    strategy_stats_6m: dict = None,
    top50_results: list = None,
    top50_results_10d: list = None,
) -> str:
    """組裝信件內容：閥值、波動率、美股漲跌、台股建議、歷史策略表、過去半年回測表、熱門台股篩選"""
    sep = "=" * 55
    sep2 = "-" * 55

    now_tw = datetime.now(ZoneInfo("Asia/Taipei"))
    now_us = now_tw.astimezone(ZoneInfo("America/New_York"))
    time_tw = now_tw.strftime("%Y-%m-%d %H:%M")
    ampm = "下午" if now_us.hour >= 12 else "上午"
    hour_12 = now_us.hour % 12 if now_us.hour % 12 else 12
    time_us_cn = f"{ampm} {hour_12}:{now_us.strftime('%M')}"

    if not report:
        return f"""{sep}
  每日美股統整與台股操作建議
{sep}

報告產生時間：{time_tw}（台灣時間）= 美東 {time_us_cn}

{sep2}
【錯誤】無法取得美股資料，請稍後再試。
建議：暫不操作，待資料更新後再執行腳本。
{sep2}

{sep}
※ 此建議僅供參考，不構成投資建議，請自行評估風險。
{sep}"""

    r = report

    if strategy_stats is None:
        strategy_stats = fetch_and_backtest()
    if strategy_stats_6m is None:
        strategy_stats_6m = fetch_and_backtest_6m()
    flat_advice, flat_conclusion = get_flat_etf_recommendation(strategy_stats)
    crash_3m, surge_3m, crash_intersection, surge_intersection = get_combined_recommendation(
        strategy_stats, strategy_stats_6m
    )

    # 取得熱門 50 檔前 20 名建議（供第四項一併顯示）
    crash_top50, surge_top50 = [], []
    if top50_results:
        crash_top50, surge_top50 = get_top20_recommendations(top50_results)

    if r["is_surge"]:
        action = "美股昨日大漲，建議隔天開盤可考慮買入："
        primary = f"{', '.join(surge_3m)}（3 個月）" if surge_3m else "（無 3 個月建議標的）"
        intersection = ", ".join(surge_intersection) if surge_intersection else None
        stocks = primary
        stocks_extra = f"\n  交集建議（3 個月與半年皆建議）：{intersection}" if intersection else ""
    elif r["is_crash"]:
        action = "美股昨日大跌，建議隔天開盤可考慮買入："
        primary = f"{', '.join(crash_3m)}（3 個月）" if crash_3m else "（無 3 個月建議標的）"
        intersection = ", ".join(crash_intersection) if crash_intersection else None
        stocks = primary
        stocks_extra = f"\n  交集建議（3 個月與半年皆建議）：{intersection}" if intersection else ""
    else:
        action = "美股昨日波動在閥值內（平盤）。"
        stocks = flat_advice
        stocks_extra = ""

    # 第四項加入熱門 50 檔前 20 名建議
    if crash_top50 or surge_top50:
        top50_block = "\n\n  【熱門 50 檔前 20 名】"
        top50_block += f"\n  美股大跌後隔天買：{', '.join(crash_top50) if crash_top50 else '無'}"
        top50_block += f"\n  美股大漲後隔天買：{', '.join(surge_top50) if surge_top50 else '無'}"
        stocks_extra = (stocks_extra or "") + top50_block

    table_block = ""
    if strategy_stats:
        start_3m = (datetime.now() - timedelta(days=95)).strftime("%Y-%m-%d")
        end_3m = datetime.now().strftime("%Y-%m-%d")
        table_block = f"""
{sep2}
五、歷史策略表（最近 3 個月回測：{start_3m} ~ {end_3m}）
{sep2}
  大跌買/大漲買/平盤買：次數、勝率%、均報酬%
  （依動態門檻，持有 3 日內有漲即獲利）

{get_strategy_table(strategy_stats)}

  平盤時 ETF 建議：{flat_conclusion}
"""

    table_block_6m = ""
    if strategy_stats_6m:
        start_6m = (datetime.now() - timedelta(days=185)).strftime("%Y-%m-%d")
        end_6m = datetime.now().strftime("%Y-%m-%d")
        table_block_6m = f"""
{sep2}
六、過去半年歷史回測表（{start_6m} ~ {end_6m}）
{sep2}
  大跌買/大漲買/平盤買：次數、勝率%、均報酬%
  （依動態門檻，持有 3 日內有漲即獲利）

{get_strategy_table(strategy_stats_6m)}
"""

    # 第七項：熱門台股篩選（50 檔 → 前 20 名，crash_top50/surge_top50 已於上方計算）
    table_block_top50 = ""
    if top50_results:
        table_block_top50 = f"""
{sep2}
七、熱門台股篩選（50 檔 → 前 20 名，3 個月回測）
{sep2}
  篩選標的：50 檔熱門高交易量台股（台灣50成分股 + 熱門中小型）
  排序依據：勝率 + 均報酬綜合評分

{get_top20_table_text(top50_results)}

  【前 20 名操作建議】
  美股大跌後隔天買：{', '.join(crash_top50) if crash_top50 else '無'}
  美股大漲後隔天買：{', '.join(surge_top50) if surge_top50 else '無'}
"""

    # 第八項：熱門 50 檔 10 日持有回測（50 選 20，半年），均報酬 >= 4% 才列入建議
    table_block_10d = ""
    crash_top50_10d, surge_top50_10d = [], []
    if top50_results_10d:
        crash_top50_10d, surge_top50_10d = get_top20_recommendations_10d(top50_results_10d, min_ret=4.0)
        start_6m = (datetime.now() - timedelta(days=185)).strftime("%Y-%m-%d")
        end_6m = datetime.now().strftime("%Y-%m-%d")
        table_block_10d = f"""
{sep2}
八、熱門 50 檔 10 日持有回測（50 選 20，半年：{start_6m} ~ {end_6m}）
{sep2}
  勝率%＝10日內有無漲；均報酬%＝持有至第10日收盤
  建議門檻：均報酬 >= 4% 才列入

{get_top20_table_text(top50_results_10d)}

  【10 日持有操作建議】（均報酬 >= 4%）
  美股大跌後隔天買：{', '.join(crash_top50_10d) if crash_top50_10d else '無'}
  美股大漲後隔天買：{', '.join(surge_top50_10d) if surge_top50_10d else '無'}
"""

    # 第九項：整合第四項與第八項，分別呈現短期與長期，並附報酬率
    table_block_9 = _build_integrated_recommendations(
        strategy_stats=strategy_stats,
        crash_3m=crash_3m,
        surge_3m=surge_3m,
        crash_intersection=crash_intersection,
        surge_intersection=surge_intersection,
        crash_top50=crash_top50,
        surge_top50=surge_top50,
        top50_results=top50_results,
        crash_top50_10d=crash_top50_10d,
        surge_top50_10d=surge_top50_10d,
        top50_results_10d=top50_results_10d,
    )

    body = f"""{sep}
  每日美股統整與台股操作建議
{sep}

報告產生時間：{time_tw}（台灣時間）= 美東 {time_us_cn}
  報價來源：{r.get('data_source', 'yfinance 即時抓取，為最近美股交易日收盤價')}

{sep2}
一、20 日波動率（每日計算）
{sep2}
  波動率：{r['vol_20d']:.2f}%
  說明：市場平靜時較低，暴風雨時較高

{sep2}
二、今日閥值（依波動率動態更新）
{sep2}
  大跌閥值：< {r['th_crash']:.1f}%
  大漲閥值：> {r['th_surge']:.1f}%
  說明：波動率高時閥值較大，更穩健

{sep2}
三、昨日美股收盤
{sep2}
  日期：{r['date']}
  QQQ 收盤：{r['close']:.2f}（即時抓取之最新收盤價）
  漲跌幅：{r['chg_pct']:+.2f}%
  判定：{r['status']}

{sep2}
四、今日台股建議
{sep2}
  {action}
  → {stocks}
{stocks_extra}

  說明：優先依 3 個月回測建議；交集為 3 個月與半年皆建議之標的；平盤依 0050/0052 歷史表現。
  策略：開盤買入，持有 3 日內若有漲可獲利了結。
{table_block}
{table_block_6m}
{table_block_top50}
{table_block_10d}
{table_block_9}

{sep}
※ 此建議僅供參考，不構成投資建議，請自行評估風險。
{sep}"""
    return body.strip()


def send_email(content: str, preview: bool = False) -> bool:
    """寄送信件（preview=True 時僅預覽不寄出）"""
    if preview:
        print("【預覽】將寄出的信件內容：")
        print("=" * 50)
        print(content)
        print("=" * 50)
        print(f"收件人：{RECIPIENT}")
        return True

    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_SENDER
        msg["To"] = RECIPIENT
        msg["Subject"] = f"【每日美股統整】{datetime.now().strftime('%Y-%m-%d')} 台股操作建議"
        msg.attach(MIMEText(content, "plain", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.ehlo()  # 驗證 SMTP 伺服器
            smtp.starttls()  # 建立加密傳輸
            smtp.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)  # 登入寄件者 Gmail
            smtp.send_message(msg)  # 寄送郵件

        print("信件已成功寄出至", RECIPIENT)
        return True
    except Exception as e:
        print("寄信失敗：", e)
        return False


if __name__ == "__main__":
    import sys
    preview_only = "--preview" in sys.argv or "-p" in sys.argv
    auto_send = "--send" in sys.argv

    # 每日流程：20日波動率 → 更新閥值 → 歷史策略表 → 產生報告
    base_dir = os.path.dirname(os.path.abspath(__file__))
    stock_dir = os.path.join(base_dir, "stock")
    os.makedirs(stock_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    report = get_us_report()
    strategy_stats = fetch_and_backtest()
    strategy_stats_6m = fetch_and_backtest_6m()
    print("\n[執行] 熱門台股篩選（50 檔，3 日）...")
    top50_results = run_screening()
    print("\n[執行] 熱門台股篩選（50 檔，10 日）...")
    top50_results_10d = run_screening_10d()
    content = build_email_content(
        report,
        strategy_stats,
        strategy_stats_6m=strategy_stats_6m,
        top50_results=top50_results,
        top50_results_10d=top50_results_10d,
    )
    send_email(content, preview=True)

    # 儲存至 stock 資料夾，檔名：當日日期_建議.txt
    save_path = os.path.join(stock_dir, f"{today}_建議.txt")
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n完整信件已儲存至: {save_path}")

    if preview_only:
        print("\n（僅預覽，未寄出。若要寄出請執行：python daily_us_tw_email.py）")
    elif auto_send:
        send_email(content, preview=False)
    else:
        try:
            ans = input("\n是否要實際寄出？(y/n): ").strip().lower()
            if ans == "y":
                send_email(content, preview=False)
        except EOFError:
            pass
