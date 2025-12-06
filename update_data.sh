#!/bin/bash

# Nasdaq Data Updater
# Runs daily at 22:01 to fetch latest market data

cd /Users/megatron16000/.gemini/antigravity/scratch/nasdaq_race

# Log file
LOG_FILE="update_log.txt"

# Run the data fetcher
echo "=== Data update started at $(date) ===" >> "$LOG_FILE"
python3 data_fetcher.py >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Data update completed successfully at $(date)" >> "$LOG_FILE"
else
    echo "✗ Data update failed at $(date)" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
