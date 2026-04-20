import unittest

from morkbotted.character import Character, ClassFeature, ClassTemplate


class CharacterRenderingTest(unittest.TestCase):
    def test_character_sheet_only_shows_selected_skinwalker_feature(self) -> None:
        class_template = ClassTemplate(
            slug="cursed-skinwalker",
            name="Cursed Skinwalker",
            source="MBC_Cursed-Skinwalker",
            description="A twice-dead soul fused with a dying beast.",
            features=[
                ClassFeature(
                    id=1,
                    category="beast_form",
                    roll_label="1",
                    name="Murder-Plagued Rat",
                    description="Agility tests and defence are DR8.",
                ),
                ClassFeature(
                    id=2,
                    category="beast_form",
                    roll_label="2",
                    name="Flayed and Dripping Wolf",
                    description="Attacks are DR10 and fangs deal d6.",
                ),
                ClassFeature(
                    id=3,
                    category="beast_form",
                    roll_label="3",
                    name="Boneskulled Raven",
                    description="Defence is DR10 and you fly.",
                ),
            ],
        )
        character = Character(
            user_id=1,
            discord_name="Player",
            name="Wolf-Thing",
            class_id=1,
            class_name="Cursed Skinwalker",
            notes=["Owes the butcher a favor."],
            selected_class_feature_ids=[2],
            class_template=class_template,
        )

        short_sheet = "\n".join(character.sheet_lines())
        export = character.export_text()

        self.assertIn("Flayed and Dripping Wolf", short_sheet)
        self.assertIn("Flayed and Dripping Wolf", export)
        self.assertIn("Class Feature: [2] Flayed and Dripping Wolf", short_sheet)
        self.assertIn("\nClass Features\n", export)
        self.assertNotIn("Murder-Plagued Rat", short_sheet)
        self.assertNotIn("Murder-Plagued Rat", export)
        self.assertNotIn("Boneskulled Raven", short_sheet)
        self.assertNotIn("Boneskulled Raven", export)

    def test_character_sheet_renders_selected_feature_id(self) -> None:
        class_template = ClassTemplate(
            slug="cursed-skinwalker",
            name="Cursed Skinwalker",
            source="MBC_Cursed-Skinwalker",
            description="A twice-dead soul fused with a dying beast.",
            features=[
                ClassFeature(
                    id=1,
                    category="beast_form",
                    roll_label="1",
                    name="Murder-Plagued Rat",
                    description="Agility tests and defence are DR8.",
                ),
                ClassFeature(
                    id=2,
                    category="beast_form",
                    roll_label="2",
                    name="Flayed and Dripping Wolf",
                    description="Attacks are DR10 and fangs deal d6.",
                ),
            ],
        )
        character = Character(
            user_id=1,
            discord_name="Player",
            name="Wolf-Thing",
            class_id=1,
            class_name="Cursed Skinwalker",
            selected_class_feature_ids=[2],
            class_template=class_template,
        )

        short_sheet = "\n".join(character.sheet_lines())
        export = character.export_text()

        self.assertIn("Flayed and Dripping Wolf", short_sheet)
        self.assertIn("Flayed and Dripping Wolf", export)
        self.assertNotIn("Murder-Plagued Rat", short_sheet)
        self.assertNotIn("Murder-Plagued Rat", export)

    def test_character_sheet_marks_missing_class_feature_selection(self) -> None:
        class_template = ClassTemplate(
            slug="cursed-skinwalker",
            name="Cursed Skinwalker",
            source="MBC_Cursed-Skinwalker",
            description="A twice-dead soul fused with a dying beast.",
            features=[
                ClassFeature(
                    id=2,
                    category="beast_form",
                    roll_label="2",
                    name="Flayed and Dripping Wolf",
                    description="Attacks are DR10 and fangs deal d6.",
                ),
            ],
        )
        character = Character(
            user_id=1,
            discord_name="Player",
            name="Wolf-Thing",
            class_id=1,
            class_name="Cursed Skinwalker",
            class_template=class_template,
        )

        short_sheet = "\n".join(character.sheet_lines())
        export = character.export_text()

        self.assertIn("Class Feature: None recorded.", short_sheet)
        self.assertIn("- None recorded for this character.", export)
        self.assertNotIn("Flayed and Dripping Wolf", short_sheet)
        self.assertNotIn("Flayed and Dripping Wolf", export)

    def test_notes_do_not_select_class_features(self) -> None:
        class_template = ClassTemplate(
            slug="cursed-skinwalker",
            name="Cursed Skinwalker",
            source="MBC_Cursed-Skinwalker",
            description="A twice-dead soul fused with a dying beast.",
            features=[
                ClassFeature(
                    id=2,
                    category="beast_form",
                    roll_label="2",
                    name="Flayed and Dripping Wolf",
                    description="Attacks are DR10 and fangs deal d6.",
                ),
            ],
        )
        character = Character(
            user_id=1,
            discord_name="Player",
            name="Wolf-Thing",
            class_id=1,
            class_name="Cursed Skinwalker",
            notes=["Remember: Flayed and Dripping Wolf owes the butcher a favor."],
            class_template=class_template,
        )

        short_sheet = "\n".join(character.sheet_lines())

        self.assertIn("Notes: Remember: Flayed and Dripping Wolf owes the butcher a favor.", short_sheet)
        self.assertIn("Class Feature: None recorded.", short_sheet)


if __name__ == "__main__":
    unittest.main()
