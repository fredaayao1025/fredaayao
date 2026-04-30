#!/bin/bash
cd /vol2/@apphome/trim.openclaw/data/workspace
python3 scripts/daily_strategy_signal.py > /tmp/daily_signal_output.txt 2>&1
