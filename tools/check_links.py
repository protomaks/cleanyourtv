#!/usr/bin/env python3
"""Every relative link in the Markdown files points at something that exists.

    check_links.py               check every Markdown file git tracks
    check_links.py FILE.md ...   check only these

Covers Markdown links and images, reference definitions, and href/src in inline HTML. A link with a
#fragment into a Markdown file must name one of its headings (as GitHub slugs them) or an id/name
attribute. External URLs are not fetched: CI should not fail because a news site is down.

Exits 1 and prints file:line for each broken link, 0 when there are none.
"""
from pathlib import Path
import re
import subprocess
import sys
import unicodedata
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

FENCE_RE = re.compile(r"^(```|~~~).*?^\1", re.M | re.S)
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
LINK_RES = (
    re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)"),
    re.compile(r"\b(?:href|src)=\"([^\"]+)\""),
    re.compile(r"^\s*\[[^\]]+\]:\s*<?(\S+?)>?(?:\s|$)", re.M),
)
SKIP_SCHEMES = ("http://", "https://", "mailto:", "tel:", "data:")


def blank(match):
    # Keep the newlines so line numbers still line up after code is cut out.
    return re.sub(r"[^\n]", " ", match.group(0))


def strip_code(text):
    return CODE_SPAN_RE.sub(blank, FENCE_RE.sub(blank, text))


def slug(heading):
    """The anchor GitHub gives a heading."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    text = "".join(c for c in text
                   if c in " -_" or c.isalnum() or unicodedata.category(c).startswith(("L", "M")))
    return text.replace(" ", "-")


def anchors(path, cache={}):
    if path not in cache:
        found, seen = set(), {}
        text = strip_code(path.read_text(encoding="utf-8"))
        for heading in re.findall(r"^#{1,6}\s+(.*?)\s*#*\s*$", text, re.M):
            s = slug(heading)
            n = seen.get(s, 0)
            seen[s] = n + 1
            found.add(s if n == 0 else f"{s}-{n}")
        found.update(re.findall(r"\b(?:id|name)=\"([^\"]+)\"", text))
        cache[path] = found
    return cache[path]


def problems(path):
    text = strip_code(path.read_text(encoding="utf-8"))
    for pattern in LINK_RES:
        for match in pattern.finditer(text):
            url = match.group(1)
            if url.lower().startswith(SKIP_SCHEMES):
                continue
            line = text.count("\n", 0, match.start(1)) + 1
            target, _, fragment = url.partition("#")
            target = unquote(target.split("?")[0])
            dest = (ROOT / target.lstrip("/")) if target.startswith("/") else (path.parent / target)
            dest = dest.resolve() if target else path
            if not dest.exists():
                yield line, url, "no such file"
            elif fragment and dest.suffix == ".md" and unquote(fragment).lower() not in anchors(dest):
                yield line, url, "no such heading"


def main(args):
    if args:
        files = [Path(a).resolve() for a in args]
    else:
        listed = subprocess.run(["git", "ls-files", "-z", "*.md"], cwd=ROOT, check=True,
                                capture_output=True, text=True).stdout
        files = [ROOT / name for name in listed.split("\0") if name]
    broken = 0
    for path in files:
        for line, url, why in problems(path):
            shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
            print(f"{shown}:{line}: {url} ({why})")
            broken += 1
    if broken:
        print(f"{broken} broken link(s) in {len(files)} file(s)", file=sys.stderr)
        return 1
    print(f"links ok in {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
