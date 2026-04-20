import unittest
from types import SimpleNamespace

from morkbotted.security import member_has_gm_access


class GmAccessTest(unittest.TestCase):
    def test_manage_server_permission_grants_gm_access(self) -> None:
        member = SimpleNamespace(
            guild_permissions=SimpleNamespace(manage_guild=True),
            roles=[],
        )

        self.assertTrue(member_has_gm_access(member, "scvm-gm"))

    def test_configured_gm_role_grants_gm_access_case_insensitively(self) -> None:
        member = SimpleNamespace(
            guild_permissions=SimpleNamespace(manage_guild=False),
            roles=[SimpleNamespace(name="SCVM-GM")],
        )

        self.assertTrue(member_has_gm_access(member, "scvm-gm"))

    def test_without_role_or_manage_server_gm_access_is_denied(self) -> None:
        member = SimpleNamespace(
            guild_permissions=SimpleNamespace(manage_guild=False),
            roles=[SimpleNamespace(name="player")],
        )

        self.assertFalse(member_has_gm_access(member, "scvm-gm"))

    def test_blank_role_name_requires_manage_server(self) -> None:
        member = SimpleNamespace(
            guild_permissions=SimpleNamespace(manage_guild=False),
            roles=[SimpleNamespace(name="scvm-gm")],
        )

        self.assertFalse(member_has_gm_access(member, None))


if __name__ == "__main__":
    unittest.main()
