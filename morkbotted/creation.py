from __future__ import annotations

from morkbotted.character import Character, ClassFeature, ClassTemplate, selector_matches_feature
from morkbotted.storage import CharacterStore


class CharacterCreationError(ValueError):
    def __init__(self, field_name: str, raw_value: str, hint: str) -> None:
        self.field_name = field_name
        self.raw_value = raw_value
        self.hint = hint
        super().__init__(f"`{field_name}` value `{raw_value}` is invalid. {hint}")


def parse_int(raw: str) -> int:
    return int(raw.replace("+", ""))


def parse_int_field(field_name: str, raw: str) -> int:
    value = raw.strip()
    if not value:
        raise CharacterCreationError(field_name, raw, "Enter a whole number, such as `-1`, `0`, `2`, or `90`.")
    try:
        return parse_int(value)
    except ValueError as error:
        raise CharacterCreationError(
            field_name,
            raw,
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


def apply_class_selection(store: CharacterStore, character: Character, raw_class_name: str) -> Character:
    resolved_class = store.find_class(raw_class_name)
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
    character = Character(
        user_id=user_id,
        discord_name=discord_name,
        name=name.strip(),
        background=background.strip(),
        description=description.strip(),
        agility=parse_int_field("agility", agility),
        presence=parse_int_field("presence", presence),
        strength=parse_int_field("strength", strength),
        toughness=parse_int_field("toughness", toughness),
        hp=parse_int_field("hp", hp),
        max_hp=parse_int_field("max_hp", max_hp),
        omens=parse_int_field("omens", omens),
        silver=parse_int_field("silver", silver),
        equipment=parse_csv_field(equipment),
        notes=parse_csv_field(notes),
    )
    apply_class_selection(store, character, class_name)
    if class_feature and not character.class_template:
        raise CharacterCreationError(
            "class_name",
            class_name,
            "Choose one of the autocompleted stored classes before selecting `class_feature`, or leave `class_feature` blank for a custom class.",
        )
    if class_feature and character.class_template and not character.class_template.features:
        raise CharacterCreationError("class_feature", class_feature, class_feature_hint(character))
    if class_feature and character.class_template and character.class_template.features:
        selected_feature = resolve_class_feature(character.class_template, class_feature)
        if selected_feature is None or selected_feature.id is None:
            raise CharacterCreationError("class_feature", class_feature, class_feature_hint(character))
        character.selected_class_feature_ids.append(selected_feature.id)
    return store.upsert(character)
