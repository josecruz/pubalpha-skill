"""Offline check of the classifier (the wedge) against the seed clusters.

Run: python3 skills/public-alpha/tests/test_wedge.py
Expects: CAKE -> organic, $MOON -> coordinated, with reasons citing the deciding signals.
No network, no API key, fully deterministic.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # skills/public-alpha/
sys.path.insert(0, ROOT)

from scripts.calls import group_by_symbol, normalize          # noqa: E402
from scripts.classifier import classify                       # noqa: E402
from scripts.sources.seed import SeedSource                   # noqa: E402
from scripts.util import load_config                           # noqa: E402


def main() -> int:
    cfg = load_config()
    calls = normalize(SeedSource().fetch(), cfg)
    groups = group_by_symbol(calls)

    results = {}
    for sym, cs in sorted(groups.items()):
        res = classify(cs, sym, conf=None, cfg=cfg)
        results[sym] = res
        print(f"\n=== {sym}  ({len(cs)} calls) ===")
        print(f"  classification : {res.classification}")
        print(f"  organic_score  : {res.score}")
        print(f"  features       : {res.features}")
        for r in res.reasons:
            print(f"   - {r}")

    ok = True
    for sym, expected in (("CAKE", "organic"), ("MOON", "coordinated")):
        got = results[sym].classification
        if got != expected:
            print(f"\nFAIL: {sym} expected {expected!r}, got {got!r}")
            ok = False
    if ok:
        print("\nOK: CAKE=organic, MOON=coordinated — the wedge discriminates.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
