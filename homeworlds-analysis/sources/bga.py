"""Board Game Arena replay logs -> hwlib game records.

READ THIS FIRST
---------------
BGA's terms of service prohibit automated scraping, and serving replay logs costs them
real money.  Liam Johansson's write-up, which describes the request endpoints used here,
carries the same warning and explicitly retracts the multi-account trick he originally
used to get past BGA's per-account replay cap:

    "Please note that web scraping is not allowed by bga's terms of service, so users
     may be banned for scraping... I no longer endorse or recommend this method.  If you
     are interested in collecting many replays, reach out to bga staff first."

So this module does two separate things, and you should think of them separately:

  * `parse_dir()` / `parse_log()` - turn replay-log JSON you already have into game
    records.  No network access.  This is the part that does the actual work, and it is
    fine to run on logs you obtained legitimately (your own games saved out of the
    browser, or a dump BGA staff gave you).

  * `fetch_logs()` - an ordinary, single-session, heavily throttled downloader.  It
    refuses to run unless you pass `i_have_permission=True`, and there is deliberately
    no login or account-rotation code in here.  Ask BGA staff before using it.

The move-type mapping below is the one piece that needs a real Homeworlds replay to pin
down; run `inspect_dir()` on a single saved log and it will print exactly what to fill in.
"""

import collections
import json
import os
import time
import urllib.parse
import urllib.request

LOGS_URL = "https://boardgamearena.com/archive/archive/logs.html"
GAMESTATS_URL = "https://boardgamearena.com/gamestats/gamestats/getGames.html"

# --------------------------------------------------------------------------
# BGA emits one entry per game event with a `type` and an `args` dict.  Map each
# Homeworlds event type onto an hwlib verb, plus the `args` keys holding the piece
# arguments in hwlib order.  Verified names go here; run inspect_dir() to fill them.
#
#   build       -> [piece]
#   trade       -> [old_piece, new_piece]
#   discover    -> [ship, from_system, new_star]
#   move        -> [ship, from_system, to_system]
#   attack      -> [piece]
#   sacrifice   -> [piece]
#   catastrophe -> [color_or_piece]
# --------------------------------------------------------------------------
MOVE_TYPES = {
    # "buildShip":   ("build",     ["piece"]),
    # "tradeShip":   ("trade",     ["piece", "newPiece"]),
    # "discover":    ("discover",  ["ship", "system", "star"]),
    # "moveShip":    ("move",      ["ship", "system", "targetSystem"]),
    # "attackShip":  ("attack",    ["piece"]),
    # "sacrifice":   ("sacrifice", ["piece"]),
    # "catastrophe": ("catastrophe", ["color"]),
}

# Event type(s) that announce each player's homeworld, and the args holding its pieces.
SETUP_TYPES = {
    # "chooseHomeworld": (["star1", "star2"], "ship"),
}

PLAYER_KEYS = ("player_name", "playerName", "player")


def _entries(blob):
    """Yield the individual event dicts from a replay-log payload."""
    data = blob.get("data", blob)
    logs = data.get("logs", data) if isinstance(data, dict) else data
    for packet in logs if isinstance(logs, list) else []:
        for item in packet.get("data", []) if isinstance(packet, dict) else []:
            if isinstance(item, dict):
                yield packet, item


def _player_of(args):
    for k in PLAYER_KEYS:
        if isinstance(args, dict) and k in args:
            return str(args[k])
    return None


def _piece(value):
    """Normalise a BGA piece token to hwlib form, e.g. 'g3'/'green3' -> 'G3'."""
    s = str(value).strip().upper()
    if len(s) == 2 and s[0] in "RGBY" and s[1] in "123":
        return s
    for name, letter in (("RED", "R"), ("GREEN", "G"), ("BLUE", "B"), ("YELLOW", "Y")):
        if s.startswith(name):
            tail = s[len(name):].strip()
            if tail and tail[0] in "123":
                return letter + tail[0]
            for word, digit in (("SMALL", "1"), ("MEDIUM", "2"), ("LARGE", "3")):
                if word in s:
                    return letter + digit
    return s


