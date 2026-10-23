# MorkBotted

![MorkBotted banner](MorkBotted%20Banner%20v2.png)

MorkBotted is a slash-command Discord bot for creating and running characters in **MÖRK BORG** and **Farewell to Arms REDUX**. It provides persistent character rosters, rules-aware random generation, dice and ability tests, character-sheet exports, and server-scoped GM tools.

The two game systems are integrated into the same bot but use separate rosters. Your active MÖRK BORG character never replaces your active Farewell to Arms grvnt.

## Features

### MÖRK BORG

- Create characters manually with guided Discord fields.
- Generate ready-to-play characters with `/scvmbirth`.
- Choose from stored core, supplemental, and server-homebrew classes.
- Track abilities, HP, Omens, silver, equipment, notes, and class features.
- Maintain multiple characters with a different active character in each server.
- Apply automatic or manual Getting Better results.
- Roll raw dice or ability tests against a Difficulty Rating.
- Export a saved character sheet as a text file.

### Farewell to Arms REDUX

- Generate a complete grvnt with `/farewell enlist`.
- Roll from all 12 entry-level REDUX classes or select a specific class.
- Generate class-adjusted stats, HP, Omens, silver, Ammo, Powers, and starting SHOCK.
- Generate firearms, side arms, armor, SHIT, War Scrolls, nicknames, battle scars, vices, enlistment reasons, histories, and class specialties.
- Apply class-specific rules for characters such as the Embedded One, Altered Mercenary, Homesick Rifleman, and New World Engineer.
- Maintain an independent Farewell roster and active grvnt per server.
- Roll grvnt stat tests and export complete sheets.

Faction special-forces classes from the companion books are not included in starting-character generation because those classes are acquired through Promotion during play. The *Alone in the MÖRK* material is likewise treated as a separate solo-play variant.

### GM tools

- View the server's active MÖRK BORG party.
- Track shared party loot and NPCs.
- Create and edit server-scoped homebrew classes.
- Create reusable homebrew features and link them to classes.
- Restrict GM operations through Manage Server permission or a configurable Discord role.

## Requirements

- Python 3.10 or newer
- A Discord application with a bot token
- The `bot` and `applications.commands` OAuth scopes when inviting the bot

## Quick start

Clone the repository, enter the project directory, and create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Copy the environment template:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Set at least `DISCORD_TOKEN` in `.env`, then start the bot:

```bash
python bot.py
```

