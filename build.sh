#!/usr/bin/env bash
pip install -r requirements.txt
playwright install chromium --with-deps 2>&1 || playwright install chromium 2>&1
