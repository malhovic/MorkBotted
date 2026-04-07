from __future__ import annotations

import os
import random
import re
import logging
from io import BytesIO
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from morkbotted.character import ABILITY_NAMES, EDITABLE_FIELDS, Character, ClassTemplate, normalize_ability_name
from morkbotted.generator import generate_random_character
from morkbotted.storage import CharacterStore

DICE_PATTERN = re.compile(r"^(?P<count>\d*)d(?P<sides>\d+)(?P<modifier>[+-]\d+)?$", re.IGNORECASE)
DEFAULT_DR = 12
INTERACTIVE_TIMEOUT_SECONDS = 900
DISCORD_MESSAGE_LIMIT = 2000
ABILITY_ALIAS_SET = {"agi", "pre", "str", "tgh", "tough"}
CREATE_FORM_TEMPLATE = """Reply with this template and replace the values after each colon.
You can leave optional fields blank.

name:
class:
background:
description:
agility:
presence:
strength:
toughness:
hp:
max_hp:
omens:
silver:
equipment:
notes:
"""

logger = logging.getLogger(__name__)


def parse_int(raw: str) -> int:
    return int(raw.replace("+", ""))


def build_character_sheet(character: Character) -> str:
    return "\n".join(character.sheet_lines())


def build_class_summary(class_template: ClassTemplate) -> str:
    lines = [
        f"**{class_template.name}**",
        f"Source: {class_template.source}",
        class_template.description,
    ]
    if class_template.starting_silver:
        lines.append(f"Starting Silver: {class_template.starting_silver}")
    if class_template.omen_die:
        lines.append(f"Omen Die: {class_template.omen_die}")
    if class_template.hp_formula:
        lines.append(f"HP Formula: {class_template.hp_formula}")
    if class_template.ability_summary:
        lines.append(f"Ability Notes: {class_template.ability_summary}")
    if class_template.equipment_summary:
        lines.append(f"Equipment Notes: {class_template.equipment_summary}")
    if class_template.notes:
        lines.append(f"Extra Notes: {class_template.notes}")
    if class_template.features:
        lines.append("Features:")
        for feature in class_template.features:
            prefix = f"[{feature.roll_label}] " if feature.roll_label else ""
            lines.append(f"- {prefix}{feature.name}: {feature.description}")
    return "\n".join(lines)


