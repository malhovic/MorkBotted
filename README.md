# MorkBotted

`MorkBotted` is a Discord bot MVP for running MORK BORG characters inside Discord. It stores multiple characters per Discord user in SQLite, tracks an active character per server, supports native Discord slash commands with helper fields, rolls raw dice, handles MORK BORG ability tests, and exports a text character sheet from the bot's saved data.

## What it supports

- Native slash-command character creation with helper fields
- One-button random character generation with `/scvmbirth`
- SQLite-backed character storage with automatic migration from the older JSON file
- Multiple characters per user with per-server active character selection
- Stored class templates and feature data for core and supplemental MORK BORG classes, including Dire Hunter
- Ability modifiers for Agility, Presence, Strength, and Toughness
- Raw dice expressions like `!roll d6` or `!roll 2d8+1`
- MORK BORG-style tests like `!roll strength` or `!roll presence 14`
- Slash-command `gettingbetter` flow with typed helper choices
- Character sheet export as a `.txt` attachment
- In-bot updates for stats, HP, Omens, silver, equipment, and notes

## Why the commands look this way

This MVP is built around the common MORK BORG structure from the materials you linked:

- Characters track four core abilities: Agility, Presence, Strength, and Toughness.
- Most tests are rolled on a d20 and modified by the relevant ability.
- A default DR of 12 is a sensible baseline for ability checks unless the GM sets a different DR.
- HP, Omens, silver, inventory, and short free-text notes are useful minimum fields for Discord-side play.

The bot now uses the attached class PDFs and rules references to store class notes, feature tables, and source metadata in the database so character sheets can grow into richer formatting later.

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

5. Edit `.env` and set `DISCORD_TOKEN` to your Discord bot token. `DB_PATH` defaults to `data/morkbotted.db`.
6. In the Discord developer portal, enable the `MESSAGE CONTENT INTENT` for your bot if you want to keep using the legacy `!` commands.
7. Run the bot:

```powershell
python bot.py
```

Character and class data are stored in `data/morkbotted.db`. If `data/characters.json` exists from an older version, the bot migrates it into SQLite the first time the new store starts.
New class seed data is also backfilled into existing databases on startup.

## Slash commands

- `/create`
- `/scvmbirth`
- `/characters`
- `/character-switch`
- `/character-archive`
- `/character-delete`
- `/classes`
- `/classinfo`
- `/sheet`
- `/export`
- `/gettingbetter`
- `/setstat`
- `/setfield`
- `/improve`
- `/additem`
- `/removeitem`
- `/addnote`
- `/removenote`
- `/roll`

## Getting Better flow

`/gettingbetter` now uses native Discord fields and supports two modes:

- `auto` rolls a d6 for each ability and adjusts it automatically
- `manual` asks whether each ability goes `up`, `down`, or `stay`

This version updates the four core abilities:

- Agility
- Presence
- Strength
- Toughness

## Create flow

`/create` now uses native command fields for:

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

Optional fields can be left blank. Equipment and notes can be entered as comma-separated lists.

If the class name matches one of the stored templates, the bot links the character to that class and includes class-source details in sheet exports.

## Random character generation

`/scvmbirth` creates a ready-to-play entry-level character in one step. By default it rolls from the full stored class catalog, including community classes, but you can also pass a specific class name if you want to force the result.

Generated characters include:

- A random name
- A class from the stored catalog
- Rolled ability modifiers using the MORK BORG ability table
- HP, Omens, and silver based on the chosen class
- Rolled weapon and armor
- Starter equipment and class-feature notes

When used inside a server, the generated character becomes your active character there automatically.

When you create a character inside a server, that character becomes your active character for that server automatically.

## Character rosters

Each Discord user can now keep multiple characters. The main play commands such as `/sheet`, `/roll`, `/gettingbetter`, `/setfield`, and `/export` act on your active character for the current server.

Use these commands to manage a roster:

- `/characters` to list all of your saved characters and statuses
- `/character-switch` to choose which character is active in the current server
- `/character-archive` to mark a character as `archived`, `dead`, `npc`, or back to `active`
- `/character-delete` to permanently remove a character

## Legacy prefix commands

The older `!` commands are still present for compatibility, but slash commands are now the primary interface and the recommended one for your next server deploy.

## Suggested next upgrades

- Add random character generation
- Expand the stored character model further with dedicated tables for powers, scrolls, active class rolls, and session history
- Add GM-only commands for shared party loot, calendars, and misery tracking
