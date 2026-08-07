# Battle Cats Save Editor — Web (Flask + Bootstrap 5, dark gold theme)

## Run

```
python app.py
```

That's it — `app.py` automatically checks for `flask` and `bcsfe` on
startup and installs them for you if missing (see `bootstrap.py`). You no
longer need to remember `pip install -r requirements.txt` first (though it
still works if you prefer to run it manually).

Then open: **http://127.0.0.1:5000**

Do not deploy this publicly on the internet — it's a personal tool meant
for localhost only. There is no multi-user login system (one shared
backend instance for whoever connects).

## What's new in this version

- **Auto dependency install** — `bootstrap.py` checks for `flask`/`bcsfe`
  and installs them automatically if missing.
- **UI rebuilt on real Bootstrap 5** (via CDN) with a custom dark
  gold/brown/red theme layered on top (CSS variable overrides + fade-in /
  hover-lift animations), instead of a from-scratch CSS framework.
- **Fixed preset buttons removed.** Every resource now has a free-form
  "Amount to add" field and a "Set to" field — enter any number you want
  (negative numbers subtract).
- **Bulk actions**:
  - Unlock ALL cats at once
  - Set level for ALL unlocked cats at once (enter base + plus, applies to
    every cat you own)
  - Edit playtime (hours / minutes / seconds)
- **Story Chapters** (Empire of Cats / Into the Future / Cats of the
  Cosmos):
  - Complete a single chapter, or complete ALL chapters at once
  - Collect treasure (reward tier 1-3) for a single chapter, or collect
    treasure for ALL chapters at once
- Everything from before still works: transfer-code login, currencies,
  array items (Catamin/Catseye/Treasure Chest/Catfruit/Labyrinth Medal),
  individual cat unlock/level, named Accounts folders, Save File, Upload &
  Get New Codes.

## How Story Chapters works technically

`bcsfe`'s `save_file.story` exposes real chapter objects
(`get_real_chapters()`), each with:
- `chapter.clear_chapter()` - marks all 48 stages as cleared and updates
  progress correctly (this is bcsfe's own method, the same one its CLI
  "clear whole chapter" feature uses, not a hand-rolled workaround).
- `stage.set_treasure(level)` - sets the treasure/reward tier for a stage
  (0 = none, 1-3 = the tiers shown in-game).

Chapter names are fetched from the game's own localized text when
possible; if that data isn't available (e.g. no internet on first run) it
falls back to generic "Chapter N" labels so the feature still works.

## Still not covered (future work, same as before)

Ototo/Gamototo, advanced cat editing (talents, 4th form), Gauntlets/Event
Chapters/Legend Quest/Zero Legends (different chapter types from the main
Story), Gatya seeds, and account unban/managed-items upload.
