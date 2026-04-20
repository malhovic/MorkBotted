from __future__ import annotations

import random
import re
from dataclasses import dataclass

from morkbotted.character import Character

OMEN_FORMULA_PATTERN = re.compile(r"^d(?P<sides>\d+)(?P<modifier>[+-]\d+)?$", re.IGNORECASE)
FEATURE_OMEN_PATTERN = re.compile(r"roll\s+(?P<formula>d\d+(?:[+-]\d+)?)\s+for\s+omens", re.IGNORECASE)


@dataclass(frozen=True)
class OmenFormula:
    sides: int
    modifier: int = 0

    @property
    def label(self) -> str:
        modifier_text = f"{self.modifier:+d}" if self.modifier else ""
        return f"d{self.sides}{modifier_text}"


def parse_omen_formula(raw: str) -> OmenFormula | None:
    match = OMEN_FORMULA_PATTERN.match(raw.strip())
    if not match:
        return None

    sides = int(match.group("sides"))
    modifier = int(match.group("modifier") or "0")
    if sides < 1:
        return None
    return OmenFormula(sides=sides, modifier=modifier)


def daily_omen_formula(character: Character) -> OmenFormula | None:
    for feature in character.selected_class_features():
        match = FEATURE_OMEN_PATTERN.search(feature.description)
        if match:
            parsed = parse_omen_formula(match.group("formula"))
            if parsed:
                return parsed

    if not character.class_template or not character.class_template.omen_die:
        return None
    return parse_omen_formula(character.class_template.omen_die)


def roll_daily_omens(character: Character, roller: random.Random | None = None) -> int:
    formula = daily_omen_formula(character)
    if formula is None:
        raise ValueError("This character does not have a stored daily omen die.")

    rng = roller or random
    return max(0, rng.randint(1, formula.sides) + formula.modifier)


def omen_status_text(character: Character) -> str:
    formula = daily_omen_formula(character)
    if formula is None:
        return f"**{character.name}** has `{character.omens}` omen(s) recorded. Daily omen die: unknown for this class."
    return f"**{character.name}** has `{character.omens}` omen(s) recorded. Daily omens: `{formula.label}`."
