"""Shared helpers: config + .env loading, paths. No third-party deps beyond PyYAML."""
import os
from pathlib import Path

import yaml

SKILL_ROOT = Path(__file__).resolve().parent.parent      # skills/public-alpha/
REPO_ROOT = SKILL_ROOT.parent.parent                     # repo root
CONFIG_PATH = SKILL_ROOT / "config" / "default.yaml"
RESULTS_DIR = SKILL_ROOT / "results"
FIXTURES_DIR = SKILL_ROOT / "scripts" / "fixtures"


def load_config(path=None) -> dict:
    """Load the Skill config (default.yaml). The agent can override values per run."""
    p = Path(path) if path else CONFIG_PATH
    with open(p) as f:
        return yaml.safe_load(f)


def load_env(path=None) -> None:
    """Minimal .env loader (avoids a python-dotenv dependency).

    Reads skills/public-alpha/.env then the repo-root .env. Does not overwrite
    variables already present in the environment.
    """
    candidates = []
    if path:
        candidates.append(Path(path))
    candidates += [SKILL_ROOT / ".env", REPO_ROOT / ".env"]
    for p in candidates:
        if not p.exists():
            continue
        for raw in p.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_key(name: str, required: bool = False) -> str:
    """Fetch an env var, loading .env files first."""
    load_env()
    val = os.environ.get(name, "")
    if required and not val:
        raise RuntimeError(
            f"Missing required env var {name!r}. Set it in skills/public-alpha/.env "
            f"(copy .env.example). Never commit real keys."
        )
    return val
