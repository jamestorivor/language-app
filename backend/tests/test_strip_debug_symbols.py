import base64
import csv
import hashlib
import os

from scripts import strip_debug_symbols


def test_strip_updates_record_without_mutating_hardlinked_cache(tmp_path, monkeypatch):
    site = tmp_path / "site-packages"
    package = site / "spacy"
    package.mkdir(parents=True)
    cached = tmp_path / "cached.so"
    cached.write_bytes(b"original binary with debug information")
    library = package / "example.so"
    os.link(cached, library)
    record = site / "spacy-1.dist-info" / "RECORD"
    record.parent.mkdir()
    record.write_text("spacy/example.so,sha256=old,38\n", encoding="utf-8")

    def fake_strip(command, check):
        assert check
        with open(command[3], "wb") as result:
            result.write(b"stripped binary")

    monkeypatch.setattr(strip_debug_symbols.sys, "platform", "linux")
    monkeypatch.setattr(strip_debug_symbols.sysconfig, "get_paths", lambda: {"purelib": str(site)})
    monkeypatch.setattr(strip_debug_symbols.shutil, "which", lambda name: "/usr/bin/strip")
    monkeypatch.setattr(strip_debug_symbols.subprocess, "run", fake_strip)
    strip_debug_symbols.main()

    assert cached.read_bytes() == b"original binary with debug information"
    assert library.read_bytes() == b"stripped binary"
    with record.open(newline="", encoding="utf-8") as file:
        row = next(csv.reader(file))
    digest = base64.urlsafe_b64encode(hashlib.sha256(b"stripped binary").digest()).rstrip(b"=").decode()
    assert row == ["spacy/example.so", f"sha256={digest}", str(len(b"stripped binary"))]
