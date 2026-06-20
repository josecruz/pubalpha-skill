"""Seed CallSource — a curated, paraphrased set of real-shaped calls.

This is the demo-safe backbone for the call layer: it always works (no network),
makes the classifier demo deterministic, and ships one organic cluster (CAKE) and
one coordinated cluster ($MOON) so the wedge can be exercised offline. Live CMC
content and the paste.trade allowed surface drop in behind the same CallSource shape.
"""
import json
from datetime import datetime, timezone
from typing import List, Optional

from ..models import CallCandidate
from ..util import FIXTURES_DIR


class SeedSource:
    name = "seed"

    def __init__(self, path=None):
        self.path = path or (FIXTURES_DIR / "calls_seed.json")

    def fetch(self, since: Optional[datetime] = None) -> List[CallCandidate]:
        with open(self.path) as f:
            data = json.load(f)
        out: List[CallCandidate] = []
        for row in data.get("calls", []):
            ts = datetime.fromisoformat(row["ts"].replace("Z", "+00:00"))
            if since is not None and ts < _aware(since):
                continue
            out.append(
                CallCandidate(
                    symbol=row.get("symbol"),
                    raw_text=row["raw_text"],
                    author=row["author"],
                    source=row.get("source", "seed"),
                    ts=ts,
                    engagement=row.get("engagement", {}),
                    url=row.get("url"),
                    stance=row.get("stance"),
                    conviction=row.get("conviction"),
                )
            )
        return out


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
