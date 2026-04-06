from __future__ import annotations

import random

from morkbotted.character import Character, ClassTemplate

NAME_TABLE = [
    "Aerg-Tval", "Agn", "Arvant", "Belsum", "Belum", "Brint", "Borda", "Daeru",
    "Eldar", "Felban", "Gotven", "Graft", "Grin", "Grittr", "Haeru", "Hargha",
    "Harmug", "Jotna", "Karg", "Karva", "Katla", "Keftar", "Klort", "Kratar",
    "Kutz", "Kvetin", "Lygan", "Margar", "Merkari", "Nagl", "Niduk", "Nifehl",
    "Prugl", "Qillnach", "Risten", "Svind", "Theras", "Therg", "Torvul", "Torn",
    "Urm", "Urvarg", "Vagal", "Vatan", "Von", "Vrakh", "Vresi", "Wemut",
]

GEAR_CARRY = [
    "Nothing but your own bad decisions",
    "Nothing but your own bad decisions",
    "Backpack (holds 7 normal-sized items)",
    "Sack (holds 10 normal-sized items)",
    "Small wagon",
    "Donkey",
]

GEAR_TABLE_ONE = [
    "Rope (30 feet)",
    "Presence + 4 torches",
    "Lantern with oil for Presence + 6 hours",
    "Magnesium strip",
    "Random unclean scroll",
    "Sharp needle",
    "Medicine chest (Presence + 4 uses)",
    "Metal file and lockpicks",
    "Bear trap",
    "Bomb",
    "Bottle of red poison (d4 doses)",
    "Silver crucifix",
]

GEAR_TABLE_TWO = [
    "Life elixir (d4 doses)",
    "Random sacred scroll",
    "Small but vicious dog",
    "d4 monkeys that ignore but love you",
    "Exquisite perfume worth 25s",
    "Toolbox",
    "Heavy chain (15 feet)",
    "Grappling hook",
    "Shield",
    "Crowbar",
    "Lard",
    "Tent",
]

WEAPONS = {
    4: ["Femur d4", "Staff d4", "Shortsword d4", "Knife d4"],
    6: ["Femur d4", "Staff d4", "Shortsword d4", "Knife d4", "Warhammer d6", "Sword d6"],
    8: ["Femur d4", "Staff d4", "Shortsword d4", "Knife d4", "Warhammer d6", "Sword d6", "Bow d6", "Flail d8"],
    10: ["Femur d4", "Staff d4", "Shortsword d4", "Knife d4", "Warhammer d6", "Sword d6", "Bow d6", "Flail d8", "Crossbow d8", "Zweihander d10"],
}

ARMOR = {
    2: ["No armor", "Light armor"],
    4: ["No armor", "Light armor", "Medium armor", "Heavy armor"],
}

CLASS_RULES = {
    "classless": {"silver": (2, 6, 10), "omens": (1, 2), "hp_die": 8, "weapon_die": 10, "armor_die": 4, "raw_mods": {}, "feature_picks": {}},
    "fanged-deserter": {"silver": (2, 6, 10), "omens": (1, 2), "hp_die": 10, "weapon_die": 10, "armor_die": 4, "raw_mods": {"strength": 2, "agility": -1, "presence": -1}, "feature_picks": {"special_item": 1}},
    "gutterborn-scum": {"silver": (1, 6, 10), "omens": (1, 2), "hp_die": 6, "weapon_die": 6, "armor_die": 2, "raw_mods": {"strength": -2}, "feature_picks": {"specialty": 1}},
    "esoteric-hermit": {"silver": (1, 6, 10), "omens": (1, 4), "hp_die": 4, "weapon_die": 4, "armor_die": 2, "raw_mods": {"presence": 2, "strength": -2}, "feature_picks": {"special_feature": 1}},
    "wretched-royalty": {"silver": (4, 6, 10), "omens": (1, 2), "hp_die": 6, "weapon_die": 8, "armor_die": 4, "raw_mods": {}, "feature_picks": {"royal_relic": 2}},
    "heretical-priest": {"silver": (3, 6, 10), "omens": (1, 4), "hp_die": 8, "weapon_die": 8, "armor_die": 4, "raw_mods": {"presence": 2, "strength": -2}, "feature_picks": {"holy_item": 1}},
    "occult-herbmaster": {"silver": (2, 6, 10), "omens": (1, 2), "hp_die": 6, "weapon_die": 6, "armor_die": 2, "raw_mods": {"toughness": 2, "strength": -2}, "feature_picks": {"decoction": 2}},
    "cursed-skinwalker": {"silver": (2, 6, 10), "omens": (1, 2), "hp_die": 8, "weapon_die": 6, "armor_die": 2, "raw_mods": {"presence": -2, "strength": 1, "toughness": 1}, "feature_picks": {"beast_form": 1}},
    "dead-gods-prophet": {"silver": (1, 6, 5), "omens": (1, 3), "hp_die": 4, "weapon_die": 4, "armor_die": 2, "raw_mods": {"presence": 2, "toughness": -2}, "feature_picks": {"gift": 2}},
    "pale-one": {"silver": (1, 6, 10), "omens": (1, 4), "hp_die": 6, "weapon_die": 6, "armor_die": 2, "raw_mods": {"agility": 1, "presence": 1, "toughness": -2}, "feature_picks": {"blessing": 1}},
    "forlorn-philosopher": {"silver": (1, 6, 10), "omens": (1, 4), "hp_die": 4, "weapon_die": 6, "armor_die": 2, "raw_mods": {"presence": 2, "strength": -2}, "feature_picks": {"philosopher_asset": 1}},
    "dire-hunter": {"silver": (1, 6, 10), "omens": (1, 2), "hp_die": 6, "weapon_die": 10, "armor_die": 2, "raw_mods": {"agility": 1, "presence": 1, "strength": -2}, "feature_picks": {"mantle": 1, "arcane_effect": 2}},
}


