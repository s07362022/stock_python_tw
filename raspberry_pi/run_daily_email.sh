#!/bin/bash
# 每日美股台股建議 - 執行腳本（樹莓派用）
# 用法：./run_daily_email.sh [--boot]
#   --boot：開機時執行，會先等待 90 秒讓網路就緒

set -e

# 專案目錄（與此腳本同目錄）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 若為開機執行，等待網路就緒
if [ "$1" = "--boot" ]; then
    echo "[$(date)] 開機執行：等待 90 秒讓網路就緒..."
    sleep 90
fi

# 設定時區為台灣時間（確保 8 點為台灣早上 8 點）
export TZ=Asia/Taipei

# 使用 python3
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "[$(date)] 開始執行每日美股台股建議..."
$PYTHON_CMD daily_us_tw_email.py --send
echo "[$(date)] 執行完成。"
