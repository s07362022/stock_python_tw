# -*- coding: utf-8 -*-
"""
LSTM 預測模型 - 基本時間序列預測
================================
使用 PyTorch 實作單向 LSTM，為股市預測常用的深度學習架構。
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from typing import Optional


class LSTMModel(nn.Module):
    """
    基本 LSTM 模型
    -------------
    架構：LSTM → Dropout → 全連接層
    輸入：過去 seq_len 天的特徵
    輸出：未來 1 天的預測值（收盤價或報酬率）
    """

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        output_size: int = 1
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        lstm_out, _ = self.lstm(x)
        # 取最後一個時間步
        last_out = lstm_out[:, -1, :]
        return self.fc(last_out)


def create_sequences(
    data: np.ndarray,
    target_col_idx: int,
    seq_len: int = 60,
    pred_horizon: int = 1
) -> tuple[np.ndarray, np.ndarray]:
    """
    建立 LSTM 的輸入序列與標籤
    :param data: 特徵矩陣 (T, F)
    :param target_col_idx: 預測目標的欄位索引（通常是收盤價）
    :param seq_len: 輸入序列長度（過去幾天）
    :param pred_horizon: 預測未來幾天
    :return: X (N, seq_len, F), y (N,)
    """
    X, y = [], []
    for i in range(seq_len, len(data) - pred_horizon + 1):
        X.append(data[i - seq_len:i])
        y.append(data[i + pred_horizon - 1, target_col_idx])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def train_lstm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    input_size: int,
    epochs: int = 100,
    hidden_size: int = 64,
    lr: float = 0.001,
    device: Optional[str] = None
) -> LSTMModel:
    """
    訓練 LSTM 模型
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    model = LSTMModel(
        input_size=input_size,
        hidden_size=hidden_size,
        num_layers=2,
        dropout=0.2
    ).to(device)

    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    X_t = torch.tensor(X_train, dtype=torch.float32).to(device)
    y_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1).to(device)

    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        out = model(X_t)
        loss = criterion(out, y_t)
        loss.backward()
        optimizer.step()
        if (epoch + 1) % 20 == 0:
            print(f"  Epoch {epoch+1}/{epochs}, Loss: {loss.item():.6f}")

    return model


def predict_lstm(
    model: LSTMModel,
    X: np.ndarray,
    device: Optional[str] = None
) -> np.ndarray:
    """使用訓練好的 LSTM 預測"""
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    model.eval()
    with torch.no_grad():
        X_t = torch.tensor(X, dtype=torch.float32).to(device)
        pred = model(X_t).cpu().numpy().flatten()
    return pred
