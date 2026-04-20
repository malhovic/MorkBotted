import unittest

from morkbotted.character import Character, ClassFeature, ClassTemplate


class CharacterRenderingTest(unittest.TestCase):
    def test_character_sheet_only_shows_selected_skinwalker_feature_note(self) -> None:
        class_template = ClassTemplate(
            slug="cursed-skinwalker",
            name="Cursed Skinwalker",
            source="MBC_Cursed-Skinwalker",
            description="A twice-dead soul fused with a dying beast.",
            features=[
                ClassFeature(
                    category="beast_form",
                    roll_label="1",
                    name="Murder-Plagued Rat",
                    description="Agility tests and defence are DR8.",
                ),
                ClassFeature(
                    category="beast_form",
                    roll_label="2",
                    name="Flayed and Dripping Wolf",
                    description="Attacks are DR10 and fangs deal d6.",
                ),
                ClassFeature(
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
            notes=["Flayed and Dripping Wolf: Attacks are DR10 and fangs deal d6."],
            class_template=class_template,
        )

        short_sheet = "\n".join(character.sheet_lines())
        export = character.export_text()

        self.assertIn("Flayed and Dripping Wolf", short_sheet)
        self.assertIn("Flayed and Dripping Wolf", export)
        self.assertNotIn("Murder-Plagued Rat", short_sheet)
        self.assertNotIn("Murder-Plagued Rat", export)
        self.assertNotIn("Boneskulled Raven", short_sheet)
        self.assertNotIn("Boneskulled Raven", export)
        self.assertNotIn("Class Features:", short_sheet)
        self.assertNotIn("\nClass Features\n", export)


if __name__ == "__main__":
    unittest.main()
