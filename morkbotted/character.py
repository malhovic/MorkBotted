from __future__ import annotations

from dataclasses import asdict, dataclass, field
from io import StringIO
from typing import Any

from morkbotted.security import escape_discord_text

ABILITY_ALIASES = {
    "agi": "agility",
    "agility": "agility",
    "pre": "presence",
    "presence": "presence",
    "str": "strength",
    "strength": "strength",
    "tough": "toughness",
    "tgh": "toughness",
    "toughness": "toughness",
}

ABILITY_NAMES = ("agility", "presence", "strength", "toughness")

EDITABLE_FIELDS = {
    "name",
    "class_name",
    "background",
    "description",
    "hp",
    "max_hp",
    "omens",
    "silver",
}


@dataclass
class ClassFeature:
    category: str
    name: str
    description: str
    roll_label: str = ""
    id: int | None = None
    guild_id: int | None = None
    class_id: int | None = None
    reusable: bool = False


@dataclass
class ClassTemplate:
    slug: str
    name: str
    source: str
    description: str
    starting_silver: str = ""
    omen_die: str = ""
    hp_formula: str = ""
    ability_summary: str = ""
    equipment_summary: str = ""
    notes: str = ""
    features: list[ClassFeature] = field(default_factory=list)
    id: int | None = None
    guild_id: int | None = None


