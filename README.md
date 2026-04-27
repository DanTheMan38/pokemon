# Pokemon Fan Meadow

A playable `pygame` mini-RPG built around one outdoor route plus connected interiors, with AI-generated pixel art for the creatures, UI, items, grass, NPCs, and room maps.

## Run

Double-click `play.bat`

Or run:

```powershell
.\.venv\Scripts\python.exe .\main.py
```

## Controls

- `WASD`
- Arrow keys
- `E`, `Space`, or `Enter` interact / confirm
- `Tab` opens the journal and lets you set the lead creature
- `F5` manually saves; progress also autosaves at key moments
- `H` opens in-game help
- `M` mutes / unmutes background music only
- `Shift` sprints after the main quest reward
- `Esc` closes the game

## Modes

The title screen has four fresh-start modes:

- Player Mode: you play normally.
- PPO Tiny: an untrained checkpoint that mostly wanders.
- PPO Mid: a real tabular PPO checkpoint trained for about 4k episodes; it can finish but wastes time.
- PPO Max: a real tabular PPO checkpoint trained for about 16k episodes; it follows the best learned route.

Regenerate the PPO checkpoints with:

```powershell
.\.venv\Scripts\python.exe .\tools\train_ppo.py
```

## What's In The Map

- Cedar Lab interior with Professor Cedar, three AI-generated elemental starters on the table, and a proper starter-choice flow
- Ranger Mira's house interior with a tighter player-scale layout, corrected doorway placement, and an exploration reward hidden inside
- Scaled indoor maps with smaller interiors and door fade transitions between buildings and the meadow
- Save / continue support with a title-screen save summary
- Objective markers, doorway glows, encounter warnings, sprint dust, and meadow ambient life
- Visible AI-generated tall grass patches that animate, favor different wild species by location, and trigger encounters
- A battle and capture loop with generated ability art, hit flicker, screen shake, damage popups, catch-rate hints, elemental strengths between Grass / Fire / Water, item animations, visible EXP bars, and animated level progression across Leafawn, Flarekit, Tidefin, Mothleaf, Bubbun, and Sparrook
- Ranger Mira heals your team outside and inside her house, and the guest bed can be used to rest
- A finished ending sequence once the full meadow survey is complete
- A richer journal with selected-creature details, survey progress tracking, and a stronger title-screen save summary for return play
- AI-generated item icons, menu panels, journal styling, NPC sprites, battle background, and interior maps
- Original chiptune-style music and sound effects for menus, battles, interactions, pickups, and progression
- A finished one-route free-roam mode after the quest reward

## Testing

Run the smoke test with:

```powershell
.\.venv\Scripts\python.exe .\tools\smoke_test.py
```

Rebuild the generated audio with:

```powershell
.\.venv\Scripts\python.exe .\tools\generate_audio.py
```

## Asset Notes

- `assets/raw/` stores the source generations for the map, sprites, creatures, interiors, battle effects, grass, UI, and item art.
- `tools/prepare_assets.py` turns those raw images into the playable files used by the game.
