#!/usr/bin/env python3
"""Run the Homeworlds opening analysis over any supported source.

    python3 analyze.py sdg  /path/to/superdupergames-archive
    python3 analyze.py bga  /path/to/saved-replays
    python3 analyze.py bga  /path/to/saved-replays --inspect

Add --p1 STARS to restrict to games where the first player opened with those stars
(e.g. --p1 B1Y2), and --depth N to change the opening length reported.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hwlib
from sources import bga, sdg


def load(source, path):
    if source == "sdg":
        return sdg.load(path)
    winners_path = os.path.join(path, "winners.json")
    winners = {}
    if os.path.exists(winners_path):
        with open(winners_path, encoding="utf-8") as fh:
            winners = json.load(fh)
    return bga.parse_dir(path, winners)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", choices=["sdg", "bga"])
    ap.add_argument("path")
    ap.add_argument("--p1", help="only games where P1's stars are these, e.g. B1Y2")
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--min-n", type=int, default=15)
    ap.add_argument("--inspect", action="store_true",
                    help="bga only: print event types from a few logs and exit")
    args = ap.parse_args()

    if args.inspect:
        print(bga.inspect_dir(args.path))
        return

    games = load(args.source, args.path)
    if not games:
        print("No games parsed from %s" % args.path)
        return
    print("Loaded %s\n" % sdg.summary(games))

    ratings = hwlib.Ratings(games)
    elite = ratings.top()
    print("Top-rated players: %s\n" %
          ", ".join(sorted(elite, key=ratings.rating, reverse=True)[:12]))

    pool = games
    if args.p1:
        want = "".join(sorted([args.p1[i:i + 2].upper() for i in (0, 2)]))
        pool = [g for g in games if hwlib.stars(g["p1"]) == want]
        print("P1 opened %s in %d games\n" % (args.p1.upper(), len(pool)))
        if not pool:
            return

    print(hwlib.render(hwlib.breakdown(pool, ratings, lambda g: hwlib.stars(g["p1"]),
                                       "p1", args.min_n),
                       "First player's star pair", "P1 stars"), "\n")
    print(hwlib.render(hwlib.breakdown(pool, ratings, lambda g: hwlib.freeze_class(g["p1"]),
                                       "p1", args.min_n),
                       "First player's instafreeze exposure", "class"), "\n")
    print(hwlib.render(hwlib.breakdown(pool, ratings, lambda g: hwlib.sizes(g["p2"]),
                                       "p2", args.min_n),
                       "Second player's star sizes", "P2 sizes"), "\n")
    print(hwlib.render(hwlib.breakdown(pool, ratings, lambda g: hwlib.setup(g["p2"]),
                                       "p2", args.min_n),
                       "Second player's full setup", "P2 setup"), "\n")

    race = hwlib.medium_race(pool)
    if race["games"]:
        print("### First medium ship ###\n   decided %d games; that player won %d (%.0f%%)\n"
              % (race["games"], race["first_medium_won"], 100 * race["rate"]))

    for side in ("p1", "p2"):
        rows = hwlib.opening_lines(pool, side, args.depth, min_n=max(4, args.min_n // 2))
        print("### %s's best %d-move openings ###" % (side.upper(), args.depth))
        for rate, n, w, line, setups in rows[:8]:
            top = ", ".join("%s x%d" % kv for kv in setups.most_common(3))
            print("   %2d/%2d = %3.0f%%   setups: %s" % (w, n, 100 * rate, top))
            for i, mv in enumerate(line.split(" | "), 1):
                print("        %d. %s" % (i, mv))
        print()


if __name__ == "__main__":
    main()