@dataclass
class Character:
    user_id: int
    discord_name: str
    id: int | None = None
    name: str = "Unnamed Scvm"
    class_id: int | None = None
    class_name: str = "Classless"
    status: str = "active"
    background: str = ""
    description: str = ""
    agility: int = 0
    presence: int = 0
    strength: int = 0
    toughness: int = 0
    hp: int = 1
    max_hp: int = 1
    omens: int = 0
    silver: int = 0
    equipment: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    selected_class_feature_ids: list[int] = field(default_factory=list)
    class_template: ClassTemplate | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Character":
        return cls(**payload)

    def set_ability(self, ability: str, value: int) -> None:
        setattr(self, normalize_ability_name(ability), value)

    def get_ability(self, ability: str) -> int:
        return getattr(self, normalize_ability_name(ability))

    def export_text(self) -> str:
        buffer = StringIO()
        selected_features = self.selected_class_features()
        buffer.write(f"{self.name}\n")
        buffer.write(f"Played by: {self.discord_name}\n")
        buffer.write(f"Class: {self.class_name}\n")
        buffer.write(f"Status: {self.status}\n")
        if self.class_template:
            buffer.write(f"Class Source: {self.class_template.source}\n")
        buffer.write(f"HP: {self.hp}/{self.max_hp}\n")
        buffer.write(f"Omens: {self.omens}\n")
        buffer.write(f"Silver: {self.silver}\n")
        buffer.write("\nAbilities\n")
        buffer.write(f"  Agility:   {self.agility:+d}\n")
        buffer.write(f"  Presence:  {self.presence:+d}\n")
        buffer.write(f"  Strength:  {self.strength:+d}\n")
        buffer.write(f"  Toughness: {self.toughness:+d}\n")
        buffer.write("\nBackground\n")
        buffer.write(f"{self.background or 'None recorded.'}\n")
        buffer.write("\nDescription\n")
        buffer.write(f"{self.description or 'None recorded.'}\n")
        if self.class_template:
            buffer.write("\nClass Notes\n")
            buffer.write(f"{self.class_template.description}\n")
            if self.class_template.ability_summary:
                buffer.write(f"Abilities: {self.class_template.ability_summary}\n")
            if self.class_template.equipment_summary:
                buffer.write(f"Equipment: {self.class_template.equipment_summary}\n")
            if self.class_template.hp_formula:
                buffer.write(f"HP Formula: {self.class_template.hp_formula}\n")
            if self.class_template.omen_die:
                buffer.write(f"Omen Die: {self.class_template.omen_die}\n")
            if self.class_template.notes:
                buffer.write(f"Notes: {self.class_template.notes}\n")
        if selected_features:
            buffer.write("\nClass Features\n")
            for feature in selected_features:
                prefix = f"[{feature.roll_label}] " if feature.roll_label else ""
                buffer.write(f"- {prefix}{feature.name}: {feature.description}\n")
        elif self.class_template and self.class_template.features:
            buffer.write("\nClass Features\n")
            buffer.write("- None recorded for this character.\n")
        buffer.write("\nEquipment\n")
        if self.equipment:
            for item in self.equipment:
                buffer.write(f"- {item}\n")
        else:
            buffer.write("- None recorded.\n")
        buffer.write("\nNotes\n")
        if self.notes:
            for note in self.notes:
                buffer.write(f"- {note}\n")
        else:
            buffer.write("- None recorded.\n")
        return buffer.getvalue().strip()

    def sheet_lines(self) -> list[str]:
        selected_features = self.selected_class_features()
        name = escape_discord_text(self.name)
        class_name = escape_discord_text(self.class_name)
        status = escape_discord_text(self.status)
        background = escape_discord_text(self.background) if self.background else "None recorded."
        description = escape_discord_text(self.description) if self.description else "None recorded."
        equipment = ", ".join(escape_discord_text(item) for item in self.equipment) if self.equipment else "None recorded."
        notes = " | ".join(escape_discord_text(note) for note in self.notes) if self.notes else "None recorded."
        lines = [
            f"**{name}** ({class_name})",
            f"Status `{status}`",
            f"HP `{self.hp}/{self.max_hp}` | Omens `{self.omens}` | Silver `{self.silver}`",
            (
                "Abilities "
                f"`AGI {self.agility:+d}` "
                f"`PRE {self.presence:+d}` "
                f"`STR {self.strength:+d}` "
                f"`TGH {self.toughness:+d}`"
            ),
            f"Background: {background}",
            f"Description: {description}",
            "Equipment: " + equipment,
            "Notes: " + notes,
        ]
        if self.class_template:
            lines.append(f"Class Source: {escape_discord_text(self.class_template.source)}")
            if self.class_template.omen_die:
                lines.append(f"Daily Omens: {escape_discord_text(self.class_template.omen_die)}")
        for feature in selected_features:
            prefix = f"[{escape_discord_text(feature.roll_label)}] " if feature.roll_label else ""
            lines.append(
                "Class Feature: "
                f"{prefix}{escape_discord_text(feature.name)}: {escape_discord_text(feature.description)}"
            )
        if self.class_template and self.class_template.features and not selected_features:
            lines.append("Class Feature: None recorded.")
        return lines

    def selected_class_features(self) -> list[ClassFeature]:
        if not self.class_template or not self.selected_class_feature_ids:
            return []

        selected_ids = set(self.selected_class_feature_ids)
        return [feature for feature in self.class_template.features if feature.id in selected_ids]


def normalize_ability_name(raw: str) -> str:
    normalized = ABILITY_ALIASES.get(raw.lower().strip())
    if not normalized:
        options = ", ".join(ABILITY_NAMES)
        raise ValueError(f"Unknown ability '{raw}'. Use one of: {options}.")
    return normalized


def selector_matches_feature(selector: str, feature: ClassFeature) -> bool:
    normalized_selector = normalize_feature_selector(selector)
    normalized_name = normalize_feature_selector(feature.name)
    normalized_roll = normalize_feature_selector(feature.roll_label)

    if normalized_selector == normalized_name:
        return True
    if normalized_roll and normalized_selector == normalized_roll:
        return True

    label_prefixes = (
        "class feature",
        "class_feature",
        "feature",
        feature.category,
        feature.category.replace("_", " "),
    )
    for label in label_prefixes:
        normalized_label = normalize_feature_selector(label)
        if normalized_selector.startswith(f"{normalized_label}:"):
            value = normalize_feature_selector(normalized_selector.split(":", 1)[1]).strip("[]")
            return value == normalized_name or bool(normalized_roll and value == normalized_roll)

    return False


def normalize_feature_selector(raw: str) -> str:
    return " ".join(raw.lower().strip().split())
