"""Seed ~30 heritage places (15 Da Nang + 15 Hue) for the homepage mock.

Run from project root with the backend venv:
  cd /mnt/d/Workspace/HeritageGraph
  apps/backend/.venv/bin/python apps/backend/db/seed_homepage_mock.py

Idempotent: existing slugs are kept, voices are keyed by name, and the
heritage_voice junction rows are upserted with sort order.
"""
from __future__ import annotations

import os

import psycopg

DB_HOST = os.environ.get("SEED_DB_HOST", "127.0.0.1")
DB_PORT = os.environ.get("SEED_DB_PORT", "5433")
DB_NAME = os.environ.get("SEED_DB_NAME", "heritagegraph")
DB_USER = os.environ.get("SEED_DB_USER", "heritagegraph")
DB_PASSWORD = os.environ.get("SEED_DB_PASSWORD", "local-only-password")

IMG = "https://picsum.photos/seed"

# (slug, title, tagline, headline, description, region, lat, lng, duration_s)
PLACES = [
    # ---------- Da Nang (15) ----------
    ("son-tra-peninsula", "Sơn Trà Peninsula", "Wild green peninsula above the bay",
     "Step into the lush nature reserve of Son Tra Peninsula.", "Home to the Linh Ung Pagoda and the majestic Lady Buddha, Son Tra is a lush nature reserve wrapped around Da Nang Bay, circling from city to sea.",
     "Đà Nẵng, Việt Nam", 16.0940, 108.2774, 1500),
    ("marble-mountains", "Ngũ Hành Sơn", "Five marble peaks between beach and river",
     "Discover caves and pagodas inside the marble mountains.", "A cluster of five marble and limestone hills bearing caves, pagodas and Buddhist sanctuaries shaped by faith and legend, standing between the city and the sea.",
     "Đà Nẵng, Việt Nam", 16.0040, 108.2630, 2700),
    ("linh-ung-pagoda", "Chùa Linh Ứng", "67-metre Lady Buddha watching the sea",
     "Stand beneath the towering white Lady Buddha of Linh Ung.", "Perched on Son Tra Peninsula, Linh Ung is Da Nang's largest pagoda and is home to the towering white Lady Buddha statue that blesses fishers at sea.",
     "Đà Nẵng, Việt Nam", 16.0994, 108.2776, 1800),
    ("my-khe-beach", "Bãi biển Mỹ Khê", "One of Vietnam's most beautiful beaches",
     "Feel the soft white sand and gentle waves of My Khe.", "Soft white sand and gentle waves along a long stretch of coast, famous worldwide for calm water, clean air and stunning sunsets.",
     "Đà Nẵng, Việt Nam", 16.0626, 108.2465, 1200),
    ("dragon-bridge", "Cầu Rồng", "A dragon-shaped landmark crossing the Han River",
     "Watch the Dragon Bridge breathe fire on weekend nights.", "A 666-metre steel dragon spanning the Han River that breathes fire and water on weekend evenings, a symbol of a modern Da Nang.",
     "Đà Nẵng, Việt Nam", 16.0612, 108.2270, 600),
    ("han-river-bridge", "Cầu Sông Hàn", "The swing bridge that lights up the river",
     "See the first swing bridge built by Vietnamese engineers.", "The first swing bridge built by Vietnamese engineers, rotating open to let ships pass under a canopy of lights after dark.",
     "Đà Nẵng, Việt Nam", 16.0663, 108.2252, 720),
    ("ba-na-hills", "Bà Nà Hills", "A hilltop French village in the clouds",
     "Ride the cable car up to the clouds at Ba Na Hills.", "A mountaintop resort reached by one of the world's longest cable car systems, famous for the Golden Bridge held by giant stone hands.",
     "Đà Nẵng, Việt Nam", 15.9951, 107.9886, 3600),
    ("golden-bridge", "Cầu Vàng", "Golden walkway held by giant hands",
     "Walk the famous Golden Bridge among the treetops.", "A 150-metre golden footbridge cradled by two colossal stone hands high above the forest canopy at Ba Na Hills.",
     "Đà Nẵng, Việt Nam", 15.9950, 107.9890, 900),
    ("son-tra-lighthouse", "Hải đăng Tiên Sa", "Guiding ships into the bay for a century",
     "Climb the century-old lighthouse over Da Nang Bay.", "A century-old lighthouse on Son Tra Peninsula offering panoramic views over Da Nang Bay and the East Sea.",
     "Đà Nẵng, Việt Nam", 16.1067, 108.2758, 1200),
    ("non-nuoc-village", "Làng đá Non Nước", "Traditional stone carving village",
     "Watch marble being shaped by Non Nuoc craftsmen.", "A centuries-old craft village at the foot of the Marble Mountains, shaping white and green marble into statues and intricate carvings.",
     "Đà Nẵng, Việt Nam", 16.0163, 108.2605, 1800),
    ("con-market", "Chợ Cồn", "Da Nang's liveliest morning market",
     "Taste the bustle of Con Market's many stalls.", "Fruit, seafood, local snacks and everyday life under one roof in the heart of Da Nang.",
     "Đà Nẵng, Việt Nam", 16.0618, 108.2129, 1500),
    ("han-market", "Chợ Hàn", "Central riverside market",
     "Browse fresh produce beside the Han River.", "A bustling riverside market selling fresh produce, dried seafood and handcrafted specialities of Da Nang.",
     "Đà Nẵng, Việt Nam", 16.0702, 108.2229, 1500),
    ("nam-o-fish-sauce", "Làng nghề nước mắm Nam Ô", "Fish sauce village by the coast",
     "Smell the salty soul of Nam O fish sauce village.", "Nam O fish sauce is fermented for over a year in clay jars, carrying the salty soul of Da Nang cuisine.",
     "Đà Nẵng, Việt Nam", 16.1116, 108.2163, 900),
    ("my-son-sanctuary", "Thánh địa Mỹ Sơn", "Ruins of the ancient Champa kingdom",
     "Wander the brick temples of the Champa civilisation.", "A cluster of red-brick Hindu sanctuaries built between the 4th and 14th centuries, a UNESCO World Heritage site near Da Nang.",
     "Đà Nẵng, Việt Nam", 15.7631, 108.1243, 3000),
    ("hai-van-pass", "Đèo Hải Vân", "The great mountain road by the sea",
     "Ride the winding coastal pass High to the clouds.", "A dramatic mountain pass running along the coast between Da Nang and Hue, offering sweeping views over Lang Co Bay and the sea.",
     "Đà Nẵng, Việt Nam", 16.1906, 108.1223, 1500),
    # ---------- Hue (15) ----------
    ("tu-duc-tomb", "Lăng Tự Đức", "An emperor's poetic retreat",
     "Step into the poetic landscape of Tu Duc Tomb.", "The most poetic of the Nguyen imperial tombs, built as a retreat where Emperor Tu Duc composed poetry among pine hills, lakes and pavilions.",
     "Huế, Việt Nam", 16.4359, 107.5652, 2400),
    ("khai-dinh-tomb", "Lăng Khải Định", "Amalgam of East and West",
     "Marvel at the glazed mosaics of Khai Dinh Tomb.", "A blend of Vietnamese, Chinese and European architecture whose interior glitters with porcelain and glass mosaics.",
     "Huế, Việt Nam", 16.3996, 107.5905, 1800),
    ("minh-mang-tomb", "Lăng Minh Mạng", "Harmony of feng-shui gardens",
     "Walk the symmetrical gardens of Minh Mang Tomb.", "The most majestic imperial tomb, laid out symmetrically between lotus lakes in a grand feng-shui garden of the Nguyen era.",
     "Huế, Việt Nam", 16.3980, 107.5640, 2100),
    ("forbidden-city", "Đại Nội Huế", "The imperial citadel of the Nguyen dynasty",
     "Enter the heart of the Nguyen imperial Citadel.", "The vast walled capital and forbidden purple city of the Nguyen emperors, a UNESCO World Heritage site of gates, palaces and gardens.",
     "Huế, Việt Nam", 16.4695, 107.5773, 3600),
    ("nine-urns", "Cửu Đỉnh", "Nine bronze urns of the emperors",
     "Study the nine bronze urns in front of the palace.", "Nine ceremonial bronze urns cast in the 19th century, each engraving the landscape and people of the Nguyen realm.",
     "Huế, Việt Nam", 16.4690, 107.5768, 900),
    ("thien-mu-pagoda", "Chùa Thiên Mụ", "The oldest pagoda on the Perfume River",
     "Ring the bell at the seven-storey Thien Mu Tower.", "A serene pagoda on the north bank of the Perfume River, crowned by the seven-storey Phuoc Duyen tower, the unofficial symbol of Hue.",
     "Huế, Việt Nam", 16.4535, 107.5450, 1500),
    ("perfume-river", "Sông Hương", "Perfume River through the ancient capital",
     "Float along the Perfume River at sunset.", "The legendary river that winds through Hue, named for the fallen flowers that perfume its waters, best seen at dusk by dragon boat.",
     "Huế, Việt Nam", 16.4700, 107.5900, 1800),
    ("trang-tien-bridge", "Cầu Tràng Tiền", "Hue's graceful bridge over the Perfume River",
     "Cross the six-arched bridge over the Perfume River.", "A graceful six-arched iron bridge built in 1899, a landmark course for photographers as it lights up with colour at night.",
     "Huế, Việt Nam", 16.4688, 107.5950, 600),
    ("dong-ba-market", "Chợ Đông Ba", "The 19th-century heart of Hue",
     "Hunt for Hue specialities at Dong Ba Market.", "Historic marketplace by the river selling conical hats, bronze castings, imperial snacks and vibrant daily life.",
     "Huế, Việt Nam", 16.4703, 107.5930, 1500),
    ("an-dinh-palace", "Cung An Định", "The palace of the last queen",
     "Admire the art-nouveau palace of the last queen.", "An elegant early-20th-century palace blending Vietnamese and art-nouveau styles, once home of the last queen of the Nguyen dynasty.",
     "Huế, Việt Nam", 16.4670, 107.5850, 900),
    ("buddha-of-hue", "Điện Hòn Chén", "Sacred shrine of the Perfume River",
     "Climb the waterfall shrine of Hon Chen temple.", "A riverside shrine built into cliffs along the Perfume River, devoted to Po Nagar and beloved for festivals on the water.",
     "Huế, Việt Nam", 16.4410, 107.5330, 1500),
    ("vong-canh-hill", "Đồi Vọng Cảnh", "A quiet hill overlooking the river",
     "Watch the river bend below Vong Canh hill.", "A quiet garden hill above the Perfume River once favoured by emperors for its sweeping view, perfect for a slow afternoon.",
     "Huế, Việt Nam", 16.4480, 107.5560, 900),
    ("gia-long-tomb", "Lăng Gia Long", "The dynastic founder's tomb",
     "Find the tomb of Gia Long in a pine forest.", "The tomb of the founder of the Nguyen dynasty, secluded in a pine forest far beyond the Perfume River.",
     "Huế, Việt Nam", 16.3790, 107.5455, 2100),
    ("thieu-tri-tomb", "Lăng Thiệu Trị", "Emperor beneficial and gentle",
     "Discover the gentle tomb of Emperor Thieu Tri.", "An imperial tomb built as retreat and resting place of the third Nguyen emperor, elegant and smaller than its royal neighbours.",
     "Huế, Việt Nam", 16.4100, 107.5710, 1500),
    ("bach-ma-national-park", "Vườn quốc gia Bạch Mã", "Mist-shrouded mountain sanctuary",
     "Hike the cloud forests of Bach Ma mountain.", "A national park south of Hue rising to a historic French hill station, home to waterfalls, cloud forests and the source rivers of the region.",
     "Huế, Việt Nam", 16.1920, 107.8600, 3600),
]


