"""tools/check_links.py finds broken relative links and headings, and leaves good ones alone.

Run from the repository root: python3 -m unittest discover -s tests -v
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "check_links.py"


def check(*files):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *map(str, files)],
                          capture_output=True, text=True, timeout=60)


class CheckLinksTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "other.md").write_text("# Other\n\n## Doing it by hand\n\n## Café_notes\n")
        (self.dir / "pic.png").write_bytes(b"")

    def write(self, text):
        page = self.dir / "page.md"
        page.write_text(text)
        return page

    def test_good_links(self):
        page = self.write(
            "# Top\n\n[a](other.md) [b](other.md#doing-it-by-hand) [c](other.md#café_notes)\n"
            '![p](pic.png) <img src="pic.png"> [self](#top) [web](https://example.com/nope)\n'
            "[ref]: other.md\n")
        result = check(page)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_missing_file_and_heading(self):
        page = self.write("# Top\n\n[a](gone.md)\n\n[b](other.md#no-such-part)\n")
        result = check(page)
        self.assertEqual(result.returncode, 1)
        self.assertIn("page.md:3: gone.md (no such file)", result.stdout)
        self.assertIn("page.md:5: other.md#no-such-part (no such heading)", result.stdout)

    def test_code_is_ignored(self):
        page = self.write("`[a](gone.md)`\n\n```\n[b](gone.md)\n```\n")
        self.assertEqual(check(page).returncode, 0)

    def test_repository_links(self):
        result = check()
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
