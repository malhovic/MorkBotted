# MorkBotted

`MorkBotted` is a Discord bot MVP for running MORK BORG characters inside Discord. It stores multiple characters per Discord user in SQLite, tracks an active character per server, supports native Discord slash commands with helper fields, rolls raw dice, handles MORK BORG ability tests, and exports a text character sheet from the bot's saved data.

## What it supports

- Native slash-command character creation with helper fields
- One-button random character generation with `/scvmbirth`
- SQLite-backed character storage with automatic migration from the older JSON file
- Multiple characters per user with per-server active character selection
- Stored class templates and feature data for core and supplemental MORK BORG classes, including Dire Hunter
- Server-scoped GM homebrew classes and reusable class features
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
6. Optional but recommended for faster slash-command updates while you deploy changes: set `COMMAND_SYNC_GUILD_ID` to your main Discord server id.
7. Optional: if you want to keep using legacy `!` commands, enable the `MESSAGE CONTENT INTENT` in the Discord developer portal and set `ENABLE_MESSAGE_CONTENT_INTENT=true` in `.env`. Slash commands do not need this privileged intent.
8. Run the bot:

```powershell
python bot.py
```

Character and class data are stored in `data/morkbotted.db`. If `data/characters.json` exists from an older version, the bot migrates it into SQLite the first time the new store starts.
New class seed data is also backfilled into existing databases on startup.
If `COMMAND_SYNC_GUILD_ID` is set, the bot also syncs slash commands directly into that server on startup so command changes appear much faster than waiting on global propagation.

## Slash commands

- `/create`
- `/scvmbirth`
- `/characters`
- `/character-switch`
- `/character-archive`
- `/character-delete`
- `/gm-characters`
- `/gm-party-loot`
- `/gm-party-loot-add`
- `/gm-party-loot-remove`
- `/gm-npcs`
- `/gm-npc`
- `/gm-npc-create`
- `/gm-classes`
- `/gm-class-create`
- `/gm-class-edit`
- `/gm-class-delete`
- `/gm-feature-create`
- `/gm-feature-edit`
- `/gm-feature-delete`
- `/gm-features`
- `/gm-feature-link`
- `/classes`
- `/classinfo`
- `/sheet`
- `/export`
- `/omens`
- `/gettingbetter`
- `/setstat`
- `/setfield`
- `/improve`
- `/additem`
- `/removeitem`
- `/notes`
- `/addnote`
- `/editnote`
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

## Omens

Characters store their current Omens and derive their daily omen die from their linked class, such as `d2`, `d3`, or `d4`.

Use `/omens` to recall the current count and daily die. Use `/omens roll` at the start of a new day to roll the character's daily Omens and save that result. Use `/omens set` with an amount to record a manual count.

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
- Optional class feature selection, such as `beast form: Flayed and Dripping Wolf`
- Notes

Optional fields can be left blank. Equipment and notes can be entered as comma-separated lists.
Ability fields use MORK BORG modifiers such as `-1`, `0`, or `+2`, not raw 3d6 ability scores.

If the class name matches one of the stored templates, the bot links the character to that class and includes class-source details in sheet exports.
If the character's class has a feature table, pick the chosen feature from `class_feature` autocomplete. Category-specific entries like `beast form: Flayed and Dripping Wolf` are preferred because they identify the exact table.
Slash `/create` autocompletes class feature options after you choose a stored class. In a Discord server, class and feature autocomplete also includes that server's GM-created homebrew.

Notes are freeform reminders only. Use `/notes` to list them, `/addnote` to append one, `/editnote` to replace a numbered note, and `/removenote` to remove a numbered note.

## Random character generation

`/scvmbirth` creates a ready-to-play entry-level character in one step. By default it rolls from the full stored class catalog, including community classes, but you can also pass a specific class name if you want to force the result.

Generated characters include:

- A random name
- A class from the stored catalog
- Rolled ability modifiers using the MORK BORG ability table
- HP, Omens, and silver based on the chosen class
- Rolled weapon and armor
- Starter equipment and selected class features

When used inside a server, the generated character becomes your active character there automatically.

When you create a character inside a server, that character becomes your active character for that server automatically.

## Character rosters

Each Discord user can now keep multiple characters. The main play commands such as `/sheet`, `/roll`, `/gettingbetter`, `/setfield`, and `/export` act on your active character for the current server.

Use these commands to manage a roster:

- `/characters` to list all of your saved characters and statuses
- `/character-switch` to choose which character is active in the current server
- `/character-archive` to mark a character as `archived`, `dead`, `npc`, or back to `active`
- `/character-delete` to permanently remove a character

## GM commands

GM commands are slash-only and server-scoped. They only read or write data for the server where the command is used.

By default, GM commands require either Discord's Manage Server permission or a server role named `scvm-gm`. You can change the role name with `GM_ROLE_NAME` in `.env`. Leave `GM_ROLE_NAME` blank if you only want Manage Server to grant GM access.

The bot enforces this check itself so GMs do not need broad Discord permissions. If you also want the commands hidden from everyone else in the slash-command picker, restrict the GM commands to the same role in Discord's server settings under Integrations.

Use these commands to manage table-facing campaign state:

- `/gm-characters` to list the active characters registered in the current server
- `/gm-party-loot` to list shared party loot for the current server
- `/gm-party-loot-add` to add shared party loot
- `/gm-party-loot-remove` to remove shared party loot by id
- `/gm-npcs` to list NPCs for the current server
- `/gm-npc` to view one NPC by id
- `/gm-npc-create` to create an NPC with description, disposition, and private notes
- `/gm-classes` to list homebrew classes for the current server
- `/gm-class-create` to create a homebrew class for the current server
- `/gm-class-edit` to rename or update a homebrew class; leave fields blank to keep them, or type `clear` to erase optional fields
- `/gm-class-delete` to delete a homebrew class from the current server
- `/gm-feature-create` to create a reusable homebrew class feature for the current server
- `/gm-feature-edit` to rename or update a reusable homebrew feature; leave fields blank to keep them, or type `clear` to erase the roll label
- `/gm-feature-delete` to delete a reusable homebrew feature from the current server
- `/gm-features` to list reusable homebrew features for the current server
- `/gm-feature-link` to attach one reusable feature to one or more classes in the current server

## Legacy prefix commands

The older `!` commands are still present for compatibility, but slash commands are now the primary interface and the recommended one for your next server deploy.
Legacy prefix commands require `ENABLE_MESSAGE_CONTENT_INTENT=true` and Discord's Message Content Intent developer-portal toggle. Leave it disabled if you only use slash commands.

## Suggested next upgrades

- Expand the stored character model further with dedicated tables for powers, scrolls, active effects, and session history
- Add GM tools for calendars, misery tracking, NPC editing, and encounter notes
