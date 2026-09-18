# Deploying to a Fedora mini PC

One process. The engine serves the API and the built cockpit on port 3002 as
a systemd *user* service that starts at boot. Tailscale puts the mini PC on a
private network with your phone and laptop, so the dashboard is reachable
from anywhere over HTTPS without opening a single router port. Claude Code
runs on the mini PC too, and Remote Control lets you drive it from the
Claude app on your phone.

Every command below runs **on the mini PC** unless it says laptop.

## 1. Fedora basics

```bash
sudo dnf upgrade -y --refresh
sudo dnf install -y git python3 python3-pip nodejs npm tmux
python3 --version    # 3.12 or newer is needed; on Fedora 41+ this is 3.13
node --version       # 20 or newer
```

If `python3` is older than 3.12: `sudo dnf install -y python3.12` and use
`python3.12 -m venv .venv` in step 3 instead of the script.

Give the machine a stable name; it becomes its address on Tailscale:

```bash
sudo hostnamectl set-hostname minipc
```

## 2. Get the code

```bash
git clone https://github.com/JuelHossain/kalshi-trading-team.git ~/kalshi-trading-team
cd ~/kalshi-trading-team
git checkout feat/orrery-cockpit     # or main once the branch is merged
```

## 3. Bring the secrets over

The engine reads `engine/.env`. Copy the laptop's file rather than typing
keys again. From the **laptop** (PowerShell or Git Bash), with the mini PC's
IP or name:

```bash
scp C:/Users/jrrah/Projects/kalshi-phone/engine/.env <user>@minipc:~/kalshi-trading-team/engine/.env
```

Then on the mini PC:

```bash
chmod 600 ~/kalshi-trading-team/engine/.env
```

Keep `KALSHI_ENV=demo` and `IS_PAPER_TRADING=true` in it until the paper
week is over. Everything in that file can later be changed from the
cockpit's Config view; the engine writes it back to the same file.

## 4. Install and start

```bash
cd ~/kalshi-trading-team
bash deploy/install-fedora.sh
```

The script creates the virtualenv, installs the engine's pinned
dependencies, builds the cockpit, runs the pre-flight check against Kalshi
and Gemini, installs `deploy/sentient-alpha.service` as a user service,
enables it, starts it, and turns on lingering so it runs without anyone
signed in. Check it:

```bash
systemctl --user status sentient-alpha
journalctl --user -u sentient-alpha -f        # live console output
curl -s localhost:3002/api/health
```

Open `http://localhost:3002` in a browser on the mini PC: the cockpit.
Sign in with the `AUTH_PASSWORD` from `engine/.env`.

Useful later:

```bash
systemctl --user restart sentient-alpha
bash deploy/update.sh        # git pull, rebuild, restart
```

## 5. Reach it from anywhere: Tailscale

Tailscale is a private network between your own devices. Nothing is
exposed to the internet; the phone reaches the mini PC through an
encrypted tunnel from any network.

On the mini PC:

```bash
sudo dnf config-manager addrepo --from-repofile=https://pkgs.tailscale.com/stable/fedora/tailscale.repo
sudo dnf install -y tailscale
sudo systemctl enable --now tailscaled
sudo tailscale up
```

`tailscale up` prints a link. Open it on any device and sign in (Google,
Microsoft, GitHub or Apple account). Then publish the cockpit with HTTPS on
the tailnet, which also handles the certificate:

```bash
sudo tailscale serve --bg 3002
tailscale serve status
```

The status shows the address, of the form `https://minipc.<tailnet>.ts.net`.
Because `tailscale serve` connects to port 3002 locally, the firewall stays
closed to everything else; you do not need to open 3002.

On the phone: install the Tailscale app, sign in with the same account,
turn it on. The cockpit is at that `https://…ts.net` address from anywhere.
On the laptop: same.

If you would rather keep a plain LAN address as well:

```bash
sudo firewall-cmd --permanent --add-port=3002/tcp && sudo firewall-cmd --reload
```

## 6. Claude Code on the mini PC, driven from your phone

Install Claude Code and sign in once (the sign-in opens a browser; on a
headless box it prints a link and a code instead):

```bash
sudo npm install -g @anthropic-ai/claude-code
cd ~/kalshi-trading-team
claude          # first run: sign in, then /exit
```

Start a session with Remote Control inside `tmux`, so it survives you
closing the terminal:

```bash
tmux new -d -s claude 'cd ~/kalshi-trading-team && claude rc'
```

On the phone, open the Claude app, go to Code, and the mini PC's session is
listed; open it and work from there. To attach from a keyboard instead,
`tmux attach -t claude`. To restart it after a reboot, run the `tmux new`
line again (or add it to a user service later).

For a shell from the phone when needed, Fedora already runs `sshd`;
Tailscale carries it: `ssh <user>@minipc` from any SSH app on the phone.

## 7. Keep the laptop out of it

Once the mini PC runs the engine, stop the laptop's copy so two engines do
not trade the same demo account, and do your edits on the mini PC through
Claude Code. Push to GitHub from the mini PC as usual; `deploy/update.sh`
brings a rebuilt cockpit into the running service.

## Where things live on the mini PC

| Path | What |
|---|---|
| `~/kalshi-trading-team/engine/.env` | Every secret and setting. The cockpit's Config view edits this file. |
| `~/kalshi-trading-team/ghost_memory.db` | Synapse queues and vault reservations. |
| `~/kalshi-trading-team/ghost_ledger.db` | Every Brain decision and every fill. |
| `~/kalshi-trading-team/ghost_journal.db` | Every event the bot emitted. |
| `journalctl --user -u sentient-alpha` | Console output with timestamps. |

Back up the three `.db` files and `.env` if you ever rebuild the machine.
