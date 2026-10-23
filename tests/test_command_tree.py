import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from discord import app_commands

from morkbotted.bot import build_bot


class CommandTreeTest(unittest.TestCase):
    def test_game_commands_are_namespaced_by_system(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "commands.db"
            with patch.dict(os.environ, {"DB_PATH": str(db_path)}):
                bot = build_bot()

        root_commands = {command.name: command for command in bot.tree.get_commands()}
        self.assertEqual(set(root_commands), {"ping", "helpmb", "mork", "arms"})

        mork = root_commands["mork"]
        arms = root_commands["arms"]
        self.assertIsInstance(mork, app_commands.Group)
        self.assertIsInstance(arms, app_commands.Group)

        mork_commands = {command.name: command for command in mork.commands}
        self.assertEqual(
            set(mork_commands),
            {
                "gm",
                "classes",
                "class-info",
                "roster",
                "switch",
                "archive",
                "delete",
                "scvmbirth",
                "sheet",
                "export",
                "roll",
                "create",
                "set-stat",
                "omens",
                "set-field",
                "improve",
                "add-item",
                "remove-item",
                "add-note",
                "notes",
                "edit-note",
                "remove-note",
                "getting-better",
            },
        )

        gm = mork_commands["gm"]
        self.assertIsInstance(gm, app_commands.Group)
        self.assertEqual(
            {command.name for command in gm.commands},
            {
                "characters",
                "party-loot",
                "loot-add",
                "loot-remove",
                "npcs",
                "npc",
                "npc-create",
                "classes",
                "class-create",
                "class-edit",
                "class-delete",
                "feature-create",
                "feature-edit",
                "feature-delete",
                "features",
                "feature-link",
            },
        )

        self.assertIn("enlist", {command.name for command in arms.commands})
        self.assertIn("info", {command.name for command in arms.commands})


if __name__ == "__main__":
    unittest.main()
