from __future__ import annotations

import os
import random
import re
from io import BytesIO
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from morkbotted.character import ABILITY_NAMES, EDITABLE_FIELDS, Character, normalize_ability_name
from morkbotted.storage import CharacterStore

DICE_PATTERN = re.compile(r"^(?P<count>\d*)d(?P<sides>\d+)(?P<modifier>[+-]\d+)?$", re.IGNORECASE)
DEFAULT_DR = 12
CREATE_TIMEOUT_SECONDS = 180


def parse_int(raw: str) -> int:
    return int(raw.replace("+", ""))


def build_character_sheet(character: Character) -> str:
    return "\n".join(character.sheet_lines())


async def prompt_for_response(
    bot: commands.Bot,
    ctx: commands.Context,
    prompt: str,
    *,
    optional: bool = False,
    timeout: int = CREATE_TIMEOUT_SECONDS,
) -> str | None:
    optional_hint = " Reply with `skip` to leave it blank." if optional else ""
    await ctx.send(f"{prompt}{optional_hint}")

    def check(message: discord.Message) -> bool:
        return message.author.id == ctx.author.id and message.channel.id == ctx.channel.id

    reply = await bot.wait_for("message", check=check, timeout=timeout)
    value = reply.content.strip()
    if optional and value.lower() == "skip":
        return None
    return value


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


