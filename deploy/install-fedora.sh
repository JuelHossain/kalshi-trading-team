#!/usr/bin/env bash
# Sentient Alpha on Fedora: engine + cockpit as a systemd user service,
# reachable from anywhere through Tailscale.
#
#   git clone https://github.com/JuelHossain/kalshi-trading-team.git ~/kalshi-trading-team
#   cd ~/kalshi-trading-team && bash deploy/install-fedora.sh
#
# Idempotent: run it again after `git pull` to rebuild and restart.
set -euo pipefail

REPO="$HOME/kalshi-trading-team"
cd "$REPO"

echo "== 1/6  packages"
sudo dnf install -y git python3 python3-pip nodejs npm tmux >/dev/null

echo "== 2/6  python environment"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r engine/requirements.txt

echo "== 3/6  cockpit build"
( cd frontend && npm ci --no-audit --no-fund --silent && npm run build --silent )

echo "== 4/6  secrets"
if [ ! -f engine/.env ]; then
  cp engine/.env.example engine/.env
  chmod 600 engine/.env
  echo "   engine/.env created from the example. Fill it in (or copy your laptop's) before starting."
  NEED_ENV=1
else
  chmod 600 engine/.env
  NEED_ENV=0
fi

echo "== 5/6  pre-flight"
if [ "$NEED_ENV" = "0" ]; then
  PYTHONPATH=engine .venv/bin/python engine/scripts/preflight.py || {
    echo "   pre-flight failed; fix engine/.env and re-run this script."; exit 1; }
fi

echo "== 6/6  service"
mkdir -p "$HOME/.config/systemd/user"
cp deploy/sentient-alpha.service "$HOME/.config/systemd/user/sentient-alpha.service"
systemctl --user daemon-reload
systemctl --user enable sentient-alpha >/dev/null
if [ "$NEED_ENV" = "0" ]; then
  systemctl --user restart sentient-alpha
  sleep 3
  systemctl --user --no-pager --lines=3 status sentient-alpha || true
  echo
  echo "   Cockpit on this machine: http://localhost:3002"
else
  echo "   Service installed but not started: engine/.env needs values first."
  echo "   Then: systemctl --user start sentient-alpha"
fi
# Survive logout and start at boot without anyone signing in.
loginctl enable-linger "$USER" 2>/dev/null || sudo loginctl enable-linger "$USER"

echo
echo "Done. Next: Tailscale for access from anywhere (docs/DEPLOY.md, step 5)."
