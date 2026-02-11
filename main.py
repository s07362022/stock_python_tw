# -*- coding: utf-8 -*-
"""
台股預測工具 - 主程式（專案一）
==============================
預測 → 驗證 → 輸出結果圖
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 設定中文字體（Windows 微軟正黑體、雅黑體；若無則嘗試其他）
plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "SimHei", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False
from data_fetcher import fetch_stock
from indicators import add_all_indicators
from model import create_sequences, train_lstm, predict_lstm
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
from config import TECH_STOCKS, START_DATE, END_DATE


def run_prediction_and_plot(ticker: str = "2330.TW", seq_len: int = 60) -> None:
    """
    執行預測、驗證，並輸出結果圖
    """
    print(f"下載 {ticker} ({TECH_STOCKS.get(ticker, ticker)}) 資料...")
    df = fetch_stock(ticker, START_DATE, END_DATE)
    if df.empty:
        print(f"無法取得 {ticker} 資料")
        return

    print("計算技術指標...")
    df = add_all_indicators(df)
    df = df.dropna()

    feature_cols = [
        "Close", "RSI_14", "MACD_DIF", "MACD_DEA", "BB_Upper", "BB_Lower",
        "ATR_14", "SMA_20", "EMA_12", "OBV"
    ]
    available = [c for c in feature_cols if c in df.columns]
    data = df[available].values

    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data)
    target_col_idx = available.index("Close")

    X, y = create_sequences(data_scaled, target_col_idx, seq_len=seq_len)
    split = int(len(X) * 0.8)
    X_train, y_train = X[:split], y[:split]
    X_test, y_test = X[split:], y[split:]

    print("訓練 LSTM...")
    model = train_lstm(X_train, y_train, input_size=len(available), epochs=100)

    pred = predict_lstm(model, X)
    pred_matrix = np.zeros((len(pred), len(available)))
    pred_matrix[:, target_col_idx] = pred
    pred_orig = scaler.inverse_transform(pred_matrix)[:, target_col_idx]

    y_matrix = np.zeros((len(y), len(available)))
    y_matrix[:, target_col_idx] = y
    y_orig = scaler.inverse_transform(y_matrix)[:, target_col_idx]

    # 驗證指標
    mae = mean_absolute_error(y_orig, pred_orig)
    rmse = np.sqrt(mean_squared_error(y_orig, pred_orig))
    direction_acc = np.mean((np.diff(y_orig) > 0) == (np.diff(pred_orig) > 0))

    print("\n========== 驗證結果 ==========")
    print(f"MAE (平均絕對誤差): {mae:.2f}")
    print(f"RMSE (均方根誤差): {rmse:.2f}")
    print(f"方向準確率 (漲跌預測): {direction_acc*100:.1f}%")
    print("==============================\n")

    # 繪圖：對齊日期（y 對應 data[seq_len:] 的每一天）
    dates = df.index[seq_len : seq_len + len(pred_orig)]

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # 圖1：實際 vs 預測
    ax1 = axes[0]
    ax1.plot(dates, y_orig, label="實際收盤價", color="#2E86AB", linewidth=1.5)
    ax1.plot(dates, pred_orig, label="LSTM 預測", color="#E94F37", linewidth=1.5, alpha=0.8)
    ax1.set_ylabel("價格")
    ax1.set_title(f"{TECH_STOCKS.get(ticker, ticker)} ({ticker}) - 預測 vs 實際")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # 圖2：訓練 / 測試區間
    train_end = split
    ax2 = axes[1]
    ax2.plot(dates[:train_end], y_orig[:train_end], color="#2E86AB", label="訓練集", linewidth=1)
    ax2.plot(dates[train_end:], y_orig[train_end:], color="#28A745", label="測試集（驗證）", linewidth=1)
    ax2.plot(dates[train_end:], pred_orig[train_end:], color="#E94F37", label="測試集預測", linewidth=1, alpha=0.8, linestyle="--")
    ax2.axvline(x=dates[train_end], color="gray", linestyle=":", alpha=0.7)
    ax2.set_ylabel("價格")
    ax2.set_xlabel("日期")
    ax2.set_title("訓練區間 vs 測試區間（驗證）")
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = "f:/代碼/202602/result_prediction.png"
    plt.savefig(out_path, dpi=150)
    print(f"結果圖已儲存至: {out_path}")
    plt.show()


if __name__ == "__main__":
    run_prediction_and_plot("2330.TW")
