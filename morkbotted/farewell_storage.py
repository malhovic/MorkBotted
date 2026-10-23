from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from morkbotted.farewell import FarewellCharacter


class FarewellCharacterStore:
    """Separate Farewell to Arms roster stored alongside the main bot database."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS farewell_characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    discord_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    class_name TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS farewell_active_characters (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    character_id INTEGER NOT NULL,
                    PRIMARY KEY (guild_id, user_id),
                    FOREIGN KEY (character_id) REFERENCES farewell_characters(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_farewell_owner ON farewell_characters(user_id, id);
                """
            )

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

    @staticmethod
    def _from_row(row: sqlite3.Row) -> FarewellCharacter:
        payload = json.loads(row["payload"])
        payload["id"] = row["id"]
        return FarewellCharacter.from_payload(payload)

    def save(self, character: FarewellCharacter) -> FarewellCharacter:
        payload = character.to_payload()
        payload.pop("id", None)
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO farewell_characters (user_id, discord_name, name, class_name, payload) VALUES (?, ?, ?, ?, ?)",
                (character.user_id, character.discord_name, character.name, character.class_name, json.dumps(payload)),
            )
            character.id = cursor.lastrowid
        return character

    def update(self, character: FarewellCharacter) -> FarewellCharacter:
        if character.id is None:
            raise ValueError("This Farewell to Arms character has not been saved yet.")
        existing = self.get(character.id, character.user_id)
        if existing is None:
            raise ValueError("That Farewell to Arms character does not belong to this user.")
        payload = character.to_payload()
        payload.pop("id", None)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE farewell_characters
                SET discord_name = ?, name = ?, class_name = ?, payload = ?
                WHERE id = ? AND user_id = ?
                """,
                (
                    character.discord_name,
                    character.name,
                    character.class_name,
                    json.dumps(payload),
                    character.id,
                    character.user_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError("The Farewell to Arms character could not be updated.")
        return character

    def list(self, user_id: int) -> list[FarewellCharacter]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM farewell_characters WHERE user_id = ? ORDER BY id", (user_id,)
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, character_id: int, user_id: int | None = None) -> FarewellCharacter | None:
        query = "SELECT * FROM farewell_characters WHERE id = ?"
        parameters: tuple[int, ...] = (character_id,)
        if user_id is not None:
            query += " AND user_id = ?"
            parameters = (character_id, user_id)
        with self._connect() as connection:
            row = connection.execute(query, parameters).fetchone()
        return self._from_row(row) if row else None

    def find(self, user_id: int, name_or_id: str) -> FarewellCharacter | None:
        normalized = name_or_id.strip()
        if not normalized:
            return None
        if normalized.isdigit():
            return self.get(int(normalized), user_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM farewell_characters
                WHERE user_id = ? AND lower(name) = lower(?)
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, normalized),
            ).fetchone()
        return self._from_row(row) if row else None

    def set_active(self, guild_id: int, user_id: int, character_id: int) -> None:
        character = self.get(character_id, user_id)
        if character is None:
            raise ValueError("That Farewell to Arms character does not belong to this user.")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO farewell_active_characters (guild_id, user_id, character_id) VALUES (?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET character_id = excluded.character_id
                """,
                (guild_id, user_id, character_id),
            )

    def get_active(self, guild_id: int | None, user_id: int) -> FarewellCharacter | None:
        if guild_id is not None:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT c.* FROM farewell_characters c
                    JOIN farewell_active_characters a ON a.character_id = c.id
                    WHERE a.guild_id = ? AND a.user_id = ?
                    """,
                    (guild_id, user_id),
                ).fetchone()
            if row:
                return self._from_row(row)
        characters = self.list(user_id)
        return characters[-1] if characters else None

    def delete(self, character_id: int, user_id: int) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM farewell_characters WHERE id = ? AND user_id = ?", (character_id, user_id)
            ).fetchone()
            if row is None:
                return False
            connection.execute(
                "DELETE FROM farewell_active_characters WHERE character_id = ?", (character_id,)
            )
            cursor = connection.execute(
                "DELETE FROM farewell_characters WHERE id = ? AND user_id = ?", (character_id, user_id)
            )
        return cursor.rowcount > 0
