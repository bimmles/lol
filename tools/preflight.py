#!/usr/bin/env python3
"""Check the JSON design sheets before generating a Source map."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEETS = ROOT / "sheets"
REQUIRED_OUTPUTS = {
    "team_round_timer": {
        "OnSetupFinished", "On3MinRemain", "On1MinRemain", "OnFinished"
    },
    "logic_auto": {"OnMapSpawn"},
}
KNOWN_INPUTS = {
    "tf_zombie_spawner": {"Enable", "Disable", "SetMaxActiveZombies"},
    "ambient_generic": {"PlaySound"},
    "game_round_win": {"RoundWin"},
}


def load(name: str) -> dict:
    return json.loads((SHEETS / name).read_text(encoding="utf-8"))


def complete(value, where: str, errors: list[str], empty_ok: bool = False) -> None:
    if value is None or value == "":
        if not empty_ok:
            errors.append(f"unfilled cell: {where}")
    elif isinstance(value, dict):
        for key, child in value.items():
            complete(child, f"{where}.{key}", errors, empty_ok=(key == "parameter"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            complete(child, f"{where}[{index}]", errors)


def check_materials(tf_root: Path, errors: list[str]) -> None:
    vpk = tf_root / "bin" / "vpk.exe"
    archives = [tf_root / "tf" / "tf2_misc_dir.vpk"]
    wanted = {
        "materials/concrete/concretefloor002.vmt",
        "materials/brick/brickwall001.vmt",
        "materials/brick/brickwall002.vmt",
    }
    if not vpk.exists():
        errors.append(f"missing TF2 VPK reader: {vpk}")
        return
    for archive in archives:
        if not archive.exists():
            errors.append(f"missing stock TF2 archive: {archive}")
            continue
        result = subprocess.run([str(vpk), "l", str(archive)], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f"could not inspect stock TF2 archive: {archive}")
            continue
        actual = set(result.stdout.replace("\\", "/").splitlines())
        for path in sorted(wanted - actual):
            errors.append(f"stock material reference does not resolve: {path}")


def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tf2-root", type=Path)
    parser.add_argument("--l4d2-root", type=Path)
    args = parser.parse_args()
    errors: list[str] = []

    project = load("project.json")
    brushes = load("brushes.json")["brushes"]
    entities = load("entities.json")["entities"]
    systems = load("systems.json")["systems"]
    launch = load("launch.json")["launch"]
    validation = load("validation.json")

    for filename, data in (
        ("project.json", project), ("brushes.json", brushes),
        ("entities.json", entities), ("systems.json", systems),
        ("launch.json", launch), ("validation.json", validation),
    ):
        complete(data, filename, errors)

    if not brushes:
        errors.append("brushes sheet has no rows")
    if not entities:
        errors.append("entities sheet has no rows")
    for sheet_name, rows in (("brushes", brushes), ("entities", entities), ("systems", systems)):
        ids = [row.get("id") for row in rows]
        if len(ids) != len(set(ids)):
            errors.append(f"duplicate row id in {sheet_name}.json")

    names: dict[str, str] = {}
    for entity in entities:
        name = entity.get("keys", {}).get("targetname")
        if name:
            if name in names:
                errors.append(f"duplicate targetname: {name}")
            names[name] = entity.get("classname", "")

    for entity in entities:
        classname = entity.get("classname", "")
        for output in entity.get("outputs", []):
            target = output.get("target", "")
            if target not in names:
                errors.append(f"unresolved entity reference: {entity.get('id')} -> {target}")
            if output.get("event") not in REQUIRED_OUTPUTS.get(classname, set()):
                errors.append(f"unverified output for {classname}: {output.get('event')}")
            target_class = names.get(target, "")
            if output.get("input") not in KNOWN_INPUTS.get(target_class, set()):
                errors.append(f"unverified input link: {target_class}.{output.get('input')} ({target})")

    max_players = project["project"]["arena"]["maxPlayers"]
    if max_players != 4:
        errors.append(f"player-capacity sheet disagrees with the user's four-player choice: {max_players}")
    if launch["hostGame"] != project["project"]["hostGame"]:
        errors.append("launch host does not match the project host")
    if launch["requiredSourceGame"] not in [g["slug"] for g in project["project"]["requiredGames"]]:
        errors.append("launcher source game is not declared as a required game")
    if launch["sourceAsset"] != project["project"]["requiredGames"][1]["sourceRelativePath"]:
        errors.append("launcher audio path does not match the required-game sheet")
    if launch["sourceFileRedistributed"] is not False:
        errors.append("Valve audio must not be included in the package")
    if launch["meltyArguments"] != ["--tf2-root", "{game}"]:
        errors.append("launcher must receive the TF2 folder from Melty")
    if "-insecure" not in launch["launchArguments"]:
        errors.append("private test and launch recipe must use TF2's -insecure option")
    if launch["mapName"] not in launch["launchArguments"]:
        errors.append("launch arguments do not start the map listed in the project sheet")
    if launch["entrySource"] != "launcher/FourCornersLauncher.cs" or not (ROOT / launch["entrySource"]).is_file():
        errors.append("companion launcher source does not resolve")

    if args.tf2_root:
        check_materials(args.tf2_root, errors)
        for executable in ("bin/vbsp.exe", "bin/vvis.exe", "bin/vrad.exe", "bin/vpk.exe", "tf/gameinfo.txt"):
            if not (args.tf2_root / executable).exists():
                errors.append(f"missing TF2 build/runtime input: {args.tf2_root / executable}")
    if args.l4d2_root:
        cue = args.l4d2_root / "left4dead2" / "sound" / "music" / "zombat" / "snare_horde_01_01a.wav"
        if not cue.is_file():
            errors.append(f"required player-owned L4D2 cue does not resolve: {cue}")

    if errors:
        print("PREFLIGHT: NOT CLEAN")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"PREFLIGHT: CLEAN — {len(brushes)} brush rows, {len(entities)} entity rows, {len(systems)} system rows; all sheet cells populated and entity links resolve.")
    if args.tf2_root:
        print("- TF2 tools, map gameinfo, and referenced stock materials resolve.")
    if args.l4d2_root:
        print("- Player-owned L4D2 horde cue resolves; it is not an upload entry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
