"""Seed a scene skeleton for every heritage place that has none.

Why
---
The tour page (`/content/{slug}/s0…sN`) renders entirely from
``GET /api/heritages/{slug}/tour``. A place with zero rows in ``scene`` still
returns a payload, but the UI has nothing to navigate, so it silently falls back
to the embedded demo tour. ``lang-tu-duc`` already has 5 authored scenes; the 29
places added by ``seed_heritage_places.py`` had none.

This script gives each of those places a *skeleton* tour built only from text
that already exists in the row — no invented facts:

    -1  Toàn cảnh {title}          ← ``headline`` (fallback ``tagline``)
     0… one scene per sentence    ← ``description``, split on sentence breaks;
                                     the title is the leading clause of that
                                     sentence, so it is always supported by the
                                     text underneath
     +1  Lễ hội và tín ngưỡng      ← only for the 8 festival-linked places,
                                     text taken from ``FESTIVAL_NOTES``
     +1  Thông tin tham quan       ← ``region`` / ``lat`` / ``lng`` /
                                     ``duration_seconds``

Camera, sky preset and model assets are left NULL on purpose: the 3D model is
uploaded to R2 later, and the viewer already self-frames via
``camera-controller.fit()``. Adding a ``model_asset`` row now would make the tour
try to load a URL that does not exist yet.

Run from the project root:
    apps/backend/.venv/bin/python apps/backend/db/seed_heritage_scenes.py --dry-run
    apps/backend/.venv/bin/python apps/backend/db/seed_heritage_scenes.py

Idempotent: places that already have at least one scene are skipped, so
``lang-tu-duc`` and any hand-authored tour are never touched.
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import psycopg

DB_HOST = os.environ.get("SEED_DB_HOST", "127.0.0.1")
DB_PORT = os.environ.get("SEED_DB_PORT", "5433")
DB_NAME = os.environ.get("SEED_DB_NAME", "heritagegraph")
DB_USER = os.environ.get("SEED_DB_USER", "heritagegraph")

# Structural scene headings — these describe the *shape* of the tour, not the
# monument, so they are safe to apply to every place.
OVERVIEW_TITLE = "Toàn cảnh {title}"
FESTIVAL_TITLE = "Lễ hội và tín ngưỡng"
VISIT_TITLE = "Thông tin tham quan"

MAX_TITLE_CHARS = 72
MIN_TITLE_CHARS = 18

# Clause openers that carry no subject (time/place/manner adverbials). A scene
# heading that starts with one of these reads like a dangling fragment —
# "Vào cuối tuần", "Trải qua nhiều lần trùng tu" — so the next clause is used.
WEAK_OPENERS = {
    "vào", "từ", "sau", "trước", "trong", "ngoài", "trên", "dưới", "giữa",
    "trải", "nhờ", "với", "do", "bởi", "khi", "nếu", "theo", "cùng", "qua",
    "hiện", "ngày", "đến", "mỗi",
}


def load_env() -> dict[str, str]:
    """Read POSTGRES_* from the repo .env so the password is never hardcoded."""
    env: dict[str, str] = {}
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def festival_notes() -> dict[str, str]:
    """Reuse the catalogue notes from ``seed_heritage_places`` instead of copying."""
    try:  # run as a script: sys.path[0] is this directory
        from seed_heritage_places import FESTIVAL_NOTES  # type: ignore
    except ImportError:  # imported as a package module
        from apps.backend.db.seed_heritage_places import (  # type: ignore
            FESTIVAL_NOTES,
        )
    return FESTIVAL_NOTES


def split_sentences(text: str | None) -> list[str]:
    """Split Vietnamese prose into sentences, keeping the terminal punctuation.

    Descriptions in the seed are short (2–3 sentences) and free of abbreviations,
    so a lookbehind on ``.!?`` followed by whitespace is enough.
    """
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    return [part.strip() for part in parts if part.strip()]


def scene_title(sentence: str) -> str:
    """Leading clause of a sentence, used as the scene heading.

    Cutting at the first comma keeps the heading close to the text it introduces
    (``Lăng của vua Minh Mạng (trị vì 1820–1841), khởi công…`` →
    ``Lăng của vua Minh Mạng``). Clauses that open on an adverbial (see
    ``WEAK_OPENERS``) or are too short to read as a heading are skipped, so
    ``Vào cuối tuần, cầu phun lửa…`` becomes ``Cầu phun lửa…`` instead of the
    dangling ``Vào cuối tuần``.
    """
    for clause in re.split(r"[,;:]", sentence):
        head = clause.strip().rstrip(".")
        if not head:
            continue
        first_word = head.split(maxsplit=1)[0].lower()
        if first_word in WEAK_OPENERS or len(head) < MIN_TITLE_CHARS:
            continue
        if len(head) > MAX_TITLE_CHARS:
            head = head[: MAX_TITLE_CHARS - 1].rstrip() + "…"
        return head[0].upper() + head[1:]
    # Everything looked weak — fall back to the sentence itself.
    head = sentence.strip().rstrip(".")
    if len(head) > MAX_TITLE_CHARS:
        head = head[: MAX_TITLE_CHARS - 1].rstrip() + "…"
    return head


def visit_description(row: dict) -> str:
    """Coordinates + suggested tour length, straight from the heritage row."""
    bits = [f"{row['title']} thuộc {row['region']}."] if row["region"] else []
    if row["lat"] is not None and row["lng"] is not None:
        bits.append(f"Toạ độ {row['lat']:.5f}, {row['lng']:.5f}.")
    seconds = row["duration_seconds"]
    if seconds:
        bits.append(f"Thời lượng tour gợi ý khoảng {max(1, round(seconds / 60))} phút.")
    return " ".join(bits)


def build_scenes(row: dict, notes: dict[str, str]) -> list[tuple[int, str, str | None]]:
    """Return ``(sequence, title, description)`` rows for one heritage."""
    scenes: list[tuple[int, str, str | None]] = []

    overview = row["headline"] or row["tagline"]
    scenes.append((-1, OVERVIEW_TITLE.format(title=row["title"]), overview))

    for index, sentence in enumerate(split_sentences(row["description"])):
        scenes.append((index, scene_title(sentence), sentence))

    note = notes.get(row["slug"])
    if note:
        scenes.append((len(scenes) - 1, FESTIVAL_TITLE, f"{note[0].upper()}{note[1:]}."))

    scenes.append((len(scenes) - 1, VISIT_TITLE, visit_description(row) or None))
    return scenes


def fetch_places_without_scenes(cur) -> list[dict]:
    cur.execute(
        """
        SELECT h.id, h.slug, h.title, h.tagline, h.headline, h.description,
               h.region, h.lat, h.lng, h.duration_seconds
        FROM heritage h
        WHERE h.publish_state = 'published'
          AND NOT EXISTS (SELECT 1 FROM scene s WHERE s.heritage_id = h.id)
        ORDER BY h.slug
        """
    )
    columns = [c.name for c in cur.description]
    return [dict(zip(columns, record)) for record in cur.fetchall()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the scenes that would be inserted, then roll back",
    )
    args = parser.parse_args()

    env = load_env()
    notes = festival_notes()
    conn = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=env.get("POSTGRES_DB", DB_NAME),
        user=env.get("POSTGRES_USER", DB_USER),
        password=env.get("POSTGRES_PASSWORD", ""),
    )
    conn.autocommit = False
    cur = conn.cursor()

    places = fetch_places_without_scenes(cur)
    if not places:
        print("Nothing to do: every published heritage already has scenes.")
        cur.close()
        conn.close()
        return

    inserted = 0
    for row in places:
        scenes = build_scenes(row, notes)
        for sequence, title, description in scenes:
            cur.execute(
                """
                INSERT INTO scene (heritage_id, sequence, title, description)
                VALUES (%s, %s, %s, %s)
                """,
                (row["id"], sequence, title, description),
            )
            inserted += 1
        if args.dry_run:
            print(f"{row['slug']}  ({len(scenes)} scenes)")
            for sequence, title, _ in scenes:
                print(f"    s{sequence + 1:<3} {title}")

    if args.dry_run:
        conn.rollback()
        print(f"\nDRY RUN: would insert {inserted} scenes across {len(places)} places.")
    else:
        conn.commit()
        print(f"Inserted {inserted} scenes across {len(places)} places.")

    cur.execute("SELECT count(*) FROM scene")
    print(f"scene total={cur.fetchone()[0]}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
