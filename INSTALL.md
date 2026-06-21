# Install — Public Alpha

> **Hand this file to an AI coding agent** (e.g. Claude Code):
> *"Read `INSTALL.md` and set this project up."*
> A human can follow it too. Steps are **ordered and gated** — run each step's **Verify** before moving on.

---

## What you're installing

**Public Alpha** is a CoinMarketCap Strategy Skill: a Python funnel that turns crypto social signal into a backtestable strategy spec (organic-vs-coordinated classifier → on-chain confirmation → regime gate → Strategy Spec / Card / Backtest).

- **Core (required):** the Python skill at `skills/public-alpha/` — the funnel CLI + the offline classifier self-test.
- **Optional add-ons:** the terminal scanner TUI (Step 6), the Claude Code `/public-alpha` skill (Step 7, already ships registered), and the web dashboard (Step 8).

Data comes from **CoinMarketCap** plus a small **bundled seed set** used for the deterministic offline tests. Quant research only — **no live execution, no real money.**

---

## Agent instructions (read first)

1. Run the steps **in order**. After each, run its **Verify** command and confirm the expected result before continuing. **Do not proceed past a failed gate** — fix it, or stop and ask the user.
2. **One secret is required and you cannot obtain it yourself:** the CoinMarketCap API key (Step 4). When you reach that step, **ask the user to paste their key**. Never invent, guess, or commit a key.
3. Commands assume **macOS** or **Debian/Ubuntu Linux** and a `bash`/`zsh` shell. Pick the branch that matches the user's OS (detect with `uname -s`).
4. The project runs fully **without a key** on bundled sample data (Steps 2–3) — use that to confirm the install before the user provides a key.

---

## Step 0 — Prerequisites (detect, then install only what's missing)

Required: **git**, **Python 3.11+**. Optional (only for the web dashboard in Step 8): **Node 20+**.

**Detect:**

```bash
git --version
python3 --version      # must be 3.11 or newer
node --version         # optional — only needed for Step 8
```

**Install if missing:**

| Tool | macOS (Homebrew) | Debian / Ubuntu (apt) |
|---|---|---|
| git | `brew install git` | `sudo apt-get update && sudo apt-get install -y git` |
| Python 3.11+ | `brew install python@3.11` | `sudo apt-get install -y python3 python3-venv python3-pip` |
| Node 20+ *(optional)* | `brew install node` | `curl -fsSL https://deb.nodesource.com/setup_20.x \| sudo -E bash - && sudo apt-get install -y nodejs` |

> If Ubuntu's default `python3` is older than 3.11: `sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv` (then use `python3.11` in the venv command below).

---

## Step 1 — Get the code

Skip if you're already inside the repo.

```bash
git clone https://github.com/josecruz/pubalpha-skill.git
cd pubalpha-skill
```

**Verify:** `ls skills/public-alpha/SKILL.md requirements.txt` lists both files.

---

## Step 2 — Python environment + dependencies

Use a virtual environment so deps stay isolated.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Dependencies: `pydantic` (v1 line), `numpy`, `PyYAML`, `requests`, `httpx`, `beautifulsoup4`, `lxml`, `textual`.

**Verify:**

```bash
python3 -c "import pydantic, numpy, yaml, requests, bs4, lxml, textual; print('deps ok')"
```

Expected: prints `deps ok`. If you get `ModuleNotFoundError`, the venv isn't active or `pip install` didn't finish.

---

## Step 3 — Offline smoke test (no API key needed) ← gate

This runs the organic-vs-coordinated classifier on the bundled seed set. Fully deterministic, no network.

```bash
python3 skills/public-alpha/tests/test_wedge.py
```

**Verify:** prints `OK: CAKE=organic, MOON=coordinated — the wedge discriminates.` and exits 0. If it fails with `ModuleNotFoundError`, return to Step 2 (activate the venv).

✅ At this point the core skill is installed and working. Steps 4–5 add live CoinMarketCap data; Steps 6–8 are optional surfaces.

---

## Step 4 — Configure the CoinMarketCap API key ← ask the user

