# MorkBotted

`MorkBotted` is a Discord bot MVP for running MORK BORG characters inside Discord. It stores one character per Discord user, rolls raw dice, handles MORK BORG ability tests like `!roll presence`, and exports a text character sheet from the bot's saved data.

## What it supports

- Guided character creation with persistent storage
- Ability modifiers for Agility, Presence, Strength, and Toughness
- Raw dice expressions like `!roll d6` or `!roll 2d8+1`
- MORK BORG-style tests like `!roll strength` or `!roll presence 14`
- `!gettingbetter` flow for post-session stat changes
- Character sheet export as a `.txt` attachment
- In-bot updates for stats, HP, Omens, silver, equipment, and notes

## Why the commands look this way

This MVP is built around the common MORK BORG structure from the materials you linked:

- Characters track four core abilities: Agility, Presence, Strength, and Toughness.
- Most tests are rolled on a d20 and modified by the relevant ability.
- A default DR of 12 is a sensible baseline for ability checks unless the GM sets a different DR.
- HP, Omens, silver, inventory, and short free-text notes are useful minimum fields for Discord-side play.

If you want to model more of the full game later, the next layer would be class tables, weapon damage, armor tiers, broken conditions, scroll tracking, powers, and GM-facing party tools.

## Setup

1. Install Python 3.10+.
2. Create and activate a virtual environment.
3. Install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

4. Create your environment file:

```powershell
Copy-Item .env.example .env
```

5. Edit `.env` and set `DISCORD_TOKEN` to your Discord bot token.
6. In the Discord developer portal, enable the `MESSAGE CONTENT INTENT` for your bot.
7. Run the bot:

```powershell
python bot.py
```

Character data is stored in `data/characters.json`.

## Commands

- `!helpmb`
- `!create`
- `!sheet`
- `!export`
- `!gettingbetter`
- `!setstat presence 2`
- `!setfield class_name Gutterborn Scum`
- `!setfield hp 6`
- `!improve hp 2`
- `!improve presence 1`
- `!setfield max_hp 8`
- `!setfield omens 2`
- `!setfield background You worked in the corpse pits and know every smell of rot.`
- `!additem Rusty sword`
- `!additem Rope`
- `!removeitem Rope`
- `!addnote Got better after last session: +1 Presence`
- `!roll d20`
- `!roll 3d6+2`
- `!roll presence`
- `!roll toughness 14`

## Getting Better flow

`!gettingbetter` now supports two modes:

- `auto` rolls a d6 for each ability and adjusts it automatically
- `manual` asks whether each ability goes `up`, `down`, or `stay`

This version updates the four core abilities:

- Agility
- Presence
- Strength
- Toughness

## Guided creation flow

`!create` now walks the player through character setup one answer at a time. The bot asks for:

- Name
- Class or archetype
- Background
- Description
- Agility, Presence, Strength, and Toughness
- HP and max HP
- Omens
- Silver
- Equipment
- Notes

For optional prompts, reply with `skip`. Equipment and notes can be entered as comma-separated lists.

## Suggested next upgrades

- Add random character generation
- Support a more robust stored character model with SQLite so the bot can scale cleanly to a larger audience
- Add GM-only commands for shared party loot, calendars, and misery tracking
