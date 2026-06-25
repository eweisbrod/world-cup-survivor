# World Cup Survivor Pool — 2026

A real-time FIFA World Cup 2026 survivor pool web app.

## How It Works
- Each round has a 2-day pick window
- Pick **one country** to win a game in each window
- If your country wins, you survive to the next window
- You can only use each country **once** the entire tournament
- If your country loses, you're eliminated
- **Special rule:** if every remaining player loses in the same window, nobody is eliminated — keep going!

## Schedule (8 Pick Windows)

| Pick | Window | Dates | Round |
|------|--------|-------|-------|
| 1 | R32 W1 | Jun 28–29 | Round of 32 (4 games) |
| 2 | R32 W2 | Jun 30–Jul 1 | Round of 32 (6 games) |
| 3 | R32 W3 | Jul 2–3 | Round of 32 (6 games) |
| 4 | R16 W4 | Jul 4–5 | Round of 16 (4 games) |
| 5 | R16 W5 | Jul 6–7 | Round of 16 (4 games) |
| 6 | QF | Jul 9–11 | Quarterfinal (4 games) |
| 7 | SF | Jul 14–15 | Semifinal (2 games) |
| 8 | Final | Jul 19 | Final (1 game) |

## Features
- Firebase Realtime Database for shared picks across all players
- Live score fetching from ESPN soccer API with auto-refresh
- Board view to see all players' picks at a glance
- Mobile-first dark UI
- "Keep going" rule: mass elimination rounds don't count
