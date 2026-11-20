"""Read-only R2 connectivity smoke check. Never writes, signs URLs or deletes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from fastapi import HTTPException

from apps.backend.core.r2_library import KnowledgeR2
from apps.backend.services.knowledge_policy import root_prefix


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    storage = None
    try:
        storage = KnowledgeR2()
        root = storage.list_objects(root_prefix(), limit=20)
        print(f"PASS fixed bucket listing: {len(root['folders'])} folders, {len(root['files'])} files on first page; "
              f"has_next_page={root['nextContinuationToken'] is not None}")
        page, files, depth = root, root["files"], 0
        # Follow only the first returned folder at each level, at most eight
        # levels. No recursive inventory and no assumptions about folder names.
        while not files and page["folders"] and depth < 8:
            page = storage.list_objects(page["folders"][0]["prefix"], limit=20)
            depth += 1
            print(f"PASS nested listing depth={depth}: {len(page['folders'])} folders, {len(page['files'])} files on first page")
            files = page["files"]
        if depth == 0:
            print("SKIPPED nested listing: no folder on the first root page")
        if files:
            metadata = storage.object_info(files[0]["key"])
            print(f"PASS real HEAD: size={metadata['size']}; etag_present={bool(metadata['etag'])}")
        else:
            print("SKIPPED HEAD: no file within the bounded inspection path")
        print("Read-only operations completed. No object names, credentials or URLs printed.")
        return 0
    except HTTPException as error:
        print(f"FAIL read-only R2 verification: HTTP {error.status_code}; {error.detail}")
        return 1
    finally:
        if storage:
            storage.client.close()


if __name__ == "__main__":
    raise SystemExit(main())
