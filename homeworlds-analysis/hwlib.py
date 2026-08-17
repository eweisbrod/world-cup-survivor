"""Source-agnostic analysis for Binary Homeworlds game records.

A game record is a plain dict:

    {
      "id":     "12345",            # unique within a source
      "source": "sdg" | "bga",
      "p1":     {"name": str, "stars": ["B1","Y3"], "ship": "G3"},   # first to set up
      "p2":     {"name": str, "stars": [...],       "ship": ...},
      "winner": str,                # must equal p1["name"] or p2["name"]
      "moves":  [ {"player": str, "verb": str, "args": [str, ...]}, ... ],
    }

`verb` is one of: build, trade, discover, move, attack, sacrifice, catastrophe, pass.
`args` are pieces (e.g. "G1") and system labels, in the order the source records them;
only the leading piece arguments are used here, so system-naming differences between
sources do not matter for any of the statistics below.

Everything in this module works off that schema alone, so SuperDuperGames archives and
Board Game Arena replays are interchangeable inputs.
"""

import collections
import math

PIECES = [c + s for c in "RGBY" for s in "123"]
COPIES_PER_PIECE = 3


# ---------------------------------------------------------------- helpers

def stars(side):
    """Canonical star-pair key, e.g. 'B1Y3'."""
    return "".join(sorted(side["stars"]))


def sizes(side):
    return "".join(sorted(p[1] for p in side["stars"]))


def colors(side):
    return "".join(sorted(set(p[0] for p in side["stars"])))


def setup(side):
    """Star pair plus starting ship, e.g. 'B1Y3/G3'."""
    return stars(side) + "/" + side["ship"]


def freeze_class(side):
    """Instafreeze exposure (Baker's tactic, per O'Dwyer's write-up).

    A homeworld containing a small star of some colour has pre-spent one of that
    colour's three smalls, so an opponent only needs to take the other two to price
    that colour out of reach.  Blue is the exception: you cannot freeze a colour the
    freezer themself cannot do without, and nobody can trade at all without blue.
    """
    smalls = [p for p in side["stars"] if p[1] == "1"]
    if not smalls:
        return "no small star"
    if len(smalls) == 2:
        return "two small stars"
    return {
        "B": "small BLUE (not freezable)",
        "R": "small RED (freezable)",
        "Y": "small YELLOW (freezable)",
        "G": "small GREEN (freezable)",
    }[smalls[0][0]]


def acquisitions(game, piece, max_plies=None):
    """[(side, ply)] for each time a player gains `piece` as a ship (build or trade)."""
    out = []
    ms = game["moves"] if max_plies is None else game["moves"][:max_plies]
    for i, m in enumerate(ms):
        side = "p1" if m["player"] == game["p1"]["name"] else "p2"
        got = ((m["verb"] == "build" and m["args"][:1] == [piece]) or
               (m["verb"] == "trade" and m["args"][1:2] == [piece]))
        if got:
            out.append((side, i))
    return out


def first_medium(game):
    """(side, ply) of the first size-2 ship either player obtains, or (None, None)."""
    for i, m in enumerate(game["moves"]):
        a = m["args"]
        got = ((m["verb"] == "build" and a and a[0][1:2] == "2") or
               (m["verb"] == "trade" and len(a) > 1 and a[1][1:2] == "2"))
        if got:
            return ("p1" if m["player"] == game["p1"]["name"] else "p2"), i
    return None, None


def opening(game, side, depth=4):
    """The first `depth` moves by `side` as compact strings, or None if unavailable.

    System names are deliberately dropped: they are player-chosen on both platforms and
    carry no information, while piece identities carry all of it.
    """
    name = game[side]["name"]
    seq = []
    for m in game["moves"]:
        if m["player"] != name:
            continue
        a = m["args"]
        if m["verb"] == "build" and a:
            seq.append("Build %s" % a[0])
        elif m["verb"] == "trade" and len(a) > 1:
            seq.append("Trade %s->%s" % (a[0], a[1]))
        elif m["verb"] == "discover" and len(a) > 2:
            seq.append("Discover %s to a new %s star" % (a[0], a[2]))
        elif m["verb"] in ("move", "attack", "sacrifice", "catastrophe") and a:
            seq.append("%s %s" % (m["verb"].capitalize(), a[0]))
        elif m["verb"] == "pass":
            seq.append("Pass")
        else:
            return None
        if len(seq) == depth:
            return seq
    return None


