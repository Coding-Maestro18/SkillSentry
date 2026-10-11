import io
import stat
import zipfile

import pytest

from app.config import Settings
from app.ingest.archive_validator import IngestError, read_zip
from app.ingest.inventory import build_inventory


def make_zip(entries: dict[str, bytes], symlink: str | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            zf.writestr(info, "/etc/passwd")
    return buf.getvalue()


S = Settings()


@pytest.mark.parametrize("bad", ["../outside.txt", "skill/../../x", "/etc/passwd", "C:/win.txt", "a\\b.txt", "skill/./x"])
def test_rejects_unsafe_paths(bad):
    with pytest.raises(IngestError) as e:
        read_zip(make_zip({"skill/SKILL.md": b"x", bad: b"y"}), S)
    assert e.value.code == "INVALID_ARCHIVE"


def test_rejects_symlink():
    with pytest.raises(IngestError):
        read_zip(make_zip({"skill/SKILL.md": b"x"}, symlink="skill/link"), S)


def test_rejects_case_collision():
    with pytest.raises(IngestError) as e:
        read_zip(make_zip({"s/SKILL.md": b"x", "s/skill.md": b"y"}), S)
    assert "colliding" in e.value.message


def test_rejects_zip_bomb_by_streamed_size():
    small = Settings(max_extracted_bytes=1000)
    with pytest.raises(IngestError) as e:
        read_zip(make_zip({"s/SKILL.md": b"A" * 5000}), small)
    assert e.value.code == "EXTRACTED_TOO_LARGE"


def test_rejects_too_many_files():
    with pytest.raises(IngestError) as e:
        read_zip(make_zip({f"s/f{i}.md": b"x" for i in range(6)}), Settings(max_files=5))
    assert e.value.code == "TOO_MANY_FILES"


def test_rejects_non_zip():
    with pytest.raises(IngestError):
        read_zip(b"not a zip", S)


def test_strips_single_root_and_classifies():
    raw = read_zip(make_zip({
        "my-skill/SKILL.md": b"---\nname: a\ndescription: b\n---\n",
        "my-skill/references/guide.md": b"hi",
        "my-skill/references/data.bin": b"\x00\x01",
        "my-skill/scripts/run.sh": b"echo hi",
    }), S)
    inv = build_inventory(raw, S)
    by = {e.relative_path: e for e in inv.entries}
    assert by["SKILL.md"].scanned and by["references/guide.md"].scanned
    assert not by["scripts/run.sh"].scanned and "never executes" in by["scripts/run.sh"].skip_reason
    assert not by["references/data.bin"].scanned


def test_invalid_utf8_preserved_with_warning():
    raw = read_zip(make_zip({"s/SKILL.md": b"ok \xff\xfe bytes"}), S)
    inv = build_inventory(raw, S)
    assert inv.entries[0].warnings and "\ufffd" in inv.texts[0].text
