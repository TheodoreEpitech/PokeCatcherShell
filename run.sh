#!/usr/bin/env bash
if [[ "$1" == "--tui" || "$1" == "-t" ]]; then
  COLORTERM=truecolor FORCE_COLOR=1 python3 tui.py
else
  python3 main.py
fi