# ---------------------------------------------------------------- ratings

class Ratings:
    """Bradley-Terry strengths fitted to the games themselves.

    `expected(game, side)` is the win probability implied by player strength alone, so
    `actual - expected` isolates how much a setup or line over-performs the people who
    happen to play it.  Without this, strong players' preferences masquerade as strong
    openings.
    """

    def __init__(self, games, iterations=400, step=0.05, ridge=0.01):
        self.players = sorted({g["p1"]["name"] for g in games} |
                              {g["p2"]["name"] for g in games})
        self.index = {p: i for i, p in enumerate(self.players)}
        self.r = [0.0] * len(self.players)
        self.n_games = collections.Counter()
        for g in games:
            self.n_games[g["p1"]["name"]] += 1
            self.n_games[g["p2"]["name"]] += 1
        for _ in range(iterations):
            grad = [0.0] * len(self.players)
            for g in games:
                a, b = self.index[g["p1"]["name"]], self.index[g["p2"]["name"]]
                p = 1.0 / (1.0 + math.exp(-(self.r[a] - self.r[b])))
                y = 1.0 if g["winner"] == g["p1"]["name"] else 0.0
                grad[a] += y - p
                grad[b] -= y - p
            for i in range(len(self.players)):
                self.r[i] += step * (grad[i] - ridge * self.r[i])

    def rating(self, player):
        return self.r[self.index[player]]

    def expected(self, game, side="p1"):
        a = self.rating(game["p1"]["name"])
        b = self.rating(game["p2"]["name"])
        p1 = 1.0 / (1.0 + math.exp(-(a - b)))
        return p1 if side == "p1" else 1.0 - p1

    def top(self, min_games=60, min_rating=3.0):
        return {p for p in self.players
                if self.n_games[p] >= min_games and self.rating(p) > min_rating}


# ---------------------------------------------------------------- tables

def won(game, side):
    return game["winner"] == game[side]["name"]


def breakdown(games, ratings, key, side="p1", min_n=15):
    """Group games by key(game) and report actual vs skill-expected win rate.

    Returns rows of (edge, key, n, actual, expected) sorted best-first.
    """
    buckets = collections.defaultdict(list)
    for g in games:
        k = key(g)
        if k is not None:
            buckets[k].append(g)
    rows = []
    for k, sub in buckets.items():
        if len(sub) < min_n:
            continue
        actual = sum(1 for g in sub if won(g, side)) / len(sub)
        exp = sum(ratings.expected(g, side) for g in sub) / len(sub)
        rows.append((actual - exp, k, len(sub), actual, exp))
    return sorted(rows, reverse=True)


def render(rows, title, label="key"):
    out = ["### %s ###" % title,
           "   %-26s %5s  %8s %9s %7s" % (label, "n", "actual", "expected", "edge")]
    for edge, k, n, actual, exp in rows:
        out.append("   %-26s %5d  %7.0f%% %8.0f%% %+6.1f" %
                   (k, n, 100 * actual, 100 * exp, 100 * edge))
    return "\n".join(out)


def opening_lines(games, side="p1", depth=4, min_n=8):
    """Most successful `depth`-move openings for `side`. Rows: (rate, n, wins, line, setups)."""
    buckets = collections.defaultdict(list)
    for g in games:
        line = opening(g, side, depth)
        if line:
            buckets[" | ".join(line)].append(g)
    rows = []
    for line, sub in buckets.items():
        if len(sub) < min_n:
            continue
        w = sum(1 for g in sub if won(g, side))
        setups = collections.Counter(setup(g[side]) for g in sub)
        rows.append((w / len(sub), len(sub), w, line, setups))
    return sorted(rows, reverse=True)


def medium_race(games):
    """Does getting the first medium ship predict the win?"""
    n = w = 0
    per_side = collections.Counter()
    for g in games:
        side, _ = first_medium(g)
        if side is None:
            continue
        n += 1
        per_side[side] += 1
        if won(g, side):
            w += 1
    return {"games": n, "first_medium_won": w,
            "rate": (w / n) if n else None, "by_side": dict(per_side)}


def stash_after_setup(game):
    """Copies of each piece still in the stash once both homeworlds are placed."""
    left = {p: COPIES_PER_PIECE for p in PIECES}
    for side in ("p1", "p2"):
        for p in game[side]["stars"] + [game[side]["ship"]]:
            if p in left:
                left[p] -= 1
    return left
