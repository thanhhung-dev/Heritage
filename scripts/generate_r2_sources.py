import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from dotenv import load_dotenv
from apps.backend.core.r2 import R2Storage, FILE_TYPES, knowledge_prefix

load_dotenv(".env")

storage = R2Storage()
prefix = knowledge_prefix()

documents = []
token = None

now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

while True:
    opts = {
        "Prefix": prefix,
        "MaxKeys": 1000,
    }

    if token:
        opts["ContinuationToken"] = token

    page = storage.call("list_objects_v2", **opts)

    for obj in page.get("Contents", []):
        key = obj["Key"]
        ext = PurePosixPath(key).suffix.lower()

        if key.endswith("/") or ext not in FILE_TYPES or obj.get("Size", 0) <= 0:
            continue

        lower_key = key.lower()

        region = (
            "da_nang"
            if any(x in lower_key for x in ("da-nang", "danang", "quang-nam"))
            else "hue"
        )

        signed_url = storage.presign("get_object", key)

        documents.append({
            "url": signed_url,
            "object_key": key,
            "source_url": f"https://r2.heritagegraph.local/{key}",
            "title": PurePosixPath(key).stem.replace("-", " ").title(),
            "region": region,
            "source_type": "official",
            "tier": 1,
            "observed_at": now_iso,
        })

    if not page.get("IsTruncated"):
        break

    token = page.get("NextContinuationToken")

out_dir = Path("data/ingestion")
out_dir.mkdir(parents=True, exist_ok=True)

config = {
    "corpus_version": int(datetime.now(timezone.utc).strftime("%Y%m%d%H%M")),
    "chunking": {
        "max_chars": 2400,
        "overlap_chars": 300,
    },
    "documents": documents,
}

output = out_dir / "sources.json"

output.write_text(
    json.dumps(config, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"Đã tạo {output.resolve()}")
print(f"Tổng tài liệu: {len(documents)}")