#!/usr/bin/env python3
"""Remove Terraform variable values and redact values marked sensitive."""

import json
import sys
from typing import Any


def apply_mask(value: Any, mask: Any) -> Any:
    if mask is True:
        return "<sensitive>"
    if isinstance(value, dict) and isinstance(mask, dict):
        return {key: apply_mask(item, mask.get(key)) for key, item in value.items()}
    if isinstance(value, list) and isinstance(mask, list):
        return [apply_mask(item, mask[index] if index < len(mask) else None) for index, item in enumerate(value)]
    return value


def redact(node: Any) -> Any:
    if isinstance(node, list):
        return [redact(item) for item in node]
    if not isinstance(node, dict):
        return node

    result = {
        key: redact(value)
        for key, value in node.items()
        if key not in {"configuration", "variables", "sensitive_values"}
        and not key.endswith("_sensitive")
    }
    pairs = (("values", "sensitive_values"), ("before", "before_sensitive"), ("after", "after_sensitive"), ("after_unknown", "after_sensitive"))
    for value_key, mask_key in pairs:
        if value_key in result and mask_key in node:
            result[value_key] = redact(apply_mask(result[value_key], node[mask_key]))
    return result


if len(sys.argv) != 3:
    raise SystemExit("usage: redact-terraform-plan.py INPUT OUTPUT")
with open(sys.argv[1], encoding="utf-8") as source:
    plan = json.load(source)
with open(sys.argv[2], "w", encoding="utf-8") as destination:
    json.dump(redact(plan), destination, indent=2, sort_keys=True)
    destination.write("\n")
