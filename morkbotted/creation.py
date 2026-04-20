from __future__ import annotations

from morkbotted.character import Character
from morkbotted.storage import CharacterStore


def parse_int(raw: str) -> int:
    return int(raw.replace("+", ""))


def parse_csv_field(value: str | None) -> list[str]:
    if not value:
        return []
    if value.strip().lower() == "skip":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def append_class_feature_note(notes: list[str], class_feature: str | None) -> list[str]:
    if not class_feature:
        return notes
    value = class_feature.strip()
    if not value or value.lower() == "skip":
        return notes
    if ":" in value:
        notes.append(value)
    else:
        notes.append(f"class feature: {value}")
    return notes


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
    class_feature: str | None = None,
) -> Character:
    parsed_notes = parse_csv_field(notes)
    append_class_feature_note(parsed_notes, class_feature)
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
        notes=parsed_notes,
    )
    apply_class_selection(store, character, class_name)
    return store.upsert(character)
