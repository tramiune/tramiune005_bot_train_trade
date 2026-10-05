#!/bin/bash
source web_app/backend/.venv/bin/activate

COINS=("SOLUSDT" "XRPUSDT" "AVAXUSDT" "LINKUSDT" "OPUSDT")
START_MONTH="2022-09"

for COIN in "${COINS[@]}"; do
    echo "Downloading 4 years of 1m data for $COIN..."
    python .agents/skills/honest-backtest/scripts/bt_data.py $COIN 1m $START_MONTH
    echo "Finished $COIN."
done
echo "ALL DOWNLOADS COMPLETED."
