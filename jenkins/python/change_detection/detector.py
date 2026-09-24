#!/usr/bin/env python3
"""Classify changed repository paths using the component catalog."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path


def matches(path: str, pattern: str) -> bool:
    candidates = [pattern]
    if pattern.startswith("**/"):
        candidates.append(pattern[3:])
    return any(fnmatch.fnmatchcase(path, candidate) for candidate in candidates) or (
        pattern.endswith("/**") and path == pattern[:-3]
    )


def classify(catalog: dict, paths: list[str], forced: list[str]) -> tuple[list[str], list[str]]:
    validate_catalog(catalog)
    components = catalog["components"]
    unknown_forced = sorted(set(forced) - set(components))
    if unknown_forced:
        raise ValueError(f"unknown forced component(s): {', '.join(unknown_forced)}")

    selected = set(forced)
    unmapped = []
    for path in sorted(set(paths)):
        if any(matches(path, pattern) for pattern in catalog["ignored_paths"]):
            continue
        matched = [
            name
            for name, component in components.items()
            if any(matches(path, pattern) for pattern in component["triggers"])
        ]
        if not matched:
            unmapped.append(path)
        selected.update(matched)
    return [name for name in components if name in selected], unmapped


def validate_catalog(catalog: dict) -> None:
    profiles = set(catalog["ci_profiles"])
    images = set(catalog["images"])
    units = set(catalog["deploy_units"])
    for name, component in catalog["components"].items():
        unknown_profiles = set(component["ci_profiles"]) - profiles
        unknown_images = set(component["images"]) - images
        unknown_units = set(component["deploy_units"]) - units
        if unknown_profiles or unknown_images or unknown_units:
            raise ValueError(
                f"invalid catalog references for {name}: "
                f"profiles={sorted(unknown_profiles)}, images={sorted(unknown_images)}, "
                f"deploy_units={sorted(unknown_units)}"
            )


def render_env(catalog: dict, selected: list[str]) -> str:
    profiles = []
    for name in selected:
        for profile in catalog["components"][name]["ci_profiles"]:
            if profile not in profiles:
                profiles.append(profile)
    lines = [
        f"CHANGED_COMPONENTS={','.join(selected) if selected else 'unchanged'}",
        f"CI_PROFILES={','.join(profiles) if profiles else 'unchanged'}",
    ]
    for profile in sorted({p for c in catalog["components"].values() for p in c["ci_profiles"]}):
        lines.append(f"CI_PROFILE_{profile.upper()}={'true' if profile in profiles else 'false'}")
    return "\n".join(lines) + "\n"


def changed_paths(base: str, head: str) -> list[str]:
    result = subprocess.run(
        [
            "git", "diff", "--name-status", "--find-renames", "--find-copies",
            "--diff-filter=ACDMRTUXB", base, head,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    paths = []
    for line in result.stdout.splitlines():
        status, *names = line.split("\t")
        paths.extend(names if status.startswith(("R", "C")) else names[:1])
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("head", nargs="?", default="HEAD")
    parser.add_argument(
        "--catalog",
        default=str(Path(__file__).resolve().parents[2] / "config/components.json"),
    )
    parser.add_argument("--output", default=".ci-components.env")
    parser.add_argument("--force-component", action="append", default=[])
    args = parser.parse_args()

    try:
        catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
        selected, unmapped = classify(
            catalog, changed_paths(args.base, args.head), args.force_component
        )
        if unmapped:
            raise ValueError("unmapped runtime path(s): " + ", ".join(unmapped))
        output = render_env(catalog, selected)
        Path(args.output).write_text(output, encoding="utf-8")
        sys.stdout.write(output)
    except (OSError, KeyError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"change detection failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
