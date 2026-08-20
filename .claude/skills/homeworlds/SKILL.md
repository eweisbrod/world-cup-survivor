---
name: homeworlds
description: Analyze a live Binary Homeworlds position and recommend a move. Use whenever the user describes a Homeworlds board, asks what to play, asks whether a move is safe, or discusses Homeworlds openings, catastrophes, captures, or stash parity.
---

# Homeworlds position analysis

Run the SAFETY AUDIT before proposing any move. Most errors come from skipping it.

## Rules that are easy to get wrong

- **Capture** needs (a) red power in that system — a red ship of yours there, a red star,
  or a red sacrifice made anywhere; and (b) the target no larger than **your largest ship
  in that system**, any colour. The red ship's own size is irrelevant to the size test.
- **A sacrifice still needs a ship of yours in the target system.** Sacrificing frees the
  colour requirement, not the presence requirement.
- **Sacrifice yields actions equal to the piece's SIZE**, all of that piece's colour.
  R2 = two captures. Y3 = three moves.
- **Build** needs green power (green ship or green star) AND a **ship** of the colour being
  built. A star of colour X does NOT let you build X. Verified: across 5,748 first builds in
  the SDG archive, the colour built always matched the player's starting ship, never a
  star-only colour.
- **Build yields the smallest available piece** of that colour.
- **Trade** is same-size, needs blue power, and **returns the old piece to the stash**.
- **Adjacency**: two systems connect iff they share NO star size.
- **Catastrophe**: 4+ of one colour in a system, ships of BOTH players plus the star. All
  pieces of that colour die, star included. Killing one star of a binary leaves a single
  star and the ships survive; killing a lone star destroys every ship there.
- **Loss**: no ships of yours at your homeworld at the start of your turn, or both stars gone.

## SAFETY AUDIT — do this every turn, for BOTH homeworlds

1. **Count every colour in each homeworld, stars included.**
   - At 3 → one more piece is a catastrophe. Say so explicitly.
   - At 2 → can the opponent add 2 of that colour? He needs 2 ships of it *plus a separate
     yellow to sacrifice as the vehicle*. If so, grade the severity — do not just say
     "Bluebird", which names only the lethal case:
     - **Lethal (the true Bluebird)**: that pair is your ONLY ships in the system. The
       catastrophe empties your homeworld and you are eliminated at the start of your turn.
     - **Star loss**: the colour matches one of your homeworld stars. The star dies too,
       which changes the system's adjacency — recompute who can reach you.
     - **Material loss**: you have other ships there. You survive, but lose both pieces of
       that colour. Losing your only reds means losing all capture ability.
2. **Reachability test — count BOTH ways a colour can grow, not just movement.**
   - **By build (one action, no movement).** If a player owns a ship of colour X in the
     system and has green power there, they add another X *in place*, size = smallest X
     left in the stash. This is the cheapest route to a catastrophe and the easiest to
     miss. Check it before committing any piece into a system.
   - **By movement.** N ships into one system in a turn needs N move actions — a yellow
     sacrifice of size N, or one free move per turn. A colour is only movement-deliverable
     if the *vehicle* is a different colour: two yellows cannot deliver themselves, since
     the sacrifice consumes one.

   Corollary for your own attacks: **do not send a piece into an enemy system where its
   colour already stands at 3, or at 2 with a build available.** "Uncapturable" is not
   "safe" — a size-3 immune to capture still dies to a catastrophe, and the defender never
   has to out-muscle it.
3. **Never leave your homeworld with one ship** unless you can prove it survives.
4. **Never reduce your homeworld ships to a single colour.**
5. **Never trade away your last green** if you have no green star — that ends building
   permanently.
6. **Losing a star changes adjacency.** Recompute which systems can reach the homeworld.

## Stash parity

Three copies of every piece; builds hand out the smallest available.

- Whoever takes the **last small** of a colour gives the opponent that colour's first medium.
- **Even count left → lead the race** (opponent is forced to take the last one).
- **Odd count left → do not lead.**
- Same logic one size up for mediums and larges.
- Trading a piece away **returns it to the stash** and lengthens the opponent's ladder to
  the next size. Building the last small **shortens** it.

## Colour roles

Green = build, Yellow = move, Blue = trade, Red = capture. A star supplies its colour's
power at that system permanently and cannot be captured — only catastrophed.

## What the move-count tool is for

`count-successors` in Quuxplusone/Homeworlds (build with `make count-successors`; rebuild if
it dies with SIGILL, it uses `-march=native`). State format:

    Name (player, stars) p0ships-p1ships
    Colony (star) p0ships-p1ships

It is a **mobility proxy, not an evaluation**. Use it for exactly two things:
- detecting that a capture became available (the opponent's `sac r` count rising)
- measuring denial (an option count dropping after you take a scarce piece)

Do not use raw move counts to claim someone is winning.

## Archive findings worth reusing

From 2,882 two-player SDG games (2005–2020), skill-adjusted:
- Whoever gets the **first medium ship** wins ~57%.
- Having a medium by move 4: 62% vs 39%.
- Trading into red in the opening as second player: 24–33%. Bad.
- First-colony star colour, founder's win rate: G2 58%, B2 48%, Y2 40%, R2 28%; red stars
  24–31% at every size.
- A homeworld with a small star of red/yellow/green is instafreeze-exposed; a small **blue**
  star is not, because nobody can afford to be the player without blue.
