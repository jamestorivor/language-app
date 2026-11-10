"""Reduce Linux NLP wheel sizes before Vercel packages the function.

Removing debug sections keeps exported symbols and parser behavior intact. Work
on a copy and replace the original: uv may have hard-linked it into its cache.
"""
from pathlib import Path
import base64
import csv
import hashlib
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile


PACKAGES = ("spacy", "thinc", "blis", "srsly", "preshed", "murmurhash", "cymem")


def main() -> None:
    if sys.platform != "linux":
        print("Skipping Linux shared-library stripping on this platform.")
        return
    strip = shutil.which("strip")
    if strip is None:
        raise SystemExit("GNU strip is required to reduce the Vercel function size")
    site_packages = Path(sysconfig.get_paths()["purelib"])
    libraries = [path for name in PACKAGES for path in (site_packages / name).rglob("*.so")]
    if not libraries:
        raise SystemExit("No NLP shared libraries were found in the build environment")
    before = after = 0
    changed: dict[str, tuple[str, str]] = {}
    for library in libraries:
        before += library.stat().st_size
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=library.parent, delete=False) as output:
                temporary = Path(output.name)
            subprocess.run([strip, "--strip-debug", "-o", str(temporary), str(library)], check=True)
            shutil.copymode(library, temporary)
            after += temporary.stat().st_size
            os.replace(temporary, library)
            with library.open("rb") as binary:
                digest = base64.urlsafe_b64encode(hashlib.file_digest(binary, "sha256").digest()).rstrip(b"=").decode("ascii")
            changed[library.relative_to(site_packages).as_posix()] = (f"sha256={digest}", str(library.stat().st_size))
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    # Vercel sizes installed distributions using RECORD, not a fresh stat.
    # Keep both sizes and hashes accurate after changing the binaries.
    recorded = set()
    for record in site_packages.glob("*.dist-info/RECORD"):
        with record.open(newline="", encoding="utf-8") as source:
            rows = list(csv.reader(source))
        modified = False
        for row in rows:
            if row and row[0] in changed:
                row[1], row[2] = changed[row[0]]
                recorded.add(row[0])
                modified = True
        if modified:
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", newline="", encoding="utf-8", dir=record.parent, delete=False) as output:
                    temporary = Path(output.name)
                    csv.writer(output, lineterminator="\n").writerows(rows)
                shutil.copymode(record, temporary)
                os.replace(temporary, record)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
    if missing := changed.keys() - recorded:
        raise SystemExit(f"Missing package RECORD entries for {len(missing)} stripped libraries")
    print(f"Removed {(before - after) / 1024**2:.1f} MiB of debug symbols from {len(libraries)} NLP libraries.")


if __name__ == "__main__":
    main()