def build_bot() -> commands.Bot:
    load_dotenv()
    prefix = os.getenv("COMMAND_PREFIX", "!")
    data_dir = Path(os.getenv("DATA_DIR", "data"))

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix=prefix, intents=intents, help_command=None)
    store = CharacterStore(data_dir)

    def require_character(user: discord.abc.User) -> Character:
        character = store.get(user.id)
        if character is None:
            raise commands.BadArgument(
                f"No character found for {user.display_name}. Start with `{prefix}create Your Name`."
            )
        return character

    @bot.event
    async def on_ready() -> None:
        print(f"Logged in as {bot.user} and ready to spread misery.")

    @bot.command(name="ping")
    async def ping(ctx: commands.Context) -> None:
        latency_ms = round(bot.latency * 1000)
        await ctx.send(f"Pong. Gateway latency: `{latency_ms}ms`")

    @bot.command(name="helpmb")
    async def helpmb(ctx: commands.Context) -> None:
        lines = [
            f"`{prefix}ping` confirm the bot is online and responding",
            f"`{prefix}create` start a guided character creation flow",
            f"`{prefix}sheet` show your current character summary",
            f"`{prefix}export` upload your character sheet as a text file",
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

    @bot.command(name="create")
    async def create(ctx: commands.Context) -> None:
        await ctx.send(
            "Starting guided character creation. "
            f"I'll ask a few questions and save the sheet at the end. "
            f"If you stop replying, the flow times out after {CREATE_TIMEOUT_SECONDS // 60} minutes."
        )

        try:
            name = await prompt_for_response(bot, ctx, "What is your character's name?")
            class_name = await prompt_for_response(
                bot,
                ctx,
                "What is their class or archetype? Use `Classless` if you want the default.",
            )
            background = await prompt_for_response(bot, ctx, "What background should I record?", optional=True)
            description = await prompt_for_response(bot, ctx, "Any short description or vibe?", optional=True)

            agility = parse_int(
                await prompt_for_response(bot, ctx, "Agility modifier? Example: `-1`, `0`, `+2`.")
            )
            presence = parse_int(
                await prompt_for_response(bot, ctx, "Presence modifier? Example: `-1`, `0`, `+2`.")
            )
            strength = parse_int(
                await prompt_for_response(bot, ctx, "Strength modifier? Example: `-1`, `0`, `+2`.")
            )
            toughness = parse_int(
                await prompt_for_response(bot, ctx, "Toughness modifier? Example: `-1`, `0`, `+2`.")
            )
            hp = parse_int(await prompt_for_response(bot, ctx, "Current HP?"))
            max_hp = parse_int(await prompt_for_response(bot, ctx, "Maximum HP?"))
            omens = parse_int(await prompt_for_response(bot, ctx, "How many Omens do they have?"))
            silver = parse_int(await prompt_for_response(bot, ctx, "How much silver do they carry?"))

            equipment_raw = await prompt_for_response(
                bot,
                ctx,
                "List equipment separated by commas, or reply `skip` if you want an empty inventory.",
                optional=True,
            )
            notes_raw = await prompt_for_response(
                bot,
                ctx,
                "Add any notes separated by commas, or reply `skip`.",
                optional=True,
            )
        except TimeoutError:
            await ctx.send("Character creation timed out before it was finished. Run `!create` to start again.")
            return
        except ValueError:
            await ctx.send(
                "One of those numeric replies was invalid. Please use whole numbers like `-1`, `0`, or `2`, then run `!create` again."
            )
            return

        equipment = [item.strip() for item in equipment_raw.split(",") if item.strip()] if equipment_raw else []
        notes = [note.strip() for note in notes_raw.split(",") if note.strip()] if notes_raw else []

        character = Character(
            user_id=ctx.author.id,
            discord_name=ctx.author.display_name,
            name=name.strip(),
            class_name=class_name.strip() or "Classless",
            background=(background or "").strip(),
            description=(description or "").strip(),
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
        store.upsert(character)
        await ctx.send("Character created and saved.")
        await ctx.send(build_character_sheet(character))

    @bot.command(name="sheet")
    async def sheet(ctx: commands.Context) -> None:
        character = require_character(ctx.author)
        await ctx.send(build_character_sheet(character))

    @bot.command(name="export")
    async def export(ctx: commands.Context) -> None:
        character = require_character(ctx.author)
        payload = BytesIO(character.export_text().encode("utf-8"))
        await ctx.send(
            content=f"Export for **{character.name}**",
            file=discord.File(payload, filename=f"{character.name.replace(' ', '_').lower()}_sheet.txt"),
        )

    @bot.command(name="setstat")
    async def setstat(ctx: commands.Context, ability: str, value: str) -> None:
        character = require_character(ctx.author)
        normalized = normalize_ability_name(ability)
        parsed_value = parse_int(value)
        character.discord_name = ctx.author.display_name
        character.set_ability(normalized, parsed_value)
        store.upsert(character)
        await ctx.send(f"{normalized.title()} set to `{parsed_value:+d}` for **{character.name}**.")

    @bot.command(name="setfield")
    async def setfield(ctx: commands.Context, field_name: str, *, value: str) -> None:
        character = require_character(ctx.author)
        normalized = field_name.lower().strip()
        if normalized not in EDITABLE_FIELDS:
            choices = ", ".join(sorted(EDITABLE_FIELDS))
            raise commands.BadArgument(f"Unknown field '{field_name}'. Use one of: {choices}.")

        character.discord_name = ctx.author.display_name
        if normalized in {"hp", "max_hp", "omens", "silver"}:
            setattr(character, normalized, parse_int(value))
        else:
            setattr(character, normalized, value.strip())

        store.upsert(character)
        await ctx.send(f"{normalized} updated for **{character.name}**.")

    @bot.command(name="improve")
    async def improve(ctx: commands.Context, field_name: str, delta: str) -> None:
        character = require_character(ctx.author)
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
        character = require_character(ctx.author)
        character.discord_name = ctx.author.display_name
        character.equipment.append(item.strip())
        store.upsert(character)
        await ctx.send(f"Added `{item.strip()}` to **{character.name}**.")

    @bot.command(name="removeitem")
    async def removeitem(ctx: commands.Context, *, item: str) -> None:
        character = require_character(ctx.author)
        target = item.strip()
        try:
            character.equipment.remove(target)
        except ValueError as error:
            raise commands.BadArgument(f"`{target}` was not found on your equipment list.") from error
        store.upsert(character)
        await ctx.send(f"Removed `{target}` from **{character.name}**.")

    @bot.command(name="addnote")
    async def addnote(ctx: commands.Context, *, note: str) -> None:
        character = require_character(ctx.author)
        character.discord_name = ctx.author.display_name
        character.notes.append(note.strip())
        store.upsert(character)
        await ctx.send(f"Added note to **{character.name}**.")

    @bot.command(name="removenote")
    async def removenote(ctx: commands.Context, *, note: str) -> None:
        character = require_character(ctx.author)
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
        if lowered in ABILITY_NAMES or lowered in {"agi", "pre", "str", "tgh", "tough"}:
            character = require_character(ctx.author)
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

    return bot


def main() -> None:
    bot = build_bot()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is missing. Copy .env.example to .env and add your bot token.")
    bot.run(token)
