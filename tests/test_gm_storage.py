import unittest
from pathlib import Path

from morkbotted.character import Character
from morkbotted.storage import CharacterStore


class GMStorageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = Path("data") / "gm_storage_test.db"
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

    def test_gm_active_character_list_is_scoped_to_guild(self) -> None:
        store = CharacterStore(self.db_path)
        first = store.upsert(Character(user_id=10, discord_name="A", name="Skarn", class_name="Classless"))
        second = store.upsert(Character(user_id=20, discord_name="B", name="Vorga", class_name="Classless"))
        assert first.id is not None
        assert second.id is not None

        store.set_active_character(100, first.user_id, first.id)
        store.set_active_character(200, second.user_id, second.id)

        guild_100_names = [character.name for character in store.list_active_characters_for_guild(100)]
        guild_200_names = [character.name for character in store.list_active_characters_for_guild(200)]

        self.assertEqual(guild_100_names, ["Skarn"])
        self.assertEqual(guild_200_names, ["Vorga"])

    def test_party_loot_is_scoped_to_guild(self) -> None:
        store = CharacterStore(self.db_path)

        first = store.add_party_loot(100, "Silver reliquary", quantity=2, notes="Cursed")
        store.add_party_loot(200, "Black salt")

        guild_100_loot = store.list_party_loot(100)
        guild_200_loot = store.list_party_loot(200)

        self.assertEqual([item.item_text for item in guild_100_loot], ["Silver reliquary"])
        self.assertEqual(guild_100_loot[0].quantity, 2)
        self.assertEqual(guild_100_loot[0].notes, "Cursed")
        self.assertEqual([item.item_text for item in guild_200_loot], ["Black salt"])
        self.assertIsNone(store.remove_party_loot(200, first.id))
        self.assertIsNotNone(store.remove_party_loot(100, first.id))

    def test_npcs_are_scoped_to_guild(self) -> None:
        store = CharacterStore(self.db_path)

        npc = store.create_npc(
            100,
            name="Mother Marrow",
            description="Sells saints' teeth.",
            disposition="Wary",
            notes="Knows where the reliquary was buried.",
        )
        store.create_npc(200, name="The Bellman")

        self.assertEqual([item.name for item in store.list_npcs(100)], ["Mother Marrow"])
        self.assertEqual([item.name for item in store.list_npcs(200)], ["The Bellman"])
        self.assertIsNone(store.get_npc(200, npc.id))
        self.assertEqual(store.get_npc(100, npc.id).notes, "Knows where the reliquary was buried.")


if __name__ == "__main__":
    unittest.main()
