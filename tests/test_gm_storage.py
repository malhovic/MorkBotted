import unittest
import sqlite3
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

    def test_homebrew_classes_and_reusable_features_are_scoped_to_guild(self) -> None:
        store = CharacterStore(self.db_path)

        store.create_homebrew_class(
            100,
            name="Grave Botanist",
            description="Cultivates corpse flowers and worse ideas.",
            hp_formula="Toughness + d6",
            omen_die="d2",
        )
        feature = store.create_homebrew_feature(
            100,
            category="gift",
            name="Rootbound",
            description="You can speak with roots that fed on the dead.",
            roll_label="1",
        )
        updated = store.link_feature_to_class(100, str(feature.id), "Grave Botanist")
        store.create_homebrew_class(200, name="Ash Heretic", description="Carries sermons in a burnt mouth.")

        guild_100_classes = [class_template.name for class_template in store.list_classes(100)]
        guild_200_classes = [class_template.name for class_template in store.list_classes(200)]
        guild_100_feature_names = [item.name for item in store.list_homebrew_features(100)]
        guild_200_feature_names = [item.name for item in store.list_homebrew_features(200)]

        self.assertIn("Grave Botanist", guild_100_classes)
        self.assertNotIn("Grave Botanist", guild_200_classes)
        self.assertIn("Ash Heretic", guild_200_classes)
        self.assertNotIn("Ash Heretic", guild_100_classes)
        self.assertEqual(guild_100_feature_names, ["Rootbound"])
        self.assertEqual(guild_200_feature_names, [])
        self.assertEqual(updated.features[0].name, "Rootbound")
        self.assertIsNone(store.find_class("Grave Botanist", 200))
        self.assertEqual(store.find_class("Grave Botanist", 100).features[0].name, "Rootbound")

        reloaded_store = CharacterStore(self.db_path)
        self.assertEqual(reloaded_store.find_class("Grave Botanist", 100).features[0].name, "Rootbound")

    def test_server_feature_can_be_selected_on_character_creation(self) -> None:
        from morkbotted.creation import create_character_from_values

        store = CharacterStore(self.db_path)
        store.create_homebrew_class(100, name="Grave Botanist", description="Cultivates corpse flowers.")
        feature = store.create_homebrew_feature(
            100,
            category="gift",
            name="Rootbound",
            description="You can speak with roots that fed on the dead.",
        )
        store.link_feature_to_class(100, str(feature.id), "Grave Botanist")

        created = create_character_from_values(
            store,
            user_id=10,
            discord_name="A",
            name="Moss-Eater",
            class_name="Grave Botanist",
            background="",
            description="",
            agility="0",
            presence="0",
            strength="0",
            toughness="0",
            hp="1",
            max_hp="1",
            omens="0",
            silver="0",
            equipment="",
            notes="",
            class_feature="gift: Rootbound",
            guild_id=100,
        )

        self.assertEqual(created.class_name, "Grave Botanist")
        self.assertEqual(len(created.selected_class_feature_ids), 1)
        self.assertIn("Rootbound", "\n".join(created.sheet_lines()))

    def test_existing_global_class_schema_migrates_before_guild_indexes(self) -> None:
        self._remove_test_db()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        try:
            connection.executescript(
                """
                CREATE TABLE classes (
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

                CREATE TABLE class_features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    roll_label TEXT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
                );
                """
            )
            connection.commit()
        finally:
            connection.close()

        store = CharacterStore(self.db_path)
        created = store.create_homebrew_class(100, name="Grave Botanist", description="Cultivates corpse flowers.")

        self.assertIsNotNone(store.find_class("Classless"))
        self.assertEqual(created.guild_id, 100)
        self.assertIn("Grave Botanist", [item.name for item in store.list_classes(100)])


if __name__ == "__main__":
    unittest.main()
