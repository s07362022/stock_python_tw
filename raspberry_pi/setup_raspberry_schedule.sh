#!/bin/bash
# 樹莓派排程安裝腳本
# 設定：1) 開機時執行一次  2) 每天早上 8 點（台灣時間）執行
#
# 使用方式：
#   chmod +x setup_raspberry_schedule.sh
#   ./setup_raspberry_schedule.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_SCRIPT="$SCRIPT_DIR/run_daily_email.sh"

# 確保 run_daily_email.sh 可執行
chmod +x "$RUN_SCRIPT"

# 設定系統時區為台灣（若尚未設定）
if [ -f /etc/timezone ]; then
    CURRENT_TZ=$(cat /etc/timezone 2>/dev/null || echo "")
    if [ "$CURRENT_TZ" != "Asia/Taipei" ]; then
        echo "建議設定系統時區為 Asia/Taipei："
        echo "  sudo timedatectl set-timezone Asia/Taipei"
        echo ""
    fi
fi

# 建立 crontab 項目
# @reboot：開機時執行（加 --boot 會先等待網路）
# 0 8 * * *：每天早上 8 點執行（使用系統時區，請確認為 Asia/Taipei）
CRON_LINE1="@reboot $RUN_SCRIPT --boot >> $SCRIPT_DIR/stock/cron_boot.log 2>&1"
CRON_LINE2="0 8 * * * $RUN_SCRIPT >> $SCRIPT_DIR/stock/cron_daily.log 2>&1"

# 建立 stock 目錄（若不存在）
mkdir -p "$SCRIPT_DIR/stock"

# 取得現有 crontab，避免覆蓋其他排程
TEMP_CRON=$(mktemp)
crontab -l 2>/dev/null > "$TEMP_CRON" || true

# 移除本專案舊的排程（若存在）
grep -v "run_daily_email.sh" "$TEMP_CRON" > "${TEMP_CRON}.new" || true
mv "${TEMP_CRON}.new" "$TEMP_CRON"

# 加入新排程
echo "$CRON_LINE1" >> "$TEMP_CRON"
echo "$CRON_LINE2" >> "$TEMP_CRON"

# 安裝 crontab
crontab "$TEMP_CRON"
rm -f "$TEMP_CRON"

echo "=========================================="
echo "  樹莓派排程已安裝完成"
echo "=========================================="
echo ""
echo "已設定："
echo "  1. 開機時執行一次（等待 90 秒後）"
echo "  2. 每天早上 8:00 執行（台灣時間）"
echo ""
echo "請確認系統時區為台灣："
echo "  timedatectl"
echo "  若非 Asia/Taipei，請執行："
echo "  sudo timedatectl set-timezone Asia/Taipei"
echo ""
echo " log 檔位置："
echo "  開機：$SCRIPT_DIR/stock/cron_boot.log"
echo "  每日：$SCRIPT_DIR/stock/cron_daily.log"
echo ""
echo "查看排程：crontab -l"
echo "移除排程：crontab -e  然後刪除相關兩行"
echo "=========================================="
