import unittest
from pathlib import Path

from morkbotted.creation import CharacterCreationError, create_character_from_values
from morkbotted.storage import CharacterStore


class ManualCharacterCreationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = Path("data") / "manual_creation_test.db"
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

    def test_manual_skinwalker_create_saves_and_renders_selected_beast_form(self) -> None:
        store = CharacterStore(self.db_path)

        created = create_character_from_values(
            store,
            user_id=98468186063663104,
            discord_name="malhovic",
            name="Skarn",
            class_name="Cursed Skinwalker",
            background="",
            description="Cruel. Deceitful. Forgotten by himself.",
            agility="1",
            presence="-1",
            strength="2",
            toughness="2",
            hp="9",
            max_hp="9",
            omens="2",
            silver="90",
            equipment="rusty knife, no armor",
            class_feature="beast form: Flayed and Dripping Wolf",
            notes="",
        )

        self.assertIsNotNone(created.id)

        reloaded = store.get_character_by_id(created.id)
        self.assertIsNotNone(reloaded)
        assert reloaded is not None

        sheet = "\n".join(reloaded.sheet_lines())
        export = reloaded.export_text()

        self.assertEqual(reloaded.class_name, "Cursed Skinwalker")
        self.assertIsNotNone(reloaded.class_template)
        self.assertIn("rusty knife", reloaded.equipment)
        self.assertEqual(reloaded.notes, [])
        self.assertEqual(len(reloaded.selected_class_feature_ids), 1)
        self.assertIn("Class Feature: [2] Flayed and Dripping Wolf", sheet)
        self.assertIn("- [2] Flayed and Dripping Wolf", export)
        self.assertNotIn("Class Feature: None recorded.", sheet)
        self.assertNotIn("Murder-Plagued Rat", sheet)
        self.assertNotIn("Murder-Plagued Rat", export)

    def test_manual_skinwalker_accepts_roll_number_for_class_feature_field(self) -> None:
        store = CharacterStore(self.db_path)

        created = create_character_from_values(
            store,
            user_id=98468186063663104,
            discord_name="malhovic",
            name="Skarn",
            class_name="Cursed Skinwalker",
            background="",
            description="Cruel. Deceitful. Forgotten by himself.",
            agility="1",
            presence="-1",
            strength="2",
            toughness="2",
            hp="9",
            max_hp="9",
            omens="2",
            silver="90",
            equipment="",
            class_feature="beast form: 2",
            notes="",
        )

        sheet = "\n".join(created.sheet_lines())

        self.assertIn("Class Feature: [2] Flayed and Dripping Wolf", sheet)

    def test_manual_skinwalker_create_without_feature_is_explicit(self) -> None:
        store = CharacterStore(self.db_path)

        created = create_character_from_values(
            store,
            user_id=98468186063663104,
            discord_name="malhovic",
            name="Skarn",
            class_name="Cursed Skinwalker",
            background="",
            description="Cruel. Deceitful. Forgotten by himself.",
            agility="1",
            presence="-1",
            strength="2",
            toughness="2",
            hp="9",
            max_hp="9",
            omens="2",
            silver="90",
            equipment="",
            class_feature="",
            notes="",
        )

        sheet = "\n".join(created.sheet_lines())
        export = created.export_text()

        self.assertIn("Class Feature: None recorded.", sheet)
        self.assertIn("- None recorded for this character.", export)
        self.assertNotIn("Flayed and Dripping Wolf", sheet)

    def test_invalid_manual_stat_names_the_bad_field(self) -> None:
        store = CharacterStore(self.db_path)

        with self.assertRaises(CharacterCreationError) as raised:
            create_character_from_values(
                store,
                user_id=98468186063663104,
                discord_name="malhovic",
                name="Skarn",
                class_name="Cursed Skinwalker",
                background="",
                description="Cruel. Deceitful. Forgotten by himself.",
                agility="raw 13",
                presence="-1",
                strength="2",
                toughness="2",
                hp="9",
                max_hp="9",
                omens="2",
                silver="90",
                equipment="",
                notes="",
            )

        self.assertEqual(raised.exception.field_name, "agility")
        self.assertIn("Ability modifiers look like", str(raised.exception))

    def test_invalid_manual_class_feature_lists_valid_options(self) -> None:
        store = CharacterStore(self.db_path)

        with self.assertRaises(CharacterCreationError) as raised:
            create_character_from_values(
                store,
                user_id=98468186063663104,
                discord_name="malhovic",
                name="Skarn",
                class_name="Cursed Skinwalker",
                background="",
                description="Cruel. Deceitful. Forgotten by himself.",
                agility="1",
                presence="-1",
                strength="2",
                toughness="2",
                hp="9",
                max_hp="9",
                omens="2",
                silver="90",
                equipment="",
                class_feature="wolf",
                notes="",
            )

        self.assertEqual(raised.exception.field_name, "class_feature")
        self.assertIn("beast form: Flayed and Dripping Wolf", str(raised.exception))

    def test_class_feature_requires_stored_class_match(self) -> None:
        store = CharacterStore(self.db_path)

        with self.assertRaises(CharacterCreationError) as raised:
            create_character_from_values(
                store,
                user_id=98468186063663104,
                discord_name="malhovic",
                name="Skarn",
                class_name="Cursed Skinwalkr",
                background="",
                description="Cruel. Deceitful. Forgotten by himself.",
                agility="1",
                presence="-1",
                strength="2",
                toughness="2",
                hp="9",
                max_hp="9",
                omens="2",
                silver="90",
                equipment="",
                class_feature="beast form: 2",
                notes="",
            )

        self.assertEqual(raised.exception.field_name, "class_name")
        self.assertIn("autocompleted stored classes", str(raised.exception))

    def test_manual_create_rejects_overlong_notes(self) -> None:
        store = CharacterStore(self.db_path)

        with self.assertRaises(CharacterCreationError) as raised:
            create_character_from_values(
                store,
                user_id=98468186063663104,
                discord_name="malhovic",
                name="Skarn",
                class_name="Cursed Skinwalker",
                background="",
                description="Cruel. Deceitful. Forgotten by himself.",
                agility="1",
                presence="-1",
                strength="2",
                toughness="2",
                hp="9",
                max_hp="9",
                omens="2",
                silver="90",
                equipment="",
                class_feature="",
                notes="x" * 501,
            )

        self.assertIn("500 characters or fewer", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
