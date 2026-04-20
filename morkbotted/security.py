from __future__ import annotations

import re


MAX_FIELD_LENGTHS = {
    "name": 80,
    "class_name": 80,
    "background": 500,
    "description": 500,
    "equipment": 200,
    "note": 500,
    "loot_item": 200,
    "loot_notes": 500,
    "class_feature": 200,
    "class_description": 1000,
    "class_source": 120,
    "class_rule": 120,
    "class_summary": 500,
    "class_notes": 1000,
    "class_feature_category": 80,
    "class_feature_name": 100,
    "class_feature_description": 1000,
    "class_feature_roll": 40,
    "npc_name": 80,
    "npc_description": 500,
    "npc_disposition": 120,
    "npc_notes": 1000,
}

MAX_EQUIPMENT_ITEMS = 30
MAX_NOTES = 30
SAFE_FILENAME_PATTERN = re.compile(r"[^a-z0-9_.-]+")


def clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.replace("\x00", "").split())


def validate_text(value: str | None, field_name: str, *, required: bool = False) -> str:
    cleaned = clean_text(value)
    if required and not cleaned:
        raise ValueError(f"{field_name.replace('_', ' ').title()} cannot be blank.")

    max_length = MAX_FIELD_LENGTHS[field_name]
    if len(cleaned) > max_length:
        raise ValueError(f"{field_name.replace('_', ' ').title()} must be {max_length} characters or fewer.")
    return cleaned


def validate_text_list(items: list[str], field_name: str, *, max_items: int) -> list[str]:
    if len(items) > max_items:
        raise ValueError(f"{field_name.replace('_', ' ').title()} can have at most {max_items} entries.")
    return [validate_text(item, field_name, required=True) for item in items]


def escape_discord_text(value: object) -> str:
    text = str(value)
    replacements = {
        "\\": "\\\\",
        "`": "\\`",
        "*": "\\*",
        "_": "\\_",
        "~": "\\~",
        "|": "\\|",
        ">": "\\>",
    }
    return "".join(replacements.get(character, character) for character in text)


def member_has_gm_access(member: object, gm_role_name: str | None) -> bool:
    guild_permissions = getattr(member, "guild_permissions", None)
    if bool(getattr(guild_permissions, "manage_guild", False)):
        return True
    if not gm_role_name:
        return False
    normalized_role_name = gm_role_name.casefold()
    return any(getattr(role, "name", "").casefold() == normalized_role_name for role in getattr(member, "roles", []))


def safe_export_filename(character_id: int | None, character_name: str) -> str:
    cleaned_name = validate_text(character_name, "name") or "character"
    normalized = SAFE_FILENAME_PATTERN.sub("_", cleaned_name.lower()).strip("._-")
    if not normalized:
        normalized = "character"
    prefix = f"character_{character_id}" if character_id is not None else normalized[:40]
    return f"{prefix}_sheet.txt"