The bot creates its SQLite schema automatically on startup. Restarting after an update also backfills class seed data and applies supported schema migrations.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DISCORD_TOKEN` | Required | Discord bot token. |
| `DATA_DIR` | `data` | Directory used for persistent application data. |
| `DB_PATH` | `data/morkbotted.db` | SQLite database path. |
| `COMMAND_SYNC_GUILD_ID` | Empty | Development server ID for faster slash-command synchronization. |
| `GM_ROLE_NAME` | `scvm-gm` | Role allowed to use GM commands. Leave blank to require Manage Server permission. |

Do not commit `.env`; it is ignored by Git. Use `.env.example` as the safe configuration template.

## First commands to try

For a MÖRK BORG character:

```text
/scvmbirth
/sheet
/roll target:strength dr:12
```

For a Farewell to Arms REDUX grvnt:

```text
/farewell enlist
/farewell sheet
/farewell roll target:presence dr:12
```

Both generators accept the relevant optional selections through Discord's native command interface. A newly generated character automatically becomes active in the server where it was created.

## Command reference

### General

| Command | Description |
| --- | --- |
| `/ping` | Check whether the bot is responding. |
| `/helpmb` | Show concise in-Discord command help. |
| `/roll` | Roll dice notation such as `2d6+1`, or test an active MÖRK BORG ability. |

### MÖRK BORG characters

| Command | Description |
| --- | --- |
| `/create` | Manually create or import a character. |
| `/scvmbirth` | Generate a complete random character, optionally from a selected class. |
| `/characters` | List your saved roster. |
| `/character-switch` | Select the active character for the current server. |
| `/character-archive` | Mark a character active, archived, dead, or NPC. |
| `/character-delete` | Permanently delete one of your characters. |
| `/sheet` | Display the active character sheet. |
| `/export` | Download the active character sheet. |
| `/classes` | List available class templates. |
| `/classinfo` | Inspect a stored class and its features. |
| `/omens` | View, reroll, or set current Omens. |
| `/gettingbetter` | Apply automatic or manual post-session stat changes. |
| `/setstat` | Set an ability modifier. |
| `/setfield` | Update a general character field. |
| `/improve` | Increase or decrease a numeric character value. |
| `/additem`, `/removeitem` | Manage equipment. |
| `/notes`, `/addnote`, `/editnote`, `/removenote` | Manage character notes. |

Ability fields use modifiers such as `-1`, `0`, or `+2`, not raw 3d6 totals. Equipment and notes supplied through `/create` accept comma-separated values. When a stored class is selected, Discord autocompletes that class's available features.

### Farewell to Arms REDUX

| Command | Description |
| --- | --- |
| `/farewell enlist` | Generate and save a complete grvnt. A class and nickname are optional. |
| `/farewell classes` | List the 12 available entry-level classes. |
| `/farewell sheet` | Display the active grvnt. |
| `/farewell roster` | List your saved grvnts. |
| `/farewell switch` | Select the active grvnt for the current server. |
| `/farewell export` | Download the active grvnt sheet. |
| `/farewell set` | Update a stat, resource, name, weapon, armor, background detail, or specialty on the active grvnt. |
| `/farewell gear-add` | Add equipment or SHIT to the active grvnt. |
| `/farewell gear-remove` | Remove equipment by the number displayed on the grvnt sheet. |
| `/farewell delete` | Permanently delete one of your saved grvnts. |
| `/farewell roll` | Roll raw dice or test an active grvnt's stat. |

The generator follows the REDUX enlistment sequence and accounts for class-specific dice, fixed equipment, specialty counts, restrictions, and starting War Scrolls. Generated Discord sheets include the rule text needed to use the selected specialty at the table.

### GM and homebrew

| Command | Description |
| --- | --- |
| `/gm-characters` | List active MÖRK BORG characters in the current server. |
| `/gm-party-loot` | Display shared party loot. |
| `/gm-party-loot-add`, `/gm-party-loot-remove` | Manage shared loot. |
| `/gm-npcs` | List server NPCs. |
| `/gm-npc` | Display one NPC. |
| `/gm-npc-create` | Create a server NPC. |
| `/gm-classes` | List server homebrew classes. |
| `/gm-class-create`, `/gm-class-edit`, `/gm-class-delete` | Manage homebrew classes. |
| `/gm-features` | List reusable homebrew features. |
| `/gm-feature-create`, `/gm-feature-edit`, `/gm-feature-delete` | Manage reusable features. |
| `/gm-feature-link` | Attach a reusable feature to a class. |

GM data and permissions are scoped to the Discord server where the command is used. By default, commands require Manage Server permission or a role named `scvm-gm`.

## Data and persistence

MorkBotted stores data in SQLite at `DB_PATH`.

- MÖRK BORG and Farewell to Arms characters occupy separate tables.
- Active-character selections are stored per Discord server and user.
- Homebrew classes, NPCs, and party loot are server-scoped.
- Existing `data/characters.json` data is migrated automatically when present.
- Database files and SQLite journals are excluded by `.gitignore`.

Back up the database file to preserve all bot state.

## Docker

Copy `.env.example` to `.env`, set `DISCORD_TOKEN`, then run:

```bash
docker compose up -d --build
```

View logs:

```bash
docker compose logs -f morkbotted
```

Stop the service:

```bash
docker compose down
```

The container runs as a non-root user. Docker Compose mounts `./data` at `/app/data`, keeping the SQLite database outside the image and persistent across rebuilds.

## Development

Run the full test suite from the project directory:

```bash
python -m unittest discover -v
```

Compile-check the source and tests:

```bash
python -m compileall -q morkbotted tests
```

The test suite covers character rendering, manual creation, class features, Omens, GM access and storage isolation, Farewell generation rules, and Farewell roster persistence.

## Project structure

```text
MorkBotted/
├── bot.py                         # Application entry point
├── morkbotted/
│   ├── bot.py                     # Discord commands and interactions
│   ├── character.py               # MÖRK BORG character models
│   ├── generator.py               # MÖRK BORG random generation
│   ├── farewell.py                # Farewell rules data and generation
│   ├── farewell_storage.py        # Separate Farewell roster persistence
│   └── storage.py                 # Main SQLite persistence and migrations
├── tests/                         # Unit test suite
├── Dockerfile
└── docker-compose.yml
```

## License

The bot source is released under the [MIT License](LICENSE). Referenced game names, rules, writing, and artwork remain the property of their respective creators and publishers.

Licensed rules and reference PDFs are intentionally excluded from this repository. They were used during development but are not read or required by the running bot.
