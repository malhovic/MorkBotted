from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from morkbotted.character import Character, ClassFeature, ClassTemplate
from morkbotted.class_data import CLASS_SEED_DATA


class CharacterStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()
        self._seed_classes()
        self._maybe_migrate_json()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL UNIQUE,
                    source TEXT NOT NULL,
                    description TEXT NOT NULL,
                    starting_silver TEXT,
                    omen_die TEXT,
                    hp_formula TEXT,
                    ability_summary TEXT,
                    equipment_summary TEXT,
                    notes TEXT
                );

                CREATE TABLE IF NOT EXISTS class_features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    roll_label TEXT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    discord_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    class_id INTEGER,
                    class_name TEXT NOT NULL,
                    background TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    agility INTEGER NOT NULL DEFAULT 0,
                    presence INTEGER NOT NULL DEFAULT 0,
                    strength INTEGER NOT NULL DEFAULT 0,
                    toughness INTEGER NOT NULL DEFAULT 0,
                    hp INTEGER NOT NULL DEFAULT 1,
                    max_hp INTEGER NOT NULL DEFAULT 1,
                    omens INTEGER NOT NULL DEFAULT 0,
                    silver INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS character_equipment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER NOT NULL,
                    item_text TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS character_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER NOT NULL,
                    note_text TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                );
                """
            )

    def _seed_classes(self) -> None:
        with self._connect() as connection:
            existing_count = connection.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
            if existing_count:
                return

            for class_payload in CLASS_SEED_DATA:
                cursor = connection.execute(
                    """
                    INSERT INTO classes (
                        slug, name, source, description, starting_silver, omen_die,
                        hp_formula, ability_summary, equipment_summary, notes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        class_payload["slug"],
                        class_payload["name"],
                        class_payload["source"],
                        class_payload["description"],
                        class_payload.get("starting_silver"),
                        class_payload.get("omen_die"),
                        class_payload.get("hp_formula"),
                        class_payload.get("ability_summary"),
                        class_payload.get("equipment_summary"),
                        class_payload.get("notes"),
                    ),
                )
                class_id = cursor.lastrowid
                for position, feature in enumerate(class_payload.get("features", []), start=1):
                    connection.execute(
                        """
                        INSERT INTO class_features (class_id, category, roll_label, name, description, position)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            class_id,
                            feature["category"],
                            feature.get("roll_label"),
                            feature["name"],
                            feature["description"],
                            position,
                        ),
                    )

    def _maybe_migrate_json(self) -> None:
        json_path = self.db_path.parent / "characters.json"
        if not json_path.exists():
            return

        with self._connect() as connection:
            existing_characters = connection.execute("SELECT COUNT(*) FROM characters").fetchone()[0]
            if existing_characters:
                return

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        for raw_character in payload.values():
            character = Character.from_dict(raw_character)
            resolved_class = self.find_class(character.class_name)
            if resolved_class:
                character.class_id = resolved_class.id
                character.class_name = resolved_class.name
                character.class_template = resolved_class
            self.upsert(character)

    def _build_class_template(self, row: sqlite3.Row, feature_rows: list[sqlite3.Row]) -> ClassTemplate:
        return ClassTemplate(
            id=row["id"],
            slug=row["slug"],
            name=row["name"],
            source=row["source"],
            description=row["description"],
            starting_silver=row["starting_silver"] or "",
            omen_die=row["omen_die"] or "",
            hp_formula=row["hp_formula"] or "",
            ability_summary=row["ability_summary"] or "",
            equipment_summary=row["equipment_summary"] or "",
            notes=row["notes"] or "",
            features=[
                ClassFeature(
                    id=feature_row["id"],
                    category=feature_row["category"],
                    roll_label=feature_row["roll_label"] or "",
                    name=feature_row["name"],
                    description=feature_row["description"],
                )
                for feature_row in feature_rows
            ],
        )

    def list_classes(self) -> list[ClassTemplate]:
        with self._connect() as connection:
            class_rows = connection.execute("SELECT * FROM classes ORDER BY name").fetchall()
            feature_rows = connection.execute(
                "SELECT * FROM class_features ORDER BY class_id, position"
            ).fetchall()

        features_by_class: dict[int, list[sqlite3.Row]] = {}
        for row in feature_rows:
            features_by_class.setdefault(row["class_id"], []).append(row)

        return [
            self._build_class_template(class_row, features_by_class.get(class_row["id"], []))
            for class_row in class_rows
        ]

    def find_class(self, query: str) -> ClassTemplate | None:
        normalized = query.strip().lower()
        if not normalized:
            return None

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM classes
                WHERE lower(name) = ? OR lower(slug) = ? OR replace(lower(name), '''', '') = ?
                """,
                (normalized, normalized, normalized.replace("'", "")),
            ).fetchone()
            if row is None:
                return None
            feature_rows = connection.execute(
                "SELECT * FROM class_features WHERE class_id = ? ORDER BY position",
                (row["id"],),
            ).fetchall()
        return self._build_class_template(row, feature_rows)

    def _build_character(
        self,
        row: sqlite3.Row,
        equipment_rows: list[sqlite3.Row],
        note_rows: list[sqlite3.Row],
    ) -> Character:
        class_template = None
        if row["class_id"] is not None:
            class_template = self.get_class_by_id(row["class_id"])

        return Character(
            user_id=row["user_id"],
            discord_name=row["discord_name"],
            name=row["name"],
            class_id=row["class_id"],
            class_name=row["class_name"],
            background=row["background"],
            description=row["description"],
            agility=row["agility"],
            presence=row["presence"],
            strength=row["strength"],
            toughness=row["toughness"],
            hp=row["hp"],
            max_hp=row["max_hp"],
            omens=row["omens"],
            silver=row["silver"],
            equipment=[item_row["item_text"] for item_row in equipment_rows],
            notes=[note_row["note_text"] for note_row in note_rows],
            class_template=class_template,
        )

    def get_class_by_id(self, class_id: int) -> ClassTemplate | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
            if row is None:
                return None
            feature_rows = connection.execute(
                "SELECT * FROM class_features WHERE class_id = ? ORDER BY position",
                (class_id,),
            ).fetchall()
        return self._build_class_template(row, feature_rows)

    def get(self, user_id: int) -> Character | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM characters WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                return None
            character_id = row["id"]
            equipment_rows = connection.execute(
                "SELECT * FROM character_equipment WHERE character_id = ? ORDER BY position, id",
                (character_id,),
            ).fetchall()
            note_rows = connection.execute(
                "SELECT * FROM character_notes WHERE character_id = ? ORDER BY position, id",
                (character_id,),
            ).fetchall()
        return self._build_character(row, equipment_rows, note_rows)

    def upsert(self, character: Character) -> Character:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT id FROM characters WHERE user_id = ?",
                (character.user_id,),
            ).fetchone()

            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO characters (
                        user_id, discord_name, name, class_id, class_name, background, description,
                        agility, presence, strength, toughness, hp, max_hp, omens, silver
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        character.user_id,
                        character.discord_name,
                        character.name,
                        character.class_id,
                        character.class_name,
                        character.background,
                        character.description,
                        character.agility,
                        character.presence,
                        character.strength,
                        character.toughness,
                        character.hp,
                        character.max_hp,
                        character.omens,
                        character.silver,
                    ),
                )
                character_id = cursor.lastrowid
            else:
                character_id = existing["id"]
                connection.execute(
                    """
                    UPDATE characters
                    SET discord_name = ?, name = ?, class_id = ?, class_name = ?, background = ?, description = ?,
                        agility = ?, presence = ?, strength = ?, toughness = ?, hp = ?, max_hp = ?, omens = ?, silver = ?
                    WHERE id = ?
                    """,
                    (
                        character.discord_name,
                        character.name,
                        character.class_id,
                        character.class_name,
                        character.background,
                        character.description,
                        character.agility,
                        character.presence,
                        character.strength,
                        character.toughness,
                        character.hp,
                        character.max_hp,
                        character.omens,
                        character.silver,
                        character_id,
                    ),
                )
                connection.execute("DELETE FROM character_equipment WHERE character_id = ?", (character_id,))
                connection.execute("DELETE FROM character_notes WHERE character_id = ?", (character_id,))

            for position, item in enumerate(character.equipment, start=1):
                connection.execute(
                    "INSERT INTO character_equipment (character_id, item_text, position) VALUES (?, ?, ?)",
                    (character_id, item, position),
                )
            for position, note in enumerate(character.notes, start=1):
                connection.execute(
                    "INSERT INTO character_notes (character_id, note_text, position) VALUES (?, ?, ?)",
                    (character_id, note, position),
                )

        return self.get(character.user_id) or character

    def delete(self, user_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM characters WHERE user_id = ?", (user_id,))