def inspect_log(path):
    """Report the event types in one saved replay, so MOVE_TYPES can be completed."""
    with open(path, encoding="utf-8") as fh:
        blob = json.load(fh)
    seen = collections.OrderedDict()
    for _, item in _entries(blob):
        t = item.get("type", "?")
        if t not in seen:
            seen[t] = {"count": 0, "log": item.get("log", ""),
                       "args": {k: v for k, v in (item.get("args") or {}).items()
                                if not k.startswith("_")}}
        seen[t]["count"] += 1
    lines = ["%s: %d distinct event types" % (os.path.basename(path), len(seen))]
    for t, info in seen.items():
        lines.append("  %-24s x%-4d  log=%r" % (t, info["count"], info["log"][:70]))
        lines.append("      args=%s" % json.dumps(info["args"])[:200])
    return "\n".join(lines)


def inspect_dir(directory, limit=3):
    paths = sorted(p for p in os.listdir(directory) if p.endswith(".json"))
    return "\n\n".join(inspect_log(os.path.join(directory, p)) for p in paths[:limit])


def parse_log(path, winner=None):
    """Turn one saved replay-log JSON into an hwlib game record (or None)."""
    if not MOVE_TYPES or not SETUP_TYPES:
        raise RuntimeError(
            "MOVE_TYPES/SETUP_TYPES are empty - run inspect_dir() on a saved Homeworlds "
            "replay and fill in the mapping at the top of this module.")

    with open(path, encoding="utf-8") as fh:
        blob = json.load(fh)

    sides, moves, order = [], [], []
    for _, item in _entries(blob):
        t, args = item.get("type"), item.get("args") or {}
        who = _player_of(args)

        if t in SETUP_TYPES and who:
            star_keys, ship_key = SETUP_TYPES[t]
            sides.append({"name": who,
                          "stars": [_piece(args[k]) for k in star_keys if k in args],
                          "ship": _piece(args.get(ship_key, ""))})
            continue

        if t in MOVE_TYPES and who:
            verb, keys = MOVE_TYPES[t]
            moves.append({"player": who, "verb": verb,
                          "args": [_piece(args[k]) for k in keys if k in args]})
            if who not in order:
                order.append(who)

    if len(sides) != 2 or any(len(s["stars"]) != 2 for s in sides):
        return None
    if winner is None:
        return None  # supply from the table metadata; logs alone are unreliable here

    return {"id": os.path.splitext(os.path.basename(path))[0], "source": "bga",
            "p1": sides[0], "p2": sides[1], "winner": winner, "moves": moves}


def parse_dir(directory, winners=None):
    """Parse every .json replay in `directory`.

    `winners` maps table id -> winning player name; BGA puts the result in the table
    metadata rather than reliably in the log stream, so pass it alongside (a small
    winners.json written when you save each replay is the easiest route).
    """
    winners = winners or {}
    games = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json") or name == "winners.json":
            continue
        table = os.path.splitext(name)[0]
        g = parse_log(os.path.join(directory, name), winners.get(table))
        if g:
            games.append(g)
    return games


def fetch_logs(table_ids, out_dir, cookie, i_have_permission=False,
               delay=3.0, user_agent="homeworlds-analysis/1.0"):
    """Download replay logs for `table_ids` into `out_dir`, one at a time.

    `cookie` is the Cookie header from your own logged-in browser session.  There is no
    login helper and no account rotation here on purpose: BGA caps replay access per
    account deliberately, and working around that cap is what the original write-up
    retracted.  Get BGA staff's go-ahead before pointing this at anything.

    Already-downloaded tables are skipped, so an interrupted run resumes for free.
    """
    if not i_have_permission:
        raise PermissionError(
            "BGA's terms of service prohibit automated access. Ask BGA staff first, "
            "then pass i_have_permission=True.")

    os.makedirs(out_dir, exist_ok=True)
    fetched, skipped = [], []
    for table in table_ids:
        dest = os.path.join(out_dir, "%s.json" % table)
        if os.path.exists(dest):
            skipped.append(table)
            continue
        url = LOGS_URL + "?" + urllib.parse.urlencode({"table": table, "translated": "true"})
        req = urllib.request.Request(url, headers={"Cookie": cookie,
                                                   "User-Agent": user_agent,
                                                   "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", "replace")
        blob = json.loads(body)
        if blob.get("status") != 1:
            raise RuntimeError("table %s: %s" % (table, blob.get("error", body[:200])))
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(blob, fh)
        fetched.append(table)
        time.sleep(delay)
    return {"fetched": fetched, "skipped": skipped}
