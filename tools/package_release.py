#!/usr/bin/env python3
"""Assemble an untested candidate package without redistributing Valve assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build_dir = args.build_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "launcher/FourCornersLauncher.exe": build_dir / "FourCornersLauncher.exe",
        "tf/custom/holdout_fourcorners/maps/zf_fourcorners.bsp": build_dir / "zf_fourcorners.bsp",
    }
    for entry, source in files.items():
        if not source.is_file():
            raise SystemExit("Required built file is missing: " + str(source))

    readme = output_dir / "README.md"
    readme.write_text(
        "# Holdout: Four Corners — candidate build\n\n"
        "This is a private-test candidate, not a verified release. It adds one TF2 holdout map and a small launcher. "
        "The launcher reads the horde cue from the player's installed Left 4 Dead 2 copy at run time; no Valve game sound is included.\n\n"
        "Required games: Team Fortress 2 and Left 4 Dead 2.\n\n"
        "The launcher starts TF2 with `-insecure` for private/offline testing. Do not connect this client to VAC-secured servers.\n\n"
        "The four-player setup, joining, the map in a running game, and Melty's one-click install are not yet tested. This candidate must not be published until those checks are complete.\n",
        encoding="utf-8",
    )

    archive = output_dir / "holdout-four-corners-candidate.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for entry, source in files.items():
            package.write(source, entry)
        package.write(readme, "README.md")

    with zipfile.ZipFile(archive) as package:
        entries = package.namelist()
        if any(name.lower().endswith((".wav", ".mp3", ".vpk")) for name in entries):
            raise SystemExit("Unexpected Valve asset or game archive found in candidate package.")
        if set(entries) != set(files) | {"README.md"}:
            raise SystemExit("Candidate package contains missing or unexpected files.")

    manifest = {
        "status": "candidate; not runtime-tested or publishable",
        "archive": archive.name,
        "bytes": archive.stat().st_size,
        "sha256": sha256(archive),
        "entries": sorted(entries),
        "redistributedValveGameAssets": False,
    }
    (output_dir / "package-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