async def send_interaction_text(
    interaction: discord.Interaction,
    content: str,
    *,
    ephemeral: bool = False,
    filename: str = "response.txt",
) -> None:
    if len(content) <= DISCORD_MESSAGE_LIMIT:
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(content, ephemeral=ephemeral)
        return

    payload = BytesIO(content.encode("utf-8"))
    discord_file = discord.File(payload, filename=filename)
    message = "The response was too long for a Discord message, so I attached it as a text file."
    if interaction.response.is_done():
        await interaction.followup.send(message, file=discord_file, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(message, file=discord_file, ephemeral=ephemeral)


def apply_class_selection(store: CharacterStore, character: Character, raw_class_name: str) -> Character:
    resolved_class = store.find_class(raw_class_name)
    if resolved_class:
        character.class_id = resolved_class.id
        character.class_name = resolved_class.name
        character.class_template = resolved_class
    else:
        character.class_id = None
        character.class_name = raw_class_name.strip() or "Classless"
        character.class_template = None
    return character


def clamp_ability(value: int) -> int:
    return max(-3, min(6, value))


async def ensure_dm_channel(user: discord.abc.User | discord.Member) -> discord.DMChannel:
    dm_channel = user.dm_channel
    if dm_channel is None:
        dm_channel = await user.create_dm()
    return dm_channel


def parse_form_reply(reply_text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in reply_text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower().replace(" ", "_")
        if normalized_key:
            data[normalized_key] = value.strip()
    return data


def parse_csv_field(value: str | None) -> list[str]:
    if not value:
        return []
    if value.strip().lower() == "skip":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


async def prompt_for_response(
    bot: commands.Bot,
    user: discord.abc.User | discord.Member,
    channel: discord.abc.Messageable,
    prompt: str,
    *,
    optional: bool = False,
    timeout: int = INTERACTIVE_TIMEOUT_SECONDS,
) -> str | None:
    optional_hint = " Reply with `skip` to leave it blank." if optional else ""
    await channel.send(f"{prompt}{optional_hint}")

    def check(message: discord.Message) -> bool:
        return message.author.id == user.id and message.channel.id == channel.id

    reply = await bot.wait_for("message", check=check, timeout=timeout)
    value = reply.content.strip()
    if optional and value.lower() == "skip":
        return None
    return value


async def prompt_for_choice(
    bot: commands.Bot,
    user: discord.abc.User | discord.Member,
    channel: discord.abc.Messageable,
    prompt: str,
    choices: dict[str, str],
    *,
    timeout: int = INTERACTIVE_TIMEOUT_SECONDS,
) -> str:
    choice_list = ", ".join(f"`{key}`" for key in choices)
    await channel.send(f"{prompt}\nChoices: {choice_list}")

    def check(message: discord.Message) -> bool:
        return message.author.id == user.id and message.channel.id == channel.id

    while True:
        reply = await bot.wait_for("message", check=check, timeout=timeout)
        selected = reply.content.strip().lower()
        if selected in choices:
            return choices[selected]
        await channel.send(f"Please reply with one of: {choice_list}")


def roll_dice(expression: str) -> tuple[list[int], int, int]:
    match = DICE_PATTERN.match(expression.strip())
    if not match:
        raise ValueError("Dice notation must look like `d20`, `2d6`, or `3d8+2`.")

    count = int(match.group("count") or "1")
    sides = int(match.group("sides"))
    modifier = int(match.group("modifier") or "0")

    if count < 1 or count > 100:
        raise ValueError("Dice count must be between 1 and 100.")
    if sides < 2 or sides > 1000:
        raise ValueError("Die size must be between 2 and 1000.")

    rolls = [random.randint(1, sides) for _ in range(count)]
    return rolls, modifier, sum(rolls) + modifier


def create_character_from_values(
    store: CharacterStore,
    *,
    user_id: int,
    discord_name: str,
    name: str,
    class_name: str,
    background: str,
    description: str,
    agility: str,
    presence: str,
    strength: str,
    toughness: str,
    hp: str,
    max_hp: str,
    omens: str,
    silver: str,
    equipment: str | None,
    notes: str | None,
) -> Character:
    character = Character(
        user_id=user_id,
        discord_name=discord_name,
        name=name.strip(),
        background=background.strip(),
        description=description.strip(),
        agility=parse_int(agility),
        presence=parse_int(presence),
        strength=parse_int(strength),
        toughness=parse_int(toughness),
        hp=parse_int(hp),
        max_hp=parse_int(max_hp),
        omens=parse_int(omens),
        silver=parse_int(silver),
        equipment=parse_csv_field(equipment),
        notes=parse_csv_field(notes),
    )
    apply_class_selection(store, character, class_name)
    return store.upsert(character)


def run_getting_better(character: Character, mode: str, manual_choices: dict[str, str] | None = None) -> list[str]:
    summaries: list[str] = []
    manual_choices = manual_choices or {}

    for ability_name in ABILITY_NAMES:
        current_value = character.get_ability(ability_name)
        if mode == "auto":
            roll = random.randint(1, 6)
            if current_value <= 1:
                proposed_value = current_value - 1 if roll == 1 else current_value + 1
            else:
                proposed_value = current_value + 1 if roll >= current_value else current_value - 1

            new_value = clamp_ability(proposed_value)
            character.set_ability(ability_name, new_value)
            if new_value == current_value:
                summaries.append(
                    f"`{ability_name.title()}` stayed at `{new_value:+d}` from `d6({roll})` because it hit a cap"
                )
            else:
                summaries.append(f"`{ability_name.title()}` {current_value:+d} -> `{new_value:+d}` from `d6({roll})`")
            continue

        direction = manual_choices.get(ability_name, "stay")
        if direction == "up":
            new_value = clamp_ability(current_value + 1)
        elif direction == "down":
            new_value = clamp_ability(current_value - 1)
        else:
            new_value = current_value

        character.set_ability(ability_name, new_value)
        summaries.append(f"`{ability_name.title()}` {current_value:+d} -> `{new_value:+d}`")

    return summaries


def get_active_character_for_context(
    store: CharacterStore,
    user: discord.abc.User,
    guild_id: int | None,
) -> Character | None:
    if guild_id is not None:
        return store.get_active_character(guild_id, user.id)
    return store.get(user.id)


def ensure_guild_id(guild: discord.Guild | None) -> int:
    if guild is None:
        raise commands.BadArgument("This command needs to be used in a server so the bot knows which active character to use.")
    return guild.id


def build_bot() -> commands.Bot:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    load_dotenv()
    prefix = os.getenv("COMMAND_PREFIX", "!")
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    db_path = Path(os.getenv("DB_PATH", str(data_dir / "morkbotted.db")))
    sync_guild_id = os.getenv("COMMAND_SYNC_GUILD_ID", "").strip()

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix=prefix, intents=intents, help_command=None)
    store = CharacterStore(db_path)
    slash_synced = False

    def require_character(user: discord.abc.User) -> Character:
        character = store.get(user.id)
        if character is None:
            raise commands.BadArgument(f"No character found for {user.display_name}. Start with `{prefix}create`.")
        return character

    def require_character_for_ctx(ctx: commands.Context) -> Character:
        character = get_active_character_for_context(store, ctx.author, ctx.guild.id if ctx.guild else None)
        if character is None:
            raise commands.BadArgument(
                f"No active character found for {ctx.author.display_name}. Use `/create` or `/character-switch`."
            )
        return character

    async def class_name_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        del interaction
        current_lower = current.lower()
        matches = [
            app_commands.Choice(name=class_template.name, value=class_template.name)
            for class_template in store.list_classes()
            if not current_lower or current_lower in class_template.name.lower()
        ]
        return matches[:25]

    async def character_name_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        current_lower = current.lower()
        matches = []
        for character in store.list_characters(interaction.user.id, include_archived=True):
            label = f"{character.name} [{character.status}] #{character.id}"
            if current_lower and current_lower not in label.lower():
                continue
            matches.append(app_commands.Choice(name=label[:100], value=str(character.id)))
        return matches[:25]

    @bot.event
    async def on_ready() -> None:
        nonlocal slash_synced
        if not slash_synced:
            if sync_guild_id:
                guild_object = discord.Object(id=int(sync_guild_id))
                bot.tree.copy_global_to(guild=guild_object)
                synced_commands = await bot.tree.sync(guild=guild_object)
                print(f"Synced {len(synced_commands)} slash command(s) to guild {sync_guild_id}.")
            synced_commands = await bot.tree.sync()
            print(f"Synced {len(synced_commands)} global slash command(s).")
            slash_synced = True
        print(f"Logged in as {bot.user} and ready to spread misery.")

    @bot.command(name="ping")
    async def ping(ctx: commands.Context) -> None:
        latency_ms = round(bot.latency * 1000)
        await ctx.send(f"Pong. Gateway latency: `{latency_ms}ms`")

    @bot.command(name="helpmb")
    async def helpmb(ctx: commands.Context) -> None:
        lines = [
            "Slash commands are now the primary interface.",
            "`/create` build or import a character with helper fields",
            "`/scvmbirth` generate a ready-to-play random character",
            "`/characters` list your roster",
            "`/character-switch` set the active character for this server",
            "`/character-archive` mark a character archived, dead, npc, or active",
            "`/gettingbetter` update stats with typed options",
            "`/classes` list stored classes",
            "`/classinfo` inspect one stored class",
            "`/sheet` show your character",
            "`/export` download your character sheet",
            f"Legacy prefix commands still exist for now under `{prefix}`.",
            f"`{prefix}setstat <ability> <value>` set agility, presence, strength, or toughness",
            f"`{prefix}setfield <field> <value>` update name, class_name, background, description, hp, max_hp, omens, or silver",
            f"`{prefix}improve <field> <delta>` increment stats, HP, omens, or silver without retyping totals",
            f"`{prefix}additem <item>` add a weapon, armor, scroll, or other equipment",
            f"`{prefix}removeitem <item>` remove one equipment entry by exact text",
            f"`{prefix}addnote <text>` add a note for scars, powers, debts, or session reminders",
            f"`{prefix}removenote <text>` remove one note by exact text",
            f"`{prefix}roll d6`, `{prefix}roll 2d8+1` for raw dice",
            f"`{prefix}roll presence` or `{prefix}roll strength 14` for MORK BORG ability tests",
        ]
        await ctx.send("\n".join(lines))

    @bot.command(name="classes")
    async def classes(ctx: commands.Context) -> None:
        class_names = [class_template.name for class_template in store.list_classes()]
        await ctx.send("Available classes:\n" + "\n".join(f"- {name}" for name in class_names))

    @bot.command(name="classinfo")
    async def classinfo(ctx: commands.Context, *, class_name: str) -> None:
        class_template = store.find_class(class_name)
        if class_template is None:
            raise commands.BadArgument(
                f"No stored class named `{class_name}`. Try `{prefix}classes` to see available options."
            )
        await ctx.send(build_class_summary(class_template))

    @bot.command(name="create")
    async def create(ctx: commands.Context) -> None:
        try:
            dm_channel = await ensure_dm_channel(ctx.author)
        except discord.Forbidden:
            await ctx.send("I couldn't DM you. Please enable direct messages from server members and try `!create` again.")
            return

        await ctx.send("I sent you a DM with the character form. Reply there and I'll save it privately.")
        await dm_channel.send(
            "Fill out this character form in one message and send it back here. "
            f"The import window stays open for {INTERACTIVE_TIMEOUT_SECONDS // 60} minutes.\n\n"
            f"```text\n{CREATE_FORM_TEMPLATE}```"
        )

        try:
            form_reply = await prompt_for_response(
                bot,
                ctx.author,
                dm_channel,
                "Send back the completed form.",
            )
        except TimeoutError:
            await dm_channel.send("Character creation timed out before it was finished. Run `!create` again when you're ready.")
            return

        form_data = parse_form_reply(form_reply or "")
        required_fields = ["name", "class", "agility", "presence", "strength", "toughness", "hp", "max_hp", "omens", "silver"]
        missing = [field for field in required_fields if not form_data.get(field)]
        if missing:
            await dm_channel.send(
                "I couldn't save that character because some required fields were missing: "
                + ", ".join(f"`{field}`" for field in missing)
            )
            return

        try:
            agility = parse_int(form_data["agility"])
            presence = parse_int(form_data["presence"])
            strength = parse_int(form_data["strength"])
            toughness = parse_int(form_data["toughness"])
            hp = parse_int(form_data["hp"])
            max_hp = parse_int(form_data["max_hp"])
            omens = parse_int(form_data["omens"])
            silver = parse_int(form_data["silver"])
        except ValueError:
            await dm_channel.send(
                "One of the numeric fields was invalid. Please use whole numbers like `-1`, `0`, or `2`, then run `!create` again."
            )
            return

        character = Character(
            user_id=ctx.author.id,
            discord_name=ctx.author.display_name,
            name=form_data["name"].strip(),
            background=form_data.get("background", "").strip(),
            description=form_data.get("description", "").strip(),
            agility=agility,
            presence=presence,
            strength=strength,
            toughness=toughness,
            hp=hp,
            max_hp=max_hp,
            omens=omens,
            silver=silver,
            equipment=parse_csv_field(form_data.get("equipment")),
            notes=parse_csv_field(form_data.get("notes")),
        )
        apply_class_selection(store, character, form_data["class"])
        character = store.upsert(character)
        if ctx.guild is not None and character.id is not None:
            store.set_active_character(ctx.guild.id, ctx.author.id, character.id)
        await dm_channel.send("Character created and saved.")
        await dm_channel.send(build_character_sheet(character))
        await ctx.send(f"Saved **{character.name}** from your DM form.")

    @bot.command(name="gettingbetter")
    async def gettingbetter(ctx: commands.Context) -> None:
        character = require_character_for_ctx(ctx)
        try:
            dm_channel = await ensure_dm_channel(ctx.author)
        except discord.Forbidden:
            await ctx.send(
                "I couldn't DM you. Please enable direct messages from server members and try `!gettingbetter` again."
            )
            return

        await ctx.send("I sent you a DM for the `Getting Better` flow so we can keep the channel clean.")
        mode_choices = {
            "auto": "auto",
            "automatic": "auto",
            "a": "auto",
            "manual": "manual",
            "m": "manual",
        }
        direction_choices = {
            "up": "up",
            "+": "up",
            "down": "down",
            "-": "down",
            "stay": "stay",
            "same": "stay",
            "0": "stay",
        }

        try:
            mode = await prompt_for_choice(
                bot,
                ctx.author,
                dm_channel,
                "Choose `Getting Better` mode. Automatic rolls a d6 for each ability. Manual lets you choose up, down, or stay for each ability.",
                mode_choices,
            )
        except TimeoutError:
            await dm_channel.send("`!gettingbetter` timed out before a mode was chosen. Run it again when you're ready.")
            return

        summaries: list[str] = []

        if mode == "auto":
            for ability_name in ABILITY_NAMES:
                current_value = character.get_ability(ability_name)
                roll = random.randint(1, 6)

                if current_value <= 1:
                    proposed_value = current_value - 1 if roll == 1 else current_value + 1
                else:
                    proposed_value = current_value + 1 if roll >= current_value else current_value - 1

                new_value = clamp_ability(proposed_value)
                character.set_ability(ability_name, new_value)

                if new_value > current_value:
                    summaries.append(
                        f"`{ability_name.title()}` {current_value:+d} -> `{new_value:+d}` from `d6({roll})`"
                    )
                elif new_value < current_value:
                    summaries.append(
                        f"`{ability_name.title()}` {current_value:+d} -> `{new_value:+d}` from `d6({roll})`"
                    )
                else:
                    summaries.append(
                        f"`{ability_name.title()}` stayed at `{new_value:+d}` from `d6({roll})` because it hit a cap"
                    )
        else:
            try:
                for ability_name in ABILITY_NAMES:
                    current_value = character.get_ability(ability_name)
                    direction = await prompt_for_choice(
                        bot,
                        ctx.author,
                        dm_channel,
                        f"What happens to `{ability_name.title()}`? Current value: `{current_value:+d}`",
                        direction_choices,
                    )
                    if direction == "up":
                        new_value = clamp_ability(current_value + 1)
                    elif direction == "down":
                        new_value = clamp_ability(current_value - 1)
                    else:
                        new_value = current_value

                    character.set_ability(ability_name, new_value)
                    summaries.append(f"`{ability_name.title()}` {current_value:+d} -> `{new_value:+d}`")
            except TimeoutError:
                await dm_channel.send("`!gettingbetter` timed out during manual selection. Run it again when you're ready.")
                return

        character.discord_name = ctx.author.display_name
        store.upsert(character)
        await dm_channel.send(f"**{character.name}** has gotten better.\n" + "\n".join(summaries))
        await dm_channel.send(build_character_sheet(character))
        await ctx.send(f"Updated **{character.name}** through DM.")

    @bot.command(name="sheet")
    async def sheet(ctx: commands.Context) -> None:
        character = require_character_for_ctx(ctx)
        await ctx.send(build_character_sheet(character))

    @bot.command(name="export")
    async def export(ctx: commands.Context) -> None:
        character = require_character_for_ctx(ctx)
        payload = BytesIO(character.export_text().encode("utf-8"))
        await ctx.send(
            content=f"Export for **{character.name}**",
            file=discord.File(payload, filename=f"{character.name.replace(' ', '_').lower()}_sheet.txt"),
        )

    @bot.command(name="setstat")
    async def setstat(ctx: commands.Context, ability: str, value: str) -> None:
        character = require_character_for_ctx(ctx)
        normalized = normalize_ability_name(ability)
        parsed_value = parse_int(value)
        character.discord_name = ctx.author.display_name
        character.set_ability(normalized, parsed_value)
        store.upsert(character)
        await ctx.send(f"{normalized.title()} set to `{parsed_value:+d}` for **{character.name}**.")

    @bot.command(name="setfield")
    async def setfield(ctx: commands.Context, field_name: str, *, value: str) -> None:
        character = require_character_for_ctx(ctx)
        normalized = field_name.lower().strip()
        if normalized not in EDITABLE_FIELDS:
            choices = ", ".join(sorted(EDITABLE_FIELDS))
            raise commands.BadArgument(f"Unknown field '{field_name}'. Use one of: {choices}.")

        character.discord_name = ctx.author.display_name
        if normalized in {"hp", "max_hp", "omens", "silver"}:
            setattr(character, normalized, parse_int(value))
        elif normalized == "class_name":
            apply_class_selection(store, character, value)
        else:
            setattr(character, normalized, value.strip())

        store.upsert(character)
        await ctx.send(f"{normalized} updated for **{character.name}**.")

    @bot.command(name="improve")
    async def improve(ctx: commands.Context, field_name: str, delta: str) -> None:
        character = require_character_for_ctx(ctx)
        normalized = field_name.lower().strip()
        amount = parse_int(delta)

        if normalized in ABILITY_NAMES:
            current_value = character.get_ability(normalized)
            new_value = current_value + amount
            character.set_ability(normalized, new_value)
        elif normalized in {"hp", "max_hp", "omens", "silver"}:
            current_value = getattr(character, normalized)
            new_value = current_value + amount
            setattr(character, normalized, new_value)
        else:
            allowed = ", ".join(list(ABILITY_NAMES) + ["hp", "max_hp", "omens", "silver"])
            raise commands.BadArgument(f"Unknown improvement field '{field_name}'. Use one of: {allowed}.")

        character.discord_name = ctx.author.display_name
        store.upsert(character)
        await ctx.send(
            f"{normalized} adjusted by `{amount:+d}`. New value for **{character.name}**: `{new_value:+d}`"
        )

    @bot.command(name="additem")
    async def additem(ctx: commands.Context, *, item: str) -> None:
        character = require_character_for_ctx(ctx)
        character.discord_name = ctx.author.display_name
        character.equipment.append(item.strip())
        store.upsert(character)
        await ctx.send(f"Added `{item.strip()}` to **{character.name}**.")

    @bot.command(name="removeitem")
    async def removeitem(ctx: commands.Context, *, item: str) -> None:
        character = require_character_for_ctx(ctx)
        target = item.strip()
        try:
            character.equipment.remove(target)
        except ValueError as error:
            raise commands.BadArgument(f"`{target}` was not found on your equipment list.") from error
        store.upsert(character)
        await ctx.send(f"Removed `{target}` from **{character.name}**.")

    @bot.command(name="addnote")
    async def addnote(ctx: commands.Context, *, note: str) -> None:
        character = require_character_for_ctx(ctx)
        character.discord_name = ctx.author.display_name
        character.notes.append(note.strip())
        store.upsert(character)
        await ctx.send(f"Added note to **{character.name}**.")

    @bot.command(name="removenote")
    async def removenote(ctx: commands.Context, *, note: str) -> None:
        character = require_character_for_ctx(ctx)
        target = note.strip()
        try:
            character.notes.remove(target)
        except ValueError as error:
            raise commands.BadArgument(f"Note `{target}` was not found.") from error
        store.upsert(character)
        await ctx.send(f"Removed note from **{character.name}**.")

    @bot.command(name="roll")
    async def roll(ctx: commands.Context, target: str, dr: int = DEFAULT_DR) -> None:
        lowered = target.lower().strip()
        if lowered in ABILITY_NAMES or lowered in ABILITY_ALIAS_SET:
            character = require_character_for_ctx(ctx)
            ability_name = normalize_ability_name(lowered)
            modifier = character.get_ability(ability_name)
            die = random.randint(1, 20)
            total = die + modifier
            outcome = "Success" if total >= dr else "Failure"
            await ctx.send(
                f"**{character.name}** rolls `{ability_name.title()}`: "
                f"`d20({die}) {modifier:+d} = {total}` vs DR `{dr}` -> **{outcome}**"
            )
            return

        rolls, modifier, total = roll_dice(lowered)
        modifier_text = f" {modifier:+d}" if modifier else ""
        await ctx.send(f"Rolled `{target}` -> {rolls}{modifier_text} = **{total}**")

    @bot.tree.command(name="ping", description="Check whether the bot is online and responding.")
    async def slash_ping(interaction: discord.Interaction) -> None:
        latency_ms = round(bot.latency * 1000)
        await interaction.response.send_message(f"Pong. Gateway latency: `{latency_ms}ms`", ephemeral=True)

    @bot.tree.command(name="classes", description="List the class templates stored in the bot database.")
    async def slash_classes(interaction: discord.Interaction) -> None:
        class_names = [class_template.name for class_template in store.list_classes()]
        await interaction.response.send_message(
            "Available classes:\n" + "\n".join(f"- {name}" for name in class_names),
            ephemeral=True,
        )

    @bot.tree.command(name="classinfo", description="Show details for one stored class.")
    @app_commands.describe(class_name="Stored class name")
    @app_commands.autocomplete(class_name=class_name_autocomplete)
    async def slash_classinfo(interaction: discord.Interaction, class_name: str) -> None:
        class_template = store.find_class(class_name)
        if class_template is None:
            await interaction.response.send_message(
                f"No stored class named `{class_name}`. Try `/classes` first.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(build_class_summary(class_template), ephemeral=True)

    @bot.tree.command(name="characters", description="List your saved characters and their status.")
    async def slash_characters(interaction: discord.Interaction) -> None:
        characters = store.list_characters(interaction.user.id, include_archived=True)
        if not characters:
            await interaction.response.send_message("You do not have any saved characters yet. Start with `/create`.", ephemeral=True)
            return
        active_id = None
        if interaction.guild_id is not None:
            active_character = store.get_active_character(interaction.guild_id, interaction.user.id)
            active_id = active_character.id if active_character else None
        lines = []
        for character in characters:
            active_marker = " <- active here" if active_id == character.id else ""
            lines.append(f"- #{character.id} **{character.name}** [{character.status}] ({character.class_name}){active_marker}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @bot.tree.command(name="character-switch", description="Set your active character for this server.")
    @app_commands.describe(character="Character name or id")
    @app_commands.autocomplete(character=character_name_autocomplete)
    async def slash_character_switch(interaction: discord.Interaction, character: str) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("Use this in a server so I can store your active character for that server.", ephemeral=True)
            return
        selected = store.find_character(interaction.user.id, character, include_archived=False)
        if selected is None:
            await interaction.response.send_message("I couldn't find an active character matching that selection.", ephemeral=True)
            return
        if selected.id is None:
            await interaction.response.send_message("That character is missing an internal id and cannot be activated.", ephemeral=True)
            return
        store.set_active_character(interaction.guild_id, interaction.user.id, selected.id)
        await interaction.response.send_message(f"Active character for this server is now **{selected.name}**.", ephemeral=True)

    @bot.tree.command(name="character-archive", description="Mark one of your characters as archived, dead, or NPC.")
    @app_commands.describe(character="Character name or id", status="New stored status")
    @app_commands.autocomplete(character=character_name_autocomplete)
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Archived", value="archived"),
            app_commands.Choice(name="Dead", value="dead"),
            app_commands.Choice(name="NPC", value="npc"),
            app_commands.Choice(name="Active", value="active"),
        ]
    )
    async def slash_character_archive(
        interaction: discord.Interaction,
        character: str,
        status: str,
    ) -> None:
        selected = store.find_character(interaction.user.id, character, include_archived=True)
        if selected is None or selected.id is None:
            await interaction.response.send_message("I couldn't find a character matching that selection.", ephemeral=True)
            return
        updated = store.set_character_status(selected.id, status)
        if updated is None:
            await interaction.response.send_message("I couldn't update that character.", ephemeral=True)
            return
        if interaction.guild_id is not None and status in {"archived", "dead", "npc"}:
            active_character = store.get_active_character(interaction.guild_id, interaction.user.id)
            if active_character and active_character.id == updated.id:
                replacement = next((item for item in store.list_characters(interaction.user.id) if item.id != updated.id), None)
                if replacement and replacement.id is not None:
                    store.set_active_character(interaction.guild_id, interaction.user.id, replacement.id)
                else:
                    store.clear_active_character(interaction.guild_id, interaction.user.id)
        await interaction.response.send_message(
            f"Character **{updated.name}** is now marked `{updated.status}`.",
            ephemeral=True,
        )

    @bot.tree.command(name="character-delete", description="Permanently delete one of your saved characters.")
    @app_commands.describe(character="Character name or id")
    @app_commands.autocomplete(character=character_name_autocomplete)
    async def slash_character_delete(interaction: discord.Interaction, character: str) -> None:
        selected = store.find_character(interaction.user.id, character, include_archived=True)
        if selected is None or selected.id is None:
            await interaction.response.send_message("I couldn't find a character matching that selection.", ephemeral=True)
            return
        store.delete_character(selected.id)
        await interaction.response.send_message(f"Deleted character **{selected.name}**.", ephemeral=True)

    @bot.tree.command(name="scvmbirth", description="Generate a ready-to-play random character.")
    @app_commands.describe(class_name="Optional class to force instead of rolling from the catalog")
    @app_commands.autocomplete(class_name=class_name_autocomplete)
    async def slash_scvmbirth(interaction: discord.Interaction, class_name: str | None = None) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        if class_name:
            class_template = store.find_class(class_name)
            if class_template is None:
                await interaction.followup.send(
                    f"No stored class named `{class_name}`. Try `/classes` first.",
                    ephemeral=True,
                )
                return
        else:
            classes = store.list_classes()
            if not classes:
                await interaction.followup.send(
                    "No stored classes are available yet, so I can't generate a character.",
                    ephemeral=True,
                )
                return
            class_template = random.choice(classes)

        character = generate_random_character(
            class_template=class_template,
            user_id=interaction.user.id,
            discord_name=interaction.user.display_name,
        )
        character = store.upsert(character)
        if interaction.guild_id is not None and character.id is not None:
            store.set_active_character(interaction.guild_id, interaction.user.id, character.id)
        await send_interaction_text(
            interaction,
            f"Scvm birthed.\n{build_character_sheet(character)}",
            ephemeral=True,
            filename="scvmbirth.txt",
        )

    @bot.tree.command(name="sheet", description="Show your saved character sheet.")
    async def slash_sheet(interaction: discord.Interaction) -> None:
        character = get_active_character_for_context(store, interaction.user, interaction.guild_id)
        if character is None:
            await interaction.response.send_message("No active character found here. Use `/create` or `/character-switch`.", ephemeral=True)
            return
        await interaction.response.send_message(build_character_sheet(character), ephemeral=True)

    @bot.tree.command(name="export", description="Export your saved character sheet as a text file.")
    async def slash_export(interaction: discord.Interaction) -> None:
        character = get_active_character_for_context(store, interaction.user, interaction.guild_id)
        if character is None:
            await interaction.response.send_message("No active character found here. Use `/create` or `/character-switch`.", ephemeral=True)
            return
        payload = BytesIO(character.export_text().encode("utf-8"))
        await interaction.response.send_message(
            content=f"Export for **{character.name}**",
            file=discord.File(payload, filename=f"{character.name.replace(' ', '_').lower()}_sheet.txt"),
            ephemeral=True,
        )

    @bot.tree.command(name="roll", description="Roll dice or roll one of your character abilities.")
    @app_commands.describe(target="Dice expression like 2d6+1 or an ability like presence", dr="Difficulty rating")
    async def slash_roll(interaction: discord.Interaction, target: str, dr: int = DEFAULT_DR) -> None:
        lowered = target.lower().strip()
        if lowered in ABILITY_NAMES or lowered in ABILITY_ALIAS_SET:
            character = get_active_character_for_context(store, interaction.user, interaction.guild_id)
            if character is None:
                await interaction.response.send_message("No active character found here. Use `/create` or `/character-switch`.", ephemeral=True)
                return
            ability_name = normalize_ability_name(lowered)
            modifier = character.get_ability(ability_name)
            die = random.randint(1, 20)
            total = die + modifier
            outcome = "Success" if total >= dr else "Failure"
            await interaction.response.send_message(
                f"**{character.name}** rolls `{ability_name.title()}`: `d20({die}) {modifier:+d} = {total}` vs DR `{dr}` -> **{outcome}**"
            )
            return

        try:
            rolls, modifier, total = roll_dice(lowered)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        modifier_text = f" {modifier:+d}" if modifier else ""
        await interaction.response.send_message(f"Rolled `{target}` -> {rolls}{modifier_text} = **{total}**")

    @bot.tree.command(name="create", description="Create a new character and make it active in this server.")
    @app_commands.describe(
        name="Character name",
        class_name="Stored class name or custom class label",
        agility="Agility modifier like -1 or +2",
        presence="Presence modifier like -1 or +2",
        strength="Strength modifier like -1 or +2",
        toughness="Toughness modifier like -1 or +2",
        hp="Current HP",
        max_hp="Maximum HP",
        omens="Current Omens",
        silver="Current silver",
        background="Short background",
        description="Short character description",
        equipment="Comma-separated equipment",
        notes="Comma-separated notes",
    )
    @app_commands.autocomplete(class_name=class_name_autocomplete)
    async def slash_create(
        interaction: discord.Interaction,
        name: str,
        class_name: str,
        agility: str,
        presence: str,
        strength: str,
        toughness: str,
        hp: str,
        max_hp: str,
        omens: str,
        silver: str,
        background: str = "",
        description: str = "",
        equipment: str = "",
        notes: str = "",
    ) -> None:
        try:
            character = create_character_from_values(
                store,
                user_id=interaction.user.id,
                discord_name=interaction.user.display_name,
                name=name,
                class_name=class_name,
                background=background,
                description=description,
                agility=agility,
                presence=presence,
                strength=strength,
                toughness=toughness,
                hp=hp,
                max_hp=max_hp,
                omens=omens,
                silver=silver,
                equipment=equipment,
                notes=notes,
            )
        except ValueError:
            await interaction.response.send_message(
                "One of the numeric fields was invalid. Use whole numbers like `-1`, `0`, or `2`.",
                ephemeral=True,
            )
            return
        if interaction.guild_id is not None and character.id is not None:
            store.set_active_character(interaction.guild_id, interaction.user.id, character.id)
        await interaction.response.send_message(f"Character saved.\n{build_character_sheet(character)}", ephemeral=True)

    @bot.tree.command(name="setstat", description="Set one of your ability modifiers.")
    @app_commands.describe(ability="Ability name", value="Modifier like -1, 0, or +2")
    async def slash_setstat(interaction: discord.Interaction, ability: str, value: str) -> None:
        character = get_active_character_for_context(store, interaction.user, interaction.guild_id)
        if character is None:
            await interaction.response.send_message("No active character found here. Use `/create` or `/character-switch`.", ephemeral=True)
            return
        try:
            normalized = normalize_ability_name(ability)
            parsed_value = parse_int(value)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        character.discord_name = interaction.user.display_name
        character.set_ability(normalized, parsed_value)
        store.upsert(character)
        await interaction.response.send_message(
            f"{normalized.title()} set to `{parsed_value:+d}` for **{character.name}**.",
            ephemeral=True,
        )

    @bot.tree.command(name="setfield", description="Update one saved character field.")
    @app_commands.describe(field_name="Field such as hp, background, or class_name", value="New value")
    async def slash_setfield(interaction: discord.Interaction, field_name: str, value: str) -> None:
        character = get_active_character_for_context(store, interaction.user, interaction.guild_id)
        if character is None:
            await interaction.response.send_message("No active character found here. Use `/create` or `/character-switch`.", ephemeral=True)
            return
        normalized = field_name.lower().strip()
        if normalized not in EDITABLE_FIELDS:
            choices = ", ".join(sorted(EDITABLE_FIELDS))
            await interaction.response.send_message(
                f"Unknown field '{field_name}'. Use one of: {choices}.",
                ephemeral=True,
            )
            return

        try:
            character.discord_name = interaction.user.display_name
            if normalized in {"hp", "max_hp", "omens", "silver"}:
                setattr(character, normalized, parse_int(value))
            elif normalized == "class_name":
                apply_class_selection(store, character, value)
            else:
                setattr(character, normalized, value.strip())
            store.upsert(character)
        except ValueError:
            await interaction.response.send_message("That field expects a whole number.", ephemeral=True)
            return

        await interaction.response.send_message(f"{normalized} updated for **{character.name}**.", ephemeral=True)

    @bot.tree.command(name="improve", description="Adjust a saved stat or tracked field by a delta.")
    @app_commands.describe(field_name="Ability, hp, max_hp, omens, or silver", delta="Adjustment like +1 or -2")
    async def slash_improve(interaction: discord.Interaction, field_name: str, delta: str) -> None:
        character = get_active_character_for_context(store, interaction.user, interaction.guild_id)
        if character is None:
            await interaction.response.send_message("No active character found here. Use `/create` or `/character-switch`.", ephemeral=True)
            return
        normalized = field_name.lower().strip()
        try:
            amount = parse_int(delta)
            if normalized in ABILITY_NAMES:
                new_value = character.get_ability(normalized) + amount
                character.set_ability(normalized, new_value)
            elif normalized in {"hp", "max_hp", "omens", "silver"}:
                new_value = getattr(character, normalized) + amount
                setattr(character, normalized, new_value)
            else:
                allowed = ", ".join(list(ABILITY_NAMES) + ["hp", "max_hp", "omens", "silver"])
                await interaction.response.send_message(
                    f"Unknown improvement field '{field_name}'. Use one of: {allowed}.",
                    ephemeral=True,
                )
                return
        except ValueError:
            await interaction.response.send_message("The delta must be a whole number like `+1` or `-2`.", ephemeral=True)
            return

        character.discord_name = interaction.user.display_name
        store.upsert(character)
        await interaction.response.send_message(
            f"{normalized} adjusted by `{amount:+d}`. New value for **{character.name}**: `{new_value:+d}`",
            ephemeral=True,
        )

    @bot.tree.command(name="additem", description="Add one item to your equipment list.")
    async def slash_additem(interaction: discord.Interaction, item: str) -> None:
        character = get_active_character_for_context(store, interaction.user, interaction.guild_id)
        if character is None:
            await interaction.response.send_message("No active character found here. Use `/create` or `/character-switch`.", ephemeral=True)
            return
        character.discord_name = interaction.user.display_name
        character.equipment.append(item.strip())
        store.upsert(character)
        await interaction.response.send_message(f"Added `{item.strip()}` to **{character.name}**.", ephemeral=True)

    @bot.tree.command(name="removeitem", description="Remove one item from your equipment list.")
    async def slash_removeitem(interaction: discord.Interaction, item: str) -> None:
        character = get_active_character_for_context(store, interaction.user, interaction.guild_id)
        if character is None:
            await interaction.response.send_message("No active character found here. Use `/create` or `/character-switch`.", ephemeral=True)
            return
        target = item.strip()
        try:
            character.equipment.remove(target)
        except ValueError:
            await interaction.response.send_message(f"`{target}` was not found on your equipment list.", ephemeral=True)
            return
        store.upsert(character)
        await interaction.response.send_message(f"Removed `{target}` from **{character.name}**.", ephemeral=True)

    @bot.tree.command(name="addnote", description="Add one note to your character.")
    async def slash_addnote(interaction: discord.Interaction, note: str) -> None:
        character = get_active_character_for_context(store, interaction.user, interaction.guild_id)
        if character is None:
            await interaction.response.send_message("No active character found here. Use `/create` or `/character-switch`.", ephemeral=True)
            return
        character.discord_name = interaction.user.display_name
        character.notes.append(note.strip())
        store.upsert(character)
        await interaction.response.send_message(f"Added note to **{character.name}**.", ephemeral=True)

    @bot.tree.command(name="removenote", description="Remove one note from your character.")
    async def slash_removenote(interaction: discord.Interaction, note: str) -> None:
        character = get_active_character_for_context(store, interaction.user, interaction.guild_id)
        if character is None:
            await interaction.response.send_message("No active character found here. Use `/create` or `/character-switch`.", ephemeral=True)
            return
        target = note.strip()
        try:
            character.notes.remove(target)
        except ValueError:
            await interaction.response.send_message(f"Note `{target}` was not found.", ephemeral=True)
            return
        store.upsert(character)
        await interaction.response.send_message(f"Removed note from **{character.name}**.", ephemeral=True)

    @bot.tree.command(name="gettingbetter", description="Apply post-session stat changes.")
    @app_commands.describe(
        mode="Automatic rolls or manual stat choices",
        agility="Manual Agility result",
        presence="Manual Presence result",
        strength="Manual Strength result",
        toughness="Manual Toughness result",
    )
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Automatic", value="auto"),
            app_commands.Choice(name="Manual", value="manual"),
        ],
        agility=[
            app_commands.Choice(name="Up", value="up"),
            app_commands.Choice(name="Down", value="down"),
            app_commands.Choice(name="Stay", value="stay"),
        ],
        presence=[
            app_commands.Choice(name="Up", value="up"),
            app_commands.Choice(name="Down", value="down"),
            app_commands.Choice(name="Stay", value="stay"),
        ],
        strength=[
            app_commands.Choice(name="Up", value="up"),
            app_commands.Choice(name="Down", value="down"),
            app_commands.Choice(name="Stay", value="stay"),
        ],
        toughness=[
            app_commands.Choice(name="Up", value="up"),
            app_commands.Choice(name="Down", value="down"),
            app_commands.Choice(name="Stay", value="stay"),
        ],
    )
    async def slash_gettingbetter(
        interaction: discord.Interaction,
        mode: str,
        agility: str | None = None,
        presence: str | None = None,
        strength: str | None = None,
        toughness: str | None = None,
    ) -> None:
        character = get_active_character_for_context(store, interaction.user, interaction.guild_id)
        if character is None:
            await interaction.response.send_message("No active character found here. Use `/create` or `/character-switch`.", ephemeral=True)
            return

        manual_choices = None
        if mode == "manual":
            manual_choices = {
                "agility": agility or "stay",
                "presence": presence or "stay",
                "strength": strength or "stay",
                "toughness": toughness or "stay",
            }

        summaries = run_getting_better(character, mode, manual_choices)
        character.discord_name = interaction.user.display_name
        store.upsert(character)
        await interaction.response.send_message(
            f"**{character.name}** has gotten better.\n" + "\n".join(summaries) + "\n\n" + build_character_sheet(character),
            ephemeral=True,
        )

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing input: {error.param.name}. Try `{prefix}helpmb`.")
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send(str(error))
            return
        raise error

    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        command_name = interaction.command.qualified_name if interaction.command else "unknown"
        logger.exception("Slash command '%s' failed", command_name, exc_info=error)

        message = "That slash command failed. Check the bot console for the traceback."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


    return bot


def main() -> None:
    bot = build_bot()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is missing. Copy .env.example to .env and add your bot token.")
    bot.run(token)
