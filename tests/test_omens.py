import random
import unittest

from morkbotted.character import Character, ClassFeature, ClassTemplate
from morkbotted.omens import daily_omen_formula, omen_status_text, parse_omen_formula, roll_daily_omens


class OmenRulesTest(unittest.TestCase):
    def test_parse_omen_formula(self) -> None:
        parsed = parse_omen_formula("d3")

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.sides, 3)
        self.assertEqual(parsed.modifier, 0)
        self.assertEqual(parsed.label, "d3")

    def test_parse_omen_formula_with_modifier(self) -> None:
        parsed = parse_omen_formula("d4+2")

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.sides, 4)
        self.assertEqual(parsed.modifier, 2)
        self.assertEqual(parsed.label, "d4+2")

    def test_character_uses_class_omen_die(self) -> None:
        character = Character(
            user_id=1,
            discord_name="Player",
            name="Skarn",
            class_name="Cursed Skinwalker",
            omens=2,
            class_template=ClassTemplate(
                slug="cursed-skinwalker",
                name="Cursed Skinwalker",
                source="MBC_Cursed-Skinwalker",
                description="A cursed shapeshifter.",
                omen_die="d2",
            ),
        )

        formula = daily_omen_formula(character)

        self.assertIsNotNone(formula)
        assert formula is not None
        self.assertEqual(formula.label, "d2")
        self.assertIn("Daily omens: `d2`", omen_status_text(character))

    def test_selected_feature_can_override_omen_formula(self) -> None:
        character = Character(
            user_id=1,
            discord_name="Player",
            name="Star-Ruined",
            class_name="Pale One",
            selected_class_feature_ids=[1],
            class_template=ClassTemplate(
                slug="pale-one",
                name="Pale One",
                source="MBC_Pale-one",
                description="A star-touched scvm.",
                omen_die="d4",
                features=[
                    ClassFeature(
                        id=1,
                        category="blessing",
                        roll_label="1",
                        name="The Stars Were Right",
                        description="Roll d4+2 for Omens and say something cryptic every time you spend one.",
                    )
                ],
            ),
        )

        formula = daily_omen_formula(character)

        self.assertIsNotNone(formula)
        assert formula is not None
        self.assertEqual(formula.label, "d4+2")

    def test_roll_daily_omens_uses_formula(self) -> None:
        character = Character(
            user_id=1,
            discord_name="Player",
            name="Skarn",
            class_name="Cursed Skinwalker",
            class_template=ClassTemplate(
                slug="cursed-skinwalker",
                name="Cursed Skinwalker",
                source="MBC_Cursed-Skinwalker",
                description="A cursed shapeshifter.",
                omen_die="d2",
            ),
        )

        rolled = roll_daily_omens(character, random.Random(1))

        self.assertIn(rolled, {1, 2})


if __name__ == "__main__":
    unittest.main()
