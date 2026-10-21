#!/usr/bin/env python3
import json
import math
import os
import sys

if len(sys.argv) not in (2, 3, 4):
    raise SystemExit("usage: metric-gate.py REPORT [REVISION [TRAFFIC_PERCENT]]")
with open(sys.argv[1], encoding="utf-8") as source:
    metrics = json.load(source)
if not isinstance(metrics, dict):
    raise SystemExit("Metric report must be a JSON object")
if len(sys.argv) >= 3 and metrics.get("revision") != sys.argv[2]:
    raise SystemExit("Metric report does not belong to MODEL_REVISION")
if len(sys.argv) == 4 and metrics.get("traffic_percent") != int(sys.argv[3]):
    raise SystemExit("Metric report does not belong to the expected traffic level")
minimums = {key[11:].lower(): float(value) for key, value in os.environ.items() if key.startswith("METRIC_MIN_")}
maximums = {key[11:].lower(): float(value) for key, value in os.environ.items() if key.startswith("METRIC_MAX_")}
if not minimums and not maximums:
    raise SystemExit("At least one METRIC_MIN_<NAME> or METRIC_MAX_<NAME> threshold is required")
values = {}
for name in minimums.keys() | maximums.keys():
    try:
        values[name] = float(metrics[name])
    except (KeyError, TypeError, ValueError):
        raise SystemExit(f"Metric is missing or non-numeric: {name}") from None
    if not math.isfinite(values[name]):
        raise SystemExit(f"Metric is not finite: {name}")
failed = [name for name, minimum in minimums.items() if values[name] < minimum]
failed.extend(name for name, maximum in maximums.items() if values[name] > maximum)
if failed:
    raise SystemExit("Metric gate failed: " + ", ".join(sorted(failed)))
print("Metric gate passed")
