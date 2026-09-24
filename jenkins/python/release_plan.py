#!/usr/bin/env python3
"""Create an affected-only software release plan from detector output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .change_detection.detector import validate_catalog
except ImportError:
    from change_detection.detector import validate_catalog


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def build_plan(catalog: dict, components: list[str]) -> dict:
    validate_catalog(catalog)
    known = catalog["components"]
    unknown = sorted(set(components) - set(known))
    if unknown:
        raise ValueError(f"unknown component(s): {', '.join(unknown)}")
    ordered = [name for name in known if name in components]
    images = unique([item for name in ordered for item in known[name]["images"]])
    selected_units = {item for name in ordered for item in known[name]["deploy_units"]}
    units = [item for item in catalog["deploy_units"] if item in selected_units]
    return {"components": ordered, "images": images, "deploy_units": units}


def read_components(path: Path) -> list[str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    changed = values.get("CHANGED_COMPONENTS", "")
    return [] if changed in ("", "unchanged") else changed.split(",")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="jenkins/config/components.json")
    parser.add_argument("--components-env", default=".ci-components.env")
    parser.add_argument("--output", default=".ci-release-plan.json")
    parser.add_argument("--env-output", default=".ci-release.env")
    args = parser.parse_args()
    try:
        catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
        plan = build_plan(catalog, read_components(Path(args.components_env)))
        Path(args.output).write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        Path(args.env_output).write_text(
            "RELEASE_IMAGES=" + ",".join(plan["images"]) + "\n"
            "DEPLOY_UNITS=" + ",".join(plan["deploy_units"]) + "\n"
            "HAS_RELEASE=" + ("true" if plan["images"] or plan["deploy_units"] else "false") + "\n",
            encoding="utf-8",
        )
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
