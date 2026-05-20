import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_frontmatter.py"
SPEC = importlib.util.spec_from_file_location("writeup_validate_frontmatter", MODULE_PATH)
validate_frontmatter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validate_frontmatter)


def writeup_content(author: str) -> str:
    return "\n".join([
        "---",
        "ctf_name: Test CTF",
        "challenge_name: Test Challenge",
        "category: web",
        "difficulty: easy",
        f"author: {author}",
        "date: 2026-05-20",
        "---",
        "body",
        "",
    ])


class GitNicknameValidationTests(unittest.TestCase):
    def test_matching_git_nickname_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "writeups" / "TestCTF" / "web" / "challenge" / "alice.md"
            path.parent.mkdir(parents=True)
            path.write_text(writeup_content("alice"), encoding="utf-8")

            errors = validate_frontmatter.validate_file(path, git_nickname="alice")

        self.assertEqual(errors, [])

    def test_mismatched_git_nickname_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "writeups" / "TestCTF" / "web" / "challenge" / "alice.md"
            path.parent.mkdir(parents=True)
            path.write_text(writeup_content("alice"), encoding="utf-8")

            errors = validate_frontmatter.validate_file(path, git_nickname="bob")

        self.assertTrue(
            any("git nickname 'bob'과 author 필드 'alice'가 불일치" in error for error in errors)
        )

    def test_git_nickname_check_is_skipped_when_not_provided(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "writeups" / "TestCTF" / "web" / "challenge" / "alice.md"
            path.parent.mkdir(parents=True)
            path.write_text(writeup_content("alice"), encoding="utf-8")

            errors = validate_frontmatter.validate_file(path)

        self.assertEqual(errors, [])

    def test_get_git_nickname_prefers_env(self) -> None:
        with patch.dict("os.environ", {"WRITEUP_GIT_NICKNAME": "alice"}, clear=True):
            self.assertEqual(validate_frontmatter.get_git_nickname(), "alice")


if __name__ == "__main__":
    unittest.main()