def _roll(num: int, sides: int) -> int:
    return sum(random.randint(1, sides) for _ in range(num))


def _to_modifier(total: int) -> int:
    if total <= 4:
        return -3
    if total <= 6:
        return -2
    if total <= 8:
        return -1
    if total <= 12:
        return 0
    if total <= 14:
        return 1
    if total <= 16:
        return 2
    return 3


def _roll_ability(raw_adjustment: int = 0) -> int:
    return _to_modifier(_roll(3, 6) + raw_adjustment)


def _pick_weapon(weapon_die: int) -> str:
    table = WEAPONS[weapon_die]
    return random.choice(table)


def _pick_armor(armor_die: int) -> str:
    table = ARMOR[armor_die]
    return random.choice(table)


def _pick_features(class_template: ClassTemplate, picks: dict[str, int]) -> list[str]:
    chosen: list[str] = []
    for category, count in picks.items():
        options = [feature for feature in class_template.features if feature.category == category]
        if not options:
            continue
        selected = random.sample(options, min(count, len(options)))
        for feature in selected:
            chosen.append(f"{feature.name}: {feature.description}")
    return chosen


def generate_random_character(
    *,
    class_template: ClassTemplate,
    user_id: int,
    discord_name: str,
) -> Character:
    rules = CLASS_RULES.get(class_template.slug, CLASS_RULES["classless"])
    raw_mods = rules["raw_mods"]
    agility = _roll_ability(raw_mods.get("agility", 0))
    presence = _roll_ability(raw_mods.get("presence", 0))
    strength = _roll_ability(raw_mods.get("strength", 0))
    toughness = _roll_ability(raw_mods.get("toughness", 0))
    hp = max(1, toughness + random.randint(1, rules["hp_die"]))
    omens = _roll(*rules["omens"])
    silver = _roll(rules["silver"][0], rules["silver"][1]) * rules["silver"][2]

    equipment = [
        _pick_weapon(rules["weapon_die"]),
        _pick_armor(rules["armor_die"]),
        random.choice(GEAR_CARRY),
        "Waterskin",
        f"{random.randint(1, 4)} day(s) of food",
        random.choice(GEAR_TABLE_ONE),
        random.choice(GEAR_TABLE_TWO),
    ]

    if class_template.slug == "esoteric-hermit":
        equipment.append("Random scroll")
    if class_template.slug == "dire-hunter":
        equipment.append("Bow d6")
        equipment.append("Arcane quiver")
    if class_template.slug == "forlorn-philosopher":
        equipment.append("Tablet of Ochre Obscurity")
    if class_template.slug == "dead-gods-prophet":
        equipment.append("Words of a dead god")

    notes = _pick_features(class_template, rules["feature_picks"])
    notes.append("Generated by MorkBotted scvmbirth.")

    return Character(
        user_id=user_id,
        discord_name=discord_name,
        name=random.choice(NAME_TABLE),
        class_id=class_template.id,
        class_name=class_template.name,
        background=f"Born into the ruin as a {class_template.name.lower()}.",
        description=f"A freshly generated {class_template.name.lower()} for the Dying World.",
        agility=agility,
        presence=presence,
        strength=strength,
        toughness=toughness,
        hp=hp,
        max_hp=hp,
        omens=omens,
        silver=silver,
        equipment=equipment,
        notes=notes,
        class_template=class_template,
    )
