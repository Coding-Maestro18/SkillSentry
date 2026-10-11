"""Rewrite invisible/format characters in source files as \\uXXXX escapes.

Keeps this repository's own source free of the hidden characters it detects.
Usage: python scripts/escape_invisibles_in_source.py [paths...]
"""

import pathlib
import sys
import unicodedata


def needs_escape(ch: str) -> bool:
    o = ord(ch)
    if o < 128:
        return False
    return (
        unicodedata.category(ch) in ("Cf", "Zs", "Zl", "Zp", "Co", "Cn")
        or 0xFE00 <= o <= 0xFE0F
        or 0xE0000 <= o <= 0xE01EF
        or o in (0x034F, 0x115F, 0x1160, 0x3164, 0xFFA0)
    )


def esc(ch: str) -> str:
    o = ord(ch)
    return f"\\u{o:04x}" if o <= 0xFFFF else f"\\U{o:08x}"


def main(paths: list[str]) -> int:
    changed = 0
    for root in paths or ["backend", "scripts", "tests"]:
        for p in pathlib.Path(root).rglob("*.py") if pathlib.Path(root).is_dir() else [pathlib.Path(root)]:
            src = p.read_text(encoding="utf-8")
            new = "".join(esc(c) if needs_escape(c) else c for c in src)
            if new != src:
                p.write_text(new, encoding="utf-8")
                changed += 1
                print(f"escaped invisibles in {p}")
    return 0 if changed >= 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
