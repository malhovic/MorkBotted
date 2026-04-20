from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from morkbotted.character import Character, ClassFeature, ClassTemplate
from morkbotted.class_data import CLASS_SEED_DATA


@dataclass
class PartyLoot:
    id: int
    guild_id: int
    item_text: str
    quantity: int = 1
    notes: str = ""


@dataclass
class NonPlayerCharacter:
    id: int
    guild_id: int
    name: str
    description: str = ""
    disposition: str = ""
    notes: str = ""


class CharacterStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()
        self._seed_classes()
        self._migrate_single_character_schema()
        self._repair_character_foreign_keys()
        self._maybe_migrate_json()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _table_columns(self, connection: sqlite3.Connection, table_name: str) -> set[str]:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row["name"] for row in rows}

    def _foreign_key_targets(self, connection: sqlite3.Connection, table_name: str) -> set[str]:
        rows = connection.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
        return {row["table"] for row in rows}

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
                    user_id INTEGER NOT NULL,
                    discord_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    class_id INTEGER,
                    class_name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
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
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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

                CREATE TABLE IF NOT EXISTS character_class_features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER NOT NULL,
                    class_feature_id INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
                    FOREIGN KEY (class_feature_id) REFERENCES class_features(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS active_characters (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    character_id INTEGER NOT NULL,
                    PRIMARY KEY (guild_id, user_id),
                    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS party_loot (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    item_text TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS npcs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    disposition TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def _migrate_single_character_schema(self) -> None:
        with self._connect() as connection:
            columns = self._table_columns(connection, "characters")
            if "status" not in columns or "created_at" not in columns or "updated_at" not in columns or "user_id" not in columns:
                connection.executescript(
                    """
                    ALTER TABLE characters RENAME TO characters_old;

                    CREATE TABLE characters (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        discord_name TEXT NOT NULL,
                        name TEXT NOT NULL,
                        class_id INTEGER,
                        class_name TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'active',
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
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL
                    );

                    INSERT INTO characters (
                        id, user_id, discord_name, name, class_id, class_name, status, background, description,
                        agility, presence, strength, toughness, hp, max_hp, omens, silver
                    )
                    SELECT
                        id, user_id, discord_name, name, class_id, class_name, 'active', background, description,
                        agility, presence, strength, toughness, hp, max_hp, omens, silver
                    FROM characters_old;

                    DROP TABLE characters_old;
                    """
                )

            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_active_characters_unique ON active_characters(guild_id, user_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_characters_owner_name ON characters(user_id, lower(name))"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_party_loot_guild ON party_loot(guild_id, id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_npcs_guild ON npcs(guild_id, lower(name), id)"
            )

    def _repair_character_foreign_keys(self) -> None:
        dependent_tables = ("character_equipment", "character_notes", "character_class_features", "active_characters")

        with self._connect() as connection:
            repair_needed = any(
                "characters_old" in self._foreign_key_targets(connection, table_name)
                for table_name in dependent_tables
            )
            if not repair_needed:
                return

            connection.execute("PRAGMA foreign_keys = OFF")
            try:
                connection.executescript(
                    """
                    ALTER TABLE character_equipment RENAME TO character_equipment_old;
                    CREATE TABLE character_equipment (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        character_id INTEGER NOT NULL,
                        item_text TEXT NOT NULL,
                        position INTEGER NOT NULL,
                        FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                    );
                    INSERT INTO character_equipment (id, character_id, item_text, position)
                    SELECT id, character_id, item_text, position
                    FROM character_equipment_old;
                    DROP TABLE character_equipment_old;

                    ALTER TABLE character_notes RENAME TO character_notes_old;
                    CREATE TABLE character_notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        character_id INTEGER NOT NULL,
                        note_text TEXT NOT NULL,
                        position INTEGER NOT NULL,
                        FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                    );
                    INSERT INTO character_notes (id, character_id, note_text, position)
                    SELECT id, character_id, note_text, position
                    FROM character_notes_old;
                    DROP TABLE character_notes_old;

                    ALTER TABLE character_class_features RENAME TO character_class_features_old;
                    CREATE TABLE character_class_features (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        character_id INTEGER NOT NULL,
                        class_feature_id INTEGER NOT NULL,
                        position INTEGER NOT NULL,
                        FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
                        FOREIGN KEY (class_feature_id) REFERENCES class_features(id) ON DELETE CASCADE
                    );
                    INSERT INTO character_class_features (id, character_id, class_feature_id, position)
                    SELECT id, character_id, class_feature_id, position
                    FROM character_class_features_old;
                    DROP TABLE character_class_features_old;

                    ALTER TABLE active_characters RENAME TO active_characters_old;
                    CREATE TABLE active_characters (
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        character_id INTEGER NOT NULL,
                        PRIMARY KEY (guild_id, user_id),
                        FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
                    );
                    INSERT INTO active_characters (guild_id, user_id, character_id)
                    SELECT guild_id, user_id, character_id
                    FROM active_characters_old;
                    DROP TABLE active_characters_old;
                    """
                )
            finally:
                connection.execute("PRAGMA foreign_keys = ON")

            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_active_characters_unique ON active_characters(guild_id, user_id)"
            )

    def _seed_classes(self) -> None:
        with self._connect() as connection:
            for class_payload in CLASS_SEED_DATA:
                existing = connection.execute(
                    "SELECT id FROM classes WHERE slug = ?",
                    (class_payload["slug"],),
                ).fetchone()
                if existing is None:
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
                else:
                    class_id = existing["id"]
                    connection.execute(
                        """
                        UPDATE classes
                        SET name = ?, source = ?, description = ?, starting_silver = ?, omen_die = ?,
                            hp_formula = ?, ability_summary = ?, equipment_summary = ?, notes = ?
                        WHERE id = ?
                        """,
                        (
                            class_payload["name"],
                            class_payload["source"],
                            class_payload["description"],
                            class_payload.get("starting_silver"),
                            class_payload.get("omen_die"),
                            class_payload.get("hp_formula"),
                            class_payload.get("ability_summary"),
                            class_payload.get("equipment_summary"),
                            class_payload.get("notes"),
                            class_id,
                        ),
                    )
                features = class_payload.get("features", [])
                existing_features = connection.execute(
                    "SELECT id, position FROM class_features WHERE class_id = ? ORDER BY position",
                    (class_id,),
                ).fetchall()
                existing_feature_ids_by_position = {row["position"]: row["id"] for row in existing_features}

                for position, feature in enumerate(features, start=1):
                    existing_feature_id = existing_feature_ids_by_position.get(position)
                    if existing_feature_id is None:
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
                    else:
                        connection.execute(
                            """
                            UPDATE class_features
                            SET category = ?, roll_label = ?, name = ?, description = ?, position = ?
                            WHERE id = ?
                            """,
                            (
                                feature["category"],
                                feature.get("roll_label"),
                                feature["name"],
                                feature["description"],
                                position,
                                existing_feature_id,
                            ),
                        )

                connection.execute(
                    "DELETE FROM class_features WHERE class_id = ? AND position > ?",
                    (class_id, len(features)),
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
        selected_feature_rows: list[sqlite3.Row],
    ) -> Character:
        class_template = None
        if row["class_id"] is not None:
            class_template = self.get_class_by_id(row["class_id"])

        return Character(
            id=row["id"],
            user_id=row["user_id"],
            discord_name=row["discord_name"],
            name=row["name"],
            class_id=row["class_id"],
            class_name=row["class_name"],
            status=row["status"],
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
            selected_class_feature_ids=[feature_row["class_feature_id"] for feature_row in selected_feature_rows],
            class_template=class_template,
        )

    def _get_character_by_row(self, row: sqlite3.Row | None) -> Character | None:
        if row is None:
            return None
        with self._connect() as connection:
            equipment_rows = connection.execute(
                "SELECT * FROM character_equipment WHERE character_id = ? ORDER BY position, id",
                (row["id"],),
            ).fetchall()
            note_rows = connection.execute(
                "SELECT * FROM character_notes WHERE character_id = ? ORDER BY position, id",
                (row["id"],),
            ).fetchall()
            selected_feature_rows = connection.execute(
                "SELECT * FROM character_class_features WHERE character_id = ? ORDER BY position, id",
                (row["id"],),
            ).fetchall()
        return self._build_character(row, equipment_rows, note_rows, selected_feature_rows)

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

    def get_character_by_id(self, character_id: int) -> Character | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM characters WHERE id = ?", (character_id,)).fetchone()
        return self._get_character_by_row(row)

    def get(self, user_id: int) -> Character | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM characters
                WHERE user_id = ? AND status = 'active'
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
        return self._get_character_by_row(row)

    def list_characters(self, user_id: int, include_archived: bool = False) -> list[Character]:
        query = "SELECT * FROM characters WHERE user_id = ?"
        params: list[object] = [user_id]
        if not include_archived:
            query += " AND status != 'archived'"
        query += " ORDER BY updated_at DESC, id DESC"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [character for character in (self._get_character_by_row(row) for row in rows) if character is not None]

    def find_character(self, user_id: int, name_or_id: str, include_archived: bool = True) -> Character | None:
        with self._connect() as connection:
            row = None
            if name_or_id.strip().isdigit():
                row = connection.execute(
                    "SELECT * FROM characters WHERE id = ? AND user_id = ?",
                    (int(name_or_id.strip()), user_id),
                ).fetchone()
            if row is None:
                query = "SELECT * FROM characters WHERE user_id = ? AND lower(name) = ?"
                params: list[object] = [user_id, name_or_id.strip().lower()]
                if not include_archived:
                    query += " AND status = 'active'"
                row = connection.execute(query, params).fetchone()
        return self._get_character_by_row(row)

    def get_active_character(self, guild_id: int, user_id: int) -> Character | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT c.*
                FROM active_characters ac
                JOIN characters c ON c.id = ac.character_id
                WHERE ac.guild_id = ? AND ac.user_id = ?
                """,
                (guild_id, user_id),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    """
                    SELECT *
                    FROM characters
                    WHERE user_id = ? AND status = 'active'
                    ORDER BY updated_at DESC, id DESC
                    LIMIT 1
                    """,
                    (user_id,),
            ).fetchone()
        return self._get_character_by_row(row)

    def list_active_characters_for_guild(self, guild_id: int) -> list[Character]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT c.*
                FROM active_characters ac
                JOIN characters c ON c.id = ac.character_id
                WHERE ac.guild_id = ? AND c.status = 'active'
                ORDER BY lower(c.name), c.id
                """,
                (guild_id,),
            ).fetchall()
        return [character for character in (self._get_character_by_row(row) for row in rows) if character is not None]

    def upsert(self, character: Character) -> Character:
        with self._connect() as connection:
            if character.id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO characters (
                        user_id, discord_name, name, class_id, class_name, status, background, description,
                        agility, presence, strength, toughness, hp, max_hp, omens, silver
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        character.user_id,
                        character.discord_name,
                        character.name,
                        character.class_id,
                        character.class_name,
                        character.status,
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
                character_id = character.id
                connection.execute(
                    """
                    UPDATE characters
                    SET discord_name = ?, name = ?, class_id = ?, class_name = ?, status = ?, background = ?, description = ?,
                        agility = ?, presence = ?, strength = ?, toughness = ?, hp = ?, max_hp = ?, omens = ?, silver = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        character.discord_name,
                        character.name,
                        character.class_id,
                        character.class_name,
                        character.status,
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
                connection.execute("DELETE FROM character_class_features WHERE character_id = ?", (character_id,))

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
            for position, feature_id in enumerate(character.selected_class_feature_ids, start=1):
                connection.execute(
                    """
                    INSERT INTO character_class_features (character_id, class_feature_id, position)
                    VALUES (?, ?, ?)
                    """,
                    (character_id, feature_id, position),
                )

        return self.get_character_by_id(character_id) or character

    def set_active_character(self, guild_id: int, user_id: int, character_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO active_characters (guild_id, user_id, character_id)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET character_id = excluded.character_id
                """,
                (guild_id, user_id, character_id),
            )

    def clear_active_character(self, guild_id: int, user_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM active_characters WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))

    def _build_party_loot(self, row: sqlite3.Row) -> PartyLoot:
        return PartyLoot(
            id=row["id"],
            guild_id=row["guild_id"],
            item_text=row["item_text"],
            quantity=row["quantity"],
            notes=row["notes"],
        )

    def list_party_loot(self, guild_id: int) -> list[PartyLoot]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM party_loot WHERE guild_id = ? ORDER BY id",
                (guild_id,),
            ).fetchall()
        return [self._build_party_loot(row) for row in rows]

    def add_party_loot(self, guild_id: int, item_text: str, quantity: int = 1, notes: str = "") -> PartyLoot:
        if quantity < 1:
            raise ValueError("Loot quantity must be at least 1.")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO party_loot (guild_id, item_text, quantity, notes)
                VALUES (?, ?, ?, ?)
                """,
                (guild_id, item_text.strip(), quantity, notes.strip()),
            )
            row = connection.execute("SELECT * FROM party_loot WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._build_party_loot(row)

    def remove_party_loot(self, guild_id: int, loot_id: int) -> PartyLoot | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM party_loot WHERE id = ? AND guild_id = ?",
                (loot_id, guild_id),
            ).fetchone()
            if row is None:
                return None
            connection.execute("DELETE FROM party_loot WHERE id = ? AND guild_id = ?", (loot_id, guild_id))
        return self._build_party_loot(row)

    def _build_npc(self, row: sqlite3.Row) -> NonPlayerCharacter:
        return NonPlayerCharacter(
            id=row["id"],
            guild_id=row["guild_id"],
            name=row["name"],
            description=row["description"],
            disposition=row["disposition"],
            notes=row["notes"],
        )

    def list_npcs(self, guild_id: int) -> list[NonPlayerCharacter]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM npcs WHERE guild_id = ? ORDER BY lower(name), id",
                (guild_id,),
            ).fetchall()
        return [self._build_npc(row) for row in rows]

    def get_npc(self, guild_id: int, npc_id: int) -> NonPlayerCharacter | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM npcs WHERE id = ? AND guild_id = ?",
                (npc_id, guild_id),
            ).fetchone()
        return self._build_npc(row) if row is not None else None

    def create_npc(
        self,
        guild_id: int,
        *,
        name: str,
        description: str = "",
        disposition: str = "",
        notes: str = "",
    ) -> NonPlayerCharacter:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO npcs (guild_id, name, description, disposition, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (guild_id, name.strip(), description.strip(), disposition.strip(), notes.strip()),
            )
            row = connection.execute("SELECT * FROM npcs WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._build_npc(row)

    def set_character_status(self, character_id: int, status: str) -> Character | None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE characters SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, character_id),
            )
        return self.get_character_by_id(character_id)

    def delete_character(self, character_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM active_characters WHERE character_id = ?", (character_id,))
            connection.execute("DELETE FROM characters WHERE id = ?", (character_id,))
