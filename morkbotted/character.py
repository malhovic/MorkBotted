from __future__ import annotations

from dataclasses import asdict, dataclass, field
from io import StringIO
from typing import Any

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
class Character:
    user_id: int
    discord_name: str
    name: str = "Unnamed Scvm"
    class_name: str = "Classless"
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
        buffer.write(f"{self.name}\n")
        buffer.write(f"Played by: {self.discord_name}\n")
        buffer.write(f"Class: {self.class_name}\n")
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
        return [
            f"**{self.name}** ({self.class_name})",
            f"HP `{self.hp}/{self.max_hp}` | Omens `{self.omens}` | Silver `{self.silver}`",
            (
                "Abilities "
                f"`AGI {self.agility:+d}` "
                f"`PRE {self.presence:+d}` "
                f"`STR {self.strength:+d}` "
                f"`TGH {self.toughness:+d}`"
            ),
            f"Background: {self.background or 'None recorded.'}",
            f"Description: {self.description or 'None recorded.'}",
            "Equipment: " + (", ".join(self.equipment) if self.equipment else "None recorded."),
            "Notes: " + (" | ".join(self.notes) if self.notes else "None recorded."),
        ]


def normalize_ability_name(raw: str) -> str:
    normalized = ABILITY_ALIASES.get(raw.lower().strip())
    if not normalized:
        options = ", ".join(ABILITY_NAMES)
        raise ValueError(f"Unknown ability '{raw}'. Use one of: {options}.")
    return normalized
