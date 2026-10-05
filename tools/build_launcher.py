#!/usr/bin/env python3
"""Generate launcher settings from launch.json and compile the companion app."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEETS = ROOT / "sheets"


def cs_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def generate_config(config: dict) -> str:
    values = {
        "HostAppId": config["hostAppId"],
        "SourceAppId": config["sourceAppId"],
        "SourceRelativeAsset": config["sourceAsset"],
        "ModDirectory": config["modDirectory"],
        "CueRelativeDestination": config["cueDestinationRelativePath"],
        "MapName": config["mapName"],
    }
    lines = ["internal static class LaunchConfig", "{"]
    for key, value in values.items():
        lines.append("    internal const string " + key + " = " + cs_string(value) + ";")
    lines.append("    internal static readonly string[] GameArguments = new string[] { " + ", ".join(cs_string(v) for v in config["launchArguments"]) + " };")
    lines.extend(["}", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csc", type=Path, default=Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"))
    parser.add_argument("--output-dir", type=Path, default=ROOT.parent.parent / "work" / "fourcorners-build")
    args = parser.parse_args()
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = json.loads((SHEETS / "launch.json").read_text(encoding="utf-8"))["launch"]
    generated = args.output_dir / "LaunchConfig.cs"
    generated.write_text(generate_config(config), encoding="utf-8")
    source = ROOT / "launcher" / "FourCornersLauncher.cs"
    output = args.output_dir / "FourCornersLauncher.exe"
    command = [str(args.csc), "/noconfig", "/target:winexe", "/out:" + str(output), "/reference:System.dll", "/reference:System.Windows.Forms.dll", "/reference:System.Core.dll", str(source), str(generated)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit("Companion launcher compilation failed.")
    print("Compiled companion launcher:", output, "(", output.stat().st_size, "bytes )")


if __name__ == "__main__":
    main()
