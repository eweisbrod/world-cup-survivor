"""SuperDuperGames archive -> hwlib game records.

Reads the .raw transcripts mirrored at
https://github.com/Quuxplusone/Homeworlds/tree/master/superdupergames-archive
(2,755+ games, 2005-2020).  Both the verbose ("Build G1 Wil") and abbreviated
("B G1 Wil") move notations appear in that archive; both are handled.
"""

import collections
import glob
import os
import re

HEADER_MOVE = re.compile(r'^\s*\d+\)\s*([^:]+):\s*(.*)$')
HOMEWORLD = re.compile(
    r'^(?:Homeworld|H)\s+([RGBY][123])\s+([RGBY][123])\s+([RGBY][123])\s*$', re.I)
PARTICIPANT = re.compile(r'([^,()]+)\s*\(([NSEW])\)')

VERBS = {"b": "build", "t": "trade", "s": "sacrifice", "m": "move",
         "d": "discover", "h": "homeworld", "a": "attack",
         "c": "catastrophe", "p": "pass"}


def _verb(token):
    t = token.lower()
    return VERBS.get(t, t) if len(t) == 1 else t


def load(archive_dir, skip_variants=("Sinister",), min_plies=8):
    """Yield hwlib game records for every parseable two-player game."""
    games = []
    for path in sorted(glob.glob(os.path.join(archive_dir, "*.raw"))):
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().split("\n")

        participants = winner = None
        variants = ""
        for ln in lines[:8]:
            if ln.startswith("Participants:"):
                participants = PARTICIPANT.findall(ln[len("Participants:"):])
            elif ln.startswith("Winner:"):
                winner = ln.split(":", 1)[1].strip()
            elif ln.startswith("Variants:"):
                variants = ln

        if not participants or len(participants) != 2 or not winner:
            continue
        if any(v in variants for v in skip_variants):
            continue

        plies = [(m.group(1).strip(), m.group(2).strip())
                 for ln in lines if (m := HEADER_MOVE.match(ln))]
        if len(plies) < min_plies:
            continue

        sides = []
        for who, text in plies[:2]:
            m = HOMEWORLD.match(text)
            if m:
                sides.append({"name": who,
                              "stars": [m.group(1).upper(), m.group(2).upper()],
                              "ship": m.group(3).upper()})
        if len(sides) != 2 or sides[0]["name"] == sides[1]["name"]:
            continue
        if winner not in (sides[0]["name"], sides[1]["name"]):
            continue

        moves = []
        for who, text in plies[2:]:
            parts = text.split()
            if not parts:
                continue
            moves.append({"player": who,
                          "verb": _verb(parts[0]),
                          "args": [p.upper() for p in parts[1:]]})

        games.append({"id": os.path.basename(path)[:-4], "source": "sdg",
                      "p1": sides[0], "p2": sides[1],
                      "winner": winner, "moves": moves})
    return games


def summary(games):
    src = collections.Counter(g["source"] for g in games)
    return "%d games (%s)" % (len(games), ", ".join("%s: %d" % kv for kv in src.items()))
