from __future__ import annotations

import json
from pathlib import Path

from morkbotted.character import Character


class CharacterStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "characters.json"
        if not self.file_path.exists():
            self.file_path.write_text("{}", encoding="utf-8")

    def _read(self) -> dict[str, dict]:
        return json.loads(self.file_path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, dict]) -> None:
        self.file_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def get(self, user_id: int) -> Character | None:
        payload = self._read()
        character = payload.get(str(user_id))
        if character is None:
            return None
        return Character.from_dict(character)

    def upsert(self, character: Character) -> Character:
        payload = self._read()
        payload[str(character.user_id)] = character.to_dict()
        self._write(payload)
        return character

    def delete(self, user_id: int) -> None:
        payload = self._read()
        payload.pop(str(user_id), None)
        self._write(payload)
