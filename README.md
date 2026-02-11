# 台股分析與美股連動預測工具

本專案整合台股預測、美股連動分析、回測策略，以及每日自動寄送美股統整與台股操作建議。

---

## 專案結構

```
202602/
├── main.py                    # 專案一：LSTM 台股預測主程式
├── daily_us_tw_email.py       # 【每日寄信】美股統整與台股建議（主程式）
├── schedule_daily_email.bat   # 【每日寄信】一鍵執行批次檔
├── strategy_stats.py          # 策略回測統計（3個月/半年）
├── dynamic_threshold.py       # 動態門檻計算模組
├── backtest_dynamic.py        # 動態門檻回測腳本
├── backtest_us_tw_tsmc.py     # 固定門檻回測腳本
├── project2_us_tw_signal.py   # 專案二：美股連動分析
├── project3_us_close_vs_tw_open.py  # 專案三：美股收盤 vs 台股開盤
├── data_fetcher.py            # 資料抓取
├── indicators.py              # 技術指標
├── model.py                   # LSTM 模型
├── config.py                  # 設定檔
├── stock/                     # 每日建議儲存目錄
│   └── {日期}_建議.txt        # 信件文字內容
├── docs/                      # 說明文件
│   ├── 檔案說明.md            # 各檔案詳細說明
│   └── 每日寄信說明.md        # 每日寄信執行指南
├── requirements.txt           # Python 依賴
└── README.md                  # 本檔案
```

---

## 每日寄信：執行方式

### 方法一：雙擊批次檔（推薦）

1.  double-click `schedule_daily_email.bat`
2.  程式會執行 `daily_us_tw_email.py --send`，直接寄出信件
3.  信件內容會同時儲存至 `stock/{當日日期}_建議.txt`

### 方法二：命令列

```bash
# 預覽（不寄出）
python daily_us_tw_email.py --preview

# 直接寄出
python daily_us_tw_email.py --send

# 互動模式（會詢問是否寄出）
python daily_us_tw_email.py
```

### 建議執行時間

- **美東收盤後** 或 **台股開盤前**（約台灣時間凌晨 5:30 後～早上 9:00 前）
- 此時可取得最新美股收盤價

---

## 環境設定

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 寄信環境變數（必要）

需設定 Gmail 應用程式密碼：

- `GMAIL_USER`：Gmail 帳號
- `GMAIL_APP_PASSWORD`：Gmail 應用程式密碼（非登入密碼）

Windows  PowerShell 範例：

```powershell
$env:GMAIL_USER = "your@gmail.com"
$env:GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
```

或於「系統內容 → 進階 → 環境變數」中永久設定。

---

## 專案模組概覽

| 模組 | 說明 |
|------|------|
| **專案一** | LSTM 預測台股走勢，產出 `result_prediction.png` |
| **專案二** | 美股連動分析，計算台股可能上漲機率 |
| **專案三** | 美股收盤與台股開盤連動比較 |
| **回測** | 美股大跌/大漲後隔天買台股的歷史勝率 |
| **每日寄信** | 整合波動率、閥值、美股表現、台股建議、歷史策略表 |

---

## 詳細說明

- 各檔案用途與邏輯：見 `docs/檔案說明.md`
- 每日寄信流程與注意事項：見 `docs/每日寄信說明.md`
