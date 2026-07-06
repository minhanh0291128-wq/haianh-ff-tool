#!/usr/bin/env bash
set -e

apt-get update -qq && apt-get install -y -qq --no-install-recommends \
  libnss3 libnspr4 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 \
  libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 libxdamage1 \
  libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2t64 \
  2>/dev/null || true

pip install -q -r requirements.txt

# Install Playwright Chromium into the project directory to survive build→runtime transition
export PLAYWRIGHT_BROWSERS_PATH="$(pwd)/.browsers"
python -m playwright install chromium 2>&1
echo "export PLAYWRIGHT_BROWSERS_PATH=$(pwd)/.browsers" >> /opt/render/project/.env 2>/dev/null || true
