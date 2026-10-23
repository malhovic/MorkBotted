import random
import unittest
from pathlib import Path

from morkbotted.farewell import (
    CLASSES,
    add_farewell_gear,
    find_farewell_class,
    generate_farewell_character,
    remove_farewell_gear,
    update_farewell_field,
)
from morkbotted.farewell_storage import FarewellCharacterStore


class FarewellCharacterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = Path("data") / "farewell_test.db"
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

    def test_every_class_generates_a_complete_rules_legal_grvnt(self) -> None:
        random.seed(1918)
        self.assertEqual(len(CLASSES), 12)

        for class_template in CLASSES:
            character = generate_farewell_character(
                user_id=123,
                discord_name="Tester",
                class_template=class_template,
            )
            self.assertEqual(character.class_slug, class_template.slug)
            self.assertGreaterEqual(character.hp, 1)
            self.assertEqual(character.hp, character.max_hp)
            self.assertGreaterEqual(character.omens, 1)
            self.assertLessEqual(character.omens, class_template.omens_die)
            self.assertIn(character.shock, (1, 2))
            self.assertGreaterEqual(character.powers, 0)
            self.assertTrue(character.name)
            self.assertTrue(character.reason)
            self.assertTrue(character.battle_scar)
            self.assertTrue(character.vice)
            self.assertTrue(character.gear)
            for stat in (character.agility, character.presence, character.strength, character.toughness):
                self.assertGreaterEqual(stat, -3)
                self.assertLessEqual(stat, 3)

    def test_class_specific_generation_rules_are_kept_separate(self) -> None:
        random.seed(7)
        embedded = generate_farewell_character(
            user_id=1, discord_name="Tester", class_template=find_farewell_class("Embedded One")
        )
        engineer = generate_farewell_character(
            user_id=1, discord_name="Tester", class_template=find_farewell_class("new-world-engineer")
        )
        homesick = generate_farewell_character(
            user_id=1, discord_name="Tester", class_template=find_farewell_class("Homesick Rifleman")
        )

        self.assertEqual(embedded.silver, 0)
        self.assertEqual(embedded.ammo, 0)
        self.assertEqual(embedded.firearm, "None")
        self.assertEqual(engineer.specialty.count(" | "), 1)
        self.assertTrue(any("Muskoxen" in item for item in engineer.gear))
        self.assertTrue(any(item.startswith(("d4 Letters", "Stop Watch", "Purple Heart", "Lovesick")) for item in homesick.gear))

    def test_farewell_roster_and_active_selection_persist(self) -> None:
        store = FarewellCharacterStore(self.db_path)
        first = store.save(generate_farewell_character(
            user_id=44, discord_name="Tester", class_template=CLASSES[0], name="Roach"
        ))
        second = store.save(generate_farewell_character(
            user_id=44, discord_name="Tester", class_template=CLASSES[1], name="Rat"
        ))
        store.save(generate_farewell_character(
            user_id=55, discord_name="Someone Else", class_template=CLASSES[2], name="Grit"
        ))

        self.assertEqual([item.name for item in store.list(44)], ["Roach", "Rat"])
        self.assertEqual(store.find(44, "Roach").id, first.id)
        self.assertEqual(store.find(44, str(second.id)).name, "Rat")
        self.assertIsNone(store.find(55, "Roach"))
        store.set_active(999, 44, first.id)
        self.assertEqual(store.get_active(999, 44).name, "Roach")
        store.set_active(999, 44, second.id)
        self.assertEqual(store.get_active(999, 44).name, "Rat")
        self.assertEqual(store.get_active(None, 44).name, "Rat")

    def test_farewell_sheet_escapes_user_controlled_name(self) -> None:
        character = generate_farewell_character(
            user_id=1, discord_name="Tester", class_template=CLASSES[0], name="**@everyone**"
        )
        self.assertIn(r"\*\*@everyone\*\*", "\n".join(character.sheet_lines()))

    def test_farewell_character_fields_and_gear_can_be_managed(self) -> None:
        store = FarewellCharacterStore(self.db_path)
        character = store.save(generate_farewell_character(
            user_id=44, discord_name="Tester", class_template=CLASSES[0], name="Roach"
        ))

        update_farewell_field(character, "HP", "-1")
        update_farewell_field(character, "shock", "8")
        update_farewell_field(character, "name", "Last Legs")
        added = add_farewell_gear(character, "Stolen helmet")
        store.update(character)

        reloaded = store.get(character.id, 44)
        self.assertEqual(reloaded.name, "Last Legs")
        self.assertEqual(reloaded.hp, -1)
        self.assertEqual(reloaded.shock, 8)
        self.assertIn(added, reloaded.gear)

        item_number = reloaded.gear.index(added) + 1
        self.assertEqual(remove_farewell_gear(reloaded, item_number), added)
        store.update(reloaded)
        self.assertNotIn(added, store.get(character.id, 44).gear)

    def test_farewell_delete_is_owner_scoped_and_clears_active_selection(self) -> None:
        store = FarewellCharacterStore(self.db_path)
        character = store.save(generate_farewell_character(
            user_id=44, discord_name="Tester", class_template=CLASSES[0], name="Roach"
        ))
        store.set_active(999, 44, character.id)

        self.assertFalse(store.delete(character.id, 55))
        self.assertIsNotNone(store.get(character.id, 44))
        self.assertTrue(store.delete(character.id, 44))
        self.assertIsNone(store.get(character.id, 44))
        self.assertIsNone(store.get_active(999, 44))

    def test_farewell_field_validation_rejects_invalid_values(self) -> None:
        character = generate_farewell_character(
            user_id=1, discord_name="Tester", class_template=CLASSES[0]
        )
        with self.assertRaisesRegex(ValueError, "between -3 and 6"):
            update_farewell_field(character, "agility", "20")
        with self.assertRaisesRegex(ValueError, "whole number"):
            update_farewell_field(character, "ammo", "lots")
        with self.assertRaisesRegex(ValueError, "Unknown field"):
            update_farewell_field(character, "class_name", "Cheater")


if __name__ == "__main__":
    unittest.main()
