# MorkBotted

`MorkBotted` is a Discord bot MVP for running MORK BORG characters inside Discord. It stores one character per Discord user, rolls raw dice, handles MORK BORG ability tests like `!roll presence`, and exports a text character sheet from the bot's saved data.

## What it supports

- Character creation with persistent storage
- Ability modifiers for Agility, Presence, Strength, and Toughness
- Raw dice expressions like `!roll d6` or `!roll 2d8+1`
- MORK BORG-style tests like `!roll strength` or `!roll presence 14`
- Character sheet export as a `.txt` attachment
- In-bot updates for stats, HP, Omens, silver, equipment, and notes

## Why the commands look this way

This MVP is built around the common MORK BORG structure from the materials you linked:

- Characters track four core abilities: Agility, Presence, Strength, and Toughness.
- Most tests are rolled on a d20 and modified by the relevant ability.
- A default DR of 12 is a sensible baseline for ability checks unless the GM sets a different DR.
- HP, Omens, silver, inventory, and short free-text notes are useful minimum fields for Discord-side play.

If you want to model more of the full game later, the next layer would be class tables, weapon damage, armor tiers, broken conditions, scroll tracking, powers, and "getting better" roll automation.
<<<<<<< HEAD

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
- `!create Fletcher`
- `!sheet`
- `!export`
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

## Suggested next upgrades

- Replace prefix commands with slash commands and Discord modals
- Add a guided `!create` flow that asks questions one step at a time
- Add class templates and random character generation
- Add a `!gettingbetter` command that automates the advancement table you use
- Add GM-only commands for shared party loot, calendars, and misery tracking
=======
>>>>>>> 4d215ac2c74a85e713f47793c8b7b379eae90627
