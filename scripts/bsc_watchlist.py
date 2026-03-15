import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.radar_engine import build_bsc_watchlist, render_watchlist


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a BSC meme watchlist snapshot every N minutes.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of candidates to print.")
    parser.add_argument("--interval-minutes", type=int, default=10, help="Loop interval in minutes.")
    parser.add_argument("--once", action="store_true", help="Run once and exit.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of human-readable text.")
    args = parser.parse_args()

    while True:
        snapshot = build_bsc_watchlist(limit=args.limit)
        if args.json:
            print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        else:
            print(render_watchlist(snapshot))

        if args.once:
            break

        time.sleep(max(1, args.interval_minutes) * 60)


if __name__ == "__main__":
    main()
