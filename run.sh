#!/usr/bin/env bash
if [[ "$1" == "--cli" || "$1" == "-c" ]]; then
  python3 old.py
else
  COLORTERM=truecolor FORCE_COLOR=1 python3 main.py
fi