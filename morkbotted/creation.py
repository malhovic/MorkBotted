from __future__ import annotations

from collections.abc import Iterable

from morkbotted.character import Character, ClassFeature, ClassTemplate, selector_matches_feature
from morkbotted.security import MAX_EQUIPMENT_ITEMS, MAX_NOTES, escape_discord_text, validate_text, validate_text_list
from morkbotted.storage import CharacterStore


class CharacterCreationError(ValueError):
    def __init__(
        self,
        field_name: str,
        raw_value: str,
        hint: str,
        field_errors: Iterable["CharacterCreationError"] | None = None,
    ) -> None:
        self.field_name = field_name
        self.raw_value = raw_value
        self.hint = hint
        self.field_errors = list(field_errors or [])
        if self.field_errors:
            details = "\n".join(f"- `{error.field_name}`: {error.hint}" for error in self.field_errors)
            super().__init__(f"Fix these fields:\n{details}")
            return
        display_value = escape_discord_text(raw_value[:80])
        super().__init__(f"`{field_name}` value `{display_value}` is invalid. {hint}")


def parse_int(raw: str) -> int:
    return int(raw.replace("+", ""))


def parse_int_field(field_name: str, raw: str | None) -> int:
    raw_value = raw or ""
    value = raw_value.strip()
    if not value:
        raise CharacterCreationError(field_name, raw_value, "Enter a whole number, such as `-1`, `0`, `2`, or `90`.")
    try:
        return parse_int(value)
    except ValueError as error:
        raise CharacterCreationError(
            field_name,
            raw_value,
            "Enter only a whole number. Ability modifiers look like `-1`, `0`, or `+2`; HP, Omens, and silver use plain totals.",
        ) from error


def parse_csv_field(value: str | None) -> list[str]:
    if not value:
        return []
    if value.strip().lower() == "skip":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def resolve_class_feature(class_template: ClassTemplate, class_feature: str | None) -> ClassFeature | None:
    if not class_feature:
        return None
    value = class_feature.strip()
    if not value or value.lower() == "skip":
        return None
    for feature in class_template.features:
        if selector_matches_feature(value, feature):
            return feature
    return None


def class_feature_hint(character: Character) -> str:
    if not character.class_template or not character.class_template.features:
        return "This class does not have stored feature choices."

    examples = []
    for feature in character.class_template.features[:6]:
        category = feature.category.replace("_", " ")
        examples.append(f"`{category}: {feature.name}`")
    return "Use one of: " + "; ".join(examples) + "."


def apply_class_selection(
    store: CharacterStore,
    character: Character,
    raw_class_name: str,
    guild_id: int | None = None,
) -> Character:
    resolved_class = store.find_class(raw_class_name, guild_id)
    previous_class_id = character.class_id
    if resolved_class:
        character.class_id = resolved_class.id
        character.class_name = resolved_class.name
        character.class_template = resolved_class
    else:
        character.class_id = None
        character.class_name = raw_class_name.strip() or "Classless"
        character.class_template = None
    if character.class_id != previous_class_id:
        character.selected_class_feature_ids = []
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
    agility: str | None,
    presence: str | None,
    strength: str | None,
    toughness: str | None,
    hp: str | None,
    max_hp: str | None,
    omens: str | None,
    silver: str | None,
    equipment: str | None,
    notes: str | None,
    class_feature: str | None = None,
    guild_id: int | None = None,
) -> Character:
    field_errors: list[CharacterCreationError] = []

    def clean_field(field_name: str, value: str | None, *, required: bool = False) -> str:
        try:
            return validate_text(value, field_name, required=required)
        except ValueError as error:
            field_errors.append(CharacterCreationError(field_name, value or "", str(error)))
            return ""

    try:
        clean_equipment = validate_text_list(parse_csv_field(equipment), "equipment", max_items=MAX_EQUIPMENT_ITEMS)
    except ValueError as error:
        field_errors.append(CharacterCreationError("equipment", equipment or "", str(error)))
        clean_equipment = []

    try:
        clean_notes = validate_text_list(parse_csv_field(notes), "note", max_items=MAX_NOTES)
    except ValueError as error:
        field_errors.append(CharacterCreationError("notes", notes or "", str(error)))
        clean_notes = []

    clean_name = clean_field("name", name, required=True)
    clean_background = clean_field("background", background)
    clean_description = clean_field("description", description)
    clean_class_name = clean_field("class_name", class_name)
    clean_class_feature = clean_field("class_feature", class_feature) if class_feature else class_feature

    parsed_numbers: dict[str, int] = {}
    for field_name, raw_value in (
        ("agility", agility),
        ("presence", presence),
        ("strength", strength),
        ("toughness", toughness),
        ("hp", hp),
        ("max_hp", max_hp),
        ("omens", omens),
        ("silver", silver),
    ):
        try:
            parsed_numbers[field_name] = parse_int_field(field_name, raw_value)
        except CharacterCreationError as error:
            field_errors.append(error)

    if field_errors:
        if len(field_errors) == 1:
            raise field_errors[0]
        raise CharacterCreationError("fields", "", "One or more character fields need attention.", field_errors)

    character = Character(
        user_id=user_id,
        discord_name=discord_name,
        name=clean_name,
        background=clean_background,
        description=clean_description,
        agility=parsed_numbers["agility"],
        presence=parsed_numbers["presence"],
        strength=parsed_numbers["strength"],
        toughness=parsed_numbers["toughness"],
        hp=parsed_numbers["hp"],
        max_hp=parsed_numbers["max_hp"],
        omens=parsed_numbers["omens"],
        silver=parsed_numbers["silver"],
        equipment=clean_equipment,
        notes=clean_notes,
    )
    apply_class_selection(store, character, clean_class_name, guild_id)
    if clean_class_feature and not character.class_template:
        raise CharacterCreationError(
            "class_name",
            clean_class_name,
            "Choose one of the autocompleted stored classes before selecting `class_feature`, or leave `class_feature` blank for a custom class.",
        )
    if clean_class_feature and character.class_template and not character.class_template.features:
        raise CharacterCreationError("class_feature", clean_class_feature, class_feature_hint(character))
    if clean_class_feature and character.class_template and character.class_template.features:
        selected_feature = resolve_class_feature(character.class_template, clean_class_feature)
        if selected_feature is None or selected_feature.id is None:
            raise CharacterCreationError("class_feature", clean_class_feature, class_feature_hint(character))
        character.selected_class_feature_ids.append(selected_feature.id)
    return store.upsert(character, guild_id)