The funnel uses the **CoinMarketCap Pro API** (paid tier) for live on-chain confirmation, the regime gate, narrative heating, and the backtest. Get a key at <https://coinmarketcap.com/api/>.

```bash
cp .env.example .env
```

Then set your key in the **repo-root** `.env` (it's gitignored and auto-loaded by the scripts):

```
CMC_PRO_API_KEY=your_real_key_here
```

> **Agent:** stop and **ask the user to paste their `CMC_PRO_API_KEY`**. Do not fabricate one or commit a real key.

**Keyless fallback:** you can skip this step entirely and run on bundled sample data by adding `--sources seed` to the Step 5 command. The live stages (on-chain, regime, narrative, backtest) will simply report "not available."

**Verify:** `grep -q '^CMC_PRO_API_KEY=.\+' .env && echo "key set"` prints `key set` (or you've chosen the keyless fallback).

---

## Step 5 — Run the funnel ← gate

```bash
python3 skills/public-alpha/scripts/run.py --symbol CAKE --risk balanced --backtest
```

Keyless variant (no `.env` key): append `--sources seed`.

**Verify:** three artifacts are written to `skills/public-alpha/results/`:

```bash
ls skills/public-alpha/results/strategy_spec.json \
   skills/public-alpha/results/strategy_card.md \
   skills/public-alpha/results/backtest_*.json
```

Read `skills/public-alpha/results/strategy_card.md` for the narrated result.

> Flags: `--risk {conservative|balanced|aggressive}` (default `balanced`), `--lookback <days>` (default 180), `--replay` re-narrates the last cached run without any live calls.

---

## Step 6 — Terminal scanner TUI (optional)

Sweeps the whole call universe and opens a navigable terminal UI. Live data needs the key from Step 4.

```bash
./skills/public-alpha/scan
```

Keys: `↑↓` navigate · `Enter` detail · `1/2/3` tabs · `r` rescan · `q` quit.

---

## Step 7 — Claude Code skill registration (ships with the repo)

The repo includes `.claude/skills/public-alpha` (a symlink to `../../skills/public-alpha`), so once the repo is opened in **Claude Code** the skill is available immediately — invoke it with `/public-alpha` or just *"build a strategy for CAKE"*, and the agent drives the funnel per `skills/public-alpha/SKILL.md`.

**Verify:**

```bash
ls -la .claude/skills/public-alpha     # → public-alpha -> ../../skills/public-alpha
```

**If missing** (e.g. a Windows clone that didn't materialize the symlink):

```bash
mkdir -p .claude/skills
ln -s ../../skills/public-alpha .claude/skills/public-alpha
```

> Optional: connect the `cmc-mcp` MCP server to give the agent CoinMarketCap's live exploration/narration tools (see `SKILL.md`). Not required — the deterministic funnel runs without it.

---

## Step 8 — Web dashboard (optional, needs Node 20+)

A browser dashboard over the same scan data.

```bash
cd web
npm install
npm run dev          # → http://localhost:3000
```

It serves the **committed data snapshot** (`web/public/scan.json`) out of the box — no extra build or scan step needed to see it running.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | Activate the venv (`source .venv/bin/activate`) and re-run Step 2. |
| `Missing required env var 'CMC_PRO_API_KEY'` | Set it in the repo-root `.env` (Step 4), or run keyless with `--sources seed`. |
| `pydantic` validation/import errors | This code uses Pydantic **v1**; `requirements.txt` pins `pydantic<2`. Reinstall into the venv. |
| `python3 --version` is below 3.11 | Install 3.11+ (Step 0) and recreate the venv with that interpreter. |
| Live CoinMarketCap calls fail / time out | Re-check the key and that your plan tier covers the endpoints, or fall back to `--sources seed`. |
| `/public-alpha` not showing in Claude Code | Confirm `.claude/skills/public-alpha` resolves (Step 7); recreate the symlink if needed. |

---

_MIT licensed. See [`README.md`](README.md) for what the funnel does and how CoinMarketCap data is used, and [`skills/public-alpha/SKILL.md`](skills/public-alpha/SKILL.md) for the agent runbook._
