import unittest
from pathlib import Path

from morkbotted.character import Character
from morkbotted.storage import CharacterStore


class CharacterManagementTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = Path("data") / "character_management_test.db"
        self._remove_test_db()

    def tearDown(self) -> None:
        self._remove_test_db()

    def _remove_test_db(self) -> None:
        for path in (
            self.db_path,
            self.db_path.with_name(f"{self.db_path.name}-journal"),
            self.db_path.with_name(f"{self.db_path.name}-wal"),
            self.db_path.with_name(f"{self.db_path.name}-shm"),
        ):
            if path.exists():
                path.unlink()

    def test_delete_removes_character_dependents_and_active_selections(self) -> None:
        store = CharacterStore(self.db_path)
        character = store.upsert(
            Character(
                user_id=10,
                discord_name="Tester",
                name="Doomed",
                class_name="Classless",
                equipment=["Rusty knife"],
                notes=["Marked for deletion"],
            )
        )
        assert character.id is not None
        store.set_active_character(100, 10, character.id)
        store.set_active_character(200, 10, character.id)

        self.assertFalse(store.delete_character(character.id, user_id=99))
        self.assertIsNotNone(store.get_character_by_id(character.id))
        self.assertTrue(store.delete_character(character.id, user_id=10))
        self.assertIsNone(store.get_character_by_id(character.id))
        self.assertIsNone(store.get_active_character(100, 10))
        self.assertIsNone(store.get_active_character(200, 10))

    def test_switch_lookup_rejects_archived_character_selected_by_id(self) -> None:
        store = CharacterStore(self.db_path)
        character = store.upsert(
            Character(user_id=10, discord_name="Tester", name="Retired", class_name="Classless")
        )
        assert character.id is not None
        store.set_character_status(character.id, "archived")

        self.assertIsNone(store.find_character(10, str(character.id), include_archived=False))
        self.assertIsNotNone(store.find_character(10, str(character.id), include_archived=True))


if __name__ == "__main__":
    unittest.main()
