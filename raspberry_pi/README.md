# Raspberry Pi - Daily US/TW Stock Recommendation

This folder contains all files needed to run the "Daily US Stock Summary & Taiwan Stock Recommendation" on Raspberry Pi.

---

## Core Files (Daily Email)

| File | Description |
|------|-------------|
| `daily_us_tw_email.py` | Main script: generates report and sends email |
| `dynamic_threshold.py` | Dynamic threshold module (volatility-based) |
| `strategy_stats.py` | Strategy backtest (7 stocks) |
| `screen_top_stocks.py` | Top 50 stocks screening |

## Scripts

| File | Description |
|------|-------------|
| `run_daily_email.sh` | Execution script (supports `--boot`) |
| `setup_raspberry_schedule.sh` | Cron setup (boot + daily 8:00) |

---

## Quick Install

```bash
cd /home/pi/202602
pip3 install -r requirements.txt
chmod +x setup_raspberry_schedule.sh
./setup_raspberry_schedule.sh
sudo timedatectl set-timezone Asia/Taipei
```

---

## Schedule

- **On boot**: Run once after 90 seconds (wait for network)
- **Daily 8:00**: Taiwan time, fixed execution and send email

---

## Manual Run

```bash
./run_daily_email.sh           # Execute and send
./run_daily_email.sh --boot    # Simulate boot (90s wait)
python3 daily_us_tw_email.py --preview   # Preview only
python3 daily_us_tw_email.py --send      # Send directly
```

---

## Output

- `stock/{YYYY-MM-DD}_建議.txt` - Daily recommendation
- `stock/cron_boot.log` - Boot execution log
- `stock/cron_daily.log` - Daily execution log

---

For detailed instructions in Traditional Chinese, see `樹莓派說明.md`.
