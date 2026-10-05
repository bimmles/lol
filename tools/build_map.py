#!/usr/bin/env python3
"""Generate the map VMF from JSON sheets; optionally compile it with TF2 tools."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEETS = ROOT / "sheets"


def kv(value) -> str:
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def plane(a, b, c) -> str:
    # Hammer VMF winding points toward the brush interior for these faces.
    return f'({c[0]} {c[1]} {c[2]}) ({b[0]} {b[1]} {b[2]}) ({a[0]} {a[1]} {a[2]})'


def brush_faces(mins, maxs):
    x0, y0, z0 = mins
    x1, y1, z1 = maxs
    return [
        plane((x0,y0,z0),(x0,y0,z1),(x0,y1,z1)),
        plane((x1,y0,z0),(x1,y1,z0),(x1,y1,z1)),
        plane((x0,y0,z0),(x1,y0,z0),(x1,y0,z1)),
        plane((x0,y1,z0),(x0,y1,z1),(x1,y1,z1)),
        plane((x0,y0,z0),(x0,y1,z0),(x1,y1,z0)),
        plane((x0,y0,z1),(x1,y0,z1),(x1,y1,z1)),
    ]


def add_brush(brush, solid_id: int, next_side: int) -> tuple[str, int]:
    sides = []
    for side_id, side_plane in enumerate(brush_faces(brush["mins"], brush["maxs"]), start=next_side):
        sides.append("\n".join([
            "side", "{", f'\t"id" "{side_id}"', f'\t"plane" {kv(side_plane)}',
            f'\t"material" {kv(brush["material"])}',
            '\t"uaxis" "[1 0 0 0] 0.25"', '\t"vaxis" "[0 -1 0 0] 0.25"',
            '\t"rotation" "0"', '\t"lightmapscale" "16"', '\t"smoothing_groups" "0"',
            "}",
        ]))
    text = "\n".join(["solid", "{", f'\t"id" "{solid_id}"', *["\t" + s.replace("\n", "\n\t") for s in sides], "}"])
    return text, next_side + len(sides)


def add_entity(entity: dict, entity_id: int) -> str:
    fields = [("id", entity_id), ("classname", entity["classname"])]
    if "origin" in entity:
        fields.append(("origin", " ".join(str(v) for v in entity["origin"])))
    fields.extend(entity["keys"].items())
    lines = ["entity", "{"]
    lines.extend(f"\t{kv(k)} {kv(v)}" for k, v in fields)
    if entity.get("outputs"):
        lines.extend(["\tconnections", "\t{"])
        for output in entity["outputs"]:
            value = ",".join([
                output["target"], output["input"], output["parameter"],
                output["delay"], output["times"],
            ])
            lines.append(f"\t\t{kv(output['event'])} {kv(value)}")
        lines.append("\t}")
    lines.append("}")
    return "\n".join(lines)


def make_vmf() -> str:
    project = json.loads((SHEETS / "project.json").read_text(encoding="utf-8"))["project"]
    brushes = json.loads((SHEETS / "brushes.json").read_text(encoding="utf-8"))["brushes"]
    entities = json.loads((SHEETS / "entities.json").read_text(encoding="utf-8"))["entities"]
    arena = project["arena"]
    brush_text = []
    solid_id, side_id = 2, 1
    for brush in brushes:
        text, side_id = add_brush(brush, solid_id, side_id)
        brush_text.append(text)
        solid_id += 1
    world = "\n".join([
        "world", "{", '\t"id" "1"', '\t"mapversion" "1"',
        '\t"classname" "worldspawn"',
        f'\t"detailmaterial" "detail/detailsprites"', f'\t"detailvbsp" "detail.vbsp"',
        f'\t"maxpropscreenwidth" "-1"',
        *["\t" + b.replace("\n", "\n\t") for b in brush_text], "}",
    ])
    point_entities = [add_entity(entity, index + 1000) for index, entity in enumerate(entities)]
    header = "\n".join([
        "versioninfo", "{", '\t"editorversion" "400"', '\t"editorbuild" "0"',
        '\t"mapversion" "1"', '\t"formatversion" "100"', '\t"prefab" "0"', "}",
        "visgroups", "{", "}",
        "viewsettings", "{", '\t"bSnapToGrid" "1"', '\t"bShowGrid" "1"',
        '\t"bShow3DGrid" "0"', '\t"bGridSpacing" "64"',
        '\t"bShowLogicalGrid" "0"', '\t"nGridSpacing" "64"', "}",
    ])
    return header + "\n" + world + "\n" + "\n".join(point_entities) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT.parent.parent / "work" / "fourcorners-build" / "zf_fourcorners.vmf")
    parser.add_argument("--tf2-root", type=Path)
    parser.add_argument("--compile", action="store_true")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(make_vmf(), encoding="utf-8")
    print(f"Generated {args.output}")
    if not args.compile:
        return
    if not args.tf2_root:
        raise SystemExit("--compile needs --tf2-root")
    game_dir = args.tf2_root / "tf"
    bin_dir = args.tf2_root / "bin"
    bsp_path = args.output.with_suffix(".bsp")
    commands = [
        [bin_dir / "vbsp.exe", "-game", game_dir, args.output],
        [bin_dir / "vvis.exe", "-game", game_dir, bsp_path],
        [bin_dir / "vrad.exe", "-game", game_dir, bsp_path],
    ]
    for command in commands:
        stage = Path(command[0]).stem
        print(f"Running {stage}...")
        result = subprocess.run([str(part) for part in command], cwd=args.output.parent, capture_output=True, text=True, check=False)
        transcript = result.stdout + "\n" + result.stderr
        (args.output.parent / f"{stage}.log").write_text(transcript, encoding="utf-8", errors="replace")
        errors = [line.strip() for line in transcript.splitlines() if "*** Error:" in line or "Error:" in line]
        if result.returncode != 0 or errors:
            detail = "\n".join(errors[-8:]) if errors else transcript[-1200:]
            raise SystemExit(f"{stage} failed with code {result.returncode}:\n{detail}")
        print(f"{stage} completed cleanly.")
    if not bsp_path.is_file():
        raise SystemExit(f"Compiler reported success without producing {bsp_path}")
    print(f"Compiled {bsp_path} ({bsp_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