def main() -> None:
    conn = psycopg.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Language ids from the seeded language table (vi / en).
    cur.execute("SELECT id FROM language WHERE code = 'vi'")
    vi = cur.fetchone()
    cur.execute("SELECT id FROM language WHERE code = 'en'")
    eng = cur.fetchone()
    if not vi or not eng:
        raise RuntimeError("language table must have 'vi' and 'en' rows seeded first")
    vi_id, eng_id = vi[0], eng[0]

    # Reusable voices (ids 1..3 already exist from the first seed).
    voice_pool = [
        ("Nguyen Minh Anh", "Hue Heritage Guide",
         "A local heritage guide sharing stories about the monuments and cultural landscape of central Vietnam."),
        ("Dr. Tran Quoc Bao", "Historian & Heritage Researcher",
         "A researcher specialising in Nguyen dynasty history and the cultural heritage of Hue and Da Nang."),
        ("Le Thi Huong", "Local Resident & Cultural Storyteller",
         "A local storyteller sharing personal perspectives on the heritage and living culture of central Vietnam."),
    ]

    inserted, updated = 0, 0
    for row in PLACES:
        slug, title, tagline, headline, description, region, lat, lng, duration = row
        cur.execute(
            """
            SELECT id FROM heritage WHERE slug = %s
            """,
            (slug,),
        )
        existing = cur.fetchone()
        if existing:
            hid = existing[0]
            cur.execute(
                """
                UPDATE heritage SET title=%s, tagline=%s, headline=%s, description=%s,
                       region=%s, lat=%s, lng=%s, duration_seconds=%s,
                       card_image_url=%s, splash_image_url=%s, hover_video_url=%s,
                       display_map=true, publish_state='published', publish_date=CURRENT_DATE,
                       launch_date=CURRENT_DATE, updated_at=now()
                WHERE id=%s
                """,
                (title, tagline, headline, description, region, lat, lng, duration,
                 f"{IMG}/{slug}-card/800/600", f"{IMG}/{slug}-splash/1600/900",
                 None, hid),
            )
            updated += 1
        else:
            cur.execute(
                """
                INSERT INTO heritage
                    (slug, title, tagline, headline, description, region, lat, lng,
                     duration_seconds, launch_date, publish_state, publish_date,
                     card_image_url, splash_image_url, hover_video_url,
                     community_made, display_map, presented_by_logo_url,
                     language1_id, language2_id, created_at, updated_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_DATE, 'published', CURRENT_DATE,
                     %s, %s, NULL, false, true, NULL, %s, %s, now(), now())
                RETURNING id
                """,
                (slug, title, tagline, headline, description, region, lat, lng, duration,
                 f"{IMG}/{slug}-card/800/600", f"{IMG}/{slug}-splash/1600/900",
                 vi_id, eng_id),
            )
            hid = cur.fetchone()[0]
            inserted += 1

        # Link the same voice pool to this heritage through the junction table.
        # Idempotent: voices are keyed by name, heritage_voice upserts on (heritage_id, voice_id).
        voice_ids = []
        for name, vtitle, bio in voice_pool:
            cur.execute(
                "SELECT id FROM voice WHERE name = %s",
                (name,),
            )
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE voice SET title = %s, bio = %s WHERE id = %s",
                    (vtitle, bio, row[0]),
                )
                voice_ids.append(row[0])
            else:
                cur.execute(
                    """
                    INSERT INTO voice (name, title, bio, created_at)
                    VALUES (%s, %s, %s, now())
                    RETURNING id
                    """,
                    (name, vtitle, bio),
                )
                voice_ids.append(cur.fetchone()[0])

        cur.executemany(
            """
            INSERT INTO heritage_voice (heritage_id, voice_id, sort_order, created_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (heritage_id, voice_id) DO UPDATE
               SET sort_order = EXCLUDED.sort_order
            """,
            [(hid, vid, i) for i, vid in enumerate(voice_ids)],
        )

    # Remove legacy mock slugs superseded by renamed rows.
    stale_slugs = ["mue-lin", "vong-canh", "tomb-gia-long", "tomb-thieu-tri"]
    cur.execute(
        "DELETE FROM heritage WHERE slug = ANY(%s)",
        (stale_slugs,),
    )

    cur.close()
    conn.close()
    print(f"Seed complete: +{inserted} inserted, {updated} updated, 30 places total")


if __name__ == "__main__":
    main()