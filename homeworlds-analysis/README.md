# Homeworlds opening analysis

Skill-adjusted opening statistics for Binary Homeworlds, built to run over more than one
game archive.

The analysis is separated from the file format, so the same tables come out of a
SuperDuperGames `.raw` archive or a folder of Board Game Arena replay logs.

```
hwlib.py          all analysis; knows nothing about either site's format
sources/sdg.py    SuperDuperGames .raw  -> game records   (working, 2,882 games)
sources/bga.py    BGA replay-log JSON   -> game records   (parser needs one sample log)
analyze.py        CLI
```

## Usage

```bash
git clone --depth 1 https://github.com/Quuxplusone/Homeworlds /tmp/hw
python3 analyze.py sdg /tmp/hw/superdupergames-archive
python3 analyze.py sdg /tmp/hw/superdupergames-archive --p1 B1Y2   # one opening
python3 analyze.py bga ./replays                                    # once mapped
```

## What it reports

- **Setup win rates, skill-adjusted.** Bradley-Terry strengths are fitted to the games
  themselves, and every table shows actual vs. expected win rate. The `edge` column is
  the difference — how much a setup beats the players who choose it. Without this you
  are mostly measuring who likes which opening.
- **Instafreeze exposure.** A homeworld with a small star of some colour has pre-spent
  one of that colour's three smalls, so an opponent needs only the other two to price it
  out of reach. Blue is exempt — nobody can trade without blue, so no one can afford to
  be the freezer. See `hwlib.freeze_class`.
- **The first-medium race.** Whoever reaches a size-2 ship first wins about 57% of SDG
  games, the cleanest single predictor in the opening.
- **N-move opening lines** for either seat, grouped with the setups that played them.
- `stash_after_setup()` for the piece accounting that decides whether a build comes out
  small or medium.

Rows below roughly n=30 are illustrations, not findings. The setup-level tables carry
enough games to lean on; individual four-move lines usually do not.

## Board Game Arena

**BGA's terms of service prohibit automated scraping**, and serving replay logs costs
them real money. Liam Johansson's write-up — the source for the endpoints in
`sources/bga.py` — carries the same warning and explicitly retracts the multi-account
trick he used to get past BGA's per-account replay cap: *"I no longer endorse or
recommend this method. If you are interested in collecting many replays, reach out to
bga staff first."*

So this repo splits the two halves of the problem:

- **Parsing** replay-log JSON is offline and unrestricted. Run it on logs you came by
  legitimately — your own games saved out of the browser, or a dump BGA staff provide.
- **Downloading** lives in `fetch_logs()`, which is an ordinary single-session,
  3-seconds-between-requests, resumable downloader that refuses to run without
  `i_have_permission=True`. There is no login helper and no account rotation in here on
  purpose. Ask BGA staff first — it is also the only route to a sample large enough to
  be worth analysing.

### Finishing the BGA parser

`MOVE_TYPES` and `SETUP_TYPES` at the top of `sources/bga.py` are empty because BGA's
Homeworlds event names need one real replay to confirm. To fill them in:

1. Open one of your finished Homeworlds tables at `boardgamearena.com/gamereview?table=<id>`.
2. In the browser's network tab, find the `archive/archive/logs.html` response and save
   it as `replays/<table id>.json`.
3. `python3 analyze.py bga ./replays --inspect` prints every event type in that log with
   a sample `args` payload.
4. Copy the Homeworlds event names into `MOVE_TYPES` / `SETUP_TYPES`.
5. Add `replays/winners.json` mapping table id to the winning player's name — BGA keeps
   the result in the table metadata rather than reliably in the log stream.

Then every table above regenerates on BGA data with no other changes.

## Caveats

- SDG spans 2005–2020 at mixed skill. It is the only large open Homeworlds archive, and
  it predates BGA's player pool entirely — opening theory may well have moved on.
- Ratings are fitted to the same games they score, so edges are shrunk, not unbiased.
- `--p1` filtering cuts sample sizes fast. Watch the `n` column.